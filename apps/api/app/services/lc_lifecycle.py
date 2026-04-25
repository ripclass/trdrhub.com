"""LC lifecycle state machine helper.

Single public entry point: ``transition(db, session, to_state, actor,
reason=None, extra=None, force=False)``.

Enforces the allowed-transitions table from
``app.models.lc_lifecycle.LC_LIFECYCLE_TRANSITIONS``. On a successful
transition:
  * Updates ``ValidationSession.lifecycle_state`` and
    ``lifecycle_state_changed_at``.
  * Writes an ``LCLifecycleEvent`` row (append-only audit trail).
  * Caller is responsible for ``db.commit()``.

Raises ``InvalidLifecycleTransition`` when the transition is not allowed
and ``force=False``. Caller (router) translates that into a 400 with a
helpful payload listing the allowed next states.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import ValidationSession
from ..models.lc_lifecycle import (
    LC_LIFECYCLE_TRANSITIONS,
    LC_LIFECYCLE_DEFAULT_STATE,
    LCLifecycleEvent,
    LCLifecycleState,
    allowed_next_states,
    is_terminal_state,
)


class InvalidLifecycleTransition(ValueError):
    """Transition rejected by the allowed-transitions table.

    Carries the from/to states + the set of valid alternatives so the
    router can surface a useful 400 payload to the caller.
    """

    def __init__(
        self,
        *,
        from_state: str,
        to_state: str,
        allowed: frozenset[LCLifecycleState],
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        super().__init__(
            f"Cannot transition LC from {from_state!r} to {to_state!r}. "
            f"Allowed next states: {sorted(s.value for s in allowed) or '<terminal>'}"
        )


def current_state(session: ValidationSession) -> LCLifecycleState:
    """Return the validation_session's current lifecycle state as enum.

    Falls back to the default if the column is unset (defensive — the
    DB column has a server_default so this should never be None in
    practice, but tests sometimes construct objects without flushing).
    """
    raw = session.lifecycle_state or LC_LIFECYCLE_DEFAULT_STATE.value
    try:
        return LCLifecycleState(raw)
    except ValueError:
        # Stale value (e.g. an old state we deprecated). Fall back to
        # default rather than blowing up — caller can transition out.
        return LC_LIFECYCLE_DEFAULT_STATE


def transition(
    db: Session,
    session: ValidationSession,
    to_state: LCLifecycleState | str,
    actor_user_id: Optional[Any] = None,
    reason: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    force: bool = False,
) -> LCLifecycleEvent:
    """Move ``session`` to ``to_state``. Returns the event row.

    Raises ``InvalidLifecycleTransition`` when the transition is not
    allowed and ``force=False``.

    Caller commits.
    """
    if isinstance(to_state, str):
        try:
            to_state = LCLifecycleState(to_state)
        except ValueError as exc:
            raise InvalidLifecycleTransition(
                from_state=session.lifecycle_state or "<unknown>",
                to_state=str(to_state),
                allowed=frozenset(),
            ) from exc

    from_enum = current_state(session)
    from_value = from_enum.value

    if to_state == from_enum:
        # No-op transition. Don't write an event row, just return None
        # equivalent — but the contract says return an event, so write a
        # marker event with reason='noop' iff caller passed reason.
        # Cleaner: just skip. Callers that want re-stamps can pass force=True.
        if not force:
            # Write an audit event anyway so observability captures the
            # idempotent call (matters for repaper retries that land on
            # an already-resolved discrepancy).
            event = LCLifecycleEvent(
                validation_session_id=session.id,
                from_state=from_value,
                to_state=to_state.value,
                actor_user_id=actor_user_id,
                reason=reason or "noop",
                extra=extra,
            )
            db.add(event)
            return event

    allowed = allowed_next_states(from_enum)
    if to_state not in allowed and not force:
        raise InvalidLifecycleTransition(
            from_state=from_value,
            to_state=to_state.value,
            allowed=allowed,
        )

    session.lifecycle_state = to_state.value
    session.lifecycle_state_changed_at = datetime.now(timezone.utc)

    event = LCLifecycleEvent(
        validation_session_id=session.id,
        from_state=from_value,
        to_state=to_state.value,
        actor_user_id=actor_user_id,
        reason=reason,
        extra=extra,
    )
    db.add(event)

    return event


def history(
    db: Session, session: ValidationSession, limit: int = 100
) -> list[LCLifecycleEvent]:
    """Return the lifecycle event history for a session, newest first."""
    return (
        db.query(LCLifecycleEvent)
        .filter(LCLifecycleEvent.validation_session_id == session.id)
        .order_by(LCLifecycleEvent.created_at.desc())
        .limit(limit)
        .all()
    )


__all__ = [
    "InvalidLifecycleTransition",
    "current_state",
    "transition",
    "history",
    "is_terminal_state",
    "allowed_next_states",
]
