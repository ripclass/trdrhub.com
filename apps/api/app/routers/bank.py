"""
Bank-facing API endpoints for portfolio visibility and governance.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, cast, case
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
import asyncio
import json
import secrets
import time

from ..core.security import require_bank_or_admin
from ..database import get_db, SessionLocal
from ..models import User, ValidationSession, SessionStatus, UsageAction
from ..services.analytics_service import AnalyticsService
from ..services.entitlements import EntitlementService, EntitlementError
from ..services import ValidationSessionService
from ..services.validator import validate_document
from ..middleware.bank_rate_limit import bank_rate_limit
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult
from ..config import settings
from ..utils.token_utils import create_signed_token, verify_signed_token
from ..utils.bulk_zip_processor import extract_and_detect_lc_sets
from ..utils.file_validation import validate_upload_file
from ..services import S3Service
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/bank", tags=["bank"])


def _resolve_bank_scope(request: Request) -> tuple[str, List[str]]:
    bank_id = getattr(request.state, "bank_id", None)
    tenant_ids = getattr(request.state, "tenant_ids", None)

    if not bank_id:
        raise HTTPException(status_code=403, detail="Bank scope could not be resolved for this request.")

    if tenant_ids is None:
        tenant_ids = []

    if isinstance(tenant_ids, list):
        tenant_scope = [str(tid) for tid in tenant_ids]
    else:
        tenant_scope = [str(tenant_ids)]

    return str(bank_id), tenant_scope


@router.get("/overview")
def get_bank_overview(
    request: Request,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    lookback_days: int = Query(30, ge=1, le=180),
):
    """Return aggregated KPIs for the authenticated bank."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    summary = analytics.get_bank_portfolio_summary(bank_id=bank_id, tenant_ids=tenant_ids, lookback_days=lookback_days)
    return summary


