"""Tests for the user-facing notification dispatcher — Phase A3.

In-process: dispatcher writes a row, optionally fires email, respects
preferences. Trigger integration is covered separately in
test_finding_persistence.py and test_repaper_email_and_revalidate.py
(those tests run the dispatcher under integration via mock email +
fake users).
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as legacy_models  # noqa: F401  (side effects)
from app.models import Discrepancy, ValidationSession
from app.models.base import Base
from app.models.bulk_jobs import BulkItem, BulkJob  # noqa: F401  — FK targets
from app.models.discrepancy_workflow import (  # noqa: F401  — keep metadata
    DiscrepancyComment,
    RepaperingRequest,
)
from app.models.user_notifications import (
    DEFAULT_NOTIFICATION_PREFS,
    Notification,
    NotificationType,
)
from app.services.user_notifications import dispatch


class _FakeUser:
    def __init__(self, *, prefs: dict | None = None, email="u@example.com"):
        self.id = uuid.uuid4()
        self.email = email
        self.onboarding_data = {"notifications": prefs} if prefs else {}


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


class TestDispatch:
    def test_writes_in_app_row_with_defaults(self, db):
        user = _FakeUser()
        with patch("app.services.user_notifications.send_email") as fake_email:
            row = dispatch(
                db,
                user,
                NotificationType.DISCREPANCY_RAISED,
                title="3 new findings",
                body="Critical: 1, Major: 2, Advisory: 0",
                link_url="/exporter/results/abc",
                metadata={"new_count": 3},
            )
            db.commit()

        assert row is not None
        # Default prefs for DISCREPANCY_RAISED are in_app + email = True
        assert fake_email.called
        sent = db.query(Notification).filter(Notification.user_id == user.id).all()
        assert len(sent) == 1
        assert sent[0].type == NotificationType.DISCREPANCY_RAISED.value
        assert sent[0].title == "3 new findings"
        assert sent[0].read_at is None
        assert json.loads(sent[0].metadata_json) == {"new_count": 3}

    def test_email_off_pref_skips_email(self, db):
        user = _FakeUser(
            prefs={
                NotificationType.DISCREPANCY_RAISED.value: {
                    "in_app": True,
                    "email": False,
                }
            }
        )
        with patch("app.services.user_notifications.send_email") as fake_email:
            dispatch(
                db,
                user,
                NotificationType.DISCREPANCY_RAISED,
                title="x",
                body="y",
            )
            db.commit()
        assert fake_email.called is False
        assert db.query(Notification).count() == 1

    def test_in_app_off_pref_skips_row(self, db):
        user = _FakeUser(
            prefs={
                NotificationType.DISCREPANCY_RAISED.value: {
                    "in_app": False,
                    "email": True,
                }
            }
        )
        with patch("app.services.user_notifications.send_email") as fake_email:
            row = dispatch(
                db,
                user,
                NotificationType.DISCREPANCY_RAISED,
                title="x",
                body="y",
            )
            db.commit()
        assert row is None
        assert fake_email.called  # email still fires
        assert db.query(Notification).count() == 0

    def test_force_email_overrides_pref(self, db):
        user = _FakeUser(
            prefs={
                NotificationType.SYSTEM.value: {"in_app": True, "email": False}
            }
        )
        with patch("app.services.user_notifications.send_email") as fake_email:
            dispatch(
                db,
                user,
                NotificationType.SYSTEM,
                title="urgent",
                body="please read",
                force_email=True,
            )
            db.commit()
        assert fake_email.called

    def test_unknown_type_uses_safe_defaults(self, db):
        user = _FakeUser()
        with patch("app.services.user_notifications.send_email") as fake_email:
            dispatch(
                db,
                user,
                "completely_made_up",
                title="x",
                body="y",
            )
            db.commit()
        # Default for unknown type is in_app=True, email=False
        assert db.query(Notification).count() == 1
        assert fake_email.called is False

    def test_none_user_is_noop(self, db):
        with patch("app.services.user_notifications.send_email") as fake_email:
            row = dispatch(
                db,
                None,
                NotificationType.SYSTEM,
                title="x",
                body="y",
            )
        assert row is None
        assert fake_email.called is False

    def test_email_failure_does_not_raise(self, db):
        user = _FakeUser()
        with patch(
            "app.services.user_notifications.send_email",
            side_effect=RuntimeError("smtp down"),
        ):
            row = dispatch(
                db,
                user,
                NotificationType.DISCREPANCY_RAISED,
                title="x",
                body="y",
            )
            db.commit()
        # Row still written even though email blew up
        assert row is not None
        assert db.query(Notification).count() == 1

    def test_link_truncation(self, db):
        user = _FakeUser()
        long_link = "/" + "x" * 3000
        with patch("app.services.user_notifications.send_email"):
            row = dispatch(
                db,
                user,
                NotificationType.SYSTEM,
                title="x",
                body="y",
                link_url=long_link,
            )
            db.commit()
        assert row is not None
        assert len(row.link_url) == 2048

    def test_default_pref_table_covers_all_types(self):
        for t in NotificationType:
            assert t.value in DEFAULT_NOTIFICATION_PREFS
            entry = DEFAULT_NOTIFICATION_PREFS[t.value]
            assert "in_app" in entry and "email" in entry
