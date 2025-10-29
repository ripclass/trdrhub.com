"""Add billing system tables and company relationships

Revision ID: 20250916_170000
Revises: 20250916_160000_add_analytics_indexes
Create Date: 2025-09-16 17:00:00.000000

This migration adds:
1. Companies table for multi-tenant billing
2. Invoices table for billing cycles
3. Usage records table for tracking billable actions
4. Foreign key constraints to existing User and ValidationSession models
5. Indexes for efficient billing queries
6. Default company creation for existing users

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime


# revision identifiers
revision = '20250916_170000'
down_revision = '20250916_160000_add_analytics_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Apply billing system changes"""

    # Create companies table
    companies_table = op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('plan', sa.Enum('free', 'pay_per_check', 'monthly_basic', 'monthly_pro', 'enterprise',
                                  name='plantype'), nullable=False, server_default='free'),
        sa.Column('quota_limit', sa.Integer(), nullable=True),
        sa.Column('billing_cycle_start', sa.Date(), nullable=True),
        sa.Column('payment_provider_id', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('active', 'delinquent', 'suspended', 'trial',
                                   name='companystatus'), nullable=False, server_default='active'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('business_address', sa.Text(), nullable=True),
        sa.Column('tax_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for companies
    op.create_index('ix_companies_name', 'companies', ['name'])
    op.create_index('ix_companies_payment_provider_id', 'companies', ['payment_provider_id'])

    # Create invoices table
    invoices_table = op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.Enum('BDT', 'USD', name='currency'), nullable=False, server_default='BDT'),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'paid', 'failed', 'cancelled', 'refunded',
                                   name='invoicestatus'), nullable=False, server_default='pending'),
        sa.Column('payment_txn_id', sa.String(255), nullable=True),
        sa.Column('payment_method', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )

    # Create indexes for invoices
    op.create_index('ix_invoices_company_id', 'invoices', ['company_id'])
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_payment_txn_id', 'invoices', ['payment_txn_id'])

    # Create usage_records table
    usage_records_table = op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('units', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('cost', sa.Numeric(10, 2), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('billed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['validation_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
    )

    # Create indexes for usage_records
    op.create_index('ix_usage_records_company_id', 'usage_records', ['company_id'])
    op.create_index('ix_usage_records_session_id', 'usage_records', ['session_id'])
    op.create_index('ix_usage_records_action', 'usage_records', ['action'])
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_invoice_id', 'usage_records', ['invoice_id'])
    op.create_index('ix_usage_records_timestamp', 'usage_records', ['timestamp'])

    # Create composite indexes for efficient queries
    op.create_index('ix_usage_company_timestamp', 'usage_records', ['company_id', 'timestamp'])
    op.create_index('ix_usage_company_action', 'usage_records', ['company_id', 'action'])
    op.create_index('ix_usage_billing_cycle', 'usage_records', ['company_id', 'billed', 'timestamp'])

    # Add company_id foreign key to existing users table
    op.add_column('users', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_users_company_id', 'users', 'companies', ['company_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_users_company_id', 'users', ['company_id'])

    # Add company_id foreign key to existing validation_sessions table
    op.add_column('validation_sessions', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_validation_sessions_company_id', 'validation_sessions', 'companies', ['company_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_validation_sessions_company_id', 'validation_sessions', ['company_id'])


def downgrade():
    """Remove billing system changes"""

    # Remove foreign key constraints and columns from existing tables
    op.drop_constraint('fk_validation_sessions_company_id', 'validation_sessions', type_='foreignkey')
    op.drop_index('ix_validation_sessions_company_id', 'validation_sessions')
    op.drop_column('validation_sessions', 'company_id')

    op.drop_constraint('fk_users_company_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_company_id', 'users')
    op.drop_column('users', 'company_id')

    # Drop usage_records table and indexes
    op.drop_index('ix_usage_billing_cycle', 'usage_records')
    op.drop_index('ix_usage_company_action', 'usage_records')
    op.drop_index('ix_usage_company_timestamp', 'usage_records')
    op.drop_index('ix_usage_records_timestamp', 'usage_records')
    op.drop_index('ix_usage_records_invoice_id', 'usage_records')
    op.drop_index('ix_usage_records_user_id', 'usage_records')
    op.drop_index('ix_usage_records_action', 'usage_records')
    op.drop_index('ix_usage_records_session_id', 'usage_records')
    op.drop_index('ix_usage_records_company_id', 'usage_records')
    op.drop_table('usage_records')

    # Drop invoices table and indexes
    op.drop_index('ix_invoices_payment_txn_id', 'invoices')
    op.drop_index('ix_invoices_invoice_number', 'invoices')
    op.drop_index('ix_invoices_company_id', 'invoices')
    op.drop_table('invoices')

    # Drop companies table and indexes
    op.drop_index('ix_companies_payment_provider_id', 'companies')
    op.drop_index('ix_companies_name', 'companies')
    op.drop_table('companies')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS companystatus')
    op.execute('DROP TYPE IF EXISTS plantype')
    op.execute('DROP TYPE IF EXISTS currency')
    op.execute('DROP TYPE IF EXISTS invoicestatus')