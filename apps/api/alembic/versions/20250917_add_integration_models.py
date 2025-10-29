"""Add integration models for partner API management

Revision ID: 20250917_002
Revises: 20250917_001
Create Date: 2025-09-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250917_002'
down_revision = '20250917_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create integration type enum
    integration_type_enum = postgresql.ENUM(
        'bank', 'customs', 'logistics', 'fx_provider', 'insurance',
        name='integrationtype'
    )
    integration_type_enum.create(op.get_bind())

    # Create integration status enum
    integration_status_enum = postgresql.ENUM(
        'active', 'inactive', 'pending', 'suspended', 'deprecated',
        name='integrationstatus'
    )
    integration_status_enum.create(op.get_bind())

    # Create billing event type enum
    billing_event_enum = postgresql.ENUM(
        'sme_validation', 'bank_recheck', 'customs_submission',
        'logistics_tracking', 'fx_quote', 'insurance_quote',
        name='billingeventtype'
    )
    billing_event_enum.create(op.get_bind())

    # Create integrations table
    op.create_table(
        'integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('type', integration_type_enum, nullable=False),
        sa.Column('status', integration_status_enum, nullable=False, default='active'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('base_url', sa.String(500), nullable=False),
        sa.Column('sandbox_url', sa.String(500), nullable=True),
        sa.Column('documentation_url', sa.String(500), nullable=True),
        sa.Column('supported_countries', postgresql.JSONB, nullable=True),
        sa.Column('supported_currencies', postgresql.JSONB, nullable=True),
        sa.Column('api_version', sa.String(50), nullable=False, default='v1'),
        sa.Column('requires_mtls', sa.Boolean, nullable=False, default=False),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer, nullable=False, default=60),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, default=30),
        sa.Column('retry_attempts', sa.Integer, nullable=False, default=3),
        sa.Column('config_schema', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.Index('ix_integrations_type', 'type'),
        sa.Index('ix_integrations_status', 'status'),
        sa.UniqueConstraint('name', name='uq_integrations_name')
    )

    # Create company_integrations table
    op.create_table(
        'company_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('client_id', sa.String(255), nullable=True),
        sa.Column('client_secret', sa.String(500), nullable=True),
        sa.Column('oauth_token', sa.Text, nullable=True),
        sa.Column('oauth_refresh_token', sa.Text, nullable=True),
        sa.Column('oauth_expires_at', sa.DateTime, nullable=True),
        sa.Column('custom_config', postgresql.JSONB, nullable=True),
        sa.Column('billing_tier', sa.String(50), nullable=False, default='standard'),
        sa.Column('price_per_check', sa.Numeric(10, 4), nullable=True),
        sa.Column('monthly_quota', sa.Integer, nullable=True),
        sa.Column('usage_count', sa.Integer, nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),

        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id']),
        sa.Index('ix_company_integrations_company', 'company_id'),
        sa.Index('ix_company_integrations_integration', 'integration_id'),
        sa.UniqueConstraint('company_id', 'integration_id', name='uq_company_integration')
    )

    # Create integration_submissions table
    op.create_table(
        'integration_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submission_type', sa.String(50), nullable=False),
        sa.Column('external_reference_id', sa.String(255), nullable=True),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('request_payload', postgresql.JSONB, nullable=False),
        sa.Column('response_payload', postgresql.JSONB, nullable=True),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('billing_recorded', sa.Boolean, nullable=False, default=False),
        sa.Column('submitted_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('next_retry_at', sa.DateTime, nullable=True),

        sa.ForeignKeyConstraint(['session_id'], ['validation_sessions.id']),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.Index('ix_integration_submissions_session', 'session_id'),
        sa.Index('ix_integration_submissions_integration', 'integration_id'),
        sa.Index('ix_integration_submissions_company', 'company_id'),
        sa.Index('ix_integration_submissions_status', 'status_code'),
        sa.Index('ix_integration_submissions_retry', 'next_retry_at'),
        sa.UniqueConstraint('idempotency_key', name='uq_integration_submissions_idempotency')
    )

    # Create integration_billing_events table
    op.create_table(
        'integration_billing_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', billing_event_enum, nullable=False),
        sa.Column('charged_amount', sa.Numeric(10, 4), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('billing_tier', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recorded_at', sa.DateTime, nullable=False),

        sa.ForeignKeyConstraint(['submission_id'], ['integration_submissions.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.Index('ix_integration_billing_company', 'company_id'),
        sa.Index('ix_integration_billing_integration', 'integration_id'),
        sa.Index('ix_integration_billing_event_type', 'event_type'),
        sa.Index('ix_integration_billing_recorded_at', 'recorded_at')
    )

    # Create integration_health_checks table
    op.create_table(
        'integration_health_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('is_healthy', sa.Boolean, nullable=False, default=True),
        sa.Column('checked_at', sa.DateTime, nullable=False),

        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id']),
        sa.Index('ix_integration_health_integration', 'integration_id'),
        sa.Index('ix_integration_health_checked_at', 'checked_at')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('integration_health_checks')
    op.drop_table('integration_billing_events')
    op.drop_table('integration_submissions')
    op.drop_table('company_integrations')
    op.drop_table('integrations')

    # Drop enums
    op.execute('DROP TYPE billingeventtype')
    op.execute('DROP TYPE integrationstatus')
    op.execute('DROP TYPE integrationtype')