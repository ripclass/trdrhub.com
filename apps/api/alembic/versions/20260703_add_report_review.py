"""Add concierge report-review state machine — Phase 1 of the 2026-07 launch.

Adds to validation_sessions:
  * review_state (text, NULLABLE — null = legacy self-serve, non-null = concierge)
  * review_state_changed_at (timestamp, nullable)
  * review_note (text, nullable) — operator summary at Approve & Deliver
  * reviewed_by (uuid FK users, SET NULL)
  * reviewed_at (timestamp, nullable)
  * delivered_at (timestamp, nullable)
  * review_report_id (uuid FK reports, SET NULL) — the released report PDF

Creates report_review_events — append-only audit log of review transitions.

Zero-downtime: review_state is nullable with no server_default, so every
existing row stays null (self-serve behavior unchanged). Only sessions that
enter the concierge queue get a non-null state.

Revision ID: 20260703_add_report_review
Revises: 20260510_pricing_restructure_tier
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260703_add_report_review"
down_revision = "20260510_pricing_restructure_tier"
branch_labels = None
depends_on = None


# Mirrors app/models/report_review.py::REPORT_REVIEW_STATE_VALUES.
_REVIEW_STATES = (
    "submitted",
    "processing",
    "engine_complete",
    "under_review",
    "needs_info",
    "delivered",
)


def upgrade() -> None:
    # 1. Add review columns to validation_sessions.
    op.add_column(
        "validation_sessions",
        sa.Column("review_state", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "validation_sessions",
        sa.Column("review_state_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "validation_sessions",
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "validation_sessions",
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "validation_sessions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "validation_sessions",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "validation_sessions",
        sa.Column(
            "review_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_validation_sessions_review_state",
        "validation_sessions",
        ["review_state"],
    )

    op.create_check_constraint(
        "ck_validation_sessions_review_state_valid",
        "validation_sessions",
        "review_state IS NULL OR review_state IN ("
        + ", ".join(f"'{s}'" for s in _REVIEW_STATES)
        + ")",
    )

    # 2. Create report_review_events table.
    op.create_table(
        "report_review_events",
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
        "ix_report_review_events_validation_session_id",
        "report_review_events",
        ["validation_session_id"],
    )
    op.create_index(
        "ix_report_review_events_actor_user_id",
        "report_review_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_report_review_events_session_created",
        "report_review_events",
        ["validation_session_id", "created_at"],
    )

    op.create_check_constraint(
        "ck_report_review_events_to_state_valid",
        "report_review_events",
        "to_state IN ("
        + ", ".join(f"'{s}'" for s in _REVIEW_STATES)
        + ")",
    )
    op.create_check_constraint(
        "ck_report_review_events_from_state_valid",
        "report_review_events",
        "from_state IS NULL OR from_state IN ("
        + ", ".join(f"'{s}'" for s in _REVIEW_STATES)
        + ")",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_review_events_session_created",
        table_name="report_review_events",
    )
    op.drop_index(
        "ix_report_review_events_actor_user_id",
        table_name="report_review_events",
    )
    op.drop_index(
        "ix_report_review_events_validation_session_id",
        table_name="report_review_events",
    )
    op.drop_table("report_review_events")
    op.drop_constraint(
        "ck_validation_sessions_review_state_valid",
        "validation_sessions",
        type_="check",
    )
    op.drop_index(
        "ix_validation_sessions_review_state",
        table_name="validation_sessions",
    )
    op.drop_column("validation_sessions", "review_report_id")
    op.drop_column("validation_sessions", "delivered_at")
    op.drop_column("validation_sessions", "reviewed_at")
    op.drop_column("validation_sessions", "reviewed_by")
    op.drop_column("validation_sessions", "review_note")
    op.drop_column("validation_sessions", "review_state_changed_at")
    op.drop_column("validation_sessions", "review_state")
