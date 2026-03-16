"""Add SME storage tables for exporter workspace and templates.

Revision ID: 20260316_add_sme_storage_tables
Revises: sanctions_001
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260316_add_sme_storage_tables"
down_revision = "sanctions_001"
branch_labels = None
depends_on = None


TEMPLATE_TYPE_ENUM = postgresql.ENUM(
    "lc",
    "document",
    name="templatetype",
    create_type=False,
)

DOCUMENT_TYPE_ENUM = postgresql.ENUM(
    "commercial_invoice",
    "bill_of_lading",
    "packing_list",
    "certificate_of_origin",
    "inspection_certificate",
    "insurance_certificate",
    "other",
    name="documenttype",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    TEMPLATE_TYPE_ENUM.create(bind, checkfirst=True)
    DOCUMENT_TYPE_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "lc_workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lc_number", sa.String(length=100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "latest_validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("completion_percentage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_lc_workspaces_lc_number", "lc_workspaces", ["lc_number"])
    op.create_index("ix_lc_workspaces_user_id", "lc_workspaces", ["user_id"])
    op.create_index("ix_lc_workspaces_company_id", "lc_workspaces", ["company_id"])

    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("lc_number", sa.String(length=100), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("draft_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("uploaded_docs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'ready_for_submission', 'submitted', 'archived')",
            name="ck_drafts_status",
        ),
    )
    op.create_index("ix_drafts_user_id", "drafts", ["user_id"])
    op.create_index("ix_drafts_company_id", "drafts", ["company_id"])
    op.create_index("ix_drafts_lc_number", "drafts", ["lc_number"])
    op.create_index("ix_drafts_status", "drafts", ["status"])

    op.create_table(
        "amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lc_number", sa.String(length=100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("amendments.id"), nullable=True),
        sa.Column(
            "validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "previous_validation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("changes_diff", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("document_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'archived')",
            name="ck_amendments_status",
        ),
    )
    op.create_index("ix_amendments_lc_number", "amendments", ["lc_number"])
    op.create_index("ix_amendments_user_id", "amendments", ["user_id"])
    op.create_index("ix_amendments_company_id", "amendments", ["company_id"])
    op.create_index("ix_amendments_status", "amendments", ["status"])

    op.create_table(
        "sme_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", TEMPLATE_TYPE_ENUM, nullable=False),
        sa.Column("document_type", DOCUMENT_TYPE_ENUM, nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sme_templates_company_id", "sme_templates", ["company_id"])
    op.create_index("ix_sme_templates_user_id", "sme_templates", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sme_templates_user_id", table_name="sme_templates")
    op.drop_index("ix_sme_templates_company_id", table_name="sme_templates")
    op.drop_table("sme_templates")

    op.drop_index("ix_amendments_status", table_name="amendments")
    op.drop_index("ix_amendments_company_id", table_name="amendments")
    op.drop_index("ix_amendments_user_id", table_name="amendments")
    op.drop_index("ix_amendments_lc_number", table_name="amendments")
    op.drop_table("amendments")

    op.drop_index("ix_drafts_status", table_name="drafts")
    op.drop_index("ix_drafts_lc_number", table_name="drafts")
    op.drop_index("ix_drafts_company_id", table_name="drafts")
    op.drop_index("ix_drafts_user_id", table_name="drafts")
    op.drop_table("drafts")

    op.drop_index("ix_lc_workspaces_company_id", table_name="lc_workspaces")
    op.drop_index("ix_lc_workspaces_user_id", table_name="lc_workspaces")
    op.drop_index("ix_lc_workspaces_lc_number", table_name="lc_workspaces")
    op.drop_table("lc_workspaces")

    DOCUMENT_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
    TEMPLATE_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
