"""Phase 7.0 multi-role RBAC foundations and bank scoping tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20251031_add_user_roles_bank_tables"
down_revision = "20251029_add_rules_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_ALLOWED_ROLES = (
    "exporter",
    "importer",
    "tenant_admin",
    "bank_officer",
    "bank_admin",
    "system_admin",
)


def _drop_users_role_constraint() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")


def _create_users_role_constraint() -> None:
    op.create_check_constraint(
        "ck_users_role",
        "users",
        f"role IN {NEW_ALLOWED_ROLES}",
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Update legacy role values before tightening constraint
    op.execute("UPDATE users SET role = 'bank_officer' WHERE role = 'bank'")
    op.execute("UPDATE users SET role = 'system_admin' WHERE role = 'admin'")

    _drop_users_role_constraint()
    _create_users_role_constraint()

    # Create user_roles table for optional multi-role assignments
    op.create_table(
        "user_roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
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
        sa.CheckConstraint(
            "role IN ('exporter','importer','tenant_admin','bank_officer','bank_admin','system_admin')",
            name="ck_user_roles_role",
        ),
    )
    op.create_index("ix_user_roles_user_role", "user_roles", ["user_id", "role"], unique=True)

    # Populate user_roles with existing single-role assignments
    op.execute(
        """
        INSERT INTO user_roles (user_id, role)
        SELECT id, role FROM users
        """
    )

    # Bank scoping tables
    op.create_table(
        "bank_tenants",
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
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
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
    op.create_index(
        "ix_bank_tenants_bank_tenant",
        "bank_tenants",
        ["bank_id", "tenant_id"],
        unique=True,
    )
    op.create_index("ix_bank_tenants_bank_status", "bank_tenants", ["bank_id", "status"])

    op.create_table(
        "bank_reports",
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
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_bank_reports_bank_period", "bank_reports", ["bank_id", "period"], unique=True)

    op.create_table(
        "bank_audit_logs",
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
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "lc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_bank_audit_logs_bank_created", "bank_audit_logs", ["bank_id", "created_at"])
    op.create_index("ix_bank_audit_logs_tenant_created", "bank_audit_logs", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_bank_audit_logs_tenant_created", table_name="bank_audit_logs")
    op.drop_index("ix_bank_audit_logs_bank_created", table_name="bank_audit_logs")
    op.drop_table("bank_audit_logs")

    op.drop_index("ix_bank_reports_bank_period", table_name="bank_reports")
    op.drop_table("bank_reports")

    op.drop_index("ix_bank_tenants_bank_status", table_name="bank_tenants")
    op.drop_index("ix_bank_tenants_bank_tenant", table_name="bank_tenants")
    op.drop_table("bank_tenants")

    op.drop_index("ix_user_roles_user_role", table_name="user_roles")
    op.drop_table("user_roles")

    _drop_users_role_constraint()
    op.create_check_constraint(
        "ck_users_role",
        "users",
        sa.text("role IN ('exporter','importer','bank','admin')"),
    )

    # Revert role values for backwards compatibility
    op.execute("UPDATE users SET role = 'bank' WHERE role = 'bank_officer'")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'system_admin'")
