"""
Validation session API endpoints.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from ..database import get_db
from app.models import User, ValidationSession, SessionStatus
from ..schemas import (
    ValidationSessionCreate, ValidationSessionResponse,
    ValidationSessionDetail, ValidationSessionSummary,
    ReportDownloadResponse, DocumentUploadUrl
)
from ..core.security import get_current_user, ensure_owner_or_privileged
from ..core.rbac import RBACPolicyEngine, Permission
from ..services import ValidationSessionService, ReportService, S3Service
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult
from ..middleware.audit_middleware import get_correlation_id, create_audit_context

router = APIRouter(prefix="/sessions", tags=["validation-sessions"])


@router.post("", response_model=ValidationSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_validation_session(
    session_data: ValidationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new validation session and return pre-signed upload URLs."""
    # Check permission to create sessions
    if not RBACPolicyEngine.has_permission(current_user.role, Permission.CREATE_JOBS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create sessions"
        )

    session_service = ValidationSessionService(db)
    s3_service = S3Service()
    
    # Create validation session
    session = session_service.create_session(current_user)
    
    # Generate pre-signed upload URLs for all document types
    upload_urls = s3_service.generate_upload_urls(session.id)
    
    return ValidationSessionResponse(
        session_id=session.id,
        status=session.status,
        upload_urls=upload_urls,
        created_at=session.created_at
    )


@router.get("", response_model=List[ValidationSessionSummary])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all validation sessions for the current user."""
    # Check permission
    if not RBACPolicyEngine.has_permission(current_user.role, Permission.VIEW_OWN_JOBS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view sessions"
        )

    session_service = ValidationSessionService(db)

    # Get sessions based on role
    if current_user.role in ["bank", "admin"]:
        # Privileged roles can see all sessions
        sessions = session_service.get_all_sessions()
    else:
        # Regular users see only their own sessions
        sessions = session_service.get_user_sessions(current_user)
    
    # Convert to summary format
    session_summaries = []
    for session in sessions:
        total_documents = len(session.documents)
        total_discrepancies = len(session.discrepancies)
        critical_discrepancies = len([
            d for d in session.discrepancies 
            if d.severity == "critical"
        ])
        
        session_summaries.append(ValidationSessionSummary(
            id=session.id,
            status=session.status,
            created_at=session.created_at,
            total_documents=total_documents,
            total_discrepancies=total_discrepancies,
            critical_discrepancies=critical_discrepancies
        ))
    
    return session_summaries


@router.get("/{session_id}", response_model=ValidationSessionDetail)
async def get_session_detail(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific validation session."""

    session_service = ValidationSessionService(db)
    session = session_service.get_session_by_id(session_id)  # Get session first

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found"
        )

    # Check access permissions
    if not RBACPolicyEngine.can_access_resource(
        user_role=current_user.role,
        resource_owner_id=str(session.user_id),
        user_id=str(current_user.id),
        permission=Permission.VIEW_OWN_JOBS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )

    return ValidationSessionDetail.from_orm(session)


