"""Add Doc Generator Phase 1 - Branding and Validation

Revision ID: doc_gen_phase1
Revises: 
Create Date: 2024-12-05

Adds:
- company_brandings table for company logos and letterheads
- validation fields to document_sets
- lcopilot integration fields
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'doc_gen_phase1'
down_revision = None  # Will be set by Alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create company_brandings table
    op.create_table(
        'company_brandings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Logo & Letterhead
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('logo_width', sa.Integer, default=150),
        sa.Column('letterhead_url', sa.String(500), nullable=True),
        
        # Company Info
        sa.Column('company_name', sa.String(500), nullable=True),
        sa.Column('company_address', sa.Text, nullable=True),
        sa.Column('company_phone', sa.String(100), nullable=True),
        sa.Column('company_email', sa.String(200), nullable=True),
        sa.Column('company_website', sa.String(200), nullable=True),
        
        # Registration Details
        sa.Column('tax_id', sa.String(100), nullable=True),
        sa.Column('registration_number', sa.String(100), nullable=True),
        sa.Column('export_license', sa.String(100), nullable=True),
        
        # Bank Details
        sa.Column('bank_name', sa.String(300), nullable=True),
        sa.Column('bank_account', sa.String(100), nullable=True),
        sa.Column('bank_swift', sa.String(20), nullable=True),
        sa.Column('bank_address', sa.Text, nullable=True),
        
        # Styling
        sa.Column('primary_color', sa.String(10), default='#1e40af'),
        sa.Column('secondary_color', sa.String(10), default='#64748b'),
        
        # Signature/Stamp
        sa.Column('signature_url', sa.String(500), nullable=True),
        sa.Column('stamp_url', sa.String(500), nullable=True),
        sa.Column('signatory_name', sa.String(200), nullable=True),
        sa.Column('signatory_title', sa.String(200), nullable=True),
        
        # Footer
        sa.Column('footer_text', sa.Text, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('company_id', name='uq_company_brandings_company_id'),
    )
    
    # Add LCopilot integration fields to document_sets
    op.add_column('document_sets', sa.Column('lcopilot_session_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('document_sets', sa.Column('imported_from_lcopilot', sa.Boolean, default=False))
    
    # Add validation fields to document_sets
    op.add_column('document_sets', sa.Column('validation_status', sa.String(20), default='not_validated'))
    op.add_column('document_sets', sa.Column('validation_errors', postgresql.JSON, nullable=True))
    op.add_column('document_sets', sa.Column('validation_warnings', postgresql.JSON, nullable=True))
    op.add_column('document_sets', sa.Column('last_validated_at', sa.DateTime, nullable=True))
    
    # Create indexes
    op.create_index('ix_company_brandings_company_id', 'company_brandings', ['company_id'])
    op.create_index('ix_document_sets_lcopilot_session', 'document_sets', ['lcopilot_session_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_document_sets_lcopilot_session', table_name='document_sets')
    op.drop_index('ix_company_brandings_company_id', table_name='company_brandings')
    
    # Remove columns from document_sets
    op.drop_column('document_sets', 'last_validated_at')
    op.drop_column('document_sets', 'validation_warnings')
    op.drop_column('document_sets', 'validation_errors')
    op.drop_column('document_sets', 'validation_status')
    op.drop_column('document_sets', 'imported_from_lcopilot')
    op.drop_column('document_sets', 'lcopilot_session_id')
    
    # Drop company_brandings table
    op.drop_table('company_brandings')

