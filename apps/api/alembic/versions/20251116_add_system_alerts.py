"""
Add system alerts table for admin dashboard

Revision ID: 20251116_add_system_alerts
Revises: 20251115_add_auth_user_id_to_users
Create Date: 2025-11-16 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251116_add_system_alerts"
down_revision = "20251115_add_auth_user_id_to_users"
branch_labels = None
depends_on = None


def upgrade():
    severity_enum = postgresql.ENUM(
        "info", "low", "medium", "high", "critical",
        name="system_alert_severity"
    )
    status_enum = postgresql.ENUM(
        "active", "acknowledged", "resolved", "snoozed",
        name="system_alert_status"
    )
    severity_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "system_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("severity", severity_enum, nullable=False, server_default="medium"),
        sa.Column("status", status_enum, nullable=False, server_default="active"),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("auto_generated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("snoozed_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index(
        "idx_system_alerts_status_severity",
        "system_alerts",
        ["status", "severity"]
    )
    op.create_index(
        "idx_system_alerts_resource",
        "system_alerts",
        ["resource_type", "resource_id"]
    )


def downgrade():
    op.drop_index("idx_system_alerts_resource", table_name="system_alerts")
    op.drop_index("idx_system_alerts_status_severity", table_name="system_alerts")
    op.drop_table("system_alerts")
    op.execute("DROP TYPE IF EXISTS system_alert_status")
    op.execute("DROP TYPE IF EXISTS system_alert_severity")

