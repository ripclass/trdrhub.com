"""Add API tokens and webhooks tables

Revision ID: 20250126_add_api_tokens_webhooks
Revises: 20250125_add_duplicate_detection
Create Date: 2025-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250126_add_api_tokens_webhooks'
down_revision = '20250125_add_duplicate_detection'
branch_labels = None
depends_on = None


def upgrade():
    # API Tokens table - stores API tokens for bank integrations
    op.create_table(
        'api_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Token metadata
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('token_hash', sa.String(64), nullable=False),  # SHA-256 hash of token
        sa.Column('token_prefix', sa.String(8), nullable=False),  # First 8 chars for display (e.g., "bk_live_")
        
        # Token lifecycle
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),  # IPv6 max length
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Scopes/permissions (JSONB array of permission strings)
        sa.Column('scopes', postgresql.JSONB, nullable=False, server_default='[]'),
        
        # Rate limiting
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revoke_reason', sa.Text(), nullable=True),
        
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
        
        sa.Index('ix_api_tokens_company_id', 'api_tokens', ['company_id']),
        sa.Index('ix_api_tokens_token_hash', 'api_tokens', ['token_hash']),
        sa.Index('ix_api_tokens_is_active', 'api_tokens', ['is_active']),
        sa.Index('ix_api_tokens_created_by', 'api_tokens', ['created_by']),
        sa.Index('ix_api_tokens_expires_at', 'api_tokens', ['expires_at']),
    )
    
    # Webhook Subscriptions table - stores webhook endpoint configurations
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Webhook metadata
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(2048), nullable=False),  # Webhook endpoint URL
        sa.Column('secret', sa.String(64), nullable=False),  # Secret for signing payloads
        
        # Event subscriptions (JSONB array of event types)
        sa.Column('events', postgresql.JSONB, nullable=False, server_default='[]'),
        
        # Configuration
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_backoff_multiplier', sa.Float(), nullable=False, server_default='2.0'),
        
        # Headers (JSONB object for custom headers)
        sa.Column('headers', postgresql.JSONB, nullable=True),
        
        # Statistics
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_delivery_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        
        sa.Index('ix_webhook_subscriptions_company_id', 'webhook_subscriptions', ['company_id']),
        sa.Index('ix_webhook_subscriptions_is_active', 'webhook_subscriptions', ['is_active']),
        sa.Index('ix_webhook_subscriptions_url', 'webhook_subscriptions', ['url']),
        sa.Index('ix_webhook_subscriptions_created_by', 'webhook_subscriptions', ['created_by']),
    )
    
    # Webhook Deliveries table - stores delivery attempts and logs
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Delivery metadata
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=True),  # ID of the event that triggered this
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('signature', sa.String(128), nullable=True),  # HMAC signature
        
        # Delivery status
        sa.Column('status', sa.String(50), nullable=False),  # pending, success, failed, retrying
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        
        # HTTP response
        sa.Column('http_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('response_headers', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        
        # Retry information
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_reason', sa.Text(), nullable=True),
        
        sa.ForeignKeyConstraint(['subscription_id'], ['webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        
        sa.Index('ix_webhook_deliveries_subscription_id', 'webhook_deliveries', ['subscription_id']),
        sa.Index('ix_webhook_deliveries_company_id', 'webhook_deliveries', ['company_id']),
        sa.Index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status']),
        sa.Index('ix_webhook_deliveries_event_type', 'webhook_deliveries', ['event_type']),
        sa.Index('ix_webhook_deliveries_started_at', 'webhook_deliveries', ['started_at']),
        sa.Index('ix_webhook_deliveries_next_retry_at', 'webhook_deliveries', ['next_retry_at']),
    )


def downgrade():
    op.drop_index('ix_webhook_deliveries_next_retry_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_started_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_event_type', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_status', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_company_id', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_subscription_id', table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')
    
    op.drop_index('ix_webhook_subscriptions_created_by', table_name='webhook_subscriptions')
    op.drop_index('ix_webhook_subscriptions_url', table_name='webhook_subscriptions')
    op.drop_index('ix_webhook_subscriptions_is_active', table_name='webhook_subscriptions')
    op.drop_index('ix_webhook_subscriptions_company_id', table_name='webhook_subscriptions')
    op.drop_table('webhook_subscriptions')
    
    op.drop_index('ix_api_tokens_expires_at', table_name='api_tokens')
    op.drop_index('ix_api_tokens_created_by', table_name='api_tokens')
    op.drop_index('ix_api_tokens_is_active', table_name='api_tokens')
    op.drop_index('ix_api_tokens_token_hash', table_name='api_tokens')
    op.drop_index('ix_api_tokens_company_id', table_name='api_tokens')
    op.drop_table('api_tokens')

