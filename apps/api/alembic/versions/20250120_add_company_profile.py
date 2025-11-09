"""Add company profile tables (addresses, compliance info, default consignee/shipper)

Revision ID: 20250120_add_company_profile
Revises: 20250115_add_rulesets_and_audit_tables
Create Date: 2025-01-20 12:00:00.000000

This migration adds:
1. company_addresses table for address book
2. company_compliance_info table for compliance and regulatory information
3. default_consignee_shipper table for pre-filling forms
4. Foreign key constraints and indexes
5. Enums for AddressType and ComplianceStatus

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers
revision = '20250120_add_company_profile'
down_revision = '20250115_add_rulesets_and_audit_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Apply company profile tables"""

    # Create AddressType enum
    op.execute("CREATE TYPE addresstype AS ENUM ('business', 'shipping', 'billing', 'warehouse', 'custom')")
    
    # Create ComplianceStatus enum
    op.execute("CREATE TYPE compliancestatus AS ENUM ('pending', 'verified', 'expired', 'rejected')")

    # Create company_addresses table
    op.create_table(
        'company_addresses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('address_type', postgresql.ENUM('business', 'shipping', 'billing', 'warehouse', 'custom', name='addresstype'), nullable=False, server_default='business'),
        sa.Column('street_address', sa.Text(), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(50), nullable=True),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('is_default_shipping', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_default_billing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata_', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_company_addresses_company_id', 'company_addresses', ['company_id'])

    # Create company_compliance_info table
    op.create_table(
        'company_compliance_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_id', sa.String(100), nullable=True),
        sa.Column('vat_number', sa.String(100), nullable=True),
        sa.Column('registration_number', sa.String(128), nullable=True),
        sa.Column('regulator_id', sa.String(128), nullable=True),
        sa.Column('compliance_status', postgresql.ENUM('pending', 'verified', 'expired', 'rejected', name='compliancestatus'), nullable=False, server_default='pending'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('compliance_documents', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_company_compliance_info_company_id', 'company_compliance_info', ['company_id'])

    # Create default_consignee_shipper table
    op.create_table(
        'default_consignee_shipper',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type_', sa.String(50), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('address_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('street_address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(50), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('bank_name', sa.String(255), nullable=True),
        sa.Column('bank_account', sa.String(100), nullable=True),
        sa.Column('swift_code', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata_', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['address_id'], ['company_addresses.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_default_consignee_shipper_company_id', 'default_consignee_shipper', ['company_id'])


def downgrade():
    """Revert company profile tables"""
    op.drop_index('ix_default_consignee_shipper_company_id', table_name='default_consignee_shipper')
    op.drop_table('default_consignee_shipper')
    op.drop_index('ix_company_compliance_info_company_id', table_name='company_compliance_info')
    op.drop_table('company_compliance_info')
    op.drop_index('ix_company_addresses_company_id', table_name='company_addresses')
    op.drop_table('company_addresses')
    op.execute('DROP TYPE compliancestatus')
    op.execute('DROP TYPE addresstype')