@router.get("/compliance")
def get_bank_compliance_heatmap(
    request: Request,
    period: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$", description="Reporting period (YYYY-MM)"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Return a rule-by-tenant compliance heatmap for the current bank."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    result = analytics.get_bank_compliance_heatmap(bank_id=bank_id, tenant_ids=tenant_ids, period=period)
    return result


@router.get("/exceptions")
def get_bank_exception_feed(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Return the most recent discrepancy events for the bank's portfolio."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    return analytics.get_bank_exception_feed(bank_id=bank_id, tenant_ids=tenant_ids, limit=limit)


@router.get("/audit")
async def search_bank_audit_log(
    request: Request,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant company ID"),
    resource_id: Optional[str] = Query(None, description="Filter by validation session ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Search the bank-scoped audit log."""
    bank_id, tenant_ids = _resolve_bank_scope(request)

    if tenant_id and tenant_ids and tenant_id not in tenant_ids:
        raise HTTPException(status_code=403, detail="Tenant is not managed by this bank.")

    entries, total = await AuditService.search_entries(
        db=db,
        tenant_id=tenant_id,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
        bank_id=bank_id,
    )

    return {
        "total": total,
        "count": len(entries),
        "results": [
            {
                "id": str(entry.id),
                "bank_id": str(entry.bank_id),
                "tenant_id": str(entry.tenant_id) if entry.tenant_id else None,
                "lc_id": str(entry.lc_id) if entry.lc_id else None,
                "event": entry.event,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
            for entry in entries
        ],
    }


@router.get("/jobs")
def list_bank_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """List validation jobs for the bank user."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None)
        )
        
        # Filter by status if provided
        if status:
            query = query.filter(ValidationSession.status == status)
        
        # Order by created_at desc
        query = query.order_by(ValidationSession.created_at.desc())
        
        # Count total
        total = query.count()
        
        # Apply pagination
        jobs = query.offset(offset).limit(limit).all()
        
        results = []
        for job in jobs:
            # Extract bank metadata from extracted_data
            metadata = job.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            
            results.append({
                "id": str(job.id),
                "job_id": str(job.id),
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
                "date_received": bank_metadata.get("date_received"),
                "status": job.status,
                "progress": _calculate_progress(job.status),
                "submitted_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
            })
        
        # Log job list access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_jobs",
            resource_id=f"list-{len(results)}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "job_count": len(results),
                "total_available": total,
                "filters": {
                    "status": status,
                    "limit": limit,
                    "offset": offset,
                }
            }
        )
        
        return {
            "total": total,
            "count": len(results),
            "jobs": results,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_jobs",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get status of a specific validation job."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        job = db.query(ValidationSession).filter(
            ValidationSession.id == job_id,
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None)
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Extract bank metadata
        metadata = job.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        
        # Log job status access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_job",
            resource_id=str(job_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "job_status": job.status,
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
            }
        )
        
        return {
            "id": str(job.id),
            "job_id": str(job.id),
            "client_name": bank_metadata.get("client_name"),
            "lc_number": bank_metadata.get("lc_number"),
            "date_received": bank_metadata.get("date_received"),
            "status": job.status,
            "progress": _calculate_progress(job.status),
            "submitted_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
            "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_job",
            resource_id=str(job_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/duplicates/check")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def check_duplicate_lc(
    lc_number: str = Query(..., description="LC number to check"),
    client_name: str = Query(..., description="Client name to check"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Check if an LC with the same LC number and client name has been validated before.
    Returns previous validation results if duplicates exist.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query for existing validation sessions with matching LC number and client name
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # Filter by LC number (case-insensitive, trimmed)
        lc_number_condition = cast(ValidationSession.extracted_data, JSONB)[
            'bank_metadata'
        ]['lc_number'].astext.ilike(lc_number.strip())
        
        # Filter by client name (case-insensitive, trimmed)
        client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
            'bank_metadata'
        ]['client_name'].astext.ilike(client_name.strip())
        
        query = query.filter(
            lc_number_condition,
            client_name_condition
        )
        
        # Order by completion date (most recent first)
        existing_sessions = query.order_by(
            ValidationSession.processing_completed_at.desc().nulls_last()
        ).limit(10).all()  # Limit to 10 most recent
        
        if not existing_sessions:
            return {
                "is_duplicate": False,
                "duplicate_count": 0,
                "previous_validations": [],
            }
        
        # Build previous validation results
        previous_validations = []
        for session in existing_sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            
            has_discrepancies = len(discrepancies) > 0
            compliance_status = "discrepancies" if has_discrepancies else "compliant"
            if session.status == SessionStatus.FAILED.value:
                compliance_status = "failed"
            
            document_count = len(session.documents) if session.documents else 0
            compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
            
            processing_time_seconds = None
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_time_seconds = round(delta.total_seconds(), 2)
            
            previous_validations.append({
                "id": str(session.id),
                "job_id": str(session.id),
                "lc_number": bank_metadata.get("lc_number"),
                "client_name": bank_metadata.get("client_name"),
                "date_received": bank_metadata.get("date_received"),
                "submitted_at": session.created_at.isoformat() if session.created_at else None,
                "completed_at": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
                "processing_time_seconds": processing_time_seconds,
                "status": compliance_status,
                "compliance_score": compliance_score,
                "discrepancy_count": len(discrepancies),
                "document_count": document_count,
            })
        
        # Log duplicate check
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="duplicate_check",
            resource_id=f"lc_{lc_number}_client_{client_name}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "lc_number": lc_number,
                "client_name": client_name,
                "duplicate_count": len(existing_sessions),
                "is_duplicate": True,
            }
        )
        
        return {
            "is_duplicate": True,
            "duplicate_count": len(existing_sessions),
            "previous_validations": previous_validations,
        }
    except Exception as e:
        logger.error(f"Duplicate check error: {e}", exc_info=True)
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="duplicate_check",
            resource_id=f"lc_{lc_number}_client_{client_name}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check for duplicates: {str(e)}"
        )


@router.get("/results")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_bank_results(
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    status: Optional[str] = Query(None, description="Filter by compliance status (compliant/discrepancies)"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum compliance score (0-100)"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum compliance score (0-100)"),
    discrepancy_type: Optional[str] = Query(None, description="Filter by discrepancy type (date_mismatch, amount_mismatch, party_mismatch, port_mismatch, missing_field, invalid_format)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get validation results with filters."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # Date filters (already in SQL)
        if start_date:
            query = query.filter(ValidationSession.created_at >= start_date)
        if end_date:
            query = query.filter(ValidationSession.created_at <= end_date)
        
        # Client name filter using JSON operators (SQL-based)
        if client_name:
            # Use PostgreSQL JSON operators to filter by client_name in extracted_data.bank_metadata.client_name
            # Cast JSON to JSONB for better operator support, then use ->> to extract text
            # Handle potential NULL values safely
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{client_name}%")
            # Also check that extracted_data is not null
            query = query.filter(
                ValidationSession.extracted_data.isnot(None),
                client_name_condition
            )
        
        # Status filter using JSON operators (SQL-based)
        if status:
            # Cast validation_results to JSONB for JSON operations
            discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
            
            if status == "compliant":
                # Compliant = no discrepancies or empty discrepancies array
                # Check if discrepancies array is empty or doesn't exist
                no_discrepancies = func.jsonb_array_length(discrepancies_path).is_(None) | \
                                  (func.jsonb_array_length(discrepancies_path) == 0)
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    no_discrepancies
                )
            elif status == "discrepancies":
                # Has discrepancies = discrepancies array exists and has length > 0
                has_discrepancies = func.jsonb_array_length(discrepancies_path) > 0
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    has_discrepancies
                )
            
            # Compliance score range filter (SQL-based)
            # Score is calculated as: 100 - (discrepancy_count * 5)
            # So we need to filter based on discrepancy count
            if min_score is not None or max_score is not None:
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                discrepancy_count_expr = func.coalesce(
                    func.jsonb_array_length(discrepancies_path),
                    0
                )
                
                # Calculate score: 100 - (discrepancy_count * 5)
                # Rearrange: discrepancy_count = (100 - score) / 5
                if min_score is not None:
                    # For min_score, we need max discrepancy_count
                    # min_score = 100 - (max_discrepancy_count * 5)
                    # max_discrepancy_count = (100 - min_score) / 5
                    max_discrepancy_count = (100 - min_score) / 5
                    query = query.filter(discrepancy_count_expr <= max_discrepancy_count)
                
                if max_score is not None:
                    # For max_score, we need min discrepancy_count
                    # max_score = 100 - (min_discrepancy_count * 5)
                    # min_discrepancy_count = (100 - max_score) / 5
                    min_discrepancy_count = (100 - max_score) / 5
                    query = query.filter(discrepancy_count_expr >= min_discrepancy_count)
            
            # Discrepancy type filter (SQL-based using JSONB contains)
            if discrepancy_type:
                # Check if discrepancies array contains an object with matching discrepancy_type
                # Using JSONB path exists: validation_results->discrepancies @> '[{"discrepancy_type": "..."}]'
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                
                # Create a JSONB array with the target discrepancy type
                target_type_json = json.dumps([{"discrepancy_type": discrepancy_type}])
                target_type_jsonb = cast(target_type_json, JSONB)
                
                # Check if discrepancies array contains the target type
                # Using @> operator (contains)
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    discrepancies_path.op('@>')(target_type_jsonb)
                )
        
        # Order by completed date desc
        query = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last())
        
        # Count total (now accurate after SQL filtering)
        total = query.count()
        
        # Apply pagination
        sessions = query.offset(offset).limit(limit).all()
        
        # Build results (no Python filtering needed - all done in SQL)
        results = []
        for session in sessions:
            # Extract bank metadata
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            
            # Extract validation results
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            
            # Determine compliance status
            has_discrepancies = len(discrepancies) > 0
            compliance_status = "discrepancies" if has_discrepancies else "compliant"
            if session.status == SessionStatus.FAILED.value:
                compliance_status = "failed"
            
            # Count documents
            document_count = len(session.documents) if session.documents else 0
            
            # Calculate compliance score (simplified - can be enhanced)
            compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
            
            # Calculate processing time in seconds
            processing_time_seconds = None
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_time_seconds = round(delta.total_seconds(), 2)
            
            # Check for duplicates (same LC number + client name)
            lc_number_val = bank_metadata.get("lc_number")
            client_name_val = bank_metadata.get("client_name")
            duplicate_count = 0
            if lc_number_val and client_name_val:
                duplicate_query = db.query(ValidationSession).filter(
                    ValidationSession.user_id == current_user.id,
                    ValidationSession.deleted_at.is_(None),
                    ValidationSession.extracted_data.isnot(None),
                    ValidationSession.id != session.id,  # Exclude current session
                    ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
                )
                
                duplicate_lc_condition = cast(ValidationSession.extracted_data, JSONB)[
                    'bank_metadata'
                ]['lc_number'].astext.ilike(lc_number_val.strip())
                
                duplicate_client_condition = cast(ValidationSession.extracted_data, JSONB)[
                    'bank_metadata'
                ]['client_name'].astext.ilike(client_name_val.strip())
                
                duplicate_count = duplicate_query.filter(
                    duplicate_lc_condition,
                    duplicate_client_condition
                ).count()
            
            results.append({
                "id": str(session.id),
                "job_id": str(session.id),
                "jobId": str(session.id),
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
                "date_received": bank_metadata.get("date_received"),
                "submitted_at": session.created_at.isoformat() if session.created_at else None,
                "processing_started_at": session.processing_started_at.isoformat() if session.processing_started_at else None,
                "completed_at": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
                "processing_time_seconds": processing_time_seconds,
                "status": compliance_status,
                "compliance_score": compliance_score,
                "discrepancy_count": len(discrepancies),
                "document_count": document_count,
                "duplicate_count": duplicate_count,  # Add duplicate count
            })
        
        # Log results view
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results",
            resource_id=f"list-{len(results)}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "result_count": len(results),
                "total_available": total,
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "client_name": client_name,
                    "status": status,
                    "min_score": min_score,
                    "max_score": max_score,
                    "discrepancy_type": discrepancy_type,
                    "limit": limit,
                    "offset": offset,
                }
            }
        )
        
        return {
            "total": total,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/results/export-pdf")
@bank_rate_limit(limiter_type="export", limit=10, window_seconds=60)
async def export_results_pdf(
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    status: Optional[str] = Query(None, description="Filter by compliance status (compliant/discrepancies)"),
    job_ids: Optional[str] = Query(None, description="Comma-separated list of job IDs to export (if provided, other filters are ignored)"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Generate a PDF report for filtered or selected validation results."""
    import time
    start_time = time.time()
    
    from ..reports.generator import ReportGenerator
    from io import BytesIO
    from fastapi.responses import Response
    
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # If specific job IDs provided, use those
        if job_ids:
            job_id_list = [UUID(jid.strip()) for jid in job_ids.split(",") if jid.strip()]
            sessions = db.query(ValidationSession).filter(
                ValidationSession.id.in_(job_id_list),
                ValidationSession.user_id == current_user.id,
                ValidationSession.deleted_at.is_(None)
            ).all()
            filtered_sessions = sessions
        else:
            # Get filtered results using optimized SQL queries (same logic as get_bank_results)
            query = db.query(ValidationSession).filter(
                ValidationSession.user_id == current_user.id,
                ValidationSession.deleted_at.is_(None),
                ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
            )
            
            # Date filters (SQL-based)
            if start_date:
                query = query.filter(ValidationSession.created_at >= start_date)
            if end_date:
                query = query.filter(ValidationSession.created_at <= end_date)
            
            # Client name filter using JSON operators (SQL-based)
            if client_name:
                client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                    'bank_metadata'
                ]['client_name'].astext.ilike(f"%{client_name}%")
                query = query.filter(
                    ValidationSession.extracted_data.isnot(None),
                    client_name_condition
                )
            
            # Status filter using JSON operators (SQL-based)
            if status:
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                
                if status == "compliant":
                    no_discrepancies = func.jsonb_array_length(discrepancies_path).is_(None) | \
                                      (func.jsonb_array_length(discrepancies_path) == 0)
                    query = query.filter(
                        ValidationSession.validation_results.isnot(None),
                        no_discrepancies
                    )
                elif status == "discrepancies":
                    has_discrepancies = func.jsonb_array_length(discrepancies_path) > 0
                    query = query.filter(
                        ValidationSession.validation_results.isnot(None),
                        has_discrepancies
                    )
            
            # Compliance score range filter (SQL-based)
            if min_score is not None or max_score is not None:
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                discrepancy_count_expr = func.coalesce(
                    func.jsonb_array_length(discrepancies_path),
                    0
                )
                
                if min_score is not None:
                    max_discrepancy_count = (100 - min_score) / 5
                    query = query.filter(discrepancy_count_expr <= max_discrepancy_count)
                
                if max_score is not None:
                    min_discrepancy_count = (100 - max_score) / 5
                    query = query.filter(discrepancy_count_expr >= min_discrepancy_count)
            
            # Discrepancy type filter (SQL-based using JSONB contains)
            if discrepancy_type:
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                target_type_json = json.dumps([{"discrepancy_type": discrepancy_type}])
                target_type_jsonb = cast(target_type_json, JSONB)
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    discrepancies_path.op('@>')(target_type_jsonb)
                )
            
            # Order by completed date desc
            query = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last())
            
            # Get all matching sessions (no pagination for export)
            filtered_sessions = query.all()
        
        # Generate summary PDF report
        report_generator = ReportGenerator()
        
        # Create HTML summary report
        html_content = _generate_summary_report_html(filtered_sessions, current_user)
        
        # Convert to PDF
        pdf_buffer = report_generator._html_to_pdf(html_content)
        # Return PDF as response
        filename = f"bank-lc-results-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        if job_ids:
            filename = f"bank-lc-results-selected-{len(filtered_sessions)}-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log successful export
        audit_service.log_action(
            action=AuditAction.DOWNLOAD,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results_export",
            resource_id=f"pdf-{len(filtered_sessions)}-results",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            duration_ms=duration_ms,
            audit_metadata={
                "export_type": "pdf",
                "result_count": len(filtered_sessions),
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "client_name": client_name,
                    "status": status,
                    "job_ids_count": len(job_ids.split(",")) if job_ids else None,
                }
            }
        )
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        # Log failed export
        audit_service.log_action(
            action=AuditAction.DOWNLOAD,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results_export",
            resource_id="pdf-export-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            duration_ms=duration_ms,
            error_message=str(e),
        )
        raise


def _generate_summary_report_html(sessions: List[ValidationSession], user: User) -> str:
    """Generate HTML summary report for multiple validation sessions."""
    from datetime import datetime
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bank LC Validation Results Summary</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            h1 {{
                color: #1f2937;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f9fafb;
            }}
            .summary {{
                margin: 20px 0;
                padding: 15px;
                background-color: #f3f4f6;
                border-radius: 5px;
            }}
            .compliant {{
                color: #10b981;
                font-weight: bold;
            }}
            .discrepancies {{
                color: #f59e0b;
                font-weight: bold;
            }}
            .failed {{
                color: #ef4444;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Bank LC Validation Results Summary</h1>
        <div class="summary">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Results:</strong> {len(sessions)}</p>
            <p><strong>Generated By:</strong> {user.email if user else 'System'}</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Job ID</th>
                    <th>LC Number</th>
                    <th>Client Name</th>
                    <th>Date Received</th>
                    <th>Submitted At</th>
                    <th>Completed At</th>
                    <th>Processing Time (s)</th>
                    <th>Status</th>
                    <th>Score (%)</th>
                    <th>Discrepancies</th>
                    <th>Documents</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for session in sessions:
        metadata = session.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        validation_results = session.validation_results or {}
        discrepancies = validation_results.get("discrepancies", [])
        
        client_name = bank_metadata.get("client_name", "")
        lc_number = bank_metadata.get("lc_number", "")
        date_received = bank_metadata.get("date_received", "")
        
        has_discrepancies = len(discrepancies) > 0
        compliance_status = "discrepancies" if has_discrepancies else "compliant"
        if session.status == SessionStatus.FAILED.value:
            compliance_status = "failed"
        
        compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
        document_count = len(session.documents) if session.documents else 0
        
        processing_time = ""
        if session.processing_started_at and session.processing_completed_at:
            delta = session.processing_completed_at - session.processing_started_at
            processing_time = f"{round(delta.total_seconds(), 2)}"
        
        submitted_at = session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else ""
        completed_at = session.processing_completed_at.strftime("%Y-%m-%d %H:%M:%S") if session.processing_completed_at else ""
        
        status_class = compliance_status
        html += f"""
                <tr>
                    <td>{str(session.id)[:8]}...</td>
                    <td>{lc_number or "N/A"}</td>
                    <td>{client_name or ""}</td>
                    <td>{date_received or ""}</td>
                    <td>{submitted_at}</td>
                    <td>{completed_at}</td>
                    <td>{processing_time}</td>
                    <td class="{status_class}">{compliance_status.upper()}</td>
                    <td>{compliance_score}</td>
                    <td>{len(discrepancies)}</td>
                    <td>{document_count}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return html


@router.get("/clients")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_client_names(
    query: Optional[str] = Query(None, description="Filter client names by search query"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get distinct client names for autocomplete."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query all validation sessions for this user
        sessions_query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None)
        )
        
        # If search query provided, filter in SQL (optimized)
        if query:
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{query}%")
            sessions_query = sessions_query.filter(client_name_condition)
        
        # Extract distinct client names from extracted_data
        client_names = set()
        sessions = sessions_query.all()
        
        for session in sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            client_name = bank_metadata.get("client_name")
            
            if client_name and isinstance(client_name, str):
                client_name_clean = client_name.strip()
                if client_name_clean:
                    client_names.add(client_name_clean)
        
        # Convert to sorted list
        client_list = sorted(list(client_names))
        
        # Apply limit
        client_list = client_list[:limit]
        
        # Log client list access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients",
            resource_id="autocomplete",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "query": query,
                "results_count": len(client_list),
                "limit": limit,
            }
        )
        
        return {
            "count": len(client_list),
            "clients": client_list,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients",
            resource_id="autocomplete-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.post("/bulk-upload/extract")
@bank_rate_limit(limiter_type="upload", limit=10, window_seconds=60)
async def extract_zip_file(
    zip_file: UploadFile = File(..., description="ZIP file containing multiple LC document sets"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Extract ZIP file and detect LC sets.
    Stores extracted files temporarily in S3 and returns detected LC sets with file references.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB
    
    try:
        # Read zip file content
        zip_content = await zip_file.read()
        
        # Validate zip file size
        if len(zip_content) > MAX_ZIP_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP file exceeds maximum size of {MAX_ZIP_SIZE / (1024 * 1024):.0f}MB"
            )
        
        # Validate zip file content (check magic bytes)
        if not zip_content.startswith(b'PK'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ZIP file format"
            )
        
        # Extract and detect LC sets
        try:
            lc_sets, file_contents = extract_and_detect_lc_sets(zip_content)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        if not lc_sets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No LC sets detected in ZIP file"
            )
        
        # Create a bulk upload session ID for grouping files
        bulk_session_id = uuid4()
        s3_service = S3Service()
        
        # Store extracted files in S3 temporarily
        # Files will be stored under: bulk-uploads/{bulk_session_id}/{filename}
        stored_files: Dict[str, Dict[str, str]] = {}  # filename -> {s3_key, s3_url}
        
        for filename, file_content in file_contents.items():
            # Validate file content
            header_bytes = file_content[:8]
            is_valid, error_message = validate_upload_file(
                header_bytes,
                filename=filename,
                content_type=None
            )
            
            if not is_valid:
                logger.warning(f"Skipping invalid file {filename}: {error_message}")
                continue
            
            # Determine content type from file signature
            content_type = 'application/pdf'  # Default
            if header_bytes.startswith(b'\xFF\xD8\xFF'):
                content_type = 'image/jpeg'
            elif header_bytes.startswith(b'\x89PNG'):
                content_type = 'image/png'
            elif header_bytes.startswith(b'II*\x00') or header_bytes.startswith(b'MM\x00*'):
                content_type = 'image/tiff'
            
            # Generate S3 key
            sanitized_filename = filename.replace('/', '_').replace('\\', '_')  # Sanitize path
            s3_key = f"bulk-uploads/{bulk_session_id}/{sanitized_filename}"
            
            # Upload to S3
            try:
                if not settings.USE_STUBS:
                    s3_service.s3_client.put_object(
                        Bucket=s3_service.bucket_name,
                        Key=s3_key,
                        Body=file_content,
                        ContentType=content_type,
                        Metadata={
                            'original_filename': filename,
                            'bulk_session_id': str(bulk_session_id),
                            'uploaded_at': datetime.now(timezone.utc).isoformat()
                        }
                    )
                    s3_url = f"https://{s3_service.bucket_name}.s3.{s3_service.region}.amazonaws.com/{s3_key}"
                else:
                    # Stub mode - store in memory/filesystem
                    s3_key = s3_key  # Keep same format
                    s3_url = f"stub://{s3_key}"
                
                stored_files[filename] = {
                    's3_key': s3_key,
                    's3_url': s3_url,
                    'size': len(file_content),
                    'content_type': content_type,
                    'valid': True,
                }
            except Exception as e:
                logger.error(f"Failed to store file {filename} in S3: {e}")
                stored_files[filename] = {
                    's3_key': None,
                    's3_url': None,
                    'size': len(file_content),
                    'content_type': content_type,
                    'valid': False,
                    'error': str(e),
                }
        
        # Prepare response with file info and S3 references
        lc_sets_response = []
        for lc_set in lc_sets:
            files_info = []
            for filename in lc_set['files']:
                if filename in stored_files:
                    file_info = stored_files[filename]
                    files_info.append({
                        'filename': filename,
                        'size': file_info['size'],
                        'valid': file_info['valid'],
                        's3_key': file_info['s3_key'],  # Include S3 key for later retrieval
                    })
                else:
                    files_info.append({
                        'filename': filename,
                        'size': 0,
                        'valid': False,
                        's3_key': None,
                    })
            
            lc_sets_response.append({
                'lc_number': lc_set.get('lc_number', ''),
                'client_name': lc_set.get('client_name', ''),
                'files': files_info,
                'file_count': len([f for f in files_info if f['valid']]),
                'detected_document_types': lc_set.get('detected_document_types', {}),
                'detection_method': lc_set.get('detection_method', 'unknown'),
            })
        
        # Log extraction
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bulk_upload_extract",
            resource_id=f"zip_{zip_file.filename}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                'zip_filename': zip_file.filename,
                'zip_size': len(zip_content),
                'lc_sets_detected': len(lc_sets),
                'bulk_session_id': str(bulk_session_id),
                'files_stored': len(stored_files),
            }
        )
        
        return {
            'status': 'success',
            'zip_filename': zip_file.filename,
            'zip_size': len(zip_content),
            'bulk_session_id': str(bulk_session_id),  # Return session ID for later submission
            'lc_sets': lc_sets_response,
            'total_lc_sets': len(lc_sets_response),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract ZIP file: {str(e)}"
        )


@router.post("/bulk-upload/submit")
@bank_rate_limit(limiter_type="upload", limit=5, window_seconds=60)
async def submit_bulk_upload(
    bulk_session_id: str = Form(..., description="Bulk session ID from extract endpoint"),
    lc_sets_data: str = Form(..., description="JSON array of LC sets with metadata and file references"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Submit bulk LC sets for validation.
    Files are retrieved from S3 using the bulk_session_id and processed individually.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    session_service = ValidationSessionService(db)
    s3_service = S3Service()
    
    try:
        import json
        lc_sets = json.loads(lc_sets_data)
        
        if not isinstance(lc_sets, list) or len(lc_sets) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid LC sets data"
            )
        
        # Check quota for all LC sets
        entitlements = EntitlementService(db)
        try:
            for _ in lc_sets:
                entitlements.enforce_quota(current_user.company, UsageAction.VALIDATE)
        except EntitlementError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "quota_exceeded",
                    "message": exc.message,
                    "quota": exc.result.to_dict(),
                    "next_action_url": exc.next_action_url,
                },
            ) from exc
        
        created_jobs = []
        
        for lc_set_index, lc_set in enumerate(lc_sets):
            try:
                # Sanitize inputs
                import re
                def sanitize_text(text: str) -> str:
                    if not text:
                        return ""
                    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                    text = re.sub(r'[^\w\s\-.,@]', '', text)  # Remove dangerous chars
                    return text.strip()
                
                client_name = sanitize_text(lc_set.get('client_name', '').strip())
                lc_number = sanitize_text(lc_set.get('lc_number', '').strip()) if lc_set.get('lc_number') else None
                date_received = lc_set.get('date_received', '') if lc_set.get('date_received') else None
                file_refs = lc_set.get('files', [])  # Array of {filename, s3_key}
                
                if not client_name:
                    logger.warning(f"Skipping LC set {lc_set_index + 1}: missing client name")
                    continue
                
                # Filter valid files
                valid_files = [f for f in file_refs if f.get('s3_key') and f.get('valid')]
                if not valid_files:
                    logger.warning(f"Skipping LC set {lc_set_index + 1}: no valid files")
                    continue
                
                # Create validation session
                session = session_service.create_session(current_user)
                
                # Prepare metadata
                bank_metadata = {
                    'client_name': client_name,
                    'lc_number': lc_number or '',
                    'date_received': date_received or '',
                    'upload_method': 'bulk_zip',
                    'bulk_session_id': bulk_session_id,
                }
                
                # Store metadata in session
                session.extracted_data = {
                    'bank_metadata': bank_metadata,
                    'bulk_upload_files': [
                        {
                            'filename': f['filename'],
                            's3_key': f['s3_key'],
                            'size': f.get('size', 0),
                        }
                        for f in valid_files
                    ],
                }
                
                # Mark session as created (will be processed asynchronously)
                session.status = SessionStatus.CREATED.value
                db.commit()
                
                created_jobs.append({
                    'job_id': str(session.id),
                    'lc_number': lc_number or 'Unknown',
                    'client_name': client_name,
                    'file_count': len(valid_files),
                    'status': 'created',
                })
                
            except Exception as e:
                logger.error(f"Error processing LC set {lc_set_index + 1}: {e}", exc_info=True)
                continue
        
        # Log bulk submission
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bulk_upload_submit",
            resource_id=f"bulk_{bulk_session_id}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                'bulk_session_id': bulk_session_id,
                'lc_sets_submitted': len(lc_sets),
                'jobs_created': len(created_jobs),
            }
        )
        
        return {
            'status': 'success',
            'message': f'Created {len(created_jobs)} validation jobs',
            'bulk_session_id': bulk_session_id,
            'lc_sets_submitted': len(lc_sets),
            'jobs_created': len(created_jobs),
            'jobs': created_jobs,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload submission error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit bulk upload: {str(e)}"
        )


async def _process_bulk_lc_set_async(
    session_id: str,
    files: List,
    metadata: Dict,
    user_id: UUID,
):
    """Background task to process an LC set from bulk upload."""
    # This will trigger the actual validation
    # For now, it's a placeholder
    pass


@router.get("/clients/stats")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_client_stats(
    query: Optional[str] = Query(None, description="Filter client names by search query"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get client statistics with validation counts and compliance metrics."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query all validation sessions for this user
        sessions_query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # If search query provided, filter in SQL
        if query:
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{query}%")
            sessions_query = sessions_query.filter(client_name_condition)
        
        # Get all matching sessions
        all_sessions = sessions_query.all()
        
        # Aggregate statistics by client name
        client_stats: Dict[str, Dict] = {}
        
        for session in all_sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            client_name = bank_metadata.get("client_name")
            
            if not client_name or not isinstance(client_name, str):
                continue
            
            client_name_clean = client_name.strip()
            if not client_name_clean:
                continue
            
            # Initialize client stats if not exists
            if client_name_clean not in client_stats:
                client_stats[client_name_clean] = {
                    "client_name": client_name_clean,
                    "total_validations": 0,
                    "compliant_count": 0,
                    "discrepancies_count": 0,
                    "failed_count": 0,
                    "total_discrepancies": 0,
                    "compliance_scores": [],
                    "last_validation_date": None,
                    "first_validation_date": None,
                }
            
            stats = client_stats[client_name_clean]
            stats["total_validations"] += 1
            
            # Extract validation results
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            discrepancy_count = len(discrepancies) if isinstance(discrepancies, list) else 0
            
            # Determine status
            if session.status == SessionStatus.FAILED.value:
                stats["failed_count"] += 1
            elif discrepancy_count == 0:
                stats["compliant_count"] += 1
            else:
                stats["discrepancies_count"] += 1
            
            stats["total_discrepancies"] += discrepancy_count
            
            # Calculate compliance score
            compliance_score = max(0, min(100, 100 - (discrepancy_count * 5)))
            stats["compliance_scores"].append(compliance_score)
            
            # Track dates
            if session.processing_completed_at:
                completed_date = session.processing_completed_at
                if not stats["last_validation_date"] or completed_date > stats["last_validation_date"]:
                    stats["last_validation_date"] = completed_date
                if not stats["first_validation_date"] or completed_date < stats["first_validation_date"]:
                    stats["first_validation_date"] = completed_date
        
        # Convert to list and calculate averages
        client_list = []
        for client_name, stats in client_stats.items():
            avg_score = 0
            if stats["compliance_scores"]:
                avg_score = sum(stats["compliance_scores"]) / len(stats["compliance_scores"])
            
            compliance_rate = 0
            if stats["total_validations"] > 0:
                compliance_rate = (stats["compliant_count"] / stats["total_validations"]) * 100
            
            client_list.append({
                "client_name": client_name,
                "total_validations": stats["total_validations"],
                "compliant_count": stats["compliant_count"],
                "discrepancies_count": stats["discrepancies_count"],
                "failed_count": stats["failed_count"],
                "total_discrepancies": stats["total_discrepancies"],
                "average_compliance_score": round(avg_score, 1),
                "compliance_rate": round(compliance_rate, 1),
                "last_validation_date": stats["last_validation_date"].isoformat() if stats["last_validation_date"] else None,
                "first_validation_date": stats["first_validation_date"].isoformat() if stats["first_validation_date"] else None,
            })
        
        # Sort by total validations (descending) or last validation date
        client_list.sort(key=lambda x: (
            x["last_validation_date"] or "1970-01-01"
        ), reverse=True)
        
        # Apply pagination
        total = len(client_list)
        paginated_list = client_list[offset:offset + limit]
        
        # Log client stats access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients_stats",
            resource_id="list",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "query": query,
                "results_count": len(paginated_list),
                "total_clients": total,
                "limit": limit,
                "offset": offset,
            }
        )
        
        return {
            "total": total,
            "count": len(paginated_list),
            "clients": paginated_list,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients_stats",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/clients/{client_name}/dashboard")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_client_dashboard(
    client_name: str,
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get comprehensive dashboard data for a specific client.
    Returns client statistics, all LCs, and performance trends.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query all validation sessions for this client
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # Filter by client name (exact match, case-insensitive)
        client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
            'bank_metadata'
        ]['client_name'].astext.ilike(client_name)
        query = query.filter(client_name_condition)
        
        # Date filters
        if start_date:
            query = query.filter(ValidationSession.created_at >= start_date)
        if end_date:
            query = query.filter(ValidationSession.created_at <= end_date)
        
        # Get all sessions for this client
        sessions = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last()).all()
        
        if not sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No validation sessions found for client: {client_name}"
            )
        
        # Calculate aggregate statistics
        total_validations = len(sessions)
        compliant_count = 0
        discrepancies_count = 0
        failed_count = 0
        total_discrepancies = 0
        compliance_scores = []
        processing_times = []
        
        # Track dates for trend analysis
        validation_dates = []
        
        for session in sessions:
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            discrepancy_count = len(discrepancies) if isinstance(discrepancies, list) else 0
            
            # Determine status
            if session.status == SessionStatus.FAILED.value:
                failed_count += 1
            elif discrepancy_count == 0:
                compliant_count += 1
            else:
                discrepancies_count += 1
            
            total_discrepancies += discrepancy_count
            
            # Calculate compliance score
            compliance_score = max(0, min(100, 100 - (discrepancy_count * 5)))
            compliance_scores.append(compliance_score)
            
            # Processing time
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_times.append(delta.total_seconds())
            
            # Track validation date for trends
            if session.processing_completed_at:
                validation_dates.append(session.processing_completed_at.date())
        
        # Calculate averages
        avg_compliance_score = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        compliance_rate = (compliant_count / total_validations * 100) if total_validations > 0 else 0
        
        # Calculate trend data (group by date)
        from collections import defaultdict
        daily_stats = defaultdict(lambda: {
            'count': 0,
            'compliant': 0,
            'discrepancies': 0,
            'failed': 0,
            'avg_score': [],
        })
        
        for session in sessions:
            if not session.processing_completed_at:
                continue
            
            date_key = session.processing_completed_at.date().isoformat()
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            discrepancy_count = len(discrepancies) if isinstance(discrepancies, list) else 0
            
            daily_stats[date_key]['count'] += 1
            compliance_score = max(0, min(100, 100 - (discrepancy_count * 5)))
            daily_stats[date_key]['avg_score'].append(compliance_score)
            
            if session.status == SessionStatus.FAILED.value:
                daily_stats[date_key]['failed'] += 1
            elif discrepancy_count == 0:
                daily_stats[date_key]['compliant'] += 1
            else:
                daily_stats[date_key]['discrepancies'] += 1
        
        # Format trend data
        trend_data = []
        for date_str in sorted(daily_stats.keys()):
            stats = daily_stats[date_str]
            trend_data.append({
                'date': date_str,
                'validations': stats['count'],
                'compliant': stats['compliant'],
                'discrepancies': stats['discrepancies'],
                'failed': stats['failed'],
                'avg_compliance_score': sum(stats['avg_score']) / len(stats['avg_score']) if stats['avg_score'] else 0,
            })
        
        # Build LC results list (similar to get_bank_results)
        lc_results = []
        for session in sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            
            has_discrepancies = len(discrepancies) > 0
            compliance_status = "discrepancies" if has_discrepancies else "compliant"
            if session.status == SessionStatus.FAILED.value:
                compliance_status = "failed"
            
            document_count = len(session.documents) if session.documents else 0
            compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
            
            processing_time_seconds = None
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_time_seconds = round(delta.total_seconds(), 2)
            
            lc_results.append({
                "id": str(session.id),
                "job_id": str(session.id),
                "jobId": str(session.id),
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
                "date_received": bank_metadata.get("date_received"),
                "submitted_at": session.created_at.isoformat() if session.created_at else None,
                "processing_started_at": session.processing_started_at.isoformat() if session.processing_started_at else None,
                "completed_at": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
                "processing_time_seconds": processing_time_seconds,
                "status": compliance_status,
                "compliance_score": compliance_score,
                "discrepancy_count": len(discrepancies),
                "document_count": document_count,
            })
        
        # Log dashboard access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="client_dashboard",
            resource_id=f"client_{client_name}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "client_name": client_name,
                "total_validations": total_validations,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        )
        
        return {
            "client_name": client_name,
            "statistics": {
                "total_validations": total_validations,
                "compliant_count": compliant_count,
                "discrepancies_count": discrepancies_count,
                "failed_count": failed_count,
                "total_discrepancies": total_discrepancies,
                "average_compliance_score": round(avg_compliance_score, 1),
                "compliance_rate": round(compliance_rate, 1),
                "average_processing_time_seconds": round(avg_processing_time, 2) if avg_processing_time else None,
                "first_validation_date": min(validation_dates).isoformat() if validation_dates else None,
                "last_validation_date": max(validation_dates).isoformat() if validation_dates else None,
            },
            "trend_data": trend_data,
            "lc_results": lc_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Client dashboard error: {e}", exc_info=True)
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="client_dashboard",
            resource_id=f"client_{client_name}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load client dashboard: {str(e)}"
        )


@router.get("/jobs/stream-token")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_job_stream_token(
    current_user: User = Depends(require_bank_or_admin),
):
    """Issue a short-lived token for establishing the SSE job stream."""

    token = create_signed_token(
        secret_key=settings.SECRET_KEY,
        payload={
            "uid": str(current_user.id),
            "nonce": secrets.token_urlsafe(8),
        },
        expires_in=STREAM_TOKEN_EXPIRY_SECONDS,
    )

    return {
        "token": token,
        "expires_in": STREAM_TOKEN_EXPIRY_SECONDS,
    }


def _calculate_progress(status: str) -> int:
    """Calculate progress percentage based on status."""
    status_map = {
        SessionStatus.CREATED.value: 0,
        SessionStatus.UPLOADING.value: 10,
        SessionStatus.PROCESSING.value: 50,
        SessionStatus.COMPLETED.value: 100,
        SessionStatus.FAILED.value: 0,
    }
    return status_map.get(status, 0)


@router.get("/jobs/stream")
async def stream_job_updates(
    request: Request,
    sse_token: str = Query(..., description="Short-lived signed token for SSE authentication"),
):
    """Server-Sent Events stream for real-time job status updates."""

    try:
        payload = verify_signed_token(settings.SECRET_KEY, sse_token)
        user_id = UUID(payload["uid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired stream token",
        )

    session = SessionLocal()
    try:
        current_user = session.query(User).filter(User.id == user_id).first()
    finally:
        session.close()

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if not (current_user.role in ["bank_officer", "bank_admin", "system_admin"] or current_user.is_bank_officer()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank access required",
        )

    async def _fetch_job_snapshots(user: User) -> List[Dict[str, Any]]:
        def _sync_fetch() -> List[Dict[str, Any]]:
            db_session = SessionLocal()
            try:
                active_jobs = db_session.query(ValidationSession).filter(
                    ValidationSession.user_id == user.id,
                    ValidationSession.deleted_at.is_(None),
                    ValidationSession.status.in_(
                        [
                            SessionStatus.CREATED.value,
                            SessionStatus.UPLOADING.value,
                            SessionStatus.PROCESSING.value,
                        ]
                    ),
                ).all()

                recent_threshold = datetime.utcnow() - timedelta(seconds=30)
                recent_jobs = db_session.query(ValidationSession).filter(
                    ValidationSession.user_id == user.id,
                    ValidationSession.deleted_at.is_(None),
                    ValidationSession.status.in_(
                        [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]
                    ),
                    ValidationSession.updated_at >= recent_threshold,
                ).all()

                jobs = active_jobs + recent_jobs

                snapshots: List[Dict[str, Any]] = []
                for job in jobs:
                    metadata = job.extracted_data or {}
                    bank_metadata = metadata.get("bank_metadata", {})

                    processing_time = None
                    if job.processing_started_at and job.processing_completed_at:
                        processing_time = int(
                            max(
                                0,
                                (job.processing_completed_at - job.processing_started_at).total_seconds(),
                            )
                        )

                    updated_at = (
                        job.updated_at
                        or job.processing_completed_at
                        or job.processing_started_at
                        or job.created_at
                    )
                    version_marker = updated_at.isoformat() if updated_at else str(time.time())

                    snapshots.append(
                        {
                            "payload": {
                                "id": str(job.id),
                                "job_id": str(job.id),
                                "client_name": bank_metadata.get("client_name"),
                                "lc_number": bank_metadata.get("lc_number"),
                                "date_received": bank_metadata.get("date_received"),
                                "status": job.status,
                                "progress": _calculate_progress(job.status),
                                "submitted_at": job.created_at.isoformat() if job.created_at else None,
                                "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
                                "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
                                "processing_time_seconds": processing_time,
                                "discrepancy_count": len((job.validation_results or {}).get("discrepancies", [])),
                                "document_count": len(job.documents) if job.documents else 0,
                            },
                            "version": version_marker,
                        }
                    )

                return snapshots
            finally:
                db_session.close()

        return await asyncio.to_thread(_sync_fetch)

    async def event_generator():
        last_sent_versions: Dict[str, str] = {}
        last_poll_time = 0.0
        last_keepalive = time.monotonic()

        try:
            while True:
                current_time = time.monotonic()

                if current_time - last_poll_time >= 1.0:
                    snapshots = await _fetch_job_snapshots(current_user)

                    for snapshot in snapshots:
                        payload = snapshot["payload"]
                        job_id = payload["id"]
                        version_marker = snapshot["version"]

                        if last_sent_versions.get(job_id) != version_marker:
                            yield f"data: {json.dumps(payload)}\n\n"
                            last_sent_versions[job_id] = version_marker

                    last_poll_time = current_time

                if current_time - last_keepalive >= 30:
                    yield ": keepalive\n\n"
                    last_keepalive = current_time

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pragma: no cover - defensive logging
            error_data = {"error": str(exc)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
