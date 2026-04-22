"""Add workflow_type to validation_sessions.

Distinguishes the three user-facing flows that share the extraction +
validation pipeline:
  * exporter_presentation  (exporter presenting docs to their bank)
  * importer_draft_lc      (importer reviewing a draft LC for risk)
  * importer_supplier_docs (importer reviewing supplier docs vs issued LC)

Zero-downtime: the ADD COLUMN statement includes a server_default, so
existing rows are backfilled atomically. No separate backfill or two-step
NOT NULL flip is needed.

Revision ID: 20260422_add_workflow_type
Revises: 20260316_add_sme_storage_tables
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260422_add_workflow_type"
down_revision = "20260316_add_sme_storage_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validation_sessions",
        sa.Column(
            "workflow_type",
            sa.String(length=50),
            nullable=False,
            server_default="exporter_presentation",
        ),
    )


def downgrade() -> None:
    op.drop_column("validation_sessions", "workflow_type")
