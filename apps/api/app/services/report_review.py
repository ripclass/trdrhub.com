"""Report-review state machine helper — Phase 1 launch (concierge queue).

Single public entry point:
    ``transition(db, session, to_state, actor_user_id=None, reason=None,
                 extra=None, force=False)``

Enforces ``app.models.report_review.REPORT_REVIEW_TRANSITIONS``. On a
successful transition it updates ``ValidationSession.review_state`` and
``review_state_changed_at``, and writes a ``ReportReviewEvent`` audit row.
Caller is responsible for ``db.commit()``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import ValidationSession
from ..models.report_review import (
    REPORT_REVIEW_DEFAULT_STATE,
    ReportReviewEvent,
    ReportReviewState,
    allowed_next_states,
    is_terminal_state,
)


class InvalidReviewTransition(ValueError):
    """Transition rejected by the allowed-transitions table."""

    def __init__(
        self,
        *,
        from_state: str,
        to_state: str,
        allowed: "frozenset[ReportReviewState]",
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        super().__init__(
            f"Cannot transition report review from {from_state!r} to {to_state!r}. "
            f"Allowed next states: {sorted(s.value for s in allowed) or '<terminal>'}"
        )


def current_state(session: ValidationSession) -> Optional[ReportReviewState]:
    """Return the session's review state as an enum, or None if not a review job."""
    raw = getattr(session, "review_state", None)
    if not raw:
        return None
    try:
        return ReportReviewState(raw)
    except ValueError:
        return None


def begin_review(
    db: Session,
    session: ValidationSession,
    actor_user_id: Optional[Any] = None,
    reason: Optional[str] = None,
) -> ReportReviewEvent:
    """Enroll a session into the concierge queue at the SUBMITTED state.

    Idempotent: if the session already has a review_state, this is a no-op that
    still writes an audit marker. Caller commits.
    """
    if getattr(session, "review_state", None):
        return _write_event(
            db, session,
            from_state=session.review_state,
            to_state=session.review_state,
            actor_user_id=actor_user_id,
            reason=reason or "begin_review (already enrolled)",
        )
    session.review_state = REPORT_REVIEW_DEFAULT_STATE.value
    session.review_state_changed_at = datetime.now(timezone.utc)
    return _write_event(
        db, session,
        from_state=None,
        to_state=REPORT_REVIEW_DEFAULT_STATE.value,
        actor_user_id=actor_user_id,
        reason=reason or "submitted to review queue",
    )


def transition(
    db: Session,
    session: ValidationSession,
    to_state: "ReportReviewState | str",
    actor_user_id: Optional[Any] = None,
    reason: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    force: bool = False,
) -> ReportReviewEvent:
    """Move ``session`` to ``to_state``. Returns the event row. Caller commits."""
    if isinstance(to_state, str):
        try:
            to_state = ReportReviewState(to_state)
        except ValueError as exc:
            raise InvalidReviewTransition(
                from_state=session.review_state or "<unknown>",
                to_state=str(to_state),
                allowed=frozenset(),
            ) from exc

    from_enum = current_state(session)
    from_value = from_enum.value if from_enum else None

    # No-op re-stamp (idempotent auto-advance retries land here).
    if from_enum is not None and to_state == from_enum and not force:
        return _write_event(
            db, session,
            from_state=from_value,
            to_state=to_state.value,
            actor_user_id=actor_user_id,
            reason=reason or "noop",
            extra=extra,
        )

    if from_enum is not None:
        allowed = allowed_next_states(from_enum)
        if to_state not in allowed and not force:
            raise InvalidReviewTransition(
                from_state=from_value or "<none>",
                to_state=to_state.value,
                allowed=allowed,
            )

    session.review_state = to_state.value
    session.review_state_changed_at = datetime.now(timezone.utc)
    return _write_event(
        db, session,
        from_state=from_value,
        to_state=to_state.value,
        actor_user_id=actor_user_id,
        reason=reason,
        extra=extra,
    )


def _write_event(
    db: Session,
    session: ValidationSession,
    *,
    from_state: Optional[str],
    to_state: str,
    actor_user_id: Optional[Any],
    reason: Optional[str],
    extra: Optional[dict[str, Any]] = None,
) -> ReportReviewEvent:
    event = ReportReviewEvent(
        validation_session_id=session.id,
        from_state=from_state,
        to_state=to_state,
        actor_user_id=actor_user_id,
        reason=reason,
        extra=extra,
    )
    db.add(event)
    return event


def on_engine_complete(
    db: Session,
    session: ValidationSession,
    actor_user_id: Optional[Any] = None,
    reason: Optional[str] = None,
) -> Optional[ReportReviewEvent]:
    """Advance a concierge session into the review queue once the engine finishes.

    Walks whatever intermediate states remain (submitted → processing →
    engine_complete → under_review) and lands on UNDER_REVIEW so the report
    appears in the operator's queue. No-op (returns None) if the session is not
    a concierge job or is already under review / delivered. Caller commits.
    """
    st = current_state(session)
    if st is None:
        return None
    if st in (ReportReviewState.UNDER_REVIEW, ReportReviewState.DELIVERED):
        return None

    last: Optional[ReportReviewEvent] = None
    if st == ReportReviewState.SUBMITTED:
        last = transition(db, session, ReportReviewState.PROCESSING,
                          actor_user_id, reason or "engine started")
        st = ReportReviewState.PROCESSING
    if st == ReportReviewState.PROCESSING:
        last = transition(db, session, ReportReviewState.ENGINE_COMPLETE,
                          actor_user_id, reason or "engine finished")
        st = ReportReviewState.ENGINE_COMPLETE
    if st in (ReportReviewState.ENGINE_COMPLETE, ReportReviewState.NEEDS_INFO):
        last = transition(db, session, ReportReviewState.UNDER_REVIEW,
                          actor_user_id, reason or "queued for review")
    return last


def history(
    db: Session, session: ValidationSession, limit: int = 100
) -> list[ReportReviewEvent]:
    """Return the review event history for a session, newest first."""
    return (
        db.query(ReportReviewEvent)
        .filter(ReportReviewEvent.validation_session_id == session.id)
        .order_by(ReportReviewEvent.created_at.desc())
        .limit(limit)
        .all()
    )


__all__ = [
    "InvalidReviewTransition",
    "current_state",
    "begin_review",
    "on_engine_complete",
    "transition",
    "history",
    "is_terminal_state",
    "allowed_next_states",
]
