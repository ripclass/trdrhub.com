"""supabase auth support

Revision ID: 20251101_supabase_auth_support
Revises: 20251101_add_onboarding_fields
Create Date: 2025-11-01 08:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251101_supabase_auth_support"
down_revision = "20251101_add_onboarding_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_step", sa.String(length=128), nullable=True))
    op.add_column(
        "users",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("kyc_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("kyc_status", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("approver_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_users_approver_id_users",
        source_table="users",
        referent_table="users",
        local_cols=["approver_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    op.add_column("companies", sa.Column("legal_name", sa.String(length=255), nullable=True))
    op.add_column("companies", sa.Column("registration_number", sa.String(length=128), nullable=True))
    op.add_column("companies", sa.Column("regulator_id", sa.String(length=128), nullable=True))
    op.add_column("companies", sa.Column("country", sa.String(length=128), nullable=True))

    op.create_table(
        "kyc_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_kyc_documents_user_id", "kyc_documents", ["user_id"], unique=False)
    op.create_index("ix_kyc_documents_company_id", "kyc_documents", ["company_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_kyc_documents_company_id", table_name="kyc_documents")
    op.drop_index("ix_kyc_documents_user_id", table_name="kyc_documents")
    op.drop_table("kyc_documents")

    op.drop_constraint("fk_users_approver_id_users", "users", type_="foreignkey")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "approver_id")
    op.drop_column("users", "kyc_status")
    op.drop_column("users", "kyc_required")
    op.drop_column("users", "status")
    op.drop_column("users", "onboarding_step")

    op.drop_column("companies", "country")
    op.drop_column("companies", "regulator_id")
    op.drop_column("companies", "registration_number")
    op.drop_column("companies", "legal_name")

