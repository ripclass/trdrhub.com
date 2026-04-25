"""Discrepancy resolution + re-papering models — Phase A2 of Path A.

Three pieces work together:

  * ``DiscrepancyState`` enum + ``DISCREPANCY_TRANSITIONS`` table — drives
    the state machine in ``app/services/discrepancy_workflow.py``.
  * ``DiscrepancyComment`` — append-only thread per discrepancy.
    Comments can come from platform users, re-papering recipients
    (token-authed, no account), or the system (auto-events like
    "re-validation cleared this discrepancy").
  * ``RepaperingRequest`` — the loop for asking a counterparty (a
    supplier, an internal team member, an agent) to fix a flagged
    document and re-upload. Token-authed so non-platform recipients
    can use it.

The legacy ``Discrepancy`` model in ``app/models.py`` gets the
state-machine columns added directly (state, owner_user_id,
acknowledged_at, resolved_at, resolution_action,
resolution_evidence_session_id, updated_at). Migration
``20260427_add_discrepancy_workflow`` ships all three changes.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


# ---------------------------------------------------------------------------
# Discrepancy state machine
# ---------------------------------------------------------------------------


class DiscrepancyState(str, enum.Enum):
    """Lifecycle of a discrepancy from auto-flagged to resolved.

    Default flow on the happy path:
        raised -> acknowledged -> responded -> repaper -> resolved

    Other terminal-ish states:
        accepted, rejected, waived (audit-trail-final, may still
        accept comments).
    """

    RAISED = "raised"
    ACKNOWLEDGED = "acknowledged"
    RESPONDED = "responded"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WAIVED = "waived"
    REPAPER = "repaper"
    RESOLVED = "resolved"


DISCREPANCY_STATE_VALUES = tuple(s.value for s in DiscrepancyState)

DISCREPANCY_TERMINAL_STATES = frozenset(
    {DiscrepancyState.ACCEPTED, DiscrepancyState.WAIVED, DiscrepancyState.RESOLVED}
)

DISCREPANCY_DEFAULT_STATE = DiscrepancyState.RAISED


# Allowed transitions table. Mirrors the LC-lifecycle pattern.
# Anything not in this map is rejected unless the caller passes
# ``force=True`` (admin override path).
DISCREPANCY_TRANSITIONS: dict[DiscrepancyState, frozenset[DiscrepancyState]] = {
    DiscrepancyState.RAISED: frozenset(
        {
            DiscrepancyState.ACKNOWLEDGED,
            DiscrepancyState.ACCEPTED,
            DiscrepancyState.REJECTED,
            DiscrepancyState.WAIVED,
            DiscrepancyState.REPAPER,
            DiscrepancyState.RESPONDED,
        }
    ),
    DiscrepancyState.ACKNOWLEDGED: frozenset(
        {
            DiscrepancyState.RESPONDED,
            DiscrepancyState.ACCEPTED,
            DiscrepancyState.REJECTED,
            DiscrepancyState.WAIVED,
            DiscrepancyState.REPAPER,
        }
    ),
    DiscrepancyState.RESPONDED: frozenset(
        {
            DiscrepancyState.ACCEPTED,
            DiscrepancyState.REJECTED,
            DiscrepancyState.WAIVED,
            DiscrepancyState.REPAPER,
            DiscrepancyState.RESOLVED,
        }
    ),
    DiscrepancyState.REPAPER: frozenset(
        {
            DiscrepancyState.RESOLVED,
            DiscrepancyState.REJECTED,  # re-papered docs still don't satisfy
            DiscrepancyState.ACCEPTED,
        }
    ),
    DiscrepancyState.ACCEPTED: frozenset(
        # Accepted == acknowledging the discrepancy is real. Can still
        # repaper or resolve later.
        {DiscrepancyState.REPAPER, DiscrepancyState.RESOLVED, DiscrepancyState.WAIVED}
    ),
    DiscrepancyState.REJECTED: frozenset(
        # Rejection means "user disputes" — bank/admin can override to
        # waive or resolved.
        {DiscrepancyState.WAIVED, DiscrepancyState.RESOLVED, DiscrepancyState.RESPONDED}
    ),
    DiscrepancyState.WAIVED: frozenset(),  # terminal
    DiscrepancyState.RESOLVED: frozenset(),  # terminal
}


def discrepancy_allowed_next_states(
    current: DiscrepancyState | str,
) -> frozenset[DiscrepancyState]:
    if isinstance(current, str):
        try:
            current = DiscrepancyState(current)
        except ValueError:
            return frozenset()
    return DISCREPANCY_TRANSITIONS.get(current, frozenset())


def discrepancy_is_terminal(state: DiscrepancyState | str) -> bool:
    if isinstance(state, str):
        try:
            state = DiscrepancyState(state)
        except ValueError:
            return False
    return state in DISCREPANCY_TERMINAL_STATES


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class DiscrepancyCommentSource(str, enum.Enum):
    USER = "user"            # platform user (signed in)
    RECIPIENT = "recipient"  # re-papering recipient (token-authed)
    SYSTEM = "system"        # auto-event (state change, re-validate result)


class DiscrepancyComment(Base):
    """Append-only thread per discrepancy.

    No edit, no delete (audit trail). Soft-delete via the parent
    discrepancy's deleted_at.
    """

    __tablename__ = "discrepancy_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discrepancy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discrepancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # author_user_id is set when the commenter has a platform account.
    # NULL for re-papering recipients without an account; in that case
    # author_email + author_display_name carry the identity.
    author_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_email = Column(String(320), nullable=True)
    author_display_name = Column(String(128), nullable=True)

    body = Column(Text, nullable=False)
    source = Column(
        String(16),
        nullable=False,
        default=DiscrepancyCommentSource.USER.value,
        server_default=DiscrepancyCommentSource.USER.value,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_discrepancy_comments_discrepancy_created",
            "discrepancy_id",
            "created_at",
        ),
    )


# ---------------------------------------------------------------------------
# Re-papering requests
# ---------------------------------------------------------------------------


class RepaperingState(str, enum.Enum):
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    CORRECTED = "corrected"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


REPAPERING_STATE_VALUES = tuple(s.value for s in RepaperingState)


REPAPERING_TRANSITIONS: dict[RepaperingState, frozenset[RepaperingState]] = {
    RepaperingState.REQUESTED: frozenset(
        {RepaperingState.IN_PROGRESS, RepaperingState.CANCELLED}
    ),
    RepaperingState.IN_PROGRESS: frozenset(
        {RepaperingState.CORRECTED, RepaperingState.CANCELLED}
    ),
    RepaperingState.CORRECTED: frozenset(
        {RepaperingState.RESOLVED, RepaperingState.IN_PROGRESS, RepaperingState.CANCELLED}
    ),
    RepaperingState.RESOLVED: frozenset(),
    RepaperingState.CANCELLED: frozenset(),
}


class RepaperingRequest(Base):
    """One re-papering loop per discrepancy.

    Created when a user clicks "Ask supplier to fix this". Carries a
    long-lived random ``access_token`` so the recipient can hit
    ``/repaper/{token}`` without an account.

    Lifecycle: requested -> in_progress -> corrected -> resolved
    (or cancelled at any non-terminal point).

    On ``corrected``, the upload kicks a fresh validation. If that
    validation comes back clean for the original discrepancy, we set
    ``state = resolved``, link ``replacement_session_id``, and
    transition the parent discrepancy to ``RESOLVED``.
    """

    __tablename__ = "repapering_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discrepancy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discrepancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    recipient_email = Column(String(320), nullable=False)
    recipient_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_display_name = Column(String(128), nullable=True)

    # Long URL-safe random token. Generate via secrets.token_urlsafe(32)
    # at insert time. Unique-indexed.
    access_token = Column(String(64), nullable=False, unique=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    message = Column(Text, nullable=True)
    state = Column(
        String(16),
        nullable=False,
        default=RepaperingState.REQUESTED.value,
        server_default=RepaperingState.REQUESTED.value,
    )

    replacement_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("validation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    opened_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_repapering_requests_token", "access_token", unique=True),
        Index("ix_repapering_requests_discrepancy", "discrepancy_id"),
        Index("ix_repapering_requests_state", "state"),
    )


def repapering_allowed_next_states(
    current: RepaperingState | str,
) -> frozenset[RepaperingState]:
    if isinstance(current, str):
        try:
            current = RepaperingState(current)
        except ValueError:
            return frozenset()
    return REPAPERING_TRANSITIONS.get(current, frozenset())


__all__ = [
    "DISCREPANCY_DEFAULT_STATE",
    "DISCREPANCY_STATE_VALUES",
    "DISCREPANCY_TERMINAL_STATES",
    "DISCREPANCY_TRANSITIONS",
    "DiscrepancyComment",
    "DiscrepancyCommentSource",
    "DiscrepancyState",
    "REPAPERING_STATE_VALUES",
    "REPAPERING_TRANSITIONS",
    "RepaperingRequest",
    "RepaperingState",
    "discrepancy_allowed_next_states",
    "discrepancy_is_terminal",
    "repapering_allowed_next_states",
]
