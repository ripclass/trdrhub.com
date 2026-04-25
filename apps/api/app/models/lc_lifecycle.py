"""LC lifecycle state machine — Phase A1 of the Path A build.

Models the trade-finance LC lifecycle as a state machine attached to
ValidationSession. Every state transition writes an LCLifecycleEvent
row so we have a complete audit trail of who pushed what when.

The legacy ``ValidationSession`` (apps/api/app/models.py) gets a
``lifecycle_state`` column added via the 20260425 migration. The state
enum + event model live here for clean separation.

States are deliberately UCP600-canonical, not platform-internal. They
map to how a banker reads an LC's progress, not how our pipeline
processes it.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class LCLifecycleState(str, enum.Enum):
    """Canonical UCP600 lifecycle stages for a Letter of Credit.

    Linear default flow:
        issued -> advised -> docs_in_preparation -> docs_presented
        -> under_bank_review -> discrepancies_raised|paid
        -> discrepancies_resolved -> paid -> closed

    Terminal states: paid, closed, expired.
    """

    ISSUED = "issued"
    ADVISED = "advised"
    DOCS_IN_PREPARATION = "docs_in_preparation"
    DOCS_PRESENTED = "docs_presented"
    UNDER_BANK_REVIEW = "under_bank_review"
    DISCREPANCIES_RAISED = "discrepancies_raised"
    DISCREPANCIES_RESOLVED = "discrepancies_resolved"
    PAID = "paid"
    CLOSED = "closed"
    EXPIRED = "expired"


LC_LIFECYCLE_STATE_VALUES = tuple(s.value for s in LCLifecycleState)

LC_LIFECYCLE_TERMINAL_STATES = frozenset(
    {LCLifecycleState.PAID, LCLifecycleState.CLOSED, LCLifecycleState.EXPIRED}
)

# Default state for new validation_sessions. Existing rows are backfilled
# to the same value via the migration's server_default. Most validation
# sessions today are mid-extraction or mid-validation, which fits
# DOCS_IN_PREPARATION best (the user is preparing the package).
LC_LIFECYCLE_DEFAULT_STATE = LCLifecycleState.DOCS_IN_PREPARATION


# Allowed transitions table. Source-of-truth for what a state CAN move
# to. The state machine helper (services/lc_lifecycle.py) enforces this.
#
# A transition not in this map raises a 400-equivalent error. Callers
# can always force a state to EXPIRED or CLOSED (terminal admin paths)
# by passing force=True.
LC_LIFECYCLE_TRANSITIONS: dict[LCLifecycleState, frozenset[LCLifecycleState]] = {
    LCLifecycleState.ISSUED: frozenset(
        {
            LCLifecycleState.ADVISED,
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.ADVISED: frozenset(
        {
            LCLifecycleState.DOCS_IN_PREPARATION,
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.DOCS_IN_PREPARATION: frozenset(
        {
            LCLifecycleState.DOCS_PRESENTED,
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.DOCS_PRESENTED: frozenset(
        {
            LCLifecycleState.UNDER_BANK_REVIEW,
            LCLifecycleState.DOCS_IN_PREPARATION,  # bank rejected on intake
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.UNDER_BANK_REVIEW: frozenset(
        {
            LCLifecycleState.DISCREPANCIES_RAISED,
            LCLifecycleState.PAID,  # clean presentation
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.DISCREPANCIES_RAISED: frozenset(
        {
            LCLifecycleState.DISCREPANCIES_RESOLVED,
            LCLifecycleState.DOCS_IN_PREPARATION,  # re-paper required
            LCLifecycleState.EXPIRED,
            LCLifecycleState.CLOSED,
        }
    ),
    LCLifecycleState.DISCREPANCIES_RESOLVED: frozenset(
        {
            LCLifecycleState.PAID,
            LCLifecycleState.CLOSED,
            LCLifecycleState.EXPIRED,
        }
    ),
    LCLifecycleState.PAID: frozenset({LCLifecycleState.CLOSED}),
    # Terminals — no further transitions without force
    LCLifecycleState.CLOSED: frozenset(),
    LCLifecycleState.EXPIRED: frozenset({LCLifecycleState.CLOSED}),
}


class LCLifecycleEvent(Base):
    """Append-only event log for LC lifecycle state transitions.

    One row per ``ValidationSession.transition()`` call. Forms the
    audit trail visible to enterprise customers + reconstructable
    history per LC.
    """

    __tablename__ = "lc_lifecycle_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("validation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # State transition
    from_state = Column(String(50), nullable=True)  # nullable for "born" event
    to_state = Column(String(50), nullable=False)

    # Who pushed it. Nullable for system-driven transitions
    # (e.g. expiry sweep, validation completion auto-transition).
    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Human/system context for the transition.
    reason = Column(Text, nullable=True)
    # JSONB on Postgres (production), JSON on SQLite (tests). The
    # ``extra`` field carries small structured context per event
    # (e.g. linked-event payload) and doesn't need JSONB-specific
    # operators, so the variant fallback is safe.
    extra = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_lc_lifecycle_events_session_created",
            "validation_session_id",
            "created_at",
        ),
    )


def is_terminal_state(state: LCLifecycleState | str) -> bool:
    """Return True if the given state has no non-force transitions out."""
    if isinstance(state, str):
        try:
            state = LCLifecycleState(state)
        except ValueError:
            return False
    return state in LC_LIFECYCLE_TERMINAL_STATES


def allowed_next_states(
    current: LCLifecycleState | str,
) -> frozenset[LCLifecycleState]:
    """Return the set of states reachable from ``current`` without force."""
    if isinstance(current, str):
        try:
            current = LCLifecycleState(current)
        except ValueError:
            return frozenset()
    return LC_LIFECYCLE_TRANSITIONS.get(current, frozenset())
