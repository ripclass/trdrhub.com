"""Add Doc Generator Phase 2 - Templates, Catalog, Buyers, Audit

Revision ID: doc_gen_phase2
Revises: doc_gen_phase1
Create Date: 2024-12-05

Adds:
- document_audit_logs table for audit trail
- document_templates table for reusable templates
- product_catalog table for frequently shipped items
- buyer_profiles table for buyer directory
- stored_documents table for S3 document storage
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'doc_gen_phase2'
down_revision = 'doc_gen_phase1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============== Audit Log Table ==============
    op.create_table(
        'document_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_set_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Action details
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('action_detail', sa.String(200), nullable=True),
        
        # Field changes
        sa.Column('field_changed', sa.String(100), nullable=True),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=True),
        
        # Context
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_set_id'], ['document_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_audit_doc_set_time', 'document_audit_logs', ['document_set_id', 'created_at'])
    op.create_index('ix_audit_user_time', 'document_audit_logs', ['user_id', 'created_at'])
    
    # ============== Templates Table ==============
    op.create_table(
        'document_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Metadata
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('use_count', sa.Integer, default=0),
        
        # Beneficiary defaults
        sa.Column('beneficiary_name', sa.String(500), nullable=True),
        sa.Column('beneficiary_address', sa.Text, nullable=True),
        sa.Column('beneficiary_country', sa.String(100), nullable=True),
        sa.Column('beneficiary_contact', sa.String(200), nullable=True),
        
        # Bank details
        sa.Column('bank_name', sa.String(300), nullable=True),
        sa.Column('bank_account', sa.String(100), nullable=True),
        sa.Column('bank_swift', sa.String(20), nullable=True),
        sa.Column('bank_address', sa.Text, nullable=True),
        
        # Shipment defaults
        sa.Column('default_port_of_loading', sa.String(200), nullable=True),
        sa.Column('default_incoterms', sa.String(10), nullable=True),
        sa.Column('default_country_of_origin', sa.String(100), nullable=True),
        
        # Document preferences
        sa.Column('preferred_document_types', postgresql.JSON, nullable=True),
        sa.Column('default_draft_tenor', sa.String(50), nullable=True),
        sa.Column('default_shipping_marks', sa.Text, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_template_company', 'document_templates', ['company_id'])
    
    # ============== Product Catalog Table ==============
    op.create_table(
        'product_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Product identification
        sa.Column('sku', sa.String(50), nullable=True),
        sa.Column('product_code', sa.String(50), nullable=True),
        sa.Column('name', sa.String(300), nullable=False),
        
        # Trade details
        sa.Column('hs_code', sa.String(20), nullable=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('short_description', sa.String(200), nullable=True),
        
        # Pricing
        sa.Column('default_unit_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('currency', sa.String(3), default='USD'),
        
        # Units
        sa.Column('default_unit', sa.String(20), default='PCS'),
        sa.Column('units_per_carton', sa.Integer, nullable=True),
        sa.Column('weight_per_unit_kg', sa.Numeric(10, 4), nullable=True),
        
        # Packing
        sa.Column('carton_dimensions', sa.String(100), nullable=True),
        sa.Column('carton_weight_kg', sa.Numeric(10, 4), nullable=True),
        sa.Column('cbm_per_carton', sa.Numeric(10, 6), nullable=True),
        
        # Origin
        sa.Column('country_of_origin', sa.String(100), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('use_count', sa.Integer, default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_product_company', 'product_catalog', ['company_id'])
    op.create_index('ix_product_hs_code', 'product_catalog', ['hs_code'])
    op.create_index('ix_product_name', 'product_catalog', ['name'])
    
    # ============== Buyer Profiles Table ==============
    op.create_table(
        'buyer_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Identification
        sa.Column('buyer_code', sa.String(50), nullable=True),
        sa.Column('company_name', sa.String(500), nullable=False),
        sa.Column('country', sa.String(100), nullable=True),
        
        # Address
        sa.Column('address_line1', sa.String(300), nullable=True),
        sa.Column('address_line2', sa.String(300), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        
        # Contact
        sa.Column('contact_person', sa.String(200), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('fax', sa.String(50), nullable=True),
        
        # Notify party
        sa.Column('notify_party_name', sa.String(500), nullable=True),
        sa.Column('notify_party_address', sa.Text, nullable=True),
        
        # Trade preferences
        sa.Column('preferred_incoterms', sa.String(10), nullable=True),
        sa.Column('preferred_port_of_discharge', sa.String(200), nullable=True),
        sa.Column('default_currency', sa.String(3), default='USD'),
        
        # Banking
        sa.Column('buyer_bank_name', sa.String(300), nullable=True),
        sa.Column('buyer_bank_swift', sa.String(20), nullable=True),
        
        # Notes
        sa.Column('notes', sa.Text, nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('use_count', sa.Integer, default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_buyer_company', 'buyer_profiles', ['company_id'])
    op.create_index('ix_buyer_name', 'buyer_profiles', ['company_name'])
    op.create_index('ix_buyer_country', 'buyer_profiles', ['country'])
    
    # ============== Stored Documents Table ==============
    op.create_table(
        'stored_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_set_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # S3 storage
        sa.Column('s3_bucket', sa.String(100), nullable=True),
        sa.Column('s3_key', sa.String(500), nullable=False),
        sa.Column('s3_region', sa.String(20), nullable=True),
        
        # File metadata
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('content_type', sa.String(100), default='application/pdf'),
        sa.Column('checksum', sa.String(64), nullable=True),
        
        # Version tracking
        sa.Column('version', sa.Integer, default=1),
        sa.Column('is_current', sa.Boolean, default=True),
        
        # Access
        sa.Column('download_count', sa.Integer, default=0),
        sa.Column('last_downloaded_at', sa.DateTime, nullable=True),
        
        # Expiry
        sa.Column('expires_at', sa.DateTime, nullable=True),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_set_id'], ['document_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_document_id'], ['generated_documents.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_stored_doc_set', 'stored_documents', ['document_set_id'])
    op.create_index('ix_stored_doc_type', 'stored_documents', ['document_type'])
    op.create_index('ix_stored_doc_s3_key', 'stored_documents', ['s3_key'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_stored_doc_s3_key', table_name='stored_documents')
    op.drop_index('ix_stored_doc_type', table_name='stored_documents')
    op.drop_index('ix_stored_doc_set', table_name='stored_documents')
    op.drop_index('ix_buyer_country', table_name='buyer_profiles')
    op.drop_index('ix_buyer_name', table_name='buyer_profiles')
    op.drop_index('ix_buyer_company', table_name='buyer_profiles')
    op.drop_index('ix_product_name', table_name='product_catalog')
    op.drop_index('ix_product_hs_code', table_name='product_catalog')
    op.drop_index('ix_product_company', table_name='product_catalog')
    op.drop_index('ix_template_company', table_name='document_templates')
    op.drop_index('ix_audit_user_time', table_name='document_audit_logs')
    op.drop_index('ix_audit_doc_set_time', table_name='document_audit_logs')
    
    # Drop tables
    op.drop_table('stored_documents')
    op.drop_table('buyer_profiles')
    op.drop_table('product_catalog')
    op.drop_table('document_templates')
    op.drop_table('document_audit_logs')

