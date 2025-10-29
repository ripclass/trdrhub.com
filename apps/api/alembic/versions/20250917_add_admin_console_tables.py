"""Add admin console tables

Revision ID: 20250917_add_admin_console_tables
Revises: 20250917_add_integration_models
Create Date: 2024-09-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250917_add_admin_console_tables'
down_revision = '20250917_add_integration_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create custom ENUM types
    approval_status_enum = postgresql.ENUM(
        'pending', 'approved', 'rejected', 'expired', 'cancelled',
        name='approval_status'
    )
    approval_status_enum.create(op.get_bind())

    job_status_enum = postgresql.ENUM(
        'queued', 'running', 'completed', 'failed', 'cancelled', 'retrying',
        name='job_status'
    )
    job_status_enum.create(op.get_bind())

    adjustment_type_enum = postgresql.ENUM(
        'credit', 'debit', 'refund', 'write_off', 'promotional',
        name='adjustment_type'
    )
    adjustment_type_enum.create(op.get_bind())

    adjustment_status_enum = postgresql.ENUM(
        'pending', 'approved', 'rejected', 'applied',
        name='adjustment_status'
    )
    adjustment_status_enum.create(op.get_bind())

    credit_type_enum = postgresql.ENUM(
        'fixed_amount', 'percentage', 'free_tier_upgrade',
        name='credit_type'
    )
    credit_type_enum.create(op.get_bind())

    dispute_type_enum = postgresql.ENUM(
        'chargeback', 'inquiry', 'quality_dispute', 'billing_error',
        name='dispute_type'
    )
    dispute_type_enum.create(op.get_bind())

    dispute_status_enum = postgresql.ENUM(
        'open', 'investigating', 'resolved', 'escalated',
        name='dispute_status'
    )
    dispute_status_enum.create(op.get_bind())

    partner_type_enum = postgresql.ENUM(
        'bank', 'customs', 'logistics', 'payment', 'data_provider',
        name='partner_type'
    )
    partner_type_enum.create(op.get_bind())

    environment_type_enum = postgresql.ENUM(
        'sandbox', 'staging', 'production',
        name='environment_type'
    )
    environment_type_enum.create(op.get_bind())

    partner_status_enum = postgresql.ENUM(
        'active', 'inactive', 'suspended', 'deprecated',
        name='partner_status'
    )
    partner_status_enum.create(op.get_bind())

    connector_status_enum = postgresql.ENUM(
        'healthy', 'degraded', 'down', 'unknown',
        name='connector_status'
    )
    connector_status_enum.create(op.get_bind())

    delivery_status_enum = postgresql.ENUM(
        'pending', 'delivered', 'failed', 'retrying', 'abandoned',
        name='delivery_status'
    )
    delivery_status_enum.create(op.get_bind())

    service_account_type_enum = postgresql.ENUM(
        'internal', 'partner', 'webhook', 'backup',
        name='service_account_type'
    )
    service_account_type_enum.create(op.get_bind())

    data_region_enum = postgresql.ENUM(
        'BD', 'EU', 'SG', 'US', 'GLOBAL',
        name='data_region'
    )
    data_region_enum.create(op.get_bind())

    legal_hold_status_enum = postgresql.ENUM(
        'active', 'released', 'expired',
        name='legal_hold_status'
    )
    legal_hold_status_enum.create(op.get_bind())

    prompt_language_enum = postgresql.ENUM(
        'en', 'bn', 'ar', 'zh',
        name='prompt_language'
    )
    prompt_language_enum.create(op.get_bind())

    budget_period_enum = postgresql.ENUM(
        'daily', 'weekly', 'monthly', 'quarterly',
        name='budget_period'
    )
    budget_period_enum.create(op.get_bind())

    flag_type_enum = postgresql.ENUM(
        'boolean', 'string', 'number', 'json',
        name='flag_type'
    )
    flag_type_enum.create(op.get_bind())

    release_type_enum = postgresql.ENUM(
        'major', 'minor', 'patch', 'hotfix',
        name='release_type'
    )
    release_type_enum.create(op.get_bind())

    # Admin roles and permissions
    op.create_table('admin_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('permissions', postgresql.JSONB, nullable=False, default=sa.text("'[]'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now())
    )

    op.create_table('admin_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True)),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['role_id'], ['admin_roles.id']),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'])
    )

    # Audit events (partitioned by month)
    op.create_table('audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True)),
        sa.Column('actor_type', sa.String(50), nullable=False, default='user'),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('changes', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('session_id', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'])
    )

    # Create partition for current month
    op.execute("""
        CREATE TABLE audit_events_y2024m09 PARTITION OF audit_events
        FOR VALUES FROM ('2024-09-01') TO ('2024-10-01')
    """)

    # 4-eyes approval system
    op.create_table('approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('request_type', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', approval_status_enum, nullable=False, default='pending'),
        sa.Column('requested_changes', postgresql.JSONB, nullable=False),
        sa.Column('approval_reason', sa.Text),
        sa.Column('rejection_reason', sa.Text),
        sa.Column('auto_expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('rejected_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'])
    )

    # Break glass access
    op.create_table('break_glass_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('granted_permissions', postgresql.JSONB, nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'])
    )

    # Job queue management
    op.create_table('jobs_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('job_data', postgresql.JSONB, nullable=False),
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('status', job_status_enum, default='queued'),
        sa.Column('attempts', sa.Integer, default=0),
        sa.Column('max_attempts', sa.Integer, default=3),
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('error_stack', sa.Text),
        sa.Column('worker_id', sa.String(255)),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True)),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('lc_id', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )

    # Dead letter queue
    op.create_table('jobs_dlq',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('original_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('job_data', postgresql.JSONB, nullable=False),
        sa.Column('failure_reason', sa.Text, nullable=False),
        sa.Column('failure_count', sa.Integer, nullable=False),
        sa.Column('last_error', sa.Text),
        sa.Column('quarantine_reason', sa.Text),
        sa.Column('can_retry', sa.Boolean, default=True),
        sa.Column('retry_after', sa.TIMESTAMP(timezone=True)),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'])
    )

    # Job execution history
    op.create_table('jobs_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', job_status_enum, nullable=False),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('memory_mb', sa.Integer),
        sa.Column('cpu_percent', sa.Numeric(5, 2)),
        sa.Column('step_name', sa.String(100)),
        sa.Column('step_data', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now())
    )

    # Billing adjustments and credits
    op.create_table('billing_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', adjustment_type_enum, nullable=False),
        sa.Column('amount_usd', sa.Numeric(12, 2), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('reference_invoice_id', postgresql.UUID(as_uuid=True)),
        sa.Column('applied_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('status', adjustment_status_enum, default='pending'),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['applied_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
    )

    # Credits and promotions
    op.create_table('credits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('type', credit_type_enum, nullable=False),
        sa.Column('value_usd', sa.Numeric(12, 2)),
        sa.Column('percentage', sa.Integer),
        sa.Column('min_spend_usd', sa.Numeric(12, 2)),
        sa.Column('max_uses', sa.Integer),
        sa.Column('uses_count', sa.Integer, default=0),
        sa.Column('valid_from', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('valid_until', sa.TIMESTAMP(timezone=True)),
        sa.Column('applicable_plans', postgresql.ARRAY(sa.Text)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Disputes and chargebacks
    op.create_table('disputes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', dispute_type_enum, nullable=False),
        sa.Column('amount_usd', sa.Numeric(12, 2), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('evidence_url', sa.Text),
        sa.Column('status', dispute_status_enum, default='open'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True)),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'])
    )

    # Partner registry
    op.create_table('partner_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('type', partner_type_enum, nullable=False),
        sa.Column('environment', environment_type_enum, default='sandbox'),
        sa.Column('status', partner_status_enum, default='active'),
        sa.Column('api_endpoint', sa.Text),
        sa.Column('auth_config', postgresql.JSONB, nullable=False, default=sa.text("'{}'")),
        sa.Column('rate_limits', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('sla_config', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('contact_email', sa.String(255)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('technical_contact', postgresql.JSONB),
        sa.Column('business_contact', postgresql.JSONB),
        sa.Column('onboarded_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_health_check', sa.TIMESTAMP(timezone=True)),
        sa.Column('health_status', sa.String(20), default='unknown'),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now())
    )

    # Partner connectors health
    op.create_table('partner_connectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_type', sa.String(100), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False, default=sa.text("'{}'")),
        sa.Column('health_endpoint', sa.Text),
        sa.Column('last_success_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_failure_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('success_count', sa.Integer, default=0),
        sa.Column('failure_count', sa.Integer, default=0),
        sa.Column('avg_response_time_ms', sa.Integer),
        sa.Column('uptime_percentage', sa.Numeric(5, 2)),
        sa.Column('status', connector_status_enum, default='unknown'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_registry.id'])
    )

    # Webhook deliveries
    op.create_table('webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_url', sa.Text, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('headers', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('http_status', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('delivery_time_ms', sa.Integer),
        sa.Column('attempts', sa.Integer, default=1),
        sa.Column('max_attempts', sa.Integer, default=3),
        sa.Column('status', delivery_status_enum, default='pending'),
        sa.Column('next_retry_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('delivered_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('failed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_registry.id'])
    )

    # Webhook DLQ
    op.create_table('webhook_dlq',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('original_delivery_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_url', sa.Text, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('failure_reason', sa.Text, nullable=False),
        sa.Column('failure_count', sa.Integer, nullable=False),
        sa.Column('can_replay', sa.Boolean, default=True),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['original_delivery_id'], ['webhook_deliveries.id']),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_registry.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'])
    )

    # API Keys management
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(20), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.Text), nullable=False, default=sa.text("'{}'")),
        sa.Column('rate_limit', sa.Integer, default=1000),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_used_ip', postgresql.INET),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Service accounts
    op.create_table('service_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('type', service_account_type_enum, default='internal'),
        sa.Column('permissions', postgresql.JSONB, nullable=False, default=sa.text("'[]'")),
        sa.Column('ip_allowlist', postgresql.ARRAY(sa.Text)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_rotation_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('next_rotation_due', sa.TIMESTAMP(timezone=True)),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # IP allowlists
    op.create_table('ip_allowlists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True)),
        sa.Column('ip_ranges', postgresql.JSONB, nullable=False),
        sa.Column('is_global', sa.Boolean, default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Session management
    op.create_table('user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('device_info', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('ip_address', postgresql.INET, nullable=False),
        sa.Column('user_agent', sa.Text),
        sa.Column('location', postgresql.JSONB),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_activity_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )

    # Data residency policies
    op.create_table('data_residency_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('region', data_region_enum, nullable=False),
        sa.Column('data_types', postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column('storage_location', sa.String(100), nullable=False),
        sa.Column('encryption_key_id', sa.String(255)),
        sa.Column('compliance_frameworks', postgresql.ARRAY(sa.Text)),
        sa.Column('policy_document_url', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('effective_from', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
    )

    # Retention policies
    op.create_table('retention_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('data_type', sa.String(100), nullable=False),
        sa.Column('retention_period_days', sa.Integer, nullable=False),
        sa.Column('archive_after_days', sa.Integer),
        sa.Column('delete_after_days', sa.Integer),
        sa.Column('legal_basis', sa.Text),
        sa.Column('applies_to_regions', postgresql.ARRAY(data_region_enum)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
    )

    # Legal holds
    op.create_table('legal_holds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('case_number', sa.String(100), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True)),
        sa.Column('data_types', postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column('date_range_start', sa.Date),
        sa.Column('date_range_end', sa.Date),
        sa.Column('custodian_users', postgresql.ARRAY(postgresql.UUID)),
        sa.Column('search_terms', postgresql.ARRAY(sa.Text)),
        sa.Column('status', legal_hold_status_enum, default='active'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('legal_contact', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('closed_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # LLM prompt library
    op.create_table('llm_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('prompt_type', sa.String(100), nullable=False),
        sa.Column('system_prompt', sa.Text, nullable=False),
        sa.Column('user_template', sa.Text, nullable=False),
        sa.Column('language', prompt_language_enum, default='en'),
        sa.Column('model_constraints', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('safety_filters', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('test_results', postgresql.JSONB),
        sa.Column('performance_metrics', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.UniqueConstraint('name', 'version')
    )

    # LLM evaluation runs
    op.create_table('llm_eval_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('eval_set_name', sa.String(200), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('test_cases_count', sa.Integer, nullable=False),
        sa.Column('passed_count', sa.Integer, default=0),
        sa.Column('failed_count', sa.Integer, default=0),
        sa.Column('avg_latency_ms', sa.Integer),
        sa.Column('avg_tokens_used', sa.Integer),
        sa.Column('cost_usd', sa.Numeric(10, 4)),
        sa.Column('quality_score', sa.Numeric(3, 2)),
        sa.Column('safety_score', sa.Numeric(3, 2)),
        sa.Column('detailed_results', postgresql.JSONB),
        sa.Column('run_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['prompt_id'], ['llm_prompts.id']),
        sa.ForeignKeyConstraint(['run_by'], ['users.id'])
    )

    # LLM budgets and usage
    op.create_table('llm_budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('budget_period', budget_period_enum, default='monthly'),
        sa.Column('budget_usd', sa.Numeric(10, 2), nullable=False),
        sa.Column('used_usd', sa.Numeric(10, 2), default=0),
        sa.Column('token_budget', sa.Integer),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('alert_threshold_percent', sa.Integer, default=80),
        sa.Column('hard_limit_enabled', sa.Boolean, default=False),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Feature flags
    op.create_table('feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('type', flag_type_enum, default='boolean'),
        sa.Column('default_value', postgresql.JSONB, default=sa.text("'false'")),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('rollout_percentage', sa.Integer, default=0),
        sa.Column('targeting_rules', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Feature flag evaluations
    op.create_table('flag_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('flag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True)),
        sa.Column('evaluation_context', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('result_value', postgresql.JSONB, nullable=False),
        sa.Column('evaluation_reason', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['flag_id'], ['feature_flags.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'])
    )

    # Release notes
    op.create_table('release_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('version', sa.String(50), nullable=False, unique=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('release_type', release_type_enum, default='minor'),
        sa.Column('features', postgresql.JSONB, default=sa.text("'[]'")),
        sa.Column('bug_fixes', postgresql.JSONB, default=sa.text("'[]'")),
        sa.Column('breaking_changes', postgresql.JSONB, default=sa.text("'[]'")),
        sa.Column('migration_notes', sa.Text),
        sa.Column('rollout_strategy', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('published_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_published', sa.Boolean, default=False),
        sa.Column('metadata', postgresql.JSONB, default=sa.text("'{}'")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.now()),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'])
    )

    # Create indexes for performance
    op.create_index('idx_audit_events_created_at', 'audit_events', ['created_at'])
    op.create_index('idx_audit_events_actor_id', 'audit_events', ['actor_id'])
    op.create_index('idx_audit_events_organization_id', 'audit_events', ['organization_id'])
    op.create_index('idx_audit_events_resource', 'audit_events', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_events_action', 'audit_events', ['action'])

    op.create_index('idx_jobs_queue_status_priority', 'jobs_queue', ['status', 'priority', 'scheduled_at'])
    op.create_index('idx_jobs_queue_organization_id', 'jobs_queue', ['organization_id'])
    op.create_index('idx_jobs_queue_job_type', 'jobs_queue', ['job_type'])
    op.create_index('idx_jobs_dlq_partner_id', 'jobs_dlq', ['original_job_id'])

    op.create_index('idx_billing_adjustments_org_status', 'billing_adjustments', ['organization_id', 'status'])
    op.create_index('idx_disputes_status_assigned', 'disputes', ['status', 'assigned_to'])

    op.create_index('idx_partner_registry_type_status', 'partner_registry', ['type', 'status'])
    op.create_index('idx_webhook_deliveries_partner_status', 'webhook_deliveries', ['partner_id', 'status'])

    op.create_index('idx_api_keys_organization_active', 'api_keys', ['organization_id', 'is_active'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])

    op.create_index('idx_feature_flags_active', 'feature_flags', ['is_active'])
    op.create_index('idx_flag_evaluations_flag_user', 'flag_evaluations', ['flag_id', 'user_id', 'created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_flag_evaluations_flag_user')
    op.drop_index('idx_feature_flags_active')
    op.drop_index('idx_api_keys_key_hash')
    op.drop_index('idx_api_keys_organization_active')
    op.drop_index('idx_webhook_deliveries_partner_status')
    op.drop_index('idx_partner_registry_type_status')
    op.drop_index('idx_disputes_status_assigned')
    op.drop_index('idx_billing_adjustments_org_status')
    op.drop_index('idx_jobs_dlq_partner_id')
    op.drop_index('idx_jobs_queue_job_type')
    op.drop_index('idx_jobs_queue_organization_id')
    op.drop_index('idx_jobs_queue_status_priority')
    op.drop_index('idx_audit_events_action')
    op.drop_index('idx_audit_events_resource')
    op.drop_index('idx_audit_events_organization_id')
    op.drop_index('idx_audit_events_actor_id')
    op.drop_index('idx_audit_events_created_at')

    # Drop tables in reverse order
    op.drop_table('release_notes')
    op.drop_table('flag_evaluations')
    op.drop_table('feature_flags')
    op.drop_table('llm_budgets')
    op.drop_table('llm_eval_runs')
    op.drop_table('llm_prompts')
    op.drop_table('legal_holds')
    op.drop_table('retention_policies')
    op.drop_table('data_residency_policies')
    op.drop_table('user_sessions')
    op.drop_table('ip_allowlists')
    op.drop_table('service_accounts')
    op.drop_table('api_keys')
    op.drop_table('webhook_dlq')
    op.drop_table('webhook_deliveries')
    op.drop_table('partner_connectors')
    op.drop_table('partner_registry')
    op.drop_table('disputes')
    op.drop_table('credits')
    op.drop_table('billing_adjustments')
    op.drop_table('jobs_history')
    op.drop_table('jobs_dlq')
    op.drop_table('jobs_queue')
    op.drop_table('break_glass_events')
    op.drop_table('approvals')

    # Drop partition first
    op.execute("DROP TABLE IF EXISTS audit_events_y2024m09")
    op.drop_table('audit_events')

    op.drop_table('admin_users')
    op.drop_table('admin_roles')

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS release_type")
    op.execute("DROP TYPE IF EXISTS flag_type")
    op.execute("DROP TYPE IF EXISTS budget_period")
    op.execute("DROP TYPE IF EXISTS prompt_language")
    op.execute("DROP TYPE IF EXISTS legal_hold_status")
    op.execute("DROP TYPE IF EXISTS data_region")
    op.execute("DROP TYPE IF EXISTS service_account_type")
    op.execute("DROP TYPE IF EXISTS delivery_status")
    op.execute("DROP TYPE IF EXISTS connector_status")
    op.execute("DROP TYPE IF EXISTS partner_status")
    op.execute("DROP TYPE IF EXISTS environment_type")
    op.execute("DROP TYPE IF EXISTS partner_type")
    op.execute("DROP TYPE IF EXISTS dispute_status")
    op.execute("DROP TYPE IF EXISTS dispute_type")
    op.execute("DROP TYPE IF EXISTS credit_type")
    op.execute("DROP TYPE IF EXISTS adjustment_status")
    op.execute("DROP TYPE IF EXISTS adjustment_type")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS approval_status")