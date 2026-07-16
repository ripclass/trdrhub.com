"""Add voluntary Proofline post-clearance outcomes.

Revision ID: 20260716_add_proofline_outcomes
Revises: 20260716_add_proofline_pricing
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260716_add_proofline_outcomes"
down_revision = "20260716_add_proofline_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_case_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("documents_accepted", sa.Boolean(), nullable=True),
        sa.Column("payment_delayed", sa.Boolean(), nullable=True),
        sa.Column("bank_additional_discrepancies", sa.Boolean(), nullable=True),
        sa.Column("shipment_held", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trade_case_id", name="uq_trade_case_outcome_case"),
    )
    op.create_index(
        "ix_trade_case_outcomes_company_created",
        "trade_case_outcomes",
        ["company_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_case_outcomes_company_created", table_name="trade_case_outcomes")
    op.drop_table("trade_case_outcomes")
