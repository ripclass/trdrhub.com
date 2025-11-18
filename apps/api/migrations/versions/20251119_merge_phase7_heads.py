"""
Merge Phase 7 heads to restore single Alembic lineage.

Revision ID: 20251119_merge_phase7_heads
Revises: 20250122_add_bank_policy_application_events, 20251118_extend_ai_cost_precision
Create Date: 2025-11-18 14:05:00.000000
"""

from alembic import op


revision = "20251119_merge_phase7_heads"
down_revision = ("20250122_add_bank_policy_application_events", "20251118_extend_ai_cost_precision")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

