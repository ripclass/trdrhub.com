"""add_user_role

Revision ID: 20250916_150000
Revises: 20250916_140000
Create Date: 2025-09-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250916_150000'
down_revision = '20250916_140000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add role column to users table with constraints and default."""

    # Add role column with default value
    op.add_column('users',
        sa.Column('role', sa.String(), nullable=False, server_default='exporter')
    )

    # Add check constraint for valid roles
    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('exporter','importer','bank','admin')"
    )

    # Create index for role-based queries
    op.create_index('idx_users_role', 'users', ['role'])

    # Update any existing users to have exporter role (if they don't already)
    # This handles the case where there are existing users without roles
    op.execute("UPDATE users SET role = 'exporter' WHERE role IS NULL")


def downgrade() -> None:
    """Remove role column and related constraints."""

    # Drop index first
    op.drop_index('idx_users_role', table_name='users')

    # Drop check constraint
    op.drop_constraint('ck_users_role', 'users', type_='check')

    # Drop role column
    op.drop_column('users', 'role')