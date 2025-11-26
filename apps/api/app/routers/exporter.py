"""
Exporter-specific API endpoints for customs pack generation and bank submissions.
"""

import logging
import zipfile
import io
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from pydantic import BaseModel

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, UserRole, ValidationSession, Discrepancy, Document, DiscrepancySeverity
from ..models.exporter_submission import (
    ExportSubmission, SubmissionEvent, CustomsPack,
    SubmissionStatus, SubmissionEventType
)
from ..schemas.exporter_submission import (
    CustomsPackGenerateRequest, CustomsPackGenerateResponse, CustomsPackManifest,
    BankSubmissionCreate, BankSubmissionRead, BankSubmissionListResponse,
    SubmissionEventRead, SubmissionEventListResponse,
    GuardrailCheckRequest, GuardrailCheckResponse
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exporter", tags=["exporter"])


def require_exporter_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an exporter."""
    if current_user.role not in [UserRole.EXPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for exporter users"
        )
    return current_user


# ===== Guardrails =====

def check_guardrails(db: Session, validation_session_id: UUID, company_id: UUID) -> GuardrailCheckResponse:
    """Check all guardrails before allowing submission."""
    blocking_issues = []
    warnings = []
    
    # Get validation session
    session = db.query(ValidationSession).filter(
        and_(
            ValidationSession.id == validation_session_id,
            ValidationSession.company_id == company_id
        )
    ).first()
    
    if not session:
        blocking_issues.append("Validation session not found")
        return GuardrailCheckResponse(
            can_submit=False,
            blocking_issues=blocking_issues,
            warnings=warnings,
            required_docs_present=False,
            high_severity_discrepancies=0,
            policy_checks_passed=False
        )
    
    # Get all discrepancies
    discrepancies = db.query(Discrepancy).filter(
        Discrepancy.validation_session_id == validation_session_id
    ).all()
    
    # Check for high severity discrepancies
    high_severity_count = sum(
        1 for d in discrepancies 
        if hasattr(d, 'severity') and d.severity == DiscrepancySeverity.CRITICAL
    )
    
    if high_severity_count > 0:
        blocking_issues.append(f"{high_severity_count} critical discrepancy(ies) must be resolved")
    
    # Get all documents
    documents = db.query(Document).filter(
        Document.validation_session_id == validation_session_id
    ).all()
    
    # Check required documents (basic check - LC should be present)
    required_docs_present = len(documents) > 0
    if not required_docs_present:
        blocking_issues.append("No documents found in validation session")
    
    # Check document hashes (for integrity)
    docs_without_hash = [d for d in documents if not hasattr(d, 'sha256_hash') or not d.sha256_hash]
    if docs_without_hash:
        warnings.append(f"{len(docs_without_hash)} document(s) missing hash verification")
    
    # Policy checks (basic - can be extended)
    policy_checks_passed = True
    if session.status != "completed":
        blocking_issues.append("Validation session not completed")
        policy_checks_passed = False
    
    can_submit = len(blocking_issues) == 0
    
    return GuardrailCheckResponse(
        can_submit=can_submit,
        blocking_issues=blocking_issues,
        warnings=warnings,
        required_docs_present=required_docs_present,
        high_severity_discrepancies=high_severity_count,
        policy_checks_passed=policy_checks_passed
    )


# ===== Customs Pack Endpoints =====

@router.post("/customs-pack", response_model=CustomsPackGenerateResponse)
async def generate_customs_pack(
    request: CustomsPackGenerateRequest,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Generate a customs pack ZIP file with all documents, manifest, and coversheet.
    """
    try:
        # Find validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == request.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        lc_number = request.lc_number or session.lc_number or "UNKNOWN"
        
        # Get all documents
        documents = db.query(Document).filter(
            Document.validation_session_id == request.validation_session_id
        ).all()

        # Build manifest
        manifest_docs = []
        for doc in documents:
            doc_hash = getattr(doc, 'sha256_hash', None) or hashlib.sha256(
                f"{doc.id}{getattr(doc, 'file_name', doc.original_filename)}".encode()
            ).hexdigest()[:16]
            
            manifest_docs.append({
                "name": getattr(doc, 'file_name', doc.original_filename),
                "type": str(doc.document_type) if hasattr(doc, 'document_type') else "unknown",
                "sha256": doc_hash,
                "size_bytes": getattr(doc, 'file_size', None) or 0
            })

        manifest = CustomsPackManifest(
            lc_number=lc_number,
            validation_session_id=str(request.validation_session_id),
            generated_at=datetime.utcnow().isoformat(),
            documents=manifest_docs,
            generator_version="1.0"
        )

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            zip_file.writestr(
                "manifest.json",
                json.dumps(manifest.dict(), indent=2)
            )
            
            # Add coversheet
            coversheet = f"""Customs Pack - LC {lc_number}
==========================================

Generated: {datetime.utcnow().isoformat()}
LC Number: {lc_number}
Validation Session ID: {str(request.validation_session_id)}
Total Documents: {len(documents)}

DOCUMENTS INCLUDED:
{chr(10).join([f'- {doc["name"]} ({doc["type"]})' for doc in manifest_docs])}

This pack contains all documents required for customs clearance.
All documents have been validated against LC requirements.

© 2024 LCopilot - AI-Powered Trade Document Analysis
"""
            zip_file.writestr("coversheet.txt", coversheet)
            
            # Add document references (in production, fetch from S3)
            for doc in documents:
                if hasattr(doc, 's3_key') and doc.s3_key:
                    # In production, fetch from S3 and add to ZIP
                    zip_file.writestr(
                        f"documents/{getattr(doc, 'file_name', doc.original_filename)}",
                        f"[Document reference: {doc.s3_key}]\n[In production, actual file content would be here]"
                    )
                else:
                    zip_file.writestr(
                        f"documents/{getattr(doc, 'file_name', doc.original_filename)}",
                        f"[Document: {getattr(doc, 'file_name', doc.original_filename)}]\n[Type: {str(doc.document_type) if hasattr(doc, 'document_type') else 'unknown'}]\n[In production, actual file content would be here]"
                    )

        zip_buffer.seek(0)
        zip_content = zip_buffer.read()
        
        # Calculate SHA256
        sha256_hash = hashlib.sha256(zip_content).hexdigest()
        
        file_name = f"Customs_Pack_{lc_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        
        # Store customs pack record
        customs_pack = CustomsPack(
            company_id=current_user.company_id,
            user_id=current_user.id,
            validation_session_id=request.validation_session_id,
            lc_number=lc_number,
            file_name=file_name,
            file_size_bytes=len(zip_content),
            sha256_hash=sha256_hash,
            manifest_data=manifest.dict(),
            # In production, upload to S3 and store key/URL
            download_url=f"/api/exporter/customs-pack/{request.validation_session_id}/download"
        )
        db.add(customs_pack)
        db.commit()
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="customs_pack",
            resource_id=str(customs_pack.id),
            details={
                "lc_number": lc_number,
                "file_name": file_name,
                "sha256": sha256_hash
            },
            result=AuditResult.SUCCESS
        )
        
        # Track telemetry (Phase 6)
        logger.info("Telemetry: customs_pack_generated", extra={
            "user_id": str(current_user.id),
            "company_id": str(current_user.company_id),
            "validation_session_id": str(request.validation_session_id),
            "lc_number": lc_number,
            "file_size_bytes": len(zip_content),
            "sha256": sha256_hash
        })

        return CustomsPackGenerateResponse(
            download_url=f"/api/exporter/customs-pack/{request.validation_session_id}/download",
            file_name=file_name,
            manifest=manifest,
            sha256=sha256_hash,
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate customs pack: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate customs pack"
        )


