"""Services persona — clients + time entries + LC attribution.

Phase A8. Same shape as the agency migration (20260429): two new
tables scoped per company, plus a nullable FK on
``validation_sessions`` so LCs validated for a client land under
that client in the services dashboard.

Revision ID: 20260430_add_services_clients_time
Revises: 20260429_add_agency_suppliers_buyers
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_add_services_clients_time"
down_revision = "20260429_add_agency_suppliers_buyers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "services_clients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "services_company_id",
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
        sa.Column("billing_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "retainer_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("retainer_hours_per_month", sa.Numeric(6, 2), nullable=True),
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
        "ix_services_clients_services_company_id",
        "services_clients",
        ["services_company_id"],
    )
    op.create_index(
        "ix_services_clients_company_name",
        "services_clients",
        ["services_company_id", "name"],
    )

    op.create_table(
        "time_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "services_company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "services_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "billable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "billed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("performed_on", sa.DateTime(timezone=True), nullable=True),
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
        "ix_time_entries_services_company_id",
        "time_entries",
        ["services_company_id"],
    )
    op.create_index(
        "ix_time_entries_services_client_id",
        "time_entries",
        ["services_client_id"],
    )
    op.create_index(
        "ix_time_entries_validation_session_id",
        "time_entries",
        ["validation_session_id"],
    )
    op.create_index(
        "ix_time_entries_user_id",
        "time_entries",
        ["user_id"],
    )
    op.create_index(
        "ix_time_entries_client_performed",
        "time_entries",
        ["services_client_id", "performed_on"],
    )

    op.add_column(
        "validation_sessions",
        sa.Column(
            "services_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services_clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_validation_sessions_services_client_id",
        "validation_sessions",
        ["services_client_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_sessions_services_client_id",
        table_name="validation_sessions",
    )
    op.drop_column("validation_sessions", "services_client_id")

    for name in (
        "ix_time_entries_client_performed",
        "ix_time_entries_user_id",
        "ix_time_entries_validation_session_id",
        "ix_time_entries_services_client_id",
        "ix_time_entries_services_company_id",
    ):
        op.drop_index(name, table_name="time_entries")
    op.drop_table("time_entries")

    for name in (
        "ix_services_clients_company_name",
        "ix_services_clients_services_company_id",
    ):
        op.drop_index(name, table_name="services_clients")
    op.drop_table("services_clients")
