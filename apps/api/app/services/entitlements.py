from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, UsageRecord, UsageAction


# Phase A4 — tier-aware monthly quota.
#
# Order of precedence for the effective limit:
#   1. Company.quota_limit when set (admin override or legacy value).
#   2. TIER_QUOTA_LIMITS[company.tier] when tier is recognised.
#   3. TIER_QUOTA_LIMITS["sme"] (the default tier per onboarding).
#
# `None` means unlimited — Enterprise tier or admin-cleared limit.
TIER_QUOTA_LIMITS: dict[str, Optional[int]] = {
    "solo": 10,
    "sme": 50,
    "enterprise": None,
}

# Per-tier max seats (members + invites). None = unlimited.
TIER_SEAT_LIMITS: dict[str, Optional[int]] = {
    "solo": 1,
    "sme": 5,
    "enterprise": None,
}


def resolve_quota_limit(company: Optional[Company]) -> Optional[int]:
    """Effective monthly quota for this company. None = unlimited."""
    if company is None:
        return None
    if company.quota_limit is not None:
        return int(company.quota_limit)
    tier = (getattr(company, "tier", None) or "sme").strip().lower()
    if tier in TIER_QUOTA_LIMITS:
        return TIER_QUOTA_LIMITS[tier]
    return TIER_QUOTA_LIMITS["sme"]


def resolve_seat_limit(company: Optional[Company]) -> Optional[int]:
    """Effective seat cap for this company. None = unlimited."""
    if company is None:
        return None
    tier = (getattr(company, "tier", None) or "sme").strip().lower()
    if tier in TIER_SEAT_LIMITS:
        return TIER_SEAT_LIMITS[tier]
    return TIER_SEAT_LIMITS["sme"]


@dataclass
class EntitlementResult:
    """Snapshot of a company's usage for a specific action."""

    used: int
    limit: Optional[int]
    remaining: Optional[int]
    period_start: datetime
    tier: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "used": int(self.used),
            "limit": int(self.limit) if self.limit is not None else None,
            "remaining": int(self.remaining) if self.remaining is not None else None,
            "period_start": self.period_start.isoformat(),
            "tier": self.tier,
        }


class EntitlementError(Exception):
    """Raised when a company exceeds its entitled usage."""

    def __init__(
        self,
        message: str,
        result: EntitlementResult,
        next_action_url: Optional[str] = None,
        *,
        code: str = "quota_exceeded",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.result = result
        self.next_action_url = next_action_url or "/pricing"
        self.code = code


class EntitlementService:
    """Utility for checking and recording company usage quotas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _current_period_start(self, company: Company) -> datetime:
        cycle_start: Optional[date] = company.billing_cycle_start
        if cycle_start:
            # Assume cycle start is first day of period; reset to current month if in past month
            today = date.today()
            if cycle_start.month == today.month and cycle_start.year == today.year:
                base = cycle_start
            else:
                base = date(today.year, today.month, 1)
        else:
            base = date.today().replace(day=1)
        return datetime.combine(base, time.min)

    def _get_usage(self, company: Company, action: UsageAction) -> EntitlementResult:
        period_start = self._current_period_start(company)
        used = (
            self.db.query(func.coalesce(func.sum(UsageRecord.units), 0))
            .filter(
                UsageRecord.company_id == company.id,
                UsageRecord.action == action.value,
                UsageRecord.timestamp >= period_start,
            )
            .scalar()
            or 0
        )

        # Tier-aware effective limit (Phase A4). Falls back to
        # company.quota_limit when set explicitly.
        limit: Optional[int] = resolve_quota_limit(company)
        remaining: Optional[int] = None
        if limit is not None:
            remaining = max(limit - int(used), 0)

        tier = (getattr(company, "tier", None) or "").strip().lower() or None
        return EntitlementResult(
            used=int(used),
            limit=limit,
            remaining=remaining,
            period_start=period_start,
            tier=tier,
        )

    def get_usage(self, company: Company, action: UsageAction) -> EntitlementResult:
        """Public read of the snapshot. Doesn't raise on overage —
        callers that want the gate use ``enforce_quota`` /
        ``enforce_bulk_quota``."""
        return self._get_usage(company, action)

    def enforce_quota(self, company: Company, action: UsageAction) -> EntitlementResult:
        """Ensure company has remaining quota for the action."""

        if not company.is_active:
            raise EntitlementError(
                "Company account is not active.",
                result=self._get_usage(company, action),
                next_action_url="/support",
                code="company_inactive",
            )

        result = self._get_usage(company, action)
        if result.limit is not None and result.used >= result.limit:
            raise EntitlementError(
                "You have reached the validation limit for your current plan.",
                result=result,
            )
        return result

    def enforce_bulk_quota(
        self, company: Company, action: UsageAction, *, count: int
    ) -> EntitlementResult:
        """Pre-check for bulk runs: refuse to start if ``count`` items
        would push usage past the monthly limit.

        Used by ``POST /api/bulk-validate/{id}/run`` so a Solo-tier
        user uploading 12 LCs gets an upfront ``quota_exceeded``
        instead of finding out after item #11 lands and #12 dies
        mid-run.
        """
        if not company.is_active:
            raise EntitlementError(
                "Company account is not active.",
                result=self._get_usage(company, action),
                next_action_url="/support",
                code="company_inactive",
            )
        result = self._get_usage(company, action)
        if result.limit is not None and result.used + max(0, int(count)) > result.limit:
            raise EntitlementError(
                (
                    f"This bulk run would push you past your monthly quota "
                    f"({result.used} used + {count} requested > "
                    f"{result.limit} limit). Upgrade or wait for the "
                    "billing period to roll over."
                ),
                result=result,
                code="bulk_quota_exceeded",
            )
        return result

    def record_usage(
        self,
        company: Company,
        action: UsageAction,
        *,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        units: int = 1,
        cost: Decimal = Decimal("0.00"),
        description: Optional[str] = None,
    ) -> EntitlementResult:
        """Record usage and return updated quota snapshot."""

        record = UsageRecord(
            company_id=company.id,
            session_id=session_id,
            action=action.value,
            units=units,
            cost=cost,
            user_id=user_id,
            description=description or "Usage recorded by entitlement service",
        )
        self.db.add(record)
        self.db.commit()
        return self._get_usage(company, action)

