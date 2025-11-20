"""
Add governance columns and indexes to the normalized rules table.

Revision ID: 20251220_add_rules_table_extensions
Revises: 20251119_merge_phase7_heads
Create Date: 2025-12-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251220_add_rules_table_extensions"
down_revision = "20251119_merge_phase7_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rules",
        sa.Column(
            "ruleset_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "rules",
        sa.Column("ruleset_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "rules",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "rules",
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_rules_ruleset_id",
        "rules",
        "rulesets",
        ["ruleset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_rules_ruleset_id",
        "rules",
        ["ruleset_id"],
        unique=False,
    )
    op.create_index(
        "ix_rules_rule_id",
        "rules",
        ["rule_id"],
        unique=True,
    )
    op.create_index(
        "ix_rules_domain_document_type",
        "rules",
        ["domain", "document_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rules_domain_document_type", table_name="rules")
    op.drop_index("ix_rules_rule_id", table_name="rules")
    op.drop_index("ix_rules_ruleset_id", table_name="rules")
    op.drop_constraint("fk_rules_ruleset_id", "rules", type_="foreignkey")

    op.drop_column("rules", "archived_at")
    op.drop_column("rules", "is_active")
    op.drop_column("rules", "ruleset_version")
    op.drop_column("rules", "ruleset_id")

