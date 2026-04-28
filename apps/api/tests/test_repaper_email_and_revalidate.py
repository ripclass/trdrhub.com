"""Tests for the Phase A2 closure — repaper email + auto re-validation.

Email helper is unit-tested for the no-SMTP branch only (the actual
SMTP send path is covered by BankNotificationService and isn't worth
re-testing here).

Auto-revalidation is tested with the pipeline call mocked out — we
care about state transitions and the replacement_session_id link, not
the actual validation engine.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as legacy_models  # noqa: F401  (side effects)
# Import all models referenced by ValidationSession FKs so SQLAlchemy
# can resolve them when create_all builds the schema.
from app.models.agency import ForeignBuyer as _AgencyBuyer, Supplier as _AgencySupplier  # noqa: F401
from app.models.services import ServicesClient as _ServicesClient, TimeEntry as _TimeEntry  # noqa: F401
_legacy_models = legacy_models  # noqa: F401  (side effects)
from app.models import Discrepancy, ValidationSession
from app.models.base import Base
from app.models.bulk_jobs import BulkItem, BulkJob  # noqa: F401  — FK targets
from app.models.discrepancy_workflow import (
    DiscrepancyComment,
    DiscrepancyState,
    RepaperingRequest,
    RepaperingState,
)
from app.models.user_notifications import Notification
from app.services.email import send_email
from app.services import repaper_revalidate


class _FakeUser:
    """Stand-in for the User row. The User table has a Postgres-only
    JSONB column that won't render on SQLite, so we patch the
    requester lookup instead of materialising the table."""

    def __init__(self, user_id, email="requester@example.com"):
        self.id = user_id
        self.email = email


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    tables = [
        BulkJob.__table__,
        BulkItem.__table__,
        ValidationSession.__table__,
        Discrepancy.__table__,
        DiscrepancyComment.__table__,
        RepaperingRequest.__table__,
        Notification.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded(db):
    """Build a ValidationSession → Discrepancy → RepaperingRequest chain in
    CORRECTED state, ready for revalidation. The requester user_id
    points at a uuid; the actual User row is faked via _FakeUser +
    monkeypatch in each test."""
    user_id = uuid.uuid4()

    session = ValidationSession(
        user_id=user_id,
        status="completed",
        workflow_type="exporter_presentation",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    discrepancy = Discrepancy(
        validation_session_id=session.id,
        discrepancy_type="ucp600",
        severity="major",
        rule_name="UCP600.18.c",
        description="Late presentation",
        state=DiscrepancyState.REPAPER.value,
    )
    db.add(discrepancy)
    db.commit()
    db.refresh(discrepancy)

    request = RepaperingRequest(
        discrepancy_id=discrepancy.id,
        requester_user_id=user_id,
        recipient_email="supplier@example.com",
        access_token="testtoken",
        state=RepaperingState.CORRECTED.value,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "user": _FakeUser(user_id),
        "session": session,
        "discrepancy": discrepancy,
        "request": request,
    }


@pytest.fixture(autouse=True)
def patch_requester_lookup(monkeypatch):
    """Default the user-lookup to a FakeUser whose id matches whatever
    the test seeded. Tests that need a None requester override this."""
    def _load(db, requester_user_id):
        if requester_user_id is None:
            return None
        return _FakeUser(requester_user_id)

    monkeypatch.setattr(repaper_revalidate, "_load_requester", _load)


class _NonClosingSession:
    """Wrap the real test session so the production code's
    `finally: db.close()` doesn't kill the session before the test can
    inspect rows. Forwards everything else to the real session."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def close(self):  # production code calls this; we no-op
        return None


# ---------------------------------------------------------------------------
# Email helper
# ---------------------------------------------------------------------------


