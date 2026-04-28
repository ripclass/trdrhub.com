"""Enterprise tier endpoints — Phase A10.

Two surfaces for users on the enterprise tier:

  GET /api/enterprise/group-overview  — cross-activity rollup KPIs
  GET /api/enterprise/audit-log       — paged audit log with filters

The agency / services / exporter / importer surfaces stay
unchanged; this router aggregates across them for a single
"group" view.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import Discrepancy, User, ValidationSession
from ..models.agency import ForeignBuyer, Supplier
from ..models.audit_log import AuditLog
from ..models.discrepancy_workflow import RepaperingRequest
from ..models.services import ServicesClient, TimeEntry
from ..services.rbac import Permission, require_permission

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


_TERMINAL_LIFECYCLE = frozenset({"paid", "closed", "expired"})
_OPEN_DISCREPANCY_STATES = ("raised", "acknowledged", "responded", "repaper")


def _company_id_or_403(user: User) -> UUID:
    if not user or not user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise endpoints require a company-scoped user",
        )
    return user.company_id


# ---------------------------------------------------------------------------
# Group overview
# ---------------------------------------------------------------------------


class ActivityKPIs(BaseModel):
    label: str
    count: int
    description: Optional[str] = None


class GroupOverviewResponse(BaseModel):
    company_id: UUID
    activities: List[str]
    total_validations: int
    active_lcs: int
    open_discrepancies: int
    open_repaper_requests: int

    suppliers: ActivityKPIs
    foreign_buyers: ActivityKPIs
    services_clients: ActivityKPIs
    billable_unbilled_hours: float

    members_active: int
    generated_at: datetime


@router.get("/group-overview", response_model=GroupOverviewResponse)
async def group_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cross-activity KPI rollup for the whole company. v1 is single-
    entity; multi-entity hierarchies (parent / subsidiary) are a
    v1.1 concern."""
    company_id = _company_id_or_403(current_user)

    # Sessions
    total_sessions = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.company_id == company_id)
        .filter(ValidationSession.deleted_at.is_(None))
        .scalar()
        or 0
    )
    active_lcs = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.company_id == company_id)
        .filter(ValidationSession.deleted_at.is_(None))
        .filter(~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE))
        .scalar()
        or 0
    )

    # Discrepancies
    open_disc = (
        db.query(func.count(Discrepancy.id))
        .join(ValidationSession, Discrepancy.validation_session_id == ValidationSession.id)
        .filter(ValidationSession.company_id == company_id)
        .filter(Discrepancy.state.in_(_OPEN_DISCREPANCY_STATES))
        .filter(Discrepancy.deleted_at.is_(None))
        .scalar()
        or 0
    )

    # Repaper
    open_repaper = (
        db.query(func.count(RepaperingRequest.id))
        .join(Discrepancy, Discrepancy.id == RepaperingRequest.discrepancy_id)
        .join(ValidationSession, ValidationSession.id == Discrepancy.validation_session_id)
        .filter(ValidationSession.company_id == company_id)
        .filter(
            RepaperingRequest.state.in_(("requested", "in_progress", "corrected"))
        )
        .scalar()
        or 0
    )

    # Roster sizes — agency persona
    supplier_count = (
        db.query(func.count(Supplier.id))
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .scalar()
        or 0
    )
    buyer_count = (
        db.query(func.count(ForeignBuyer.id))
        .filter(ForeignBuyer.agent_company_id == company_id)
        .filter(ForeignBuyer.deleted_at.is_(None))
        .scalar()
        or 0
    )
    # Services persona
    services_count = (
        db.query(func.count(ServicesClient.id))
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .scalar()
        or 0
    )
    billable_unbilled = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_company_id == company_id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(TimeEntry.billable.is_(True))
        .filter(TimeEntry.billed.is_(False))
        .scalar()
        or 0
    )

    # Members
    from ..models.rbac import CompanyMember, MemberStatus

    members_active = (
        db.query(func.count(CompanyMember.id))
        .filter(CompanyMember.company_id == company_id)
        .filter(CompanyMember.status == MemberStatus.ACTIVE.value)
        .scalar()
        or 0
    )

    # Activities — pulled from Company.business_activities
    activities: List[str] = []
    company = getattr(current_user, "company", None)
    if company is not None:
        ba = getattr(company, "business_activities", None)
        if isinstance(ba, list):
            activities = [str(a) for a in ba]

    return GroupOverviewResponse(
        company_id=company_id,
        activities=activities,
        total_validations=int(total_sessions),
        active_lcs=int(active_lcs),
        open_discrepancies=int(open_disc),
        open_repaper_requests=int(open_repaper),
        suppliers=ActivityKPIs(
            label="Suppliers",
            count=int(supplier_count),
            description="Domestic factories the agent manages",
        ),
        foreign_buyers=ActivityKPIs(
            label="Foreign buyers",
            count=int(buyer_count),
            description="Overseas counterparties",
        ),
        services_clients=ActivityKPIs(
            label="Services clients",
            count=int(services_count),
            description="Companies the consultant manages LCs for",
        ),
        billable_unbilled_hours=float(billable_unbilled),
        members_active=int(members_active),
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    timestamp: datetime
    ip_address: Optional[str] = None
    metadata: Optional[dict] = None


class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    days_back: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paged audit log scoped to the caller's company. Required
    permission: VIEW_AUDIT_LOG (admin/owner only)."""
    require_permission(db, current_user, Permission.VIEW_AUDIT_LOG)
    _company_id_or_403(current_user)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # The legacy AuditLog table doesn't carry company_id — scope via
    # the writer (User.company_id). Approximate: fetch users in this
    # company and filter logs by user_id IN (..). Acceptable v1
    # constraint; v1.1 should add company_id directly to AuditLog.
    company_user_ids = (
        db.query(User.id).filter(User.company_id == current_user.company_id).subquery()
    )

    base = (
        db.query(AuditLog)
        .filter(AuditLog.user_id.in_(company_user_ids))
        .filter(AuditLog.timestamp >= cutoff)
    )
    if user_id is not None:
        base = base.filter(AuditLog.user_id == user_id)
    if action:
        base = base.filter(AuditLog.action == action)

    total = base.count() or 0
    rows = (
        base.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    entries: List[AuditLogEntry] = []
    for r in rows:
        meta: Optional[dict] = None
        # Some AuditLog implementations carry a `details` or
        # `metadata_json` JSON column; surface it best-effort.
        for attr in ("metadata_json", "details", "metadata", "context"):
            v = getattr(r, attr, None)
            if isinstance(v, dict):
                meta = v
                break
        entries.append(
            AuditLogEntry(
                id=r.id,
                user_id=r.user_id,
                user_email=getattr(r, "user_email", None),
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                timestamp=r.timestamp,
                ip_address=getattr(r, "ip_address", None),
                metadata=meta,
            )
        )

    return AuditLogResponse(
        entries=entries,
        total_count=int(total),
        page=int(page),
        page_size=int(page_size),
    )


# ---------------------------------------------------------------------------
# Current user role (used by the frontend to decide which controls to render)
# ---------------------------------------------------------------------------


class MyRoleResponse(BaseModel):
    role: Optional[str]
    permissions: List[str]


@router.get("/my-role", response_model=MyRoleResponse)
async def get_my_role(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the caller's resolved role + permission set so the UI
    can hide actions the user can't take."""
    from ..services.rbac import _ROLE_PERMISSIONS, get_user_role

    role = get_user_role(db, current_user)
    perms = _ROLE_PERMISSIONS.get(role or "", frozenset()) if role else frozenset()
    return MyRoleResponse(
        role=role,
        permissions=sorted(p.value for p in perms),
    )


__all__ = ["router"]
