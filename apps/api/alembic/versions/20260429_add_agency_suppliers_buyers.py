"""Agency persona — supplier + foreign buyer rosters + LC attribution.

Phase A5 part 1. Adds:

  * ``agency_foreign_buyers`` — the agent's overseas counterparties.
  * ``agency_suppliers`` — the agent's domestic factories. Optional
    FK to ``agency_foreign_buyers`` for the supplier's default buyer.
  * ``validation_sessions.supplier_id`` — nullable FK so an LC can
    be attributed to one of the agent's suppliers. Old rows keep
    ``NULL`` (un-attributed legacy / non-agent runs).

Revision ID: 20260429_add_agency_suppliers_buyers
Revises: 20260428_add_user_notifications
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260429_add_agency_suppliers_buyers"
down_revision = "20260428_add_user_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agency_foreign_buyers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "agent_company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_agency_foreign_buyers_agent_company_id",
        "agency_foreign_buyers",
        ["agent_company_id"],
    )
    op.create_index(
        "ix_agency_foreign_buyers_company_name",
        "agency_foreign_buyers",
        ["agent_company_id", "name"],
    )

    op.create_table(
        "agency_suppliers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "agent_company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("factory_address", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "foreign_buyer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agency_foreign_buyers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_agency_suppliers_agent_company_id",
        "agency_suppliers",
        ["agent_company_id"],
    )
    op.create_index(
        "ix_agency_suppliers_foreign_buyer_id",
        "agency_suppliers",
        ["foreign_buyer_id"],
    )
    op.create_index(
        "ix_agency_suppliers_company_name",
        "agency_suppliers",
        ["agent_company_id", "name"],
    )

    # supplier_id on validation_session — nullable so non-agent runs
    # keep their existing schema. Old rows backfill to NULL.
    op.add_column(
        "validation_sessions",
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agency_suppliers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_validation_sessions_supplier_id",
        "validation_sessions",
        ["supplier_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_sessions_supplier_id", table_name="validation_sessions"
    )
    op.drop_column("validation_sessions", "supplier_id")

    op.drop_index(
        "ix_agency_suppliers_company_name", table_name="agency_suppliers"
    )
    op.drop_index(
        "ix_agency_suppliers_foreign_buyer_id", table_name="agency_suppliers"
    )
    op.drop_index(
        "ix_agency_suppliers_agent_company_id", table_name="agency_suppliers"
    )
    op.drop_table("agency_suppliers")

    op.drop_index(
        "ix_agency_foreign_buyers_company_name",
        table_name="agency_foreign_buyers",
    )
    op.drop_index(
        "ix_agency_foreign_buyers_agent_company_id",
        table_name="agency_foreign_buyers",
    )
    op.drop_table("agency_foreign_buyers")
