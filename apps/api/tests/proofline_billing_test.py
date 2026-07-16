"""Proofline package quoting, hosted checkout, and payment webhook behavior."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.proofline import billing


def _package(**overrides):
    values = dict(
        id="proofline_standard",
        name="Proofline Standard",
        description="Verified review for a standard trade case.",
        currency="USD",
        amount_cents=19900,
        stripe_price_id=None,
        billing_mode="payment",
        self_service_enabled=True,
        active=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _lcopilot_payment(*, now, **overrides):
    values = dict(
        id=uuid.uuid4(),
        payment_status="paid",
        amount_paid_cents=5900,
        paid_at=now - timedelta(days=5),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_quote_credits_recent_lcopilot_payment_without_exceeding_case_price():
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    quote = billing.calculate_quote(
        _package(),
        source_lcopilot_session=_lcopilot_payment(now=now),
        now=now,
        credit_days=30,
        credit_percent=100,
    )

    assert quote.base_amount_cents == 19900
    assert quote.credit_amount_cents == 5900
    assert quote.amount_due_cents == 14000
    assert quote.currency == "USD"
    assert quote.credit_eligible_until == now - timedelta(days=5) + timedelta(days=30)


def test_quote_does_not_credit_expired_or_unpaid_lcopilot_work():
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    expired = billing.calculate_quote(
        _package(),
        source_lcopilot_session=_lcopilot_payment(now=now, paid_at=now - timedelta(days=31)),
        now=now,
        credit_days=30,
        credit_percent=100,
    )
    unpaid = billing.calculate_quote(
        _package(),
        source_lcopilot_session=_lcopilot_payment(now=now, payment_status="pending"),
        now=now,
        credit_days=30,
        credit_percent=100,
    )

    assert expired.credit_amount_cents == 0
    assert unpaid.credit_amount_cents == 0
    assert expired.amount_due_cents == 19900


class _CheckoutDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_checkout_uses_transparent_net_price_and_proofline_metadata(monkeypatch):
    created = {}

    def create(**kwargs):
        created.update(kwargs)
        return SimpleNamespace(id="cs_proofline_1", url="https://checkout.stripe.test/proofline")

    stripe = SimpleNamespace(
        api_key=None,
        checkout=SimpleNamespace(Session=SimpleNamespace(create=create)),
    )
    monkeypatch.setitem(sys.modules, "stripe", stripe)
    monkeypatch.setattr(billing.settings, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(billing.settings, "FRONTEND_URL", "https://trdrhub.test")

    trade_case = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        case_reference="PL-CREDIT1",
        title="US buyer shipment",
        status="awaiting_payment",
        service_package_id="proofline_standard",
        payment_status="pending",
        stripe_checkout_session_id=None,
        amount_paid_cents=None,
        credit_amount_cents=None,
        pricing_snapshot={},
    )
    user = SimpleNamespace(id=uuid.uuid4(), email="exporter@example.com")
    quote = billing.ProoflineQuote(
        package_id="proofline_standard",
        currency="USD",
        base_amount_cents=19900,
        credit_amount_cents=5900,
        amount_due_cents=14000,
        credit_eligible_until=None,
    )

    url = billing.create_checkout_session(
        _CheckoutDb(), trade_case, _package(), user, quote=quote
    )

    assert url == "https://checkout.stripe.test/proofline"
    assert created["line_items"][0]["price_data"]["unit_amount"] == 14000
    assert created["metadata"]["trdr_proofline_case_id"] == str(trade_case.id)
    assert created["metadata"]["trdr_proofline_credit_cents"] == "5900"
    assert trade_case.credit_amount_cents == 5900
    assert trade_case.stripe_checkout_session_id == "cs_proofline_1"


def test_checkout_rejects_manual_quote_packages():
    with pytest.raises(billing.ProoflineCheckoutError):
        billing.create_checkout_session(
            _CheckoutDb(),
            SimpleNamespace(id=uuid.uuid4(), status="awaiting_payment"),
            _package(self_service_enabled=False, billing_mode="manual"),
            SimpleNamespace(id=uuid.uuid4(), email="x@example.com"),
        )


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class _WebhookDb:
    def __init__(self, trade_case):
        self.trade_case = trade_case
        self.commits = 0

    def query(self, _model):
        return _Query(self.trade_case)

    def add(self, _value):
        return None

    def commit(self):
        self.commits += 1


def test_checkout_webhook_marks_paid_and_releases_case_for_processing(monkeypatch):
    trade_case = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        status="awaiting_payment",
        payment_status="pending",
        service_package_id="proofline_standard",
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
        amount_paid_cents=None,
        payment_currency=None,
        paid_at=None,
        submitted_at=None,
        deleted_at=None,
    )

    def transition(_db, case, target, **_kwargs):
        case.status = target.value

    monkeypatch.setattr(billing, "transition_case", transition)
    event = {
        "id": "cs_proofline_1",
        "payment_intent": "pi_proofline_1",
        "amount_total": 14000,
        "currency": "usd",
        "metadata": {
            "trdr_proofline_case_id": str(trade_case.id),
            "trdr_proofline_package_id": "proofline_standard",
        },
    }

    result = billing.handle_checkout_completed(_WebhookDb(trade_case), event)

    assert result.handled is True
    assert result.should_process is True
    assert result.case_id == trade_case.id
    assert trade_case.payment_status == "paid"
    assert trade_case.status == "submitted"
    assert trade_case.amount_paid_cents == 14000
    assert trade_case.payment_currency == "USD"
    assert trade_case.paid_at is not None


def test_non_proofline_checkout_event_falls_through():
    result = billing.handle_checkout_completed(
        _WebhookDb(None), {"metadata": {"trdr_job_id": str(uuid.uuid4())}}
    )
    assert result.handled is False

