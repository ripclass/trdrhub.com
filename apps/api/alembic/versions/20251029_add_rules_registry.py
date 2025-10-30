from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251029_add_rules_registry"
down_revision = "20250917_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure required extension for UUID generation exists
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "rules_registry",
        sa.Column(
            "id",
            sa.UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String, nullable=False),
        sa.Column("title", sa.String),
        sa.Column("description", sa.Text),
        sa.Column("condition", postgresql.JSONB, nullable=False),
        sa.Column("expected_outcome", postgresql.JSONB, nullable=False),
        sa.Column("domain", sa.String, nullable=False),
        sa.Column(
            "jurisdiction",
            sa.String,
            nullable=False,
            server_default=sa.text("'global'"),
        ),
        sa.Column("document_type", sa.String, nullable=False),
        sa.Column(
            "version",
            sa.String,
            nullable=False,
            server_default=sa.text("'UCP600:2007'"),
        ),
        sa.Column(
            "severity",
            sa.String,
            nullable=False,
            server_default=sa.text("'fail'"),
        ),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("rules_registry")


