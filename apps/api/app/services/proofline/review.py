"""Proofline analyst actions and reviewer-only workflow guards."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    ProoflineDecisionValue,
    ProoflineFinding,
    RemediationAction,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseEvent,
    TradeCaseStatus,
)
from app.services.proofline.decisions import record_decision
from app.services.proofline.state import transition_case


SYSTEM_VERSION = os.getenv("APP_VERSION", "proofline-v1")
REVIEW_QUEUE_STATUSES = (
    TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE.value,
    TradeCaseStatus.AWAITING_ANALYST_REVIEW.value,
    TradeCaseStatus.ACTION_REQUIRED.value,
    TradeCaseStatus.CUSTOMER_RESUBMITTED.value,
    TradeCaseStatus.FINAL_REVIEW.value,
)


class ReviewWorkflowError(ValueError):
    """A reviewer action is invalid for the current case state."""


def ensure_reviewable_status(status: str) -> None:
    if status not in REVIEW_QUEUE_STATUSES:
        raise ReviewWorkflowError(f"Case status {status!r} is not active in the analyst queue")


def decision_target_status(decision: ProoflineDecisionValue | str) -> TradeCaseStatus:
    value = decision.value if isinstance(decision, ProoflineDecisionValue) else str(decision)
    mapping = {
        ProoflineDecisionValue.CLEAR.value: TradeCaseStatus.CLEARED,
        ProoflineDecisionValue.CONDITIONAL_CLEARANCE.value: TradeCaseStatus.CONDITIONALLY_CLEARED,
        ProoflineDecisionValue.BLOCKED.value: TradeCaseStatus.BLOCKED,
        ProoflineDecisionValue.ACTION_REQUIRED.value: TradeCaseStatus.ACTION_REQUIRED,
        ProoflineDecisionValue.MANUAL_REVIEW_REQUIRED.value: TradeCaseStatus.ACTION_REQUIRED,
        ProoflineDecisionValue.UNABLE_TO_ASSESS.value: TradeCaseStatus.ACTION_REQUIRED,
    }
    try:
        return mapping[value]
    except KeyError as exc:
        raise ReviewWorkflowError(f"Unsupported Proofline decision: {value!r}") from exc


def append_reviewer_event(
    db: Session,
    trade_case: TradeCase,
    *,
    reviewer_user_id: Any,
    event_type: str,
    reason: str,
    details: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> TradeCaseEvent:
    event = TradeCaseEvent(
        id=uuid.uuid4(),
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        event_type=event_type,
        from_status=trade_case.status,
        to_status=trade_case.status,
        actor_type="reviewer",
        actor_user_id=reviewer_user_id,
        reason=reason,
        details=details or {},
        idempotency_key=idempotency_key or f"{event_type}:{uuid.uuid4()}",
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event


def claim_case(
    db: Session,
    trade_case: TradeCase,
    *,
    reviewer_user_id: Any,
    force: bool = False,
) -> TradeCase:
    ensure_reviewable_status(trade_case.status)
    if (
        trade_case.reviewer_user_id is not None
        and str(trade_case.reviewer_user_id) != str(reviewer_user_id)
        and not force
    ):
        raise ReviewWorkflowError("This case is already assigned to another reviewer")
    previous = trade_case.reviewer_user_id
    trade_case.reviewer_user_id = reviewer_user_id
    append_reviewer_event(
        db,
        trade_case,
        reviewer_user_id=reviewer_user_id,
        event_type="reviewer_assigned",
        reason="Analyst claimed the Proofline case",
        details={"previous_reviewer_id": str(previous) if previous else None},
    )
    return trade_case


def add_internal_note(
    db: Session,
    trade_case: TradeCase,
    *,
    reviewer_user_id: Any,
    note: str,
) -> TradeCaseEvent:
    ensure_reviewable_status(trade_case.status)
    if not note.strip():
        raise ReviewWorkflowError("Internal note cannot be empty")
    return append_reviewer_event(
        db,
        trade_case,
        reviewer_user_id=reviewer_user_id,
        event_type="reviewer_note",
        reason="Internal analyst note added",
        details={"visibility": "internal", "note": note.strip()},
    )


def request_correction(
    db: Session,
    trade_case: TradeCase,
    finding: ProoflineFinding,
    *,
    reviewer_user_id: Any,
    requested_action: str,
    responsible_party: Optional[str] = None,
    requested_document_type: Optional[str] = None,
    due_at: Optional[datetime] = None,
) -> RemediationAction:
    ensure_reviewable_status(trade_case.status)
    if str(finding.trade_case_id) != str(trade_case.id):
        raise ReviewWorkflowError("Finding does not belong to this trade case")
    if not requested_action.strip():
        raise ReviewWorkflowError("A clear customer action is required")
    round_number = int(trade_case.correction_rounds_used or 0) + 1
    action = RemediationAction(
        id=uuid.uuid4(),
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        finding_id=finding.id,
        requested_action=requested_action.strip(),
        responsible_party=responsible_party,
        requested_document_type=requested_document_type,
        due_at=due_at,
        status="requested",
        correction_round=round_number,
        requested_by_user_id=reviewer_user_id,
    )
    db.add(action)
    finding.status = "customer_action_required"
    finding.visibility = "customer"
    finding.reviewed_by_user_id = reviewer_user_id
    if trade_case.status != TradeCaseStatus.ACTION_REQUIRED.value:
        transition_case(
            db,
            trade_case,
            TradeCaseStatus.ACTION_REQUIRED,
            actor_type="reviewer",
            actor_user_id=reviewer_user_id,
            reason="Analyst requested customer correction",
            idempotency_key=f"correction-request:{action.id}",
            details={"finding_id": str(finding.id), "correction_round": round_number},
        )
    else:
        append_reviewer_event(
            db,
            trade_case,
            reviewer_user_id=reviewer_user_id,
            event_type="correction_requested",
            reason="Additional customer correction requested",
            details={"finding_id": str(finding.id), "correction_round": round_number},
        )
    return action


def approve_final_decision(
    db: Session,
    trade_case: TradeCase,
    *,
    reviewer_user_id: Any,
    decision: ProoflineDecisionValue | str,
    summary: str,
    reason: str,
    override_reason: Optional[str],
    idempotency_key: str,
) -> Any:
    ensure_reviewable_status(trade_case.status)
    if trade_case.status == TradeCaseStatus.AWAITING_ANALYST_REVIEW.value:
        transition_case(
            db,
            trade_case,
            TradeCaseStatus.FINAL_REVIEW,
            actor_type="reviewer",
            actor_user_id=reviewer_user_id,
            reason="Analyst started final decision review",
            idempotency_key=f"final-review:{idempotency_key}",
        )
    if trade_case.status != TradeCaseStatus.FINAL_REVIEW.value:
        raise ReviewWorkflowError("Resolve customer actions before approving a final decision")
    checks = (
        db.query(TradeCaseCheckRun)
        .filter(TradeCaseCheckRun.trade_case_id == trade_case.id)
        .all()
    )
    findings = (
        db.query(ProoflineFinding)
        .filter(ProoflineFinding.trade_case_id == trade_case.id)
        .all()
    )
    record = record_decision(
        db,
        trade_case,
        decision=decision,
        decision_type="final",
        summary=summary,
        reason=reason,
        reviewer_user_id=reviewer_user_id,
        idempotency_key=idempotency_key,
        system_version=SYSTEM_VERSION,
        findings=findings,
        checks=checks,
        contributing_finding_ids=[str(item.id) for item in findings],
        override_reason=override_reason,
    )
    transition_case(
        db,
        trade_case,
        decision_target_status(decision),
        actor_type="reviewer",
        actor_user_id=reviewer_user_id,
        reason=reason,
        idempotency_key=f"final-status:{idempotency_key}",
        details={"decision": record.decision, "decision_version": record.version_number},
    )
    return record


__all__ = [
    "REVIEW_QUEUE_STATUSES",
    "ReviewWorkflowError",
    "add_internal_note",
    "approve_final_decision",
    "claim_case",
    "decision_target_status",
    "ensure_reviewable_status",
    "request_correction",
]
