from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, UsageRecord, UsageAction


@dataclass
class EntitlementResult:
    """Snapshot of a company's usage for a specific action."""

    used: int
    limit: Optional[int]
    remaining: Optional[int]
    period_start: datetime

    def to_dict(self) -> dict:
        return {
            "used": int(self.used),
            "limit": int(self.limit) if self.limit is not None else None,
            "remaining": int(self.remaining) if self.remaining is not None else None,
            "period_start": self.period_start.isoformat(),
        }


class EntitlementError(Exception):
    """Raised when a company exceeds its entitled usage."""

    def __init__(self, message: str, result: EntitlementResult, next_action_url: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.result = result
        self.next_action_url = next_action_url or "/billing/upgrade"


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

        limit: Optional[int] = company.quota_limit
        remaining: Optional[int] = None
        if limit is not None:
            remaining = max(limit - int(used), 0)

        return EntitlementResult(used=int(used), limit=limit, remaining=remaining, period_start=period_start)

    def enforce_quota(self, company: Company, action: UsageAction) -> EntitlementResult:
        """Ensure company has remaining quota for the action."""

        if not company.is_active:
            raise EntitlementError(
                "Company account is not active.",
                result=self._get_usage(company, action),
                next_action_url="/support",
            )

        result = self._get_usage(company, action)
        if result.limit is not None and result.used >= result.limit:
            raise EntitlementError(
                "You have reached the validation limit for your current plan.",
                result=result,
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

