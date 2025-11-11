"""Add webhook hardening fields

Revision ID: 20250127_add_webhook_hardening
Revises: 20250127_add_org_indexes
Create Date: 2025-01-27 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250127_add_webhook_hardening'
down_revision = '20250127_add_org_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add webhook hardening fields:
    - max_backoff_seconds: Cap exponential backoff
    - rate_limit_per_minute: Provider rate limiting
    - rate_limit_per_hour: Provider rate limiting
    - Add PARKED status support (already in enum, just ensure DB accepts it)
    """
    # Add new columns to webhook_subscriptions
    op.add_column('webhook_subscriptions', sa.Column('max_backoff_seconds', sa.Integer(), nullable=False, server_default='3600'))
    op.add_column('webhook_subscriptions', sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True))
    op.add_column('webhook_subscriptions', sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True))


def downgrade():
    """Remove webhook hardening fields"""
    op.drop_column('webhook_subscriptions', 'rate_limit_per_hour')
    op.drop_column('webhook_subscriptions', 'rate_limit_per_minute')
    op.drop_column('webhook_subscriptions', 'max_backoff_seconds')

