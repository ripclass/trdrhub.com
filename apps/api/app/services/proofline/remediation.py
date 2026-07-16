"""Customer response and correction-round workflow for Proofline."""

from __future__ import annotations

import uuid
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.models import RemediationAction, TradeCase, TradeCaseDocument, TradeCaseStatus
from app.services.proofline.review import append_reviewer_event
from app.services.proofline.state import transition_case


class RemediationWorkflowError(ValueError):
    """Customer remediation evidence is incomplete or out of sequence."""


def next_correction_round(rounds_used: int | None) -> int:
    return max(0, int(rounds_used or 0)) + 1


def validate_resubmission(actions: Iterable[Any]) -> None:
    rows = list(actions)
    if not rows:
        raise RemediationWorkflowError("No customer correction requests are open")
    incomplete = [
        item for item in rows
        if item.status not in {"customer_responded", "resolved"}
        or (
            item.status == "customer_responded"
            and not (str(item.customer_response or "").strip() or item.correction_document_id)
        )
    ]
    if incomplete:
        raise RemediationWorkflowError("Respond to every open correction request before final review")


def respond_to_action(
    db: Session,
    trade_case: TradeCase,
    action: RemediationAction,
    *,
    customer_user_id: Any,
    response: Optional[str],
    correction_document: Optional[TradeCaseDocument],
) -> RemediationAction:
    if trade_case.status != TradeCaseStatus.ACTION_REQUIRED.value:
        raise RemediationWorkflowError("This case is not awaiting customer corrections")
    if str(action.trade_case_id) != str(trade_case.id):
        raise RemediationWorkflowError("Correction request does not belong to this trade case")
    if correction_document is not None and (
        str(correction_document.trade_case_id) != str(trade_case.id)
        or str(correction_document.company_id) != str(trade_case.company_id)
    ):
        raise RemediationWorkflowError("Corrected document does not belong to this trade case")
    clean_response = str(response or "").strip()
    if not clean_response and correction_document is None:
        raise RemediationWorkflowError("Add a response or select the corrected document")
    action.customer_response = clean_response or None
    action.correction_document_id = correction_document.id if correction_document else None
    action.status = "customer_responded"
    # Reuse the append-only event helper; actor fields are corrected to the
    # customer immediately so internal/customer provenance stays explicit.
    event = append_reviewer_event(
        db,
        trade_case,
        reviewer_user_id=customer_user_id,
        event_type="customer_correction_response",
        reason="Customer responded to a remediation request",
        details={
            "action_id": str(action.id),
            "correction_document_id": str(correction_document.id) if correction_document else None,
        },
        idempotency_key=f"customer-response:{action.id}:{uuid.uuid4()}",
    )
    event.actor_type = "customer"
    return action


def submit_corrections(
    db: Session,
    trade_case: TradeCase,
    *,
    customer_user_id: Any,
    actions: Iterable[RemediationAction],
) -> None:
    if trade_case.status != TradeCaseStatus.ACTION_REQUIRED.value:
        raise RemediationWorkflowError("This case is not awaiting customer corrections")
    action_rows = list(actions)
    validate_resubmission(action_rows)
    round_number = max(
        next_correction_round(trade_case.correction_rounds_used),
        max((int(item.correction_round or 1) for item in action_rows), default=1),
    )
    trade_case.correction_rounds_used = round_number
    for action in action_rows:
        if action.status == "customer_responded":
            action.status = "submitted_for_review"
    transition_case(
        db,
        trade_case,
        TradeCaseStatus.CUSTOMER_RESUBMITTED,
        actor_type="customer",
        actor_user_id=customer_user_id,
        reason="Customer submitted corrections for final review",
        idempotency_key=f"customer-resubmit:{trade_case.id}:{round_number}",
        details={"correction_round": round_number},
    )


__all__ = [
    "RemediationWorkflowError",
    "next_correction_round",
    "respond_to_action",
    "submit_corrections",
    "validate_resubmission",
]
