from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, CompanyMember, UsageRecord, UsageAction, User

logger = logging.getLogger(__name__)


def _smoke_bypass_emails() -> set[str]:
    """User emails whose Company is exempt from validation quota.

    Source of truth: the ``SMOKE_TEST_EMAILS`` env var, comma-
    separated email addresses, lower-cased on read. Empty / unset =
    no bypass. Used for launch-prep smoke + load-test runs so we
    don't burn through real customer quota when re-validating the
    same fixtures repeatedly.

    NEVER add a real customer's email here.
    """
    raw = os.getenv("SMOKE_TEST_EMAILS", "") or ""
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _smoke_bypass_result(action: UsageAction) -> "EntitlementResult":
    """Synthetic 'unlimited' result returned when smoke-bypass is on."""
    return EntitlementResult(
        used=0,
        limit=None,        # None = unlimited
        remaining=None,
        period_start=datetime.combine(
            date.today().replace(day=1), time.min, tzinfo=timezone.utc
        ),
        tier="smoke_bypass",
    )


# Pricing-restructure 2026-05-10 — tier-aware monthly quota across the
# 7-value BusinessTier enum (see app.models.company.BusinessTier).
#
# Order of precedence for the effective limit:
#   1. Company.quota_limit when set (admin override or legacy value).
#   2. TIER_QUOTA_LIMITS[company.tier] when tier is recognised.
#   3. TIER_QUOTA_LIMITS["business"] (the common paying tier — default for
#      unrecognised / un-migrated tier strings).
#
# `None` means unlimited (agency-track tiers, or an admin-cleared limit).
# A quota of 0 (PAYG) means "no included pool — every validation is a
# billable $12 event"; the quota gate still blocks PAYG until a usage
# charge is recorded, which the validation pipeline does up front.
TIER_QUOTA_LIMITS: dict[str, Optional[int]] = {
    "payg": 0,
    "solo": 5,
    "business": 25,
    "enterprise": 100,
    "agency_starter": None,      # "unlimited" within the fair-use soft cap below
    "agency_pro": None,
    "agency_enterprise": None,
}

# Per-tier max seats (members + invites). None = unlimited.
TIER_SEAT_LIMITS: dict[str, Optional[int]] = {
    "payg": 1,
    "solo": 1,
    "business": 5,
    "enterprise": 10,
    "agency_starter": None,
    "agency_pro": None,
    "agency_enterprise": None,
}

# Per-LC overage rate (USD) shown to a Trader-track customer once they've
# burned their included pool ("5 of 5 used — extra LCs at $10, or upgrade").
# NOT auto-charged yet: self-serve metered billing is v1.1, so for now the
# quota gate still hard-blocks at the included amount and this map is
# display-only. When metered billing lands, switch enforce_quota to
# allow-and-charge using these rates. PAYG has no overage — it IS per-use.
TIER_OVERAGE_RATE_USD: dict[str, Decimal] = {
    "solo": Decimal("10.00"),
    "business": Decimal("7.00"),
    "enterprise": Decimal("5.00"),
}

# Agency-track tiers advertise "unlimited LCs per seat" but carry a fair-use
# soft cap (LCs / seat / month). It is NOT hard-enforced — crossing it logs
# an internal alert so sales can have a volume conversation. Implemented as a
# company-level monthly threshold (cap × seat count); see _soft_cap_alert.
AGENCY_FAIR_USE_SOFT_CAP: dict[str, int] = {
    "agency_starter": 50,
    "agency_pro": 50,
}

_DEFAULT_TIER = "business"


def _company_tier(company: Optional[Company]) -> str:
    return (getattr(company, "tier", None) or _DEFAULT_TIER).strip().lower()


def resolve_quota_limit(company: Optional[Company]) -> Optional[int]:
    """Effective monthly quota for this company. None = unlimited."""
    if company is None:
        return None
    if company.quota_limit is not None:
        return int(company.quota_limit)
    tier = _company_tier(company)
    if tier in TIER_QUOTA_LIMITS:
        return TIER_QUOTA_LIMITS[tier]
    return TIER_QUOTA_LIMITS[_DEFAULT_TIER]


