"""Hub Multi-Tool Foundation - Organizations, Plans, Subscriptions, Usage

Adds infrastructure for multi-tool SaaS architecture:
- Extends companies table with org fields
- Creates hub_plans table for pricing tiers
- Creates hub_subscriptions for plan tracking
- Creates hub_usage for monthly usage tracking
- Creates hub_usage_logs for detailed audit

Revision ID: hub_multi_tool_001
Revises: 20251201_commodity_resolution
Create Date: 2025-12-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

# revision identifiers
revision = 'hub_multi_tool_001'
down_revision = '20251201_commodity_resolution'  # Fixed: use actual revision ID
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # 1. EXTEND COMPANIES TABLE (now acts as "organizations")
    # =========================================================================
    
    # Add new columns to companies table for multi-tool support
    op.add_column('companies', sa.Column('org_type', sa.String(50), nullable=True, comment='exporter, importer, both, bank'))
    op.add_column('companies', sa.Column('org_size', sa.String(50), nullable=True, comment='sme, medium, large'))
    op.add_column('companies', sa.Column('slug', sa.String(100), nullable=True, unique=True, comment='URL-friendly identifier'))
    op.add_column('companies', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('companies', sa.Column('white_label_config', JSONB, nullable=True, comment='For banks: logo, colors, domain'))
    
    # Create index on slug
    op.create_index('ix_companies_slug', 'companies', ['slug'], unique=True)
    
    # =========================================================================
    # 2. CREATE HUB_PLANS TABLE (Pricing tiers)
    # =========================================================================
    
    op.create_table(
        'hub_plans',
        sa.Column('id', sa.String(50), primary_key=True, comment='payg, starter, growth, pro, enterprise'),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=True, comment='NULL for payg and enterprise'),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=True),
        
        # Limits per tool (-1 = unlimited, 0 = not included)
        sa.Column('limits', JSONB, nullable=False, comment='{"lc_validations": 10, "price_checks": 30, ...}'),
        
        # Overage rates when limits exceeded
        sa.Column('overage_rates', JSONB, nullable=False, comment='{"lc_validations": 7.00, "price_checks": 0.80, ...}'),
        
        # Feature flags
        sa.Column('features', JSONB, nullable=True, comment='{"api_access": false, "priority_support": false, ...}'),
        
        # User limits
        sa.Column('max_users', sa.Integer, default=1, comment='-1 = unlimited'),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('display_order', sa.Integer, default=0, comment='Order on pricing page'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # =========================================================================
    # 3. CREATE HUB_SUBSCRIPTIONS TABLE
    # =========================================================================
    
    op.create_table(
        'hub_subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(50), sa.ForeignKey('hub_plans.id'), nullable=False),
        
        # Subscription status
        sa.Column('status', sa.String(50), default='active', nullable=False, 
                  comment='active, cancelled, past_due, trialing, paused'),
        
        # Billing period
        sa.Column('current_period_start', sa.Date, nullable=False),
        sa.Column('current_period_end', sa.Date, nullable=False),
        
        # Cancellation
        sa.Column('cancel_at_period_end', sa.Boolean, default=False, nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        
        # Trial
        sa.Column('trial_end', sa.Date, nullable=True),
        
        # Stripe integration
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # One active subscription per company
    op.create_index('ix_hub_subscriptions_company', 'hub_subscriptions', ['company_id'], unique=True)
    op.create_index('ix_hub_subscriptions_status', 'hub_subscriptions', ['status'])
    
    # =========================================================================
    # 4. CREATE HUB_USAGE TABLE (Monthly aggregated usage)
    # =========================================================================
    
    op.create_table(
        'hub_usage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period', sa.String(7), nullable=False, comment='YYYY-MM format'),
        
        # Usage counts per tool
        sa.Column('lc_validations_used', sa.Integer, default=0, nullable=False),
        sa.Column('price_checks_used', sa.Integer, default=0, nullable=False),
        sa.Column('hs_lookups_used', sa.Integer, default=0, nullable=False),
        sa.Column('sanctions_screens_used', sa.Integer, default=0, nullable=False),
        sa.Column('container_tracks_used', sa.Integer, default=0, nullable=False),
        
        # Overage tracking
        sa.Column('lc_validations_overage', sa.Integer, default=0, nullable=False),
        sa.Column('price_checks_overage', sa.Integer, default=0, nullable=False),
        sa.Column('hs_lookups_overage', sa.Integer, default=0, nullable=False),
        sa.Column('sanctions_screens_overage', sa.Integer, default=0, nullable=False),
        sa.Column('container_tracks_overage', sa.Integer, default=0, nullable=False),
        
        # Total overage charges for the period
        sa.Column('overage_charges', sa.Numeric(10, 2), default=0, nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # One record per company per period
    op.create_index('ix_hub_usage_company_period', 'hub_usage', ['company_id', 'period'], unique=True)
    op.create_index('ix_hub_usage_period', 'hub_usage', ['period'])
    
    # =========================================================================
    # 5. CREATE HUB_USAGE_LOGS TABLE (Detailed audit trail)
    # =========================================================================
    
    op.create_table(
        'hub_usage_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Operation details
        sa.Column('operation', sa.String(50), nullable=False, 
                  comment='lc_validation, price_check, hs_lookup, sanctions_screen, container_track'),
        sa.Column('tool', sa.String(50), nullable=False,
                  comment='lcopilot, price_verify, hs_code, sanctions, tracking'),
        sa.Column('quantity', sa.Integer, default=1, nullable=False),
        
        # Cost (if overage)
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True, comment='Cost if overage charge applied'),
        sa.Column('is_overage', sa.Boolean, default=False, nullable=False),
        
        # Context
        sa.Column('metadata', JSONB, nullable=True, comment='{"job_id": "xxx", "document_count": 6, ...}'),
        sa.Column('description', sa.String(500), nullable=True),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Indexes for querying
    op.create_index('ix_hub_usage_logs_company', 'hub_usage_logs', ['company_id'])
    op.create_index('ix_hub_usage_logs_user', 'hub_usage_logs', ['user_id'])
    op.create_index('ix_hub_usage_logs_operation', 'hub_usage_logs', ['operation'])
    op.create_index('ix_hub_usage_logs_tool', 'hub_usage_logs', ['tool'])
    op.create_index('ix_hub_usage_logs_created', 'hub_usage_logs', ['created_at'])
    op.create_index('ix_hub_usage_logs_company_created', 'hub_usage_logs', ['company_id', 'created_at'])
    
    # =========================================================================
    # 6. SEED DEFAULT PLANS
    # =========================================================================
    
    hub_plans = sa.table(
        'hub_plans',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('price_monthly', sa.Numeric),
        sa.column('price_yearly', sa.Numeric),
        sa.column('limits', JSONB),
        sa.column('overage_rates', JSONB),
        sa.column('features', JSONB),
        sa.column('max_users', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('display_order', sa.Integer),
    )
    
    op.bulk_insert(hub_plans, [
        {
            'id': 'payg',
            'name': 'Pay-as-you-go',
            'description': 'No monthly commitment. Pay only for what you use.',
            'price_monthly': None,
            'price_yearly': None,
            'limits': {
                'lc_validations': 0,
                'price_checks': 0,
                'hs_lookups': 0,
                'sanctions_screens': 0,
                'container_tracks': 0
            },
            'overage_rates': {
                'lc_validations': 8.00,
                'price_checks': 1.00,
                'hs_lookups': 0.50,
                'sanctions_screens': 2.00,
                'container_tracks': 1.50
            },
            'features': {
                'api_access': False,
                'priority_support': False,
                'data_export': 'basic',
                'white_label': False
            },
            'max_users': 1,
            'is_active': True,
            'display_order': 0
        },
        {
            'id': 'starter',
            'name': 'Starter',
            'description': 'Perfect for small businesses with occasional needs.',
            'price_monthly': 49.00,
            'price_yearly': 470.00,
            'limits': {
                'lc_validations': 10,
                'price_checks': 30,
                'hs_lookups': 50,
                'sanctions_screens': 20,
                'container_tracks': 10
            },
            'overage_rates': {
                'lc_validations': 7.00,
                'price_checks': 0.80,
                'hs_lookups': 0.40,
                'sanctions_screens': 1.50,
                'container_tracks': 1.20
            },
            'features': {
                'api_access': False,
                'priority_support': False,
                'data_export': 'full',
                'white_label': False
            },
            'max_users': 1,
            'is_active': True,
            'display_order': 1
        },
        {
            'id': 'growth',
            'name': 'Growth',
            'description': 'For growing SMEs with regular trade activity.',
            'price_monthly': 99.00,
            'price_yearly': 950.00,
            'limits': {
                'lc_validations': 30,
                'price_checks': 80,
                'hs_lookups': 150,
                'sanctions_screens': 60,
                'container_tracks': 30
            },
            'overage_rates': {
                'lc_validations': 6.00,
                'price_checks': 0.60,
                'hs_lookups': 0.30,
                'sanctions_screens': 1.20,
                'container_tracks': 1.00
            },
            'features': {
                'api_access': False,
                'priority_support': False,
                'data_export': 'full',
                'white_label': False
            },
            'max_users': 3,
            'is_active': True,
            'display_order': 2
        },
        {
            'id': 'pro',
            'name': 'Pro',
            'description': 'For active trading companies with high volume.',
            'price_monthly': 199.00,
            'price_yearly': 1910.00,
            'limits': {
                'lc_validations': 80,
                'price_checks': 200,
                'hs_lookups': 400,
                'sanctions_screens': 150,
                'container_tracks': 80
            },
            'overage_rates': {
                'lc_validations': 5.00,
                'price_checks': 0.40,
                'hs_lookups': 0.20,
                'sanctions_screens': 1.00,
                'container_tracks': 0.80
            },
            'features': {
                'api_access': True,
                'priority_support': True,
                'data_export': 'full_api',
                'white_label': False
            },
            'max_users': 10,
            'is_active': True,
            'display_order': 3
        },
        {
            'id': 'enterprise',
            'name': 'Enterprise',
            'description': 'Custom solutions for banks and large enterprises.',
            'price_monthly': None,
            'price_yearly': None,
            'limits': {
                'lc_validations': -1,
                'price_checks': -1,
                'hs_lookups': -1,
                'sanctions_screens': -1,
                'container_tracks': -1
            },
            'overage_rates': {
                'lc_validations': 1.50,
                'price_checks': 0.20,
                'hs_lookups': 0.10,
                'sanctions_screens': 0.50,
                'container_tracks': 0.40
            },
            'features': {
                'api_access': True,
                'priority_support': True,
                'data_export': 'full_api',
                'white_label': True,
                'sso': True,
                'custom_integrations': True,
                'dedicated_support': True
            },
            'max_users': -1,
            'is_active': True,
            'display_order': 4
        }
    ])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('hub_usage_logs')
    op.drop_table('hub_usage')
    op.drop_table('hub_subscriptions')
    op.drop_table('hub_plans')
    
    # Remove added columns from companies
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_column('companies', 'white_label_config')
    op.drop_column('companies', 'stripe_customer_id')
    op.drop_column('companies', 'slug')
    op.drop_column('companies', 'org_size')
    op.drop_column('companies', 'org_type')

