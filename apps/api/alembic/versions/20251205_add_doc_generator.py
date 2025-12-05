"""Add doc generator tables

Revision ID: 20251205_doc_gen
Revises: 20251205_add_tracking_tables
Create Date: 2024-12-05

Creates tables for shipping document generation:
- document_sets: Master record for a set of shipping documents
- document_line_items: Line items (goods) for each document set
- generated_documents: PDF outputs from generation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = '20251205_doc_gen'
down_revision = '20251205_add_tracking_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Document status enum
    op.execute("CREATE TYPE document_status AS ENUM ('draft', 'generated', 'finalized', 'archived')")
    
    # Document type enum
    op.execute("""
        CREATE TYPE doc_gen_document_type AS ENUM (
            'commercial_invoice', 'packing_list', 'beneficiary_certificate',
            'bill_of_exchange', 'certificate_of_origin', 'shipping_instructions',
            'weight_certificate', 'insurance_declaration'
        )
    """)
    
    # Document sets table
    op.create_table(
        'document_sets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=True),
        
        # Metadata
        sa.Column('name', sa.String(200)),
        sa.Column('status', sa.Enum('draft', 'generated', 'finalized', 'archived', name='document_status'), default='draft'),
        
        # LC Reference
        sa.Column('lc_number', sa.String(100)),
        sa.Column('lc_date', sa.Date),
        sa.Column('lc_amount', sa.Numeric(15, 2)),
        sa.Column('lc_currency', sa.String(3), default='USD'),
        sa.Column('issuing_bank', sa.String(300)),
        sa.Column('advising_bank', sa.String(300)),
        
        # Beneficiary
        sa.Column('beneficiary_name', sa.String(500), nullable=False),
        sa.Column('beneficiary_address', sa.Text),
        sa.Column('beneficiary_country', sa.String(100)),
        sa.Column('beneficiary_contact', sa.String(200)),
        
        # Applicant
        sa.Column('applicant_name', sa.String(500), nullable=False),
        sa.Column('applicant_address', sa.Text),
        sa.Column('applicant_country', sa.String(100)),
        
        # Notify Party
        sa.Column('notify_party_name', sa.String(500)),
        sa.Column('notify_party_address', sa.Text),
        
        # Shipment
        sa.Column('vessel_name', sa.String(200)),
        sa.Column('voyage_number', sa.String(50)),
        sa.Column('bl_number', sa.String(100)),
        sa.Column('bl_date', sa.Date),
        sa.Column('container_number', sa.String(50)),
        sa.Column('seal_number', sa.String(50)),
        sa.Column('port_of_loading', sa.String(200)),
        sa.Column('port_of_loading_code', sa.String(10)),
        sa.Column('port_of_discharge', sa.String(200)),
        sa.Column('port_of_discharge_code', sa.String(10)),
        sa.Column('final_destination', sa.String(200)),
        
        # Trade Terms
        sa.Column('incoterms', sa.String(10)),
        sa.Column('incoterms_place', sa.String(200)),
        
        # Packing
        sa.Column('total_cartons', sa.Integer),
        sa.Column('gross_weight_kg', sa.Numeric(12, 3)),
        sa.Column('net_weight_kg', sa.Numeric(12, 3)),
        sa.Column('cbm', sa.Numeric(10, 3)),
        sa.Column('shipping_marks', sa.Text),
        
        # Document Numbers
        sa.Column('invoice_number', sa.String(100)),
        sa.Column('invoice_date', sa.Date),
        sa.Column('proforma_number', sa.String(100)),
        sa.Column('proforma_date', sa.Date),
        sa.Column('po_number', sa.String(100)),
        
        # Additional
        sa.Column('country_of_origin', sa.String(100)),
        sa.Column('remarks', sa.Text),
        
        # Bill of Exchange
        sa.Column('draft_tenor', sa.String(50)),
        sa.Column('drawee_name', sa.String(500)),
        sa.Column('drawee_address', sa.Text),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_document_sets_user_id', 'document_sets', ['user_id'])
    op.create_index('ix_document_sets_company_id', 'document_sets', ['company_id'])
    op.create_index('ix_document_sets_lc_number', 'document_sets', ['lc_number'])
    op.create_index('ix_document_sets_status', 'document_sets', ['status'])
    
    # Document line items table
    op.create_table(
        'document_line_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_set_id', UUID(as_uuid=True), sa.ForeignKey('document_sets.id', ondelete='CASCADE'), nullable=False),
        
        # Item Details
        sa.Column('line_number', sa.Integer, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('hs_code', sa.String(20)),
        
        # Quantity & Price
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit', sa.String(20), default='PCS'),
        sa.Column('unit_price', sa.Numeric(12, 4)),
        sa.Column('total_price', sa.Numeric(15, 2)),
        
        # Packing
        sa.Column('cartons', sa.Integer),
        sa.Column('carton_dimensions', sa.String(100)),
        sa.Column('gross_weight_kg', sa.Numeric(12, 3)),
        sa.Column('net_weight_kg', sa.Numeric(12, 3)),
        
        # Additional
        sa.Column('remarks', sa.Text),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_index('ix_document_line_items_document_set_id', 'document_line_items', ['document_set_id'])
    
    # Generated documents table
    op.create_table(
        'generated_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_set_id', UUID(as_uuid=True), sa.ForeignKey('document_sets.id', ondelete='CASCADE'), nullable=False),
        
        # Document Info
        sa.Column('document_type', sa.Enum(
            'commercial_invoice', 'packing_list', 'beneficiary_certificate',
            'bill_of_exchange', 'certificate_of_origin', 'shipping_instructions',
            'weight_certificate', 'insurance_declaration',
            name='doc_gen_document_type'
        ), nullable=False),
        sa.Column('file_name', sa.String(300)),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.Integer),
        
        # Version Control
        sa.Column('version', sa.Integer, default=1),
        sa.Column('is_current', sa.Boolean, default=True),
        
        # Generation Metadata
        sa.Column('generated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('generated_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        
        # Validation
        sa.Column('validation_passed', sa.Boolean),
        sa.Column('validation_errors', sa.JSON),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('ix_generated_documents_document_set_id', 'generated_documents', ['document_set_id'])
    op.create_index('ix_generated_documents_document_type', 'generated_documents', ['document_type'])


def downgrade() -> None:
    op.drop_table('generated_documents')
    op.drop_table('document_line_items')
    op.drop_table('document_sets')
    
    op.execute("DROP TYPE IF EXISTS doc_gen_document_type")
    op.execute("DROP TYPE IF EXISTS document_status")

