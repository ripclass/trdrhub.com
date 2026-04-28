"""Tests for tier-aware quota — Phase A4.

Pure helper tests (no DB) for the resolve_* helpers, plus DB-backed
tests for EntitlementService.enforce_quota and enforce_bulk_quota
with each tier.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.entitlements import (
    EntitlementError,
    EntitlementService,
    TIER_QUOTA_LIMITS,
    TIER_SEAT_LIMITS,
    resolve_quota_limit,
    resolve_seat_limit,
)


def _company(tier: str | None = None, quota_limit: int | None = None, active: bool = True):
    """Lightweight stand-in for a Company row that doesn't need to be
    persisted. EntitlementService only reads ``id``, ``tier``,
    ``quota_limit``, ``billing_cycle_start``, and ``is_active``."""
    return SimpleNamespace(
        id=None,
        tier=tier,
        quota_limit=quota_limit,
        billing_cycle_start=None,
        is_active=active,
    )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestResolveLimits:
    def test_solo_default(self):
        assert resolve_quota_limit(_company(tier="solo")) == 10
        assert resolve_seat_limit(_company(tier="solo")) == 1

    def test_sme_default(self):
        assert resolve_quota_limit(_company(tier="sme")) == 50
        assert resolve_seat_limit(_company(tier="sme")) == 5

    def test_enterprise_unlimited(self):
        assert resolve_quota_limit(_company(tier="enterprise")) is None
        assert resolve_seat_limit(_company(tier="enterprise")) is None

    def test_explicit_quota_overrides_tier(self):
        # Admin-set quota_limit takes precedence over the tier default.
        assert resolve_quota_limit(_company(tier="solo", quota_limit=999)) == 999

    def test_unknown_tier_falls_back_to_sme(self):
        assert resolve_quota_limit(_company(tier="???")) == TIER_QUOTA_LIMITS["sme"]
        assert resolve_seat_limit(_company(tier="???")) == TIER_SEAT_LIMITS["sme"]

    def test_none_company(self):
        assert resolve_quota_limit(None) is None
        assert resolve_seat_limit(None) is None

    def test_tier_is_case_insensitive(self):
        assert resolve_quota_limit(_company(tier="SOLO")) == 10
        assert resolve_quota_limit(_company(tier="Enterprise")) is None


# ---------------------------------------------------------------------------
# DB-backed enforcement
# ---------------------------------------------------------------------------


import uuid as _uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as legacy_models  # noqa: F401  (side effects)
from app.models import UsageAction, UsageRecord
from app.models.base import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[UsageRecord.__table__])
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_usage(db, *, company_id, count: int):
    """Insert ``count`` UsageRecords against ``company_id`` for VALIDATE."""
    for _ in range(count):
        db.add(
            UsageRecord(
                company_id=company_id,
                action=UsageAction.VALIDATE.value,
                units=1,
                cost=Decimal("0.00"),
                description="seed",
            )
        )
    db.commit()


class TestEnforceQuota:
    def test_solo_under_limit(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=5)
        result = EntitlementService(db).enforce_quota(
            SimpleNamespace(id=cid, tier="solo", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
        )
        assert result.used == 5
        assert result.limit == 10
        assert result.remaining == 5
        assert result.tier == "solo"

    def test_solo_at_limit_blocks(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=10)
        with pytest.raises(EntitlementError) as exc:
            EntitlementService(db).enforce_quota(
                SimpleNamespace(id=cid, tier="solo", quota_limit=None,
                                billing_cycle_start=None, is_active=True),
                UsageAction.VALIDATE,
            )
        assert exc.value.code == "quota_exceeded"
        assert exc.value.result.used == 10
        assert exc.value.result.limit == 10

    def test_enterprise_never_blocks(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=10_000)
        result = EntitlementService(db).enforce_quota(
            SimpleNamespace(id=cid, tier="enterprise", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
        )
        assert result.limit is None
        assert result.remaining is None

    def test_inactive_company_blocks(self, db):
        cid = _uuid.uuid4()
        with pytest.raises(EntitlementError) as exc:
            EntitlementService(db).enforce_quota(
                SimpleNamespace(id=cid, tier="sme", quota_limit=None,
                                billing_cycle_start=None, is_active=False),
                UsageAction.VALIDATE,
            )
        assert exc.value.code == "company_inactive"


class TestEnforceBulkQuota:
    def test_solo_bulk_within_remaining(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=3)
        # 3 used + 5 requested = 8 ≤ 10. OK.
        EntitlementService(db).enforce_bulk_quota(
            SimpleNamespace(id=cid, tier="solo", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
            count=5,
        )

    def test_solo_bulk_exceeds(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=3)
        # 3 used + 12 requested = 15 > 10. Reject upfront.
        with pytest.raises(EntitlementError) as exc:
            EntitlementService(db).enforce_bulk_quota(
                SimpleNamespace(id=cid, tier="solo", quota_limit=None,
                                billing_cycle_start=None, is_active=True),
                UsageAction.VALIDATE,
                count=12,
            )
        assert exc.value.code == "bulk_quota_exceeded"
        assert "monthly quota" in exc.value.message.lower()

    def test_sme_bulk_under_remaining(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=10)
        EntitlementService(db).enforce_bulk_quota(
            SimpleNamespace(id=cid, tier="sme", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
            count=20,
        )  # 10+20=30 ≤ 50

    def test_enterprise_bulk_unlimited(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=99_000)
        EntitlementService(db).enforce_bulk_quota(
            SimpleNamespace(id=cid, tier="enterprise", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
            count=10_000,
        )

    def test_zero_count_is_ok(self, db):
        cid = _uuid.uuid4()
        _seed_usage(db, company_id=cid, count=10)
        EntitlementService(db).enforce_bulk_quota(
            SimpleNamespace(id=cid, tier="solo", quota_limit=None,
                            billing_cycle_start=None, is_active=True),
            UsageAction.VALIDATE,
            count=0,
        )