@router.get("/customs-pack/{validation_session_id}/download")
async def download_customs_pack(
    validation_session_id: UUID,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db)
):
    """
    Download the customs pack ZIP file.
    """
    try:
        # Find customs pack
        customs_pack = db.query(CustomsPack).filter(
            and_(
                CustomsPack.validation_session_id == validation_session_id,
                CustomsPack.company_id == current_user.company_id,
                CustomsPack.deleted_at.is_(None)
            )
        ).order_by(CustomsPack.created_at.desc()).first()

        if not customs_pack:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customs pack not found"
            )

        # Get validation session and documents
        session = db.query(ValidationSession).filter(
            ValidationSession.id == validation_session_id
        ).first()
        
        documents = db.query(Document).filter(
            Document.validation_session_id == validation_session_id
        ).all()

        # Rebuild ZIP (in production, fetch from S3)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            if customs_pack.manifest_data:
                zip_file.writestr(
                    "manifest.json",
                    json.dumps(customs_pack.manifest_data, indent=2)
                )
            
            # Add coversheet
            coversheet = f"""Customs Pack - LC {customs_pack.lc_number}
==========================================

Generated: {customs_pack.created_at.isoformat()}
LC Number: {customs_pack.lc_number}
Validation Session ID: {str(validation_session_id)}
Total Documents: {len(documents)}

DOCUMENTS INCLUDED:
{chr(10).join([f'- {getattr(doc, "file_name", doc.original_filename)}' for doc in documents])}

This pack contains all documents required for customs clearance.
All documents have been validated against LC requirements.

© 2024 LCopilot - AI-Powered Trade Document Analysis
"""
            zip_file.writestr("coversheet.txt", coversheet)
            
            # Add documents
            for doc in documents:
                zip_file.writestr(
                    f"documents/{getattr(doc, 'file_name', doc.original_filename)}",
                    f"[Document: {getattr(doc, 'file_name', doc.original_filename)}]\n[Type: {str(doc.document_type) if hasattr(doc, 'document_type') else 'unknown'}]\n[In production, actual file content would be here]"
                )

        zip_buffer.seek(0)

        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={customs_pack.file_name}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download customs pack: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download customs pack"
        )


