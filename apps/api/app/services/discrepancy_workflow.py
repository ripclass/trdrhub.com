"""Discrepancy state-machine helper — Phase A2.

Same shape as ``app/services/lc_lifecycle.py``: a single ``transition``
entry point that enforces the allowed-transitions table, optionally
writes a ``DiscrepancyComment`` audit row, and lets the caller commit.

The legacy ``Discrepancy`` model lives in ``app/models.py`` (added
state + resolution columns in the 20260427 migration). The new
``DiscrepancyComment`` and ``RepaperingRequest`` models live in
``app/models/discrepancy_workflow.py``.

Caller responsibility:
  * Pass the right actor_user_id (router gets it from get_current_user).
  * Commit. The service stages writes via ``db.add`` only.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import Discrepancy
from ..models.discrepancy_workflow import (
    DISCREPANCY_DEFAULT_STATE,
    DiscrepancyComment,
    DiscrepancyCommentSource,
    DiscrepancyState,
    REPAPERING_TRANSITIONS,
    RepaperingRequest,
    RepaperingState,
    discrepancy_allowed_next_states,
    discrepancy_is_terminal,
    repapering_allowed_next_states,
)


# ---------------------------------------------------------------------------
# Discrepancy state machine
# ---------------------------------------------------------------------------


class InvalidDiscrepancyTransition(ValueError):
    """Transition rejected by the allowed-transitions table."""

    def __init__(
        self,
        *,
        from_state: str,
        to_state: str,
        allowed: frozenset[DiscrepancyState],
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        super().__init__(
            f"Cannot transition discrepancy from {from_state!r} to {to_state!r}. "
            f"Allowed next: {sorted(s.value for s in allowed) or '<terminal>'}"
        )


def discrepancy_current_state(discrepancy: Discrepancy) -> DiscrepancyState:
    raw = discrepancy.state or DISCREPANCY_DEFAULT_STATE.value
    try:
        return DiscrepancyState(raw)
    except ValueError:
        return DISCREPANCY_DEFAULT_STATE


def transition_discrepancy(
    db: Session,
    discrepancy: Discrepancy,
    to_state: DiscrepancyState | str,
    *,
    actor_user_id: Optional[Any] = None,
    resolution_action: Optional[str] = None,
    resolution_evidence_session_id: Optional[Any] = None,
    system_comment: Optional[str] = None,
    force: bool = False,
) -> Optional[DiscrepancyComment]:
    """Move a discrepancy to a new state.

    Updates ``state``, ``state_changed_at``, and (when entering
    ``RESOLVED``/terminal-via-action) ``resolved_at``,
    ``resolution_action``, ``resolution_evidence_session_id``.

    Optionally writes a system audit comment so the thread carries
    machine-driven events alongside human messages.

    Caller commits.
    """
    if isinstance(to_state, str):
        try:
            to_state = DiscrepancyState(to_state)
        except ValueError as exc:
            raise InvalidDiscrepancyTransition(
                from_state=discrepancy.state or "<unknown>",
                to_state=str(to_state),
                allowed=frozenset(),
            ) from exc

    from_enum = discrepancy_current_state(discrepancy)
    from_value = from_enum.value

    if to_state == from_enum and not force:
        # Idempotent. Don't double-write state_changed_at; do leave a
        # system comment if the caller asked for one.
        if system_comment:
            comment = DiscrepancyComment(
                discrepancy_id=discrepancy.id,
                author_user_id=actor_user_id,
                body=system_comment,
                source=DiscrepancyCommentSource.SYSTEM.value,
            )
            db.add(comment)
            return comment
        return None

    allowed = discrepancy_allowed_next_states(from_enum)
    if to_state not in allowed and not force:
        raise InvalidDiscrepancyTransition(
            from_state=from_value,
            to_state=to_state.value,
            allowed=allowed,
        )

    now = datetime.now(timezone.utc)
    discrepancy.state = to_state.value
    discrepancy.state_changed_at = now

    # Side-effects per target state.
    if to_state == DiscrepancyState.ACKNOWLEDGED and discrepancy.acknowledged_at is None:
        discrepancy.acknowledged_at = now
    if to_state in (
        DiscrepancyState.ACCEPTED,
        DiscrepancyState.WAIVED,
        DiscrepancyState.RESOLVED,
    ):
        if discrepancy.resolved_at is None:
            discrepancy.resolved_at = now
        if resolution_action:
            discrepancy.resolution_action = resolution_action
        elif to_state == DiscrepancyState.RESOLVED:
            discrepancy.resolution_action = "resolved"
        else:
            discrepancy.resolution_action = to_state.value
    if resolution_evidence_session_id is not None:
        discrepancy.resolution_evidence_session_id = resolution_evidence_session_id

    body = system_comment or f"State changed: {from_value} -> {to_state.value}"
    comment = DiscrepancyComment(
        discrepancy_id=discrepancy.id,
        author_user_id=actor_user_id,
        body=body,
        source=DiscrepancyCommentSource.SYSTEM.value,
    )
    db.add(comment)
    return comment


def add_user_comment(
    db: Session,
    discrepancy: Discrepancy,
    *,
    body: str,
    author_user_id: Any,
) -> DiscrepancyComment:
    """Append a user-authored comment. Auto-transitions ``raised`` →
    ``responded`` so the thread reflects engagement.

    Returns the comment row. Caller commits.
    """
    comment = DiscrepancyComment(
        discrepancy_id=discrepancy.id,
        author_user_id=author_user_id,
        body=body,
        source=DiscrepancyCommentSource.USER.value,
    )
    db.add(comment)

    current = discrepancy_current_state(discrepancy)
    if current in (DiscrepancyState.RAISED, DiscrepancyState.ACKNOWLEDGED):
        # Light-touch auto-advance — the user has at least engaged.
        try:
            transition_discrepancy(
                db,
                discrepancy,
                DiscrepancyState.RESPONDED,
                actor_user_id=author_user_id,
                system_comment=None,  # don't double up — the user comment IS the engagement signal
            )
        except InvalidDiscrepancyTransition:
            pass
    return comment


def add_recipient_comment(
    db: Session,
    discrepancy: Discrepancy,
    *,
    body: str,
    author_email: str,
    author_display_name: Optional[str] = None,
) -> DiscrepancyComment:
    """Append a comment from a token-authed re-papering recipient
    (no platform account)."""
    comment = DiscrepancyComment(
        discrepancy_id=discrepancy.id,
        author_user_id=None,
        author_email=author_email,
        author_display_name=author_display_name,
        body=body,
        source=DiscrepancyCommentSource.RECIPIENT.value,
    )
    db.add(comment)
    return comment


def assign_discrepancy_owner(
    db: Session,
    discrepancy: Discrepancy,
    *,
    owner_user_id: Any,
    actor_user_id: Optional[Any] = None,
) -> DiscrepancyComment:
    """Set ``owner_user_id`` and write an audit-trail system comment.
    Idempotent: assigning to the existing owner is a no-op (returns
    None)."""
    if discrepancy.owner_user_id == owner_user_id:
        return None  # type: ignore[return-value]
    previous = discrepancy.owner_user_id
    discrepancy.owner_user_id = owner_user_id
    body = f"Owner changed: {previous!s} -> {owner_user_id!s}"
    comment = DiscrepancyComment(
        discrepancy_id=discrepancy.id,
        author_user_id=actor_user_id,
        body=body,
        source=DiscrepancyCommentSource.SYSTEM.value,
    )
    db.add(comment)
    return comment


# ---------------------------------------------------------------------------
# Re-papering loop
# ---------------------------------------------------------------------------


class InvalidRepaperingTransition(ValueError):
    def __init__(
        self,
        *,
        from_state: str,
        to_state: str,
        allowed: frozenset[RepaperingState],
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        super().__init__(
            f"Cannot transition repapering from {from_state!r} to {to_state!r}. "
            f"Allowed next: {sorted(s.value for s in allowed) or '<terminal>'}"
        )


def create_repapering_request(
    db: Session,
    discrepancy: Discrepancy,
    *,
    requester_user_id: Any,
    recipient_email: str,
    recipient_display_name: Optional[str] = None,
    message: Optional[str] = None,
) -> RepaperingRequest:
    """Create a re-papering request and transition the discrepancy to
    ``REPAPER`` state. Returns the request row (with access_token
    populated). Caller commits.
    """
    request = RepaperingRequest(
        discrepancy_id=discrepancy.id,
        requester_user_id=requester_user_id,
        recipient_email=recipient_email,
        recipient_display_name=recipient_display_name,
        access_token=secrets.token_urlsafe(32),
        message=message,
        state=RepaperingState.REQUESTED.value,
    )
    db.add(request)

    # Transition the parent discrepancy. Best-effort — if it's already in
    # REPAPER (multiple requests on the same discrepancy) or in a state
    # that doesn't allow it, swallow the error so the request still
    # lands.
    try:
        transition_discrepancy(
            db,
            discrepancy,
            DiscrepancyState.REPAPER,
            actor_user_id=requester_user_id,
            system_comment=f"Re-papering requested from {recipient_email}",
        )
    except InvalidDiscrepancyTransition:
        pass

    return request


def transition_repapering(
    db: Session,
    request: RepaperingRequest,
    to_state: RepaperingState | str,
    *,
    replacement_session_id: Optional[Any] = None,
    force: bool = False,
) -> None:
    """Move a re-papering request to a new state. Caller commits."""
    if isinstance(to_state, str):
        try:
            to_state = RepaperingState(to_state)
        except ValueError as exc:
            raise InvalidRepaperingTransition(
                from_state=request.state or "<unknown>",
                to_state=str(to_state),
                allowed=frozenset(),
            ) from exc

    try:
        from_enum = RepaperingState(request.state)
    except ValueError:
        from_enum = RepaperingState.REQUESTED

    if to_state == from_enum and not force:
        return

    allowed = repapering_allowed_next_states(from_enum)
    if to_state not in allowed and not force:
        raise InvalidRepaperingTransition(
            from_state=from_enum.value,
            to_state=to_state.value,
            allowed=allowed,
        )

    now = datetime.now(timezone.utc)
    request.state = to_state.value
    if to_state == RepaperingState.IN_PROGRESS and request.opened_at is None:
        request.opened_at = now
    if to_state == RepaperingState.CORRECTED and request.submitted_at is None:
        request.submitted_at = now
    if to_state == RepaperingState.RESOLVED and request.resolved_at is None:
        request.resolved_at = now
    if to_state == RepaperingState.CANCELLED and request.cancelled_at is None:
        request.cancelled_at = now
    if replacement_session_id is not None:
        request.replacement_session_id = replacement_session_id


__all__ = [
    "InvalidDiscrepancyTransition",
    "InvalidRepaperingTransition",
    "add_recipient_comment",
    "add_user_comment",
    "assign_discrepancy_owner",
    "create_repapering_request",
    "discrepancy_current_state",
    "discrepancy_is_terminal",
    "transition_discrepancy",
    "transition_repapering",
]
