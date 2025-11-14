"""
Admin dashboard endpoints for KPIs and recent activity.
"""
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.database import get_db
from app.models import User, Company, ValidationSession, SessionStatus
from app.models.company import CompanyStatus
from app.models.ruleset import Ruleset, RulesetStatus
from app.models.admin import SystemAlert, SystemAlertStatus
from app.services.audit_service import AuditService

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


def _range_to_timedelta(range_value: str) -> timedelta:
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    if range_value not in mapping:
        raise HTTPException(status_code=400, detail="Unsupported range")
    return mapping[range_value]


def _format_value(value: int) -> str:
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value/1_000:.1f}K"
    return str(value)


def _build_stat(
    *,
    stat_id: str,
    label: str,
    current: int,
    previous: int,
    href: str | None = None,
    emphasis: bool = False,
) -> Dict[str, str]:
    delta = current - previous
    direction = "flat"
    if delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"

    change_label = "No change"
    if previous > 0:
        percent = (delta / previous) * 100
        change_label = f"{percent:+.1f}% vs prev"
    elif current > 0 and previous == 0:
        change_label = "New"

    return {
        "id": stat_id,
        "label": label,
        "value": _format_value(current),
        "change": delta,
        "changeLabel": change_label,
        "changeDirection": direction,
        "href": href,
        "emphasis": emphasis,
    }


@router.get("/kpis")
async def get_dashboard_kpis(
    range_value: str = Query("7d", alias="range", pattern="^(24h|7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    now = datetime.utcnow()
    window = _range_to_timedelta(range_value)
    start = now - window
    prev_start = start - window
    prev_end = start

    # Validation volume
    total_sessions = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.created_at >= start)
        .scalar()
        or 0
    )
    prev_sessions = (
        db.query(func.count(ValidationSession.id))
        .filter(
            ValidationSession.created_at >= prev_start,
            ValidationSession.created_at < prev_end,
        )
        .scalar()
        or 0
    )

    # Success ratio
    success_count = (
        db.query(func.count(ValidationSession.id))
        .filter(
            ValidationSession.status == SessionStatus.COMPLETED.value,
            ValidationSession.created_at >= start,
        )
        .scalar()
        or 0
    )
    prev_success = (
        db.query(func.count(ValidationSession.id))
        .filter(
            ValidationSession.status == SessionStatus.COMPLETED.value,
            ValidationSession.created_at.between(prev_start, prev_end),
        )
        .scalar()
        or 0
    )

    # Active companies
    active_companies = (
        db.query(func.count(Company.id))
        .filter(Company.status == CompanyStatus.ACTIVE.value)
        .scalar()
        or 0
    )

    # Rulesets
    active_rulesets = (
        db.query(func.count(Ruleset.id))
        .filter(Ruleset.status == RulesetStatus.ACTIVE.value)
        .scalar()
        or 0
    )

    # Alerts
    open_alerts = (
        db.query(func.count(SystemAlert.id))
        .filter(SystemAlert.status.in_([SystemAlertStatus.ACTIVE, SystemAlertStatus.ACKNOWLEDGED, SystemAlertStatus.SNOOZED]))
        .scalar()
        or 0
    )

    stats = [
        _build_stat(
            stat_id="lc-volume",
            label="LCs processed",
            current=total_sessions,
            previous=prev_sessions,
            href="ops-jobs",
            emphasis=True,
        ),
        _build_stat(
            stat_id="lc-success",
            label="Successful validations",
            current=success_count,
            previous=prev_success,
        ),
        _build_stat(
            stat_id="active-companies",
            label="Active companies",
            current=active_companies,
            previous=active_companies,  # assume flat when historical data not available
            href="partners-registry",
        ),
        _build_stat(
            stat_id="active-rulesets",
            label="Published rulesets",
            current=active_rulesets,
            previous=active_rulesets,
            href="rules-list",
        ),
        _build_stat(
            stat_id="open-alerts",
            label="Operational alerts",
            current=open_alerts,
            previous=open_alerts,
            href="ops-alerts",
            emphasis=open_alerts > 0,
        ),
    ]

    return {
        "range": range_value,
        "generated_at": now.isoformat(),
        "stats": stats,
    }


@router.get("/activity")
async def get_recent_admin_activity(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    audit_service = AuditService(db)
    recent_actions = audit_service.get_recent_actions(action="admin_action", days=7)
    items: List[Dict[str, str]] = []

    for entry in recent_actions[:limit]:
        items.append(
            {
                "id": str(entry.id),
                "actor": entry.user_email or "system",
                "action": entry.action,
                "summary": entry.audit_metadata.get("summary") if entry.audit_metadata else entry.action,
                "createdAt": entry.timestamp.isoformat() if entry.timestamp else None,
            }
        )

    return {"items": items}

