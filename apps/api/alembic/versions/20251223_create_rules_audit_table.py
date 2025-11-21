"""create rules_audit table

Revision ID: 20251223_create_rules_audit_table
Revises: 20251222_add_unique_ruleset_rule
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251223_create_rules_audit_table"
down_revision = "20251222_add_unique_ruleset_rule"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "rules_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("ruleset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detail", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False)
    )
    op.create_index("idx_rules_audit_ruleset", "rules_audit", ["ruleset_id"])
    op.create_index("idx_rules_audit_rule", "rules_audit", ["rule_id"])

def downgrade():
    op.drop_index("idx_rules_audit_ruleset", table_name="rules_audit")
    op.drop_index("idx_rules_audit_rule", table_name="rules_audit")
    op.drop_table("rules_audit")

