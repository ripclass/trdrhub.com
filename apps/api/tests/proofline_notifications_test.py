"""Proofline notifications reuse the existing user dispatcher safely."""

from types import SimpleNamespace
from uuid import uuid4

from app.models.user_notifications import NotificationType
from app.services.proofline.notifications import notify_customer


class _Query:
    def __init__(self, user):
        self.user = user

    def filter(self, *_args):
        return self

    def first(self):
        return self.user


class _Db:
    def __init__(self, user):
        self.user = user
        self.commits = 0
        self.rollbacks = 0

    def query(self, _model):
        return _Query(self.user)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_notify_customer_dispatches_plain_language_case_metadata(monkeypatch):
    user = SimpleNamespace(id=uuid4(), email="exporter@example.com")
    db = _Db(user)
    trade_case = SimpleNamespace(
        id=uuid4(),
        customer_user_id=user.id,
        case_reference="PL-2026-0042",
    )
    captured = {}

    def _dispatch(_db, actual_user, notification_type, **kwargs):
        captured.update(user=actual_user, notification_type=notification_type, **kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr("app.services.proofline.notifications.dispatch", _dispatch)

    notification = notify_customer(db, trade_case, event="action_required")

    assert notification is not None
    assert captured["user"] is user
    assert captured["notification_type"] == NotificationType.PROOFLINE_ACTION_REQUIRED
    assert captured["title"] == "Action required for your Proofline case"
    assert captured["link_url"] == f"/proofline/cases/{trade_case.id}"
    assert captured["metadata"] == {
        "trade_case_id": str(trade_case.id),
        "case_reference": "PL-2026-0042",
        "event": "action_required",
    }
    assert "document" not in str(captured["metadata"]).lower()
    assert db.commits == 1


def test_notify_customer_is_best_effort_for_missing_user_or_dispatch_failure(monkeypatch):
    case_without_customer = SimpleNamespace(
        id=uuid4(), customer_user_id=None, case_reference="PL-EMPTY"
    )
    assert notify_customer(_Db(None), case_without_customer, event="submitted") is None

    user = SimpleNamespace(id=uuid4(), email="exporter@example.com")
    db = _Db(user)
    trade_case = SimpleNamespace(
        id=uuid4(), customer_user_id=user.id, case_reference="PL-FAIL"
    )

    def _raise(*_args, **_kwargs):
        raise RuntimeError("delivery unavailable")

    monkeypatch.setattr("app.services.proofline.notifications.dispatch", _raise)

    assert notify_customer(db, trade_case, event="final_report_ready") is None
    assert db.rollbacks == 1


def test_notification_type_defaults_avoid_excess_email():
    from app.models.user_notifications import DEFAULT_NOTIFICATION_PREFS

    assert DEFAULT_NOTIFICATION_PREFS[NotificationType.PROOFLINE_CASE_UPDATE.value] == {
        "in_app": True,
        "email": False,
    }
    assert DEFAULT_NOTIFICATION_PREFS[
        NotificationType.PROOFLINE_ACTION_REQUIRED.value
    ]["email"] is True
    assert DEFAULT_NOTIFICATION_PREFS[NotificationType.PROOFLINE_REPORT_READY.value][
        "email"
    ] is True
