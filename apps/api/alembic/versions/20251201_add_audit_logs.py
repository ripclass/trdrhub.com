"""Add audit_logs table for Price Verification compliance

Revision ID: 20251201_audit
Revises: 20251130_price_verify
Create Date: 2024-12-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251201_audit'
down_revision: Union[str, None] = '20251130_price_verify'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table for compliance-grade logging
    op.create_table(
        'price_verify_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Action type
        sa.Column('action', sa.String(50), nullable=False),  # price_verify_single, price_verify_batch, etc.
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),  # info, warning, critical
        
        # Who
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('company_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 compatible
        sa.Column('user_agent', sa.Text, nullable=True),
        
        # What
        sa.Column('resource_type', sa.String(50), nullable=False),  # verification, extraction, report
        sa.Column('resource_id', sa.String(255), nullable=True),
        
        # Input/Output (JSONB for flexibility)
        sa.Column('request_data', postgresql.JSONB, nullable=True),
        sa.Column('response_summary', postgresql.JSONB, nullable=True),
        
        # Results
        sa.Column('verdict', sa.String(20), nullable=True),  # pass, warning, fail
        sa.Column('risk_level', sa.String(20), nullable=True),  # low, medium, high, critical
        
        # Source Attribution
        sa.Column('data_sources', postgresql.JSONB, nullable=True),  # Array of sources used
        
        # Context
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('request_id', sa.String(255), nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for common queries
    op.create_index('ix_audit_logs_timestamp', 'price_verify_audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user_id', 'price_verify_audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_company_id', 'price_verify_audit_logs', ['company_id'])
    op.create_index('ix_audit_logs_action', 'price_verify_audit_logs', ['action'])
    op.create_index('ix_audit_logs_severity', 'price_verify_audit_logs', ['severity'])
    op.create_index('ix_audit_logs_verdict', 'price_verify_audit_logs', ['verdict'])
    op.create_index('ix_audit_logs_risk_level', 'price_verify_audit_logs', ['risk_level'])
    
    # Composite index for compliance reports
    op.create_index(
        'ix_audit_logs_company_timestamp',
        'price_verify_audit_logs',
        ['company_id', 'timestamp']
    )
    
    # Index for TBML alerts (critical severity)
    op.create_index(
        'ix_audit_logs_tbml_alerts',
        'price_verify_audit_logs',
        ['severity', 'timestamp'],
        postgresql_where=sa.text("severity = 'critical'")
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_logs_tbml_alerts', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_company_timestamp', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_risk_level', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_verdict', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_severity', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_company_id', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='price_verify_audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='price_verify_audit_logs')
    
    # Drop table
    op.drop_table('price_verify_audit_logs')

