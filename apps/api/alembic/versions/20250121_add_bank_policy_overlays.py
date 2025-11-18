"""Add bank policy overlays and exceptions tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20250121_add_bank_policy_overlays"
down_revision = "20250120_add_company_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bank_policy_overlays table
    op.create_table(
        "bank_policy_overlays",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "bank_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "published_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_bank_policy_overlays_bank_id", "bank_policy_overlays", ["bank_id"])
    op.create_index(
        "ix_bank_policy_overlays_bank_active",
        "bank_policy_overlays",
        ["bank_id", "active"],
    )

    # Create bank_policy_exceptions table
    op.create_table(
        "bank_policy_exceptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "bank_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "overlay_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_policy_overlays.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column(
            "scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effect", sa.String(length=20), nullable=False, server_default="waive"),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_bank_policy_exceptions_bank_id", "bank_policy_exceptions", ["bank_id"])
    op.create_index(
        "ix_bank_policy_exceptions_bank_rule",
        "bank_policy_exceptions",
        ["bank_id", "rule_code"],
    )
    op.create_index(
        "ix_bank_policy_exceptions_expires",
        "bank_policy_exceptions",
        ["bank_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bank_policy_exceptions_expires", table_name="bank_policy_exceptions")
    op.drop_index("ix_bank_policy_exceptions_bank_rule", table_name="bank_policy_exceptions")
    op.drop_index("ix_bank_policy_exceptions_bank_id", table_name="bank_policy_exceptions")
    op.drop_table("bank_policy_exceptions")
    
    op.drop_index("ix_bank_policy_overlays_bank_active", table_name="bank_policy_overlays")
    op.drop_index("ix_bank_policy_overlays_bank_id", table_name="bank_policy_overlays")
    op.drop_table("bank_policy_overlays")