@router.get("/{session_id}/report", response_model=ReportDownloadResponse)
async def get_session_report(
    session_id: UUID,
    request: Request,
    languages: Optional[str] = Query(None, description="Comma-separated language codes (e.g., 'en,bn')"),
    report_mode: str = Query("single", description="Report mode: 'single', 'bilingual', or 'parallel'"),
    regenerate: bool = Query(False, description="Force regenerate report with new language settings"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get download URL for the session's validation report."""

    audit_service = AuditService(db)
    audit_context = create_audit_context(request)

    session_service = ValidationSessionService(db)
    report_service = ReportService(db)

    # Verify session exists
    session = session_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found"
        )

    # Check access permissions
    if not RBACPolicyEngine.can_access_resource(
        user_role=current_user.role,
        resource_owner_id=str(session.user_id),
        user_id=str(current_user.id),
        permission=Permission.DOWNLOAD_OWN_EVIDENCE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to download this report"
        )
    
    # Check if session is completed
    if session.status != SessionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation session not completed"
        )
    
    # Determine requested languages
    if languages:
        requested_languages = languages
    else:
        # Use company's preferred language + English as default
        company_lang = current_user.company.preferred_language.value if current_user.company else "en"
        requested_languages = f"en,{company_lang}" if company_lang != "en" else "en"

    # Get existing report if not forcing regeneration
    report = None
    if not regenerate:
        report = report_service.get_latest_report(session)

        # Check if existing report matches requested languages and mode
        if report and report.metadata:
            existing_languages = report.metadata.get("languages", ["en"])
            existing_mode = report.metadata.get("report_mode", "single")

            # If languages or mode don't match, regenerate
            if (set(existing_languages) != set(requested_languages.split(",")) or
                existing_mode != report_mode):
                report = None

    # Generate new report if needed
    if not report:
        try:
            report = await report_service.generate_report(
                session=session,
                user=current_user,
                languages=requested_languages,
                report_mode=report_mode
            )

            # Log report generation
            audit_service.log_action(
                user=current_user,
                action="generate_report",
                resource_type="validation_report",
                resource_id=str(report.id),
                lc_number=getattr(session, 'lc_number', None),
                correlation_id=audit_context['correlation_id'],
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                result=AuditResult.SUCCESS,
                details={
                    "languages": requested_languages,
                    "report_mode": report_mode,
                    "session_id": str(session_id)
                }
            )

        except Exception as e:
            # Log error
            audit_service.log_action(
                user=current_user,
                action="generate_report",
                resource_type="validation_report",
                resource_id=str(session_id),
                correlation_id=audit_context['correlation_id'],
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                result=AuditResult.FAILURE,
                error_message=str(e)
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate report: {str(e)}"
            )

    # Generate download URL
    download_url = report_service.generate_download_url(report)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Log download action
    audit_service.log_download(
        user=current_user,
        resource_id=str(report.id),
        resource_type="validation_report",
        lc_number=getattr(session, 'lc_number', None),
        correlation_id=audit_context['correlation_id'],
        ip_address=audit_context['ip_address'],
        user_agent=audit_context['user_agent'],
        result=AuditResult.SUCCESS
    )

    return ReportDownloadResponse(
        download_url=download_url,
        expires_at=expires_at,
        report_info=report
    )


@router.post("/{session_id}/process")
async def start_session_processing(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start processing a validation session (trigger OCR and validation)."""

    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    start_time = time.time()

    session_service = ValidationSessionService(db)
    session = session_service.get_session_by_id(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found"
        )

    # Check access permissions
    if not RBACPolicyEngine.can_access_resource(
        user_role=current_user.role,
        resource_owner_id=str(session.user_id),
        user_id=str(current_user.id),
        permission=Permission.VIEW_OWN_JOBS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to process this session"
        )
    
    # Check if session is in correct state
    if session.status not in [SessionStatus.CREATED.value, SessionStatus.UPLOADING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session cannot be processed in current state"
        )
    
    # Update status to processing
    session = session_service.update_session_status(session, SessionStatus.PROCESSING)
    
    # In stub mode, process documents immediately
    from ..config import settings
    if settings.USE_STUBS:
        # Process documents synchronously in stub mode
        from ..services import DocumentProcessingService
        processing_service = DocumentProcessingService(db)
        
        try:
            await processing_service.process_documents(session)
            session_service.update_session_status(session, SessionStatus.COMPLETED)

            # Log successful validation
            duration_ms = int((time.time() - start_time) * 1000)
            audit_service.log_validation(
                user=current_user,
                validation_session_id=str(session_id),
                lc_number=getattr(session, 'lc_number', None),
                discrepancy_count=len(session.discrepancies),
                correlation_id=audit_context['correlation_id'],
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                duration_ms=duration_ms,
                result=AuditResult.SUCCESS
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            session_service.update_session_status(session, SessionStatus.FAILED)

            # Log failed validation
            duration_ms = int((time.time() - start_time) * 1000)
            audit_service.log_validation(
                user=current_user,
                validation_session_id=str(session_id),
                lc_number=getattr(session, 'lc_number', None),
                correlation_id=audit_context['correlation_id'],
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                duration_ms=duration_ms,
                result=AuditResult.ERROR,
                error_message=str(e)
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Processing failed: {str(e)}"
            )
    else:
        # TODO: Queue OCR and validation processing
        # This would typically send a message to SQS to trigger async processing

        # Log async processing start
        audit_service.log_validation(
            user=current_user,
            validation_session_id=str(session_id),
            lc_number=getattr(session, 'lc_number', None),
            correlation_id=audit_context['correlation_id'],
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            result=AuditResult.SUCCESS,
            audit_metadata={"processing_mode": "async"}
        )

    return {"message": "Processing started", "session_id": session_id}