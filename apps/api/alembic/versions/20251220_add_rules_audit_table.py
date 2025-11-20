"""
Create rules_audit table for governance tracking.

Revision ID: 20251220_add_rules_audit_table
Revises: 20251220_add_rules_table_extensions
Create Date: 2025-12-20 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251220_add_rules_audit_table"
down_revision = "20251220_add_rules_table_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rules_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("rule_id", sa.String(length=255), nullable=True),
        sa.Column(
            "ruleset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rulesets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("detail", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_rules_audit_rule_id", "rules_audit", ["rule_id"])
    op.create_index("ix_rules_audit_ruleset_id", "rules_audit", ["ruleset_id"])
    op.create_index("ix_rules_audit_created_at", "rules_audit", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_rules_audit_created_at", table_name="rules_audit")
    op.drop_index("ix_rules_audit_ruleset_id", table_name="rules_audit")
    op.drop_index("ix_rules_audit_rule_id", table_name="rules_audit")
    op.drop_table("rules_audit")

