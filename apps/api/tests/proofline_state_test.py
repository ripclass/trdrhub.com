"""Proofline workflow transition and domain-audit behavior."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models import TradeCaseEvent
from app.services.proofline.state import (
    InvalidTradeCaseTransition,
    transition_case,
)


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *criteria):
        for criterion in criteria:
            column = getattr(getattr(criterion, "left", None), "name", None)
            expected = getattr(getattr(criterion, "right", None), "value", None)
            if column is not None:
                self.rows = [
                    row for row in self.rows if getattr(row, column, None) == expected
                ]
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _Db:
    def __init__(self):
        self.added = []

    def query(self, model):
        rows = [row for row in self.added if isinstance(row, model)]
        return _Query(rows)

    def add(self, row):
        self.added.append(row)


def _case(status="draft"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        status=status,
        submitted_at=None,
        processing_started_at=None,
        automated_review_completed_at=None,
        final_decision_at=None,
        closed_at=None,
    )


def test_happy_path_transitions_are_validated_timestamped_and_audited():
    db = _Db()
    trade_case = _case()
    actor_id = uuid.uuid4()
    audit_calls = []
    path = [
        ("awaiting_payment", "customer"),
        ("submitted", "system"),
        ("processing", "system"),
        ("automated_review_complete", "system"),
        ("awaiting_analyst_review", "system"),
        ("action_required", "reviewer"),
        ("customer_resubmitted", "customer"),
        ("final_review", "reviewer"),
        ("cleared", "reviewer"),
        ("closed", "reviewer"),
    ]

    for index, (target, actor_type) in enumerate(path):
        event = transition_case(
            db,
            trade_case,
            target,
            actor_type=actor_type,
            actor_user_id=actor_id if actor_type != "system" else None,
            reason=f"step {index}",
            idempotency_key=f"transition-{index}",
            audit_logger=lambda **values: audit_calls.append(values),
        )
        assert event.to_status == target
        assert event.from_status != event.to_status
        assert event.actor_type == actor_type
        assert event.occurred_at is not None

    assert trade_case.status == "closed"
    assert trade_case.submitted_at is not None
    assert trade_case.processing_started_at is not None
    assert trade_case.automated_review_completed_at is not None
    assert trade_case.final_decision_at is not None
    assert trade_case.closed_at is not None
    assert len([item for item in db.added if isinstance(item, TradeCaseEvent)]) == len(path)
    assert len(audit_calls) == len(path)
    assert all(call["resource_type"] == "proofline_trade_case" for call in audit_calls)


def test_invalid_jump_and_wrong_actor_are_rejected_without_mutation():
    db = _Db()
    trade_case = _case()

    with pytest.raises(InvalidTradeCaseTransition):
        transition_case(
            db,
            trade_case,
            "cleared",
            actor_type="customer",
            actor_user_id=uuid.uuid4(),
            reason="skip review",
            idempotency_key="invalid-jump",
        )

    with pytest.raises(InvalidTradeCaseTransition):
        transition_case(
            db,
            trade_case,
            "processing",
            actor_type="customer",
            actor_user_id=uuid.uuid4(),
            reason="customer cannot run engine",
            idempotency_key="wrong-actor",
        )

    assert trade_case.status == "draft"
    assert db.added == []


def test_replayed_transition_returns_existing_event_without_duplicate_audit():
    db = _Db()
    trade_case = _case()
    audit_calls = []
    kwargs = dict(
        actor_type="customer",
        actor_user_id=uuid.uuid4(),
        reason="ready for checkout",
        idempotency_key="same-transition",
        audit_logger=lambda **values: audit_calls.append(values),
    )

    first = transition_case(db, trade_case, "awaiting_payment", **kwargs)
    replay = transition_case(db, trade_case, "awaiting_payment", **kwargs)

    assert replay is first
    assert len(db.added) == 1
    assert len(audit_calls) == 1
