"""Add LC lifecycle state machine — Phase A1 of Path A.

Adds:
  * validation_sessions.lifecycle_state (text, default 'docs_in_preparation',
    NOT NULL via server_default for atomic backfill).
  * validation_sessions.lifecycle_state_changed_at (timestamp, nullable).
  * lc_lifecycle_events table — append-only audit log of state transitions.

Zero-downtime: new column has a server_default so existing rows are
backfilled atomically. Existing rows enter the lifecycle in
'docs_in_preparation' which is the most common starting point for an
exporter or importer mid-validation.

Revision ID: 20260425_add_lc_lifecycle
Revises: 20260423_add_company_onboarding_fields
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260425_add_lc_lifecycle"
down_revision = "20260423_add_company_onboarding_fields"
branch_labels = None
depends_on = None


# Allowed values mirror app/models/lc_lifecycle.py::LC_LIFECYCLE_STATE_VALUES.
# Keep in lockstep — adding a state requires editing both + a new migration.
_LIFECYCLE_STATES = (
    "issued",
    "advised",
    "docs_in_preparation",
    "docs_presented",
    "under_bank_review",
    "discrepancies_raised",
    "discrepancies_resolved",
    "paid",
    "closed",
    "expired",
)


def upgrade() -> None:
    # 1. Add lifecycle_state + lifecycle_state_changed_at to validation_sessions.
    op.add_column(
        "validation_sessions",
        sa.Column(
            "lifecycle_state",
            sa.String(length=50),
            nullable=False,
            server_default="docs_in_preparation",
        ),
    )
    op.add_column(
        "validation_sessions",
        sa.Column(
            "lifecycle_state_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # CHECK constraint to keep lifecycle_state in the canonical set.
    op.create_check_constraint(
        "ck_validation_sessions_lifecycle_state_valid",
        "validation_sessions",
        "lifecycle_state IN ("
        + ", ".join(f"'{s}'" for s in _LIFECYCLE_STATES)
        + ")",
    )

    # 2. Create lc_lifecycle_events table.
    op.create_table(
        "lc_lifecycle_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(length=50), nullable=True),
        sa.Column("to_state", sa.String(length=50), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_lc_lifecycle_events_validation_session_id",
        "lc_lifecycle_events",
        ["validation_session_id"],
    )
    op.create_index(
        "ix_lc_lifecycle_events_actor_user_id",
        "lc_lifecycle_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_lc_lifecycle_events_session_created",
        "lc_lifecycle_events",
        ["validation_session_id", "created_at"],
    )

    # CHECK constraints on event states (mirrors app-level enum).
    op.create_check_constraint(
        "ck_lc_lifecycle_events_to_state_valid",
        "lc_lifecycle_events",
        "to_state IN ("
        + ", ".join(f"'{s}'" for s in _LIFECYCLE_STATES)
        + ")",
    )
    op.create_check_constraint(
        "ck_lc_lifecycle_events_from_state_valid",
        "lc_lifecycle_events",
        "from_state IS NULL OR from_state IN ("
        + ", ".join(f"'{s}'" for s in _LIFECYCLE_STATES)
        + ")",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lc_lifecycle_events_session_created",
        table_name="lc_lifecycle_events",
    )
    op.drop_index(
        "ix_lc_lifecycle_events_actor_user_id",
        table_name="lc_lifecycle_events",
    )
    op.drop_index(
        "ix_lc_lifecycle_events_validation_session_id",
        table_name="lc_lifecycle_events",
    )
    op.drop_table("lc_lifecycle_events")
    op.drop_constraint(
        "ck_validation_sessions_lifecycle_state_valid",
        "validation_sessions",
        type_="check",
    )
    op.drop_column("validation_sessions", "lifecycle_state_changed_at")
    op.drop_column("validation_sessions", "lifecycle_state")
