"""Validated Proofline workflow transitions with append-only domain events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models import TradeCase, TradeCaseEvent, TradeCaseStatus


AuditLogger = Callable[..., Any]


TRANSITIONS: dict[TradeCaseStatus, frozenset[TradeCaseStatus]] = {
    TradeCaseStatus.DRAFT: frozenset(
        {
            TradeCaseStatus.AWAITING_PAYMENT,
            TradeCaseStatus.SUBMITTED,
            TradeCaseStatus.CANCELLED,
        }
    ),
    TradeCaseStatus.AWAITING_PAYMENT: frozenset(
        {TradeCaseStatus.SUBMITTED, TradeCaseStatus.CANCELLED}
    ),
    TradeCaseStatus.SUBMITTED: frozenset(
        {TradeCaseStatus.PROCESSING, TradeCaseStatus.CANCELLED}
    ),
    TradeCaseStatus.PROCESSING: frozenset(
        {
            TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE,
            TradeCaseStatus.ACTION_REQUIRED,
            TradeCaseStatus.CANCELLED,
        }
    ),
    TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE: frozenset(
        {TradeCaseStatus.AWAITING_ANALYST_REVIEW, TradeCaseStatus.CANCELLED}
    ),
    TradeCaseStatus.AWAITING_ANALYST_REVIEW: frozenset(
        {
            TradeCaseStatus.ACTION_REQUIRED,
            TradeCaseStatus.FINAL_REVIEW,
            TradeCaseStatus.BLOCKED,
            TradeCaseStatus.CANCELLED,
        }
    ),
    TradeCaseStatus.ACTION_REQUIRED: frozenset(
        {TradeCaseStatus.CUSTOMER_RESUBMITTED, TradeCaseStatus.CANCELLED}
    ),
    TradeCaseStatus.CUSTOMER_RESUBMITTED: frozenset(
        {
            TradeCaseStatus.PROCESSING,
            TradeCaseStatus.AWAITING_ANALYST_REVIEW,
            TradeCaseStatus.FINAL_REVIEW,
            TradeCaseStatus.CANCELLED,
        }
    ),
    TradeCaseStatus.FINAL_REVIEW: frozenset(
        {
            TradeCaseStatus.CLEARED,
            TradeCaseStatus.CONDITIONALLY_CLEARED,
            TradeCaseStatus.ACTION_REQUIRED,
            TradeCaseStatus.BLOCKED,
            TradeCaseStatus.CANCELLED,
        }
    ),
    TradeCaseStatus.CLEARED: frozenset({TradeCaseStatus.CLOSED}),
    TradeCaseStatus.CONDITIONALLY_CLEARED: frozenset({TradeCaseStatus.CLOSED}),
    TradeCaseStatus.BLOCKED: frozenset({TradeCaseStatus.CLOSED}),
    TradeCaseStatus.CANCELLED: frozenset({TradeCaseStatus.CLOSED}),
    TradeCaseStatus.CLOSED: frozenset(),
}


ACTOR_TARGETS: dict[str, frozenset[TradeCaseStatus]] = {
    "customer": frozenset(
        {
            TradeCaseStatus.AWAITING_PAYMENT,
            TradeCaseStatus.SUBMITTED,
            TradeCaseStatus.CUSTOMER_RESUBMITTED,
            TradeCaseStatus.CANCELLED,
        }
    ),
    "system": frozenset(
        {
            TradeCaseStatus.AWAITING_PAYMENT,
            TradeCaseStatus.SUBMITTED,
            TradeCaseStatus.PROCESSING,
            TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE,
            TradeCaseStatus.AWAITING_ANALYST_REVIEW,
        }
    ),
    "reviewer": frozenset(
        {
            TradeCaseStatus.AWAITING_ANALYST_REVIEW,
            TradeCaseStatus.ACTION_REQUIRED,
            TradeCaseStatus.FINAL_REVIEW,
            TradeCaseStatus.CLEARED,
            TradeCaseStatus.CONDITIONALLY_CLEARED,
            TradeCaseStatus.BLOCKED,
            TradeCaseStatus.CANCELLED,
            TradeCaseStatus.CLOSED,
        }
    ),
}


class InvalidTradeCaseTransition(ValueError):
    """Raised when a state jump or actor is not allowed."""


def _as_status(value: TradeCaseStatus | str) -> TradeCaseStatus:
    try:
        return value if isinstance(value, TradeCaseStatus) else TradeCaseStatus(value)
    except ValueError as exc:
        raise InvalidTradeCaseTransition(f"Unknown Proofline status: {value!r}") from exc


def transition_case(
    db: Session,
    trade_case: TradeCase,
    to_status: TradeCaseStatus | str,
    *,
    actor_type: str,
    actor_user_id: Optional[Any],
    reason: Optional[str],
    idempotency_key: str,
    details: Optional[dict[str, Any]] = None,
    audit_logger: Optional[AuditLogger] = None,
    now: Optional[datetime] = None,
) -> TradeCaseEvent:
    """Transition a case and append one idempotent domain event.

    The caller owns the transaction.  An injected audit hook lets HTTP and job
    boundaries call the existing AuditService without coupling this domain
    service to request context or forcing a nested commit.
    """
    if not idempotency_key or not idempotency_key.strip():
        raise InvalidTradeCaseTransition("A non-empty idempotency key is required")

    existing = (
        db.query(TradeCaseEvent)
        .filter(
            TradeCaseEvent.trade_case_id == trade_case.id,
            TradeCaseEvent.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing is not None:
        return existing

    current = _as_status(trade_case.status)
    target = _as_status(to_status)
    allowed = TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTradeCaseTransition(
            f"Cannot transition Proofline case from {current.value!r} to {target.value!r}; "
            f"allowed: {sorted(item.value for item in allowed) or ['<terminal>']}"
        )

    actor_targets = ACTOR_TARGETS.get(actor_type)
    if actor_targets is None or target not in actor_targets:
        raise InvalidTradeCaseTransition(
            f"Actor type {actor_type!r} cannot transition a case to {target.value!r}"
        )
    if actor_type != "system" and actor_user_id is None:
        raise InvalidTradeCaseTransition(f"Actor user identity is required for {actor_type}")

    timestamp = now or datetime.now(timezone.utc)
    trade_case.status = target.value
    if target == TradeCaseStatus.SUBMITTED and trade_case.submitted_at is None:
        trade_case.submitted_at = timestamp
    elif target == TradeCaseStatus.PROCESSING and trade_case.processing_started_at is None:
        trade_case.processing_started_at = timestamp
    elif target == TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE:
        trade_case.automated_review_completed_at = timestamp
    elif target in {
        TradeCaseStatus.CLEARED,
        TradeCaseStatus.CONDITIONALLY_CLEARED,
        TradeCaseStatus.BLOCKED,
    }:
        trade_case.final_decision_at = timestamp
    elif target == TradeCaseStatus.CLOSED:
        trade_case.closed_at = timestamp

    event = TradeCaseEvent(
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        event_type="status_transition",
        from_status=current.value,
        to_status=target.value,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        reason=reason,
        details=details or {},
        idempotency_key=idempotency_key,
        occurred_at=timestamp,
    )
    db.add(event)

    if audit_logger is not None:
        audit_logger(
            action="proofline_status_transition",
            user_id=actor_user_id,
            resource_type="proofline_trade_case",
            resource_id=str(trade_case.id),
            request_data={"from_status": current.value, "to_status": target.value},
            audit_metadata={
                "actor_type": actor_type,
                "reason": reason,
                "idempotency_key": idempotency_key,
            },
        )
    return event


__all__ = [
    "ACTOR_TARGETS",
    "TRANSITIONS",
    "InvalidTradeCaseTransition",
    "transition_case",
]

