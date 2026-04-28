"""Entitlements endpoint — Phase A4.

Single read-only endpoint that surfaces the company's tier, monthly
quota, used count, and remaining count to the dashboard quota strip.

Mutations (upgrade) are handled by the existing /api/billing flow;
this is purely a read for the quota UI.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import User, UsageAction
from ..services.entitlements import (
    EntitlementService,
    TIER_QUOTA_LIMITS,
    TIER_SEAT_LIMITS,
    resolve_quota_limit,
    resolve_seat_limit,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/entitlements", tags=["entitlements"])


class CurrentEntitlementsResponse(BaseModel):
    tier: Optional[str]
    plan: Optional[str]
    quota_used: int
    quota_limit: Optional[int]  # None = unlimited
    quota_remaining: Optional[int]
    quota_pct_used: Optional[float]  # 0..1
    period_start: Optional[str]
    seat_limit: Optional[int]
    upgrade_url: str


@router.get("/current", response_model=CurrentEntitlementsResponse)
async def get_current_entitlements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = getattr(current_user, "company", None)
    tier = (
        (getattr(company, "tier", None) or "").strip().lower()
        if company
        else None
    ) or None
    plan_value = None
    plan = getattr(company, "plan", None) if company else None
    if plan is not None:
        plan_value = getattr(plan, "value", None) or str(plan)

    quota_limit = resolve_quota_limit(company)
    seat_limit = resolve_seat_limit(company)

    used = 0
    remaining: Optional[int] = None
    period_start: Optional[str] = None
    if company is not None:
        snapshot = EntitlementService(db).get_usage(company, UsageAction.VALIDATE)
        used = snapshot.used
        remaining = snapshot.remaining
        period_start = snapshot.period_start.isoformat()

    pct: Optional[float] = None
    if quota_limit and quota_limit > 0:
        pct = min(1.0, max(0.0, used / float(quota_limit)))

    return CurrentEntitlementsResponse(
        tier=tier,
        plan=plan_value,
        quota_used=used,
        quota_limit=quota_limit,
        quota_remaining=remaining,
        quota_pct_used=pct,
        period_start=period_start,
        seat_limit=seat_limit,
        upgrade_url="/pricing",
    )


__all__ = ["router"]