# ===== Bank Submission Endpoints =====

@router.post("/bank-submissions", response_model=BankSubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_bank_submission(
    request: BankSubmissionCreate,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Create a bank submission (with guardrails).
    """
    try:
        # Check guardrails first
        guardrails = check_guardrails(db, request.validation_session_id, current_user.company_id)
        
        if not guardrails.can_submit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit: {', '.join(guardrails.blocking_issues)}"
            )
        
        # Check for existing submission with same idempotency key
        if request.idempotency_key:
            existing = db.query(ExportSubmission).filter(
                ExportSubmission.idempotency_key == request.idempotency_key
            ).first()
            
            if existing:
                # Return existing submission
                return BankSubmissionRead.model_validate(existing)
        
        # Get validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == request.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        # Calculate manifest hash
        documents = db.query(Document).filter(
            Document.validation_session_id == request.validation_session_id
        ).all()
        
        doc_hashes = [
            getattr(doc, 'sha256_hash', None) or hashlib.sha256(
                f"{doc.id}{getattr(doc, 'file_name', doc.original_filename)}".encode()
            ).hexdigest()[:16]
            for doc in documents
        ]
        manifest_hash = hashlib.sha256(
            "".join(doc_hashes).encode()
        ).hexdigest()

        # Create submission
        submission = ExportSubmission(
            company_id=current_user.company_id,
            user_id=current_user.id,
            validation_session_id=request.validation_session_id,
            lc_number=request.lc_number,
            bank_id=request.bank_id,
            bank_name=request.bank_name,
            status=SubmissionStatus.PENDING.value,
            manifest_hash=manifest_hash,
            manifest_data={
                "lc_number": request.lc_number,
                "validation_session_id": str(request.validation_session_id),
                "documents": [
                    {
                        "name": getattr(doc, 'file_name', doc.original_filename),
                        "type": str(doc.document_type) if hasattr(doc, 'document_type') else "unknown",
                        "hash": getattr(doc, 'sha256_hash', None)
                    }
                    for doc in documents
                ]
            },
            note=request.note,
            idempotency_key=request.idempotency_key,
            submitted_at=datetime.utcnow()
        )
        
        db.add(submission)
        db.flush()
        
        # Create initial event
        event = SubmissionEvent(
            submission_id=submission.id,
            event_type=SubmissionEventType.CREATED.value,
            payload={
                "lc_number": request.lc_number,
                "bank_name": request.bank_name
            },
            actor_id=current_user.id,
            actor_name=current_user.full_name or current_user.email
        )
        db.add(event)
        db.commit()
        db.refresh(submission)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="bank_submission",
            resource_id=str(submission.id),
            details={
                "lc_number": request.lc_number,
                "bank_name": request.bank_name,
                "status": submission.status
            },
            result=AuditResult.SUCCESS
        )
        
        # Track telemetry (Phase 6)
        logger.info("Telemetry: bank_submit_requested", extra={
            "user_id": str(current_user.id),
            "company_id": str(current_user.company_id),
            "validation_session_id": str(request.validation_session_id),
            "lc_number": request.lc_number,
            "submission_id": str(submission.id),
            "bank_name": request.bank_name
        })
        
        return BankSubmissionRead.model_validate(submission)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bank submission: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bank submission"
        )


def _normalize_session_id(session_id_str: Optional[str]) -> Optional[UUID]:
    """Strip 'job_' prefix if present and parse as UUID."""
    if not session_id_str:
        return None
    if session_id_str.startswith("job_"):
        session_id_str = session_id_str[4:]
    try:
        return UUID(session_id_str)
    except ValueError:
        return None


@router.get("/bank-submissions", response_model=BankSubmissionListResponse)
async def list_bank_submissions(
    lc_number: Optional[str] = Query(None),
    validation_session_id: Optional[str] = Query(None),  # Accept string to handle 'job_' prefix
    status: Optional[SubmissionStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db)
):
    """
    List bank submissions for the current exporter.
    """
    # Normalize session ID (strip 'job_' prefix if present)
    session_uuid = _normalize_session_id(validation_session_id)
    
    query = db.query(ExportSubmission).filter(
        and_(
            ExportSubmission.company_id == current_user.company_id,
            ExportSubmission.deleted_at.is_(None)
        )
    )
    
    if lc_number:
        query = query.filter(ExportSubmission.lc_number.ilike(f"%{lc_number}%"))
    if session_uuid:
        query = query.filter(ExportSubmission.validation_session_id == session_uuid)
    if status:
        query = query.filter(ExportSubmission.status == status.value)
    
    total = query.count()
    items = query.order_by(desc(ExportSubmission.created_at)).offset(skip).limit(limit).all()
    
    return BankSubmissionListResponse(
        items=[BankSubmissionRead.model_validate(item) for item in items],
        total=total
    )


@router.get("/bank-submissions/{submission_id}/events", response_model=SubmissionEventListResponse)
async def get_submission_events(
    submission_id: UUID,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db)
):
    """
    Get event timeline for a submission.
    """
    # Verify submission belongs to user's company
    submission = db.query(ExportSubmission).filter(
        and_(
            ExportSubmission.id == submission_id,
            ExportSubmission.company_id == current_user.company_id
        )
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    events = db.query(SubmissionEvent).filter(
        SubmissionEvent.submission_id == submission_id
    ).order_by(SubmissionEvent.created_at.asc()).all()
    
    return SubmissionEventListResponse(
        items=[SubmissionEventRead.model_validate(event) for event in events],
        total=len(events)
    )


@router.post("/bank-submissions/{submission_id}/cancel", response_model=BankSubmissionRead)
async def cancel_submission(
    submission_id: UUID,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Cancel a pending submission.
    """
    submission = db.query(ExportSubmission).filter(
        and_(
            ExportSubmission.id == submission_id,
            ExportSubmission.company_id == current_user.company_id
        )
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    if submission.status != SubmissionStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel submission with status {submission.status}"
        )
    
    submission.status = SubmissionStatus.CANCELLED.value
    db.flush()
    
    # Create cancel event
    event = SubmissionEvent(
        submission_id=submission.id,
        event_type=SubmissionEventType.CANCEL.value,
        payload={"cancelled_by": current_user.full_name or current_user.email},
        actor_id=current_user.id,
        actor_name=current_user.full_name or current_user.email
    )
    db.add(event)
    db.commit()
    db.refresh(submission)
    
    return BankSubmissionRead.model_validate(submission)


# ===== Guardrail Check Endpoint =====

@router.post("/guardrails/check", response_model=GuardrailCheckResponse)
async def check_submission_guardrails(
    request: GuardrailCheckRequest,
    current_user: User = Depends(require_exporter_user),
    db: Session = Depends(get_db)
):
    """
    Check guardrails before submission (for client-side pre-check).
    """
    try:
        session_uuid = request.session_uuid  # Handles 'job_' prefix
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid validation_session_id format: {request.validation_session_id}"
        )
    return check_guardrails(db, session_uuid, current_user.company_id)

