"""Add onboarding fields to users table

Revision ID: 20251101_onboarding
Revises: 20250917_compliance
Create Date: 2025-11-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251101_onboarding'
down_revision = '20250917_compliance'
branch_labels = None
depends_on = None


def upgrade():
    # Add onboarding fields to users table
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onboarding_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))


def downgrade():
    # Remove onboarding fields from users table
    op.drop_column('users', 'onboarding_data')
    op.drop_column('users', 'onboarding_completed')

