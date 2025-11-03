"""
Bank-facing API endpoints for portfolio visibility and governance.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..core.security import require_bank_or_admin
from ..database import get_db
from ..models import User, ValidationSession, SessionStatus
from ..services.analytics_service import AnalyticsService
from ..services.audit_service import AuditService


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
):
    """List validation jobs for the bank user."""
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
    
    return {
        "total": total,
        "count": len(results),
        "jobs": results,
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Get status of a specific validation job."""
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


@router.get("/results")
def get_bank_results(
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    status: Optional[str] = Query(None, description="Filter by compliance status (compliant/discrepancies)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Get validation results with filters."""
    query = db.query(ValidationSession).filter(
        ValidationSession.user_id == current_user.id,
        ValidationSession.deleted_at.is_(None),
        ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
    )
    
    # Date filters
    if start_date:
        query = query.filter(ValidationSession.created_at >= start_date)
    if end_date:
        query = query.filter(ValidationSession.created_at <= end_date)
    
    # Order by completed date desc
    query = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last())
    
    # Count total
    total = query.count()
    
    # Apply pagination
    sessions = query.offset(offset).limit(limit).all()
    
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
        
        # Apply status filter
        if status and compliance_status != status:
            continue
        
        # Apply client name filter (case-insensitive partial match)
        client_name_val = bank_metadata.get("client_name", "")
        if client_name and client_name.lower() not in client_name_val.lower():
            continue
        
        # Count documents
        document_count = len(session.documents) if session.documents else 0
        
        # Calculate compliance score (simplified - can be enhanced)
        compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
        
        results.append({
            "id": str(session.id),
            "job_id": str(session.id),
            "jobId": str(session.id),
            "client_name": client_name_val,
            "lc_number": bank_metadata.get("lc_number"),
            "submitted_at": session.created_at.isoformat() if session.created_at else None,
            "completed_at": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
            "status": compliance_status,
            "compliance_score": compliance_score,
            "discrepancy_count": len(discrepancies),
            "document_count": document_count,
        })
    
    return {
        "total": total,
        "count": len(results),
        "results": results,
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
