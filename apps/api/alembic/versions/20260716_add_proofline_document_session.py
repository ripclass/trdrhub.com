"""Reuse a tenant-owned validation session for Proofline document storage.

Revision ID: 20260716_add_proofline_document_session
Revises: 20260716_add_proofline_trade_cases
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260716_add_proofline_document_session"
down_revision = "20260716_add_proofline_trade_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trade_cases",
        sa.Column(
            "document_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_trade_cases_document_session",
        "trade_cases",
        "validation_sessions",
        ["document_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_trade_cases_document_session",
        "trade_cases",
        ["document_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_cases_document_session", table_name="trade_cases")
    op.drop_constraint(
        "fk_trade_cases_document_session", "trade_cases", type_="foreignkey"
    )
    op.drop_column("trade_cases", "document_session_id")
