"""Proofline recommendation/final-decision launch guards."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models import TradeCaseDecision
from app.services.proofline.decisions import DecisionGuardError, record_decision


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

    def order_by(self, *_args):
        return self

    def first(self):
        return self.rows[-1] if self.rows else None


class _Db:
    def __init__(self):
        self.added = []

    def query(self, model):
        return _Query([row for row in self.added if isinstance(row, model)])

    def add(self, row):
        self.added.append(row)


def _case(**overrides):
    values = dict(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        status="final_review",
        payment_status="paid",
        recommended_decision="CONDITIONAL_CLEARANCE",
        final_decision=None,
        final_decision_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _finding(**overrides):
    values = dict(
        severity="medium",
        visibility="customer",
        status="open",
        title="Finding",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _check(**overrides):
    values = dict(
        module="rulhub",
        applicable=True,
        required=True,
        state="clear",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_paid_final_decision_requires_reviewer():
    with pytest.raises(DecisionGuardError, match="reviewer"):
        record_decision(
            _Db(),
            _case(),
            decision="CONDITIONAL_CLEARANCE",
            decision_type="final",
            summary="Proceed after listed conditions.",
            reason="Conditions are documented.",
            reviewer_user_id=None,
            idempotency_key="final-no-reviewer",
            system_version="proofline-1",
        )


def test_clear_rejects_unresolved_critical_finding_and_unavailable_required_check():
    reviewer = uuid.uuid4()
    with pytest.raises(DecisionGuardError, match="critical"):
        record_decision(
            _Db(),
            _case(recommended_decision="CLEAR"),
            decision="CLEAR",
            decision_type="final",
            summary="Clear.",
            reason="Automated and analyst review complete.",
            reviewer_user_id=reviewer,
            idempotency_key="critical-open",
            system_version="proofline-1",
            findings=[_finding(severity="critical")],
            checks=[_check()],
        )

    with pytest.raises(DecisionGuardError, match="required check"):
        record_decision(
            _Db(),
            _case(recommended_decision="CLEAR"),
            decision="CLEAR",
            decision_type="final",
            summary="Clear.",
            reason="Review complete.",
            reviewer_user_id=reviewer,
            idempotency_key="rulhub-down",
            system_version="proofline-1",
            findings=[],
            checks=[_check(state="unable_to_assess")],
        )


def test_override_requires_reason_and_preserves_previous_recommendation():
    db = _Db()
    trade_case = _case(recommended_decision="ACTION_REQUIRED")
    reviewer = uuid.uuid4()

    with pytest.raises(DecisionGuardError, match="override reason"):
        record_decision(
            db,
            trade_case,
            decision="CONDITIONAL_CLEARANCE",
            decision_type="final",
            summary="Proceed subject to conditions.",
            reason="Analyst reviewed the evidence.",
            reviewer_user_id=reviewer,
            idempotency_key="override-no-reason",
            system_version="proofline-1",
        )

    decision = record_decision(
        db,
        trade_case,
        decision="CONDITIONAL_CLEARANCE",
        decision_type="final",
        summary="Proceed subject to conditions.",
        reason="Analyst reviewed the evidence.",
        reviewer_user_id=reviewer,
        idempotency_key="override-with-reason",
        system_version="proofline-1",
        override_reason="The remaining gap is non-blocking and explicitly conditioned.",
    )

    assert decision.previous_recommendation == "ACTION_REQUIRED"
    assert decision.override_reason.startswith("The remaining gap")
    assert trade_case.final_decision == "CONDITIONAL_CLEARANCE"


def test_decisions_are_versioned_and_idempotent():
    db = _Db()
    trade_case = _case(recommended_decision=None, payment_status=None)

    recommendation = record_decision(
        db,
        trade_case,
        decision="MANUAL_REVIEW_REQUIRED",
        decision_type="recommendation",
        summary="Analyst review is required.",
        reason="One applicable check could not be assessed.",
        reviewer_user_id=None,
        idempotency_key="recommendation-1",
        system_version="proofline-1",
    )
    replay = record_decision(
        db,
        trade_case,
        decision="MANUAL_REVIEW_REQUIRED",
        decision_type="recommendation",
        summary="Analyst review is required.",
        reason="One applicable check could not be assessed.",
        reviewer_user_id=None,
        idempotency_key="recommendation-1",
        system_version="proofline-1",
    )

    assert recommendation.version_number == 1
    assert replay is recommendation
    assert len(db.added) == 1