class TestEmailHelper:
    def test_no_smtp_returns_false_quietly(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        ok = send_email(
            to="x@example.com",
            subject="hi",
            html_body="<p>hi</p>",
        )
        assert ok is False

    def test_html_to_text_fallback(self, monkeypatch):
        # Even with no SMTP, building the message must not raise on
        # missing text_body — the helper synthesizes it from html.
        monkeypatch.delenv("SMTP_HOST", raising=False)
        ok = send_email(
            to="x@example.com",
            subject="hi",
            html_body="<p>Hello <b>world</b></p>",
        )
        assert ok is False  # skipped, but no exception


# ---------------------------------------------------------------------------
# Auto re-validation
# ---------------------------------------------------------------------------


class TestRevalidate:
    @pytest.mark.asyncio
    async def test_skips_if_already_resolved(self, db, seeded, monkeypatch):
        seeded["request"].state = RepaperingState.RESOLVED.value
        db.commit()

        called = {"hit": False}

        async def _fake_pipeline(*a, **k):
            called["hit"] = True
            return {}

        monkeypatch.setattr(repaper_revalidate, "_run_pipeline", _fake_pipeline)
        # Re-route SessionLocal to our test session
        monkeypatch.setattr(repaper_revalidate, "SessionLocal", lambda: _NonClosingSession(db))

        await repaper_revalidate.revalidate_repaper_request(
            seeded["request"].id
        )
        assert called["hit"] is False

    @pytest.mark.asyncio
    async def test_no_files_skips_pipeline(self, db, seeded, monkeypatch, tmp_path):
        monkeypatch.setenv("BULK_VALIDATE_STORAGE_DIR", str(tmp_path))
        called = {"hit": False}

        async def _fake_pipeline(*a, **k):
            called["hit"] = True
            return {}

        monkeypatch.setattr(repaper_revalidate, "_run_pipeline", _fake_pipeline)
        monkeypatch.setattr(repaper_revalidate, "SessionLocal", lambda: _NonClosingSession(db))

        await repaper_revalidate.revalidate_repaper_request(
            seeded["request"].id
        )
        assert called["hit"] is False

    @pytest.mark.asyncio
    async def test_clean_revalidation_resolves_discrepancy(
        self, db, seeded, monkeypatch, tmp_path
    ):
        # Stage a corrected file
        monkeypatch.setenv("BULK_VALIDATE_STORAGE_DIR", str(tmp_path))
        repaper_dir = tmp_path / "repaper" / str(seeded["request"].id)
        repaper_dir.mkdir(parents=True)
        (repaper_dir / "fixed_bl.pdf").write_bytes(b"%PDF-1.4 stub")

        new_session_id = str(uuid.uuid4())

        async def _fake_pipeline(*a, **k):
            return {
                "validation_session_id": new_session_id,
                "structured_result": {"issues": []},
            }

        monkeypatch.setattr(repaper_revalidate, "_run_pipeline", _fake_pipeline)
        monkeypatch.setattr(repaper_revalidate, "SessionLocal", lambda: _NonClosingSession(db))

        await repaper_revalidate.revalidate_repaper_request(
            seeded["request"].id
        )

        db.refresh(seeded["request"])
        db.refresh(seeded["discrepancy"])
        assert seeded["request"].state == RepaperingState.RESOLVED.value
        assert str(seeded["request"].replacement_session_id) == new_session_id
        assert seeded["request"].resolved_at is not None
        assert seeded["discrepancy"].state == DiscrepancyState.RESOLVED.value
        assert (
            str(seeded["discrepancy"].resolution_evidence_session_id)
            == new_session_id
        )
        assert seeded["discrepancy"].resolution_action == "resolved"

    @pytest.mark.asyncio
    async def test_findings_left_keeps_discrepancy_open(
        self, db, seeded, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("BULK_VALIDATE_STORAGE_DIR", str(tmp_path))
        repaper_dir = tmp_path / "repaper" / str(seeded["request"].id)
        repaper_dir.mkdir(parents=True)
        (repaper_dir / "fixed_bl.pdf").write_bytes(b"stub")

        new_session_id = str(uuid.uuid4())

        async def _fake_pipeline(*a, **k):
            return {
                "validation_session_id": new_session_id,
                "structured_result": {
                    "issues": [
                        {"id": "X", "severity": "major", "title": "still broken"}
                    ]
                },
            }

        monkeypatch.setattr(repaper_revalidate, "_run_pipeline", _fake_pipeline)
        monkeypatch.setattr(repaper_revalidate, "SessionLocal", lambda: _NonClosingSession(db))

        await repaper_revalidate.revalidate_repaper_request(
            seeded["request"].id
        )

        db.refresh(seeded["request"])
        db.refresh(seeded["discrepancy"])
        # Repaper request resolves to RESOLVED regardless — recipient did
        # their part. Replacement session is linked.
        assert seeded["request"].state == RepaperingState.RESOLVED.value
        assert str(seeded["request"].replacement_session_id) == new_session_id
        # But the parent discrepancy stays in REPAPER (or whatever its
        # state was before) because findings remain.
        assert seeded["discrepancy"].state == DiscrepancyState.REPAPER.value
        assert seeded["discrepancy"].resolution_evidence_session_id is None

    @pytest.mark.asyncio
    async def test_pipeline_failure_logs_and_continues(
        self, db, seeded, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("BULK_VALIDATE_STORAGE_DIR", str(tmp_path))
        repaper_dir = tmp_path / "repaper" / str(seeded["request"].id)
        repaper_dir.mkdir(parents=True)
        (repaper_dir / "fixed_bl.pdf").write_bytes(b"stub")

        async def _exploding_pipeline(*a, **k):
            raise RuntimeError("LLM provider down")

        monkeypatch.setattr(
            repaper_revalidate, "_run_pipeline", _exploding_pipeline
        )
        monkeypatch.setattr(repaper_revalidate, "SessionLocal", lambda: _NonClosingSession(db))

        # Must not raise
        await repaper_revalidate.revalidate_repaper_request(
            seeded["request"].id
        )

        db.refresh(seeded["request"])
        # State is unchanged — still CORRECTED, awaiting requester to
        # manually re-validate or cancel.
        assert seeded["request"].state == RepaperingState.CORRECTED.value
        assert seeded["request"].replacement_session_id is None
