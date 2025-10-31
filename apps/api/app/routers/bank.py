"""
Bank-facing API endpoints for portfolio visibility and governance.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..core.security import require_bank_or_admin
from ..database import get_db
from ..models import User
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