def resolve_seat_limit(company: Optional[Company]) -> Optional[int]:
    """Effective seat cap for this company. None = unlimited."""
    if company is None:
        return None
    tier = _company_tier(company)
    if tier in TIER_SEAT_LIMITS:
        return TIER_SEAT_LIMITS[tier]
    return TIER_SEAT_LIMITS[_DEFAULT_TIER]


def resolve_overage_rate(company: Optional[Company]) -> Optional[Decimal]:
    """Per-LC overage rate (USD) for display, or None if the tier has no
    overage concept (PAYG, agency tiers)."""
    if company is None:
        return None
    return TIER_OVERAGE_RATE_USD.get(_company_tier(company))


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


def _is_smoke_bypass_company(db: Session, company: Optional[Company]) -> bool:
    """Return True if any active member of `company` matches the
    `SMOKE_TEST_EMAILS` allowlist.

    Cheap one-shot DB query keyed off (company_id, lower(email)). The
    allowlist is recomputed each call so removing an email from the
    Render env var takes effect on the next request without a restart.
    """
    if company is None or company.id is None:
        return False
    allowlist = _smoke_bypass_emails()
    if not allowlist:
        return False
    member_email = (
        db.query(func.lower(User.email))
        .join(CompanyMember, CompanyMember.user_id == User.id)
        .filter(CompanyMember.company_id == company.id)
        .filter(func.lower(User.email).in_(allowlist))
        .limit(1)
        .scalar()
    )
    return member_email is not None


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

    def _maybe_soft_cap_alert(self, company: Company, used: int) -> None:
        """Agency-track tiers are 'unlimited' but carry a fair-use soft cap
        (LCs / seat / month). This does NOT block — it logs a warning when the
        company's monthly usage exceeds (cap × seat count) so sales can have
        the volume conversation. No-op for non-agency tiers."""
        tier = (getattr(company, "tier", None) or "").strip().lower()
        soft_cap = AGENCY_FAIR_USE_SOFT_CAP.get(tier)
        if soft_cap is None:
            return
        seats = (
            self.db.query(func.count(CompanyMember.id))
            .filter(CompanyMember.company_id == company.id)
            .scalar()
        ) or 1
        threshold = soft_cap * max(1, int(seats))
        if int(used) > threshold:
            logger.warning(
                "Agency fair-use soft cap exceeded: company=%s tier=%s used=%d "
                "threshold=%d (%d LCs/seat × %d seats)",
                company.id, tier, int(used), threshold, soft_cap, int(seats),
            )

    def enforce_quota(self, company: Company, action: UsageAction) -> EntitlementResult:
        """Ensure company has remaining quota for the action."""

        # Smoke-bypass: companies whose UUIDs are listed in the
        # SMOKE_TEST_COMPANY_IDS env var skip the quota gate entirely.
        # This keeps repeated launch-prep / load-test runs from
        # exhausting real-customer monthly limits. Never add a real
        # customer ID to that env var.
        if _is_smoke_bypass_company(self.db, company):
            logger.info(
                "Quota bypass for smoke-test company %s on action %s",
                company.id, action,
            )
            return _smoke_bypass_result(action)

        if not company.is_active:
            raise EntitlementError(
                "Company account is not active.",
                result=self._get_usage(company, action),
                next_action_url="/support",
                code="company_inactive",
            )

        result = self._get_usage(company, action)
        self._maybe_soft_cap_alert(company, result.used)
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
        if _is_smoke_bypass_company(self.db, company):
            logger.info(
                "Bulk-quota bypass for smoke-test company %s on action %s (count=%d)",
                company.id, action, count,
            )
            return _smoke_bypass_result(action)

        if not company.is_active:
            raise EntitlementError(
                "Company account is not active.",
                result=self._get_usage(company, action),
                next_action_url="/support",
                code="company_inactive",
            )
        result = self._get_usage(company, action)
        self._maybe_soft_cap_alert(company, result.used + max(0, int(count)))
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

