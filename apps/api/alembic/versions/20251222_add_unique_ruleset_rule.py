"""Add UNIQUE(ruleset_id, rule_id) constraint to rules table.

Revision ID: 20251222_add_unique_ruleset_rule
Revises: 20251220_add_rules_table_extensions
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20251222_add_unique_ruleset_rule"
down_revision = "20251220_add_rules_table_extensions"
branch_labels = None
depends_on = None

def upgrade():
    # Only add constraint if it does not already exist
    try:
        op.create_unique_constraint(
            "uq_rules_ruleset_rule",
            "rules",
            ["ruleset_id", "rule_id"],
        )
    except Exception:
        pass

def downgrade():
    # Drop the UNIQUE constraint on downgrade
    op.drop_constraint(
        "uq_rules_ruleset_rule",
        "rules",
        type_="unique",
    )

