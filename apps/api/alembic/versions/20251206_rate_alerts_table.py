"""Add rate_alerts table for Phase 2

Revision ID: rate_alerts_001
Revises: hs_code_finder_001
Create Date: 2025-12-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'rate_alerts_001'
down_revision = 'hs_code_finder_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create rate_alerts table
    op.create_table(
        'rate_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hs_code', sa.String(15), nullable=False),
        sa.Column('import_country', sa.String(2), nullable=False, server_default='US'),
        sa.Column('export_country', sa.String(2), nullable=True),
        sa.Column('alert_type', sa.String(20), server_default='any'),
        sa.Column('threshold_percent', sa.Float(), nullable=True),
        sa.Column('baseline_rate', sa.Float(), nullable=True),
        sa.Column('baseline_date', sa.DateTime(), nullable=True),
        sa.Column('email_notification', sa.Boolean(), server_default='true'),
        sa.Column('in_app_notification', sa.Boolean(), server_default='true'),
        sa.Column('last_notified', sa.DateTime(), nullable=True),
        sa.Column('notification_count', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_rate_alerts_user', 'rate_alerts', ['user_id', 'is_active'], if_not_exists=True)
    op.create_index('ix_rate_alerts_hs_code', 'rate_alerts', ['hs_code'], if_not_exists=True)


def downgrade():
    op.drop_index('ix_rate_alerts_hs_code', table_name='rate_alerts')
    op.drop_index('ix_rate_alerts_user', table_name='rate_alerts')
    op.drop_table('rate_alerts')

