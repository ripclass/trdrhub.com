"""Report-review (concierge) state machine — Phase 1 of the 2026-07 launch.

TRDR Hub launches as service-as-software: a customer submits documents, the
engine runs, and then a human (Ripon) reviews every report before it is
delivered. This module models that back-office review workflow as a state
machine attached to ``ValidationSession``, deliberately SEPARATE from:

  * ``ValidationSession.status`` (SessionStatus) — the extraction/validation
    pipeline's own lifecycle (created → processing → completed).
  * ``ValidationSession.lifecycle_state`` (LCLifecycleState) — the UCP600
    banker's-eye view of the LC itself.

``review_state`` is NULLABLE on ValidationSession: a null value means the
session is a legacy self-serve validation (results visible as soon as the
engine finishes). A non-null value means the session went through the concierge
queue and its results are withheld from the customer until ``delivered``.

Every transition writes a ``ReportReviewEvent`` row (append-only audit trail),
mirroring the LCLifecycleEvent pattern.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from .base import Base


class ReportReviewState(str, enum.Enum):
    """Concierge review workflow states for a submitted report.

    Flow:
        submitted -> processing -> engine_complete -> under_review -> delivered

    ``needs_info`` is an off-ramp reachable from any active state when the
    operator needs more from the customer; it flows back into the pipeline
    (processing) or straight to review once resolved.

    Terminal: delivered.
    """

    SUBMITTED = "submitted"          # customer submitted; queued (post-payment in Phase 5)
    PROCESSING = "processing"        # engine (extraction + validation) is running
    ENGINE_COMPLETE = "engine_complete"  # engine finished; not yet in the human queue
    UNDER_REVIEW = "under_review"    # in the operator's review queue
    NEEDS_INFO = "needs_info"        # blocked on the customer for more information
    DELIVERED = "delivered"          # operator approved; report released to the customer


REPORT_REVIEW_STATE_VALUES = tuple(s.value for s in ReportReviewState)

REPORT_REVIEW_TERMINAL_STATES = frozenset({ReportReviewState.DELIVERED})

# Where a concierge submission starts.
REPORT_REVIEW_DEFAULT_STATE = ReportReviewState.SUBMITTED


# Allowed-transitions table. The service helper enforces this; anything not
# listed raises unless the caller passes force=True (admin override).
REPORT_REVIEW_TRANSITIONS: dict[ReportReviewState, frozenset[ReportReviewState]] = {
    ReportReviewState.SUBMITTED: frozenset(
        {ReportReviewState.PROCESSING, ReportReviewState.NEEDS_INFO}
    ),
    ReportReviewState.PROCESSING: frozenset(
        {ReportReviewState.ENGINE_COMPLETE, ReportReviewState.NEEDS_INFO}
    ),
    ReportReviewState.ENGINE_COMPLETE: frozenset(
        {ReportReviewState.UNDER_REVIEW, ReportReviewState.NEEDS_INFO}
    ),
    ReportReviewState.UNDER_REVIEW: frozenset(
        {ReportReviewState.DELIVERED, ReportReviewState.NEEDS_INFO}
    ),
    ReportReviewState.NEEDS_INFO: frozenset(
        {ReportReviewState.PROCESSING, ReportReviewState.UNDER_REVIEW}
    ),
    # Terminal — re-opening a delivered report requires force=True.
    ReportReviewState.DELIVERED: frozenset(),
}


class ReportReviewEvent(Base):
    """Append-only event log for report-review state transitions."""

    __tablename__ = "report_review_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("validation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_state = Column(String(50), nullable=True)  # nullable for the "born" event
    to_state = Column(String(50), nullable=False)

    # Who pushed it. Nullable for system-driven transitions (pipeline auto-advance).
    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reason = Column(Text, nullable=True)
    extra = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_report_review_events_session_created",
            "validation_session_id",
            "created_at",
        ),
    )


def is_terminal_state(state: "ReportReviewState | str") -> bool:
    if isinstance(state, str):
        try:
            state = ReportReviewState(state)
        except ValueError:
            return False
    return state in REPORT_REVIEW_TERMINAL_STATES


def allowed_next_states(
    current: "ReportReviewState | str",
) -> frozenset[ReportReviewState]:
    if isinstance(current, str):
        try:
            current = ReportReviewState(current)
        except ValueError:
            return frozenset()
    return REPORT_REVIEW_TRANSITIONS.get(current, frozenset())
