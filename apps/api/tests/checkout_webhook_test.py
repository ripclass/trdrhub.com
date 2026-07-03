"""Concierge checkout — webhook handlers + catalog guards (Phase 5 launch).

Pure-unit tests with a fake DB: the load-bearing behaviors are
(1) checkout.session.completed marks the job paid AND advances it from
    submitted into the operator's queue (under_review),
(2) replayed events are no-ops (idempotent),
(3) events without our metadata fall through to the legacy path,
(4) charge.refunded stamps refunded via payment-intent match,
(5) product/workflow mismatches are rejected before any Stripe call.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.services import checkout as co


class FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class FakeDb:
    def __init__(self, session=None):
        self.session = session
        self.added = []
        self.commits = 0

    def query(self, model):
        from app.models import ValidationSession
        if model is ValidationSession:
            return FakeQuery(self.session)
        return FakeQuery(None)  # User lookups in notifications → skip

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def _job(**overrides):
    base = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        company_id=None,
        workflow_type="cbam_readiness",
        review_state="submitted",
        review_state_changed_at=None,
        payment_status="pending",
        payment_product_id="cbam_report",
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
        amount_paid_cents=None,
        paid_at=None,
        refunded_at=None,
        deleted_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _event(job, **overrides):
    base = {
        "id": "cs_test_123",
        "payment_intent": "pi_test_456",
        "amount_total": 14900,
        "metadata": {"trdr_job_id": str(job.id), "trdr_product_id": "cbam_report"},
    }
    base.update(overrides)
    return base


def test_checkout_completed_marks_paid_and_advances_to_queue():
    job = _job()
    db = FakeDb(job)
    handled = co.handle_checkout_completed(db, _event(job))
    assert handled is True
    assert job.payment_status == "paid"
    assert job.amount_paid_cents == 14900
    assert job.stripe_payment_intent_id == "pi_test_456"
    assert job.paid_at is not None
    # submitted → … → under_review: now visible in the operator's queue.
    assert job.review_state == "under_review"
    assert db.commits >= 1


def test_checkout_completed_is_idempotent_on_replay():
    job = _job(payment_status="paid", review_state="under_review")
    db = FakeDb(job)
    handled = co.handle_checkout_completed(db, _event(job))
    assert handled is True
    assert job.payment_status == "paid"
    assert job.review_state == "under_review"


def test_event_without_trdr_metadata_falls_through_to_legacy():
    db = FakeDb(None)
    handled = co.handle_checkout_completed(db, {"id": "cs_x", "metadata": {}})
    assert handled is False
    assert db.commits == 0


def test_checkout_completed_enrolls_job_that_missed_begin_review():
    job = _job(review_state=None)
    db = FakeDb(job)
    assert co.handle_checkout_completed(db, _event(job)) is True
    assert job.review_state == "under_review"


def test_charge_refunded_matches_by_payment_intent():
    job = _job(payment_status="paid", stripe_payment_intent_id="pi_test_456")
    db = FakeDb(job)
    handled = co.handle_charge_refunded(db, {
        "id": "ch_test_1",
        "payment_intent": "pi_test_456",
        "metadata": {},
    })
    assert handled is True
    assert job.payment_status == "refunded"
    assert job.refunded_at is not None


def test_charge_refunded_unknown_falls_through():
    db = FakeDb(None)
    assert co.handle_charge_refunded(db, {"id": "ch_x", "metadata": {}}) is False


def test_create_checkout_rejects_wrong_product_for_workflow():
    job = _job(workflow_type="cbam_readiness", payment_status=None)
    user = SimpleNamespace(id=uuid.uuid4(), email="x@y.com")
    with pytest.raises(co.CheckoutError):
        co.create_checkout_session(FakeDb(job), job, user, "pack_review")


def test_create_checkout_rejects_already_paid():
    job = _job(workflow_type="exporter_presentation", payment_status="paid")
    user = SimpleNamespace(id=uuid.uuid4(), email="x@y.com")
    with pytest.raises(co.CheckoutError):
        co.create_checkout_session(FakeDb(job), job, user, "pack_review")


def test_lc_jobs_offer_three_tiers_and_readiness_offers_its_report():
    lc = _job(workflow_type="exporter_presentation")
    assert co.product_ids_for_session(lc) == list(co.LC_PRODUCT_IDS)
    rdy = _job(workflow_type="eudr_readiness")
    assert co.product_ids_for_session(rdy) == ["eudr_report"]


def test_catalog_amounts_match_launch_prices():
    amounts = {pid: p["amount_cents"] for pid, p in co.LAUNCH_PRODUCTS.items()}
    assert amounts == {
        "pack_review": 2900,
        "pack_review_memo": 4900,
        "priority_review": 7900,
        "cbam_report": 14900,
        "eudr_report": 14900,
        "cbam_eudr_bundle": 24900,
    }
