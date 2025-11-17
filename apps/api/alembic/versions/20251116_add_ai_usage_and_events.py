"""Add tables for AI usage tracking and assist events.

Revision ID: 20251116_add_ai_usage_and_events
Revises: 20251116_add_system_alerts
Create Date: 2025-11-16 12:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251116_add_ai_usage_and_events"
down_revision = "20251116_add_system_alerts"  # Fixed: point to latest migration in alembic/versions
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=True,
        ),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_usage_records_tenant_id", "ai_usage_records", ["tenant_id"])
    op.create_index("ix_ai_usage_records_user_id", "ai_usage_records", ["user_id"])
    op.create_index(
        "ix_ai_usage_records_validation_session_id",
        "ai_usage_records",
        ["validation_session_id"],
    )

    op.create_table(
        "ai_assist_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("validation_sessions.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("output_type", sa.String(length=50), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_output", sa.Text(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.String(length=20), nullable=True),
        sa.Column("lc_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("validation_sessions.id"), nullable=True),
        sa.Column("rule_references", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prompt_template_id", sa.String(length=100), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_assist_events_session_id", "ai_assist_events", ["session_id"])
    op.create_index("ix_ai_assist_events_user_id", "ai_assist_events", ["user_id"])
    op.create_index("ix_ai_assist_events_company_id", "ai_assist_events", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_assist_events_company_id", table_name="ai_assist_events")
    op.drop_index("ix_ai_assist_events_user_id", table_name="ai_assist_events")
    op.drop_index("ix_ai_assist_events_session_id", table_name="ai_assist_events")
    op.drop_table("ai_assist_events")

    op.drop_index("ix_ai_usage_records_validation_session_id", table_name="ai_usage_records")
    op.drop_index("ix_ai_usage_records_user_id", table_name="ai_usage_records")
    op.drop_index("ix_ai_usage_records_tenant_id", table_name="ai_usage_records")
    op.drop_table("ai_usage_records")

