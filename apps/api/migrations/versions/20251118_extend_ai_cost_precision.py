"""Expand AI cost columns to avoid truncation.

Revision ID: 20251118_extend_ai_cost_precision
Revises: 20251116_add_ai_usage_and_events
Create Date: 2025-11-18 13:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251118_extend_ai_cost_precision"
down_revision = "20251116_add_ai_usage_and_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ai_usage_records",
        "estimated_cost_usd",
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
    op.alter_column(
        "ai_assist_events",
        "estimated_cost_usd",
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "ai_assist_events",
        "estimated_cost_usd",
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "ai_usage_records",
        "estimated_cost_usd",
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=True,
    )

