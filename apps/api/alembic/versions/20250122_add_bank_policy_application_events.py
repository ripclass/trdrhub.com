"""Add bank policy application events table for analytics."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20250122_add_bank_policy_application_events"
down_revision = "20250121_add_bank_policy_overlays"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bank_policy_application_events table
    op.create_table(
        "bank_policy_application_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "bank_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "overlay_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_policy_overlays.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("overlay_version", sa.Integer(), nullable=True),
        sa.Column(
            "exception_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_policy_exceptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("application_type", sa.String(length=20), nullable=False),  # overlay, exception, both
        sa.Column("rule_code", sa.String(length=100), nullable=True),
        sa.Column("exception_effect", sa.String(length=20), nullable=True),  # waive, downgrade, override
        sa.Column("discrepancies_before", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discrepancies_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "severity_changes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_policy_app_bank_created", "bank_policy_application_events", ["bank_id", "created_at"])
    op.create_index("ix_policy_app_overlay_created", "bank_policy_application_events", ["overlay_id", "created_at"])
    op.create_index("ix_policy_app_exception_created", "bank_policy_application_events", ["exception_id", "created_at"])
    op.create_index("ix_policy_app_session", "bank_policy_application_events", ["validation_session_id"])


def downgrade() -> None:
    op.drop_index("ix_policy_app_session", table_name="bank_policy_application_events")
    op.drop_index("ix_policy_app_exception_created", table_name="bank_policy_application_events")
    op.drop_index("ix_policy_app_overlay_created", table_name="bank_policy_application_events")
    op.drop_index("ix_policy_app_bank_created", table_name="bank_policy_application_events")
    op.drop_table("bank_policy_application_events")

