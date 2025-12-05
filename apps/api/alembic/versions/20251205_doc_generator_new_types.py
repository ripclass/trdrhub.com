"""Add new document types and company fields to doc generator

Revision ID: 20251205_doc_gen_new_types
Revises: 20251205_add_doc_generator_phase2
Create Date: 2024-12-05

Adds:
- New document types: bill_of_lading_draft, inspection_certificate, quality_certificate,
  health_certificate, fumigation_certificate, insurance_certificate
- Company/signatory fields to document_sets
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = 'doc_gen_new_types'
down_revision = 'doc_gen_phase2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new document types to the enum
    # PostgreSQL requires special handling for adding enum values
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'bill_of_lading_draft'")
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'inspection_certificate'")
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'quality_certificate'")
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'health_certificate'")
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'fumigation_certificate'")
    op.execute("ALTER TYPE doc_gen_document_type ADD VALUE IF NOT EXISTS 'insurance_certificate'")
    
    # Add company/signatory fields to document_sets
    op.add_column('document_sets', sa.Column('company_logo_url', sa.String(500), nullable=True))
    op.add_column('document_sets', sa.Column('company_signatory_name', sa.String(200), nullable=True))
    op.add_column('document_sets', sa.Column('company_signatory_title', sa.String(200), nullable=True))
    op.add_column('document_sets', sa.Column('company_contact_email', sa.String(200), nullable=True))
    op.add_column('document_sets', sa.Column('company_contact_phone', sa.String(100), nullable=True))
    op.add_column('document_sets', sa.Column('company_stamp_url', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove new columns
    op.drop_column('document_sets', 'company_stamp_url')
    op.drop_column('document_sets', 'company_contact_phone')
    op.drop_column('document_sets', 'company_contact_email')
    op.drop_column('document_sets', 'company_signatory_title')
    op.drop_column('document_sets', 'company_signatory_name')
    op.drop_column('document_sets', 'company_logo_url')
    
    # Note: PostgreSQL doesn't support removing values from enums easily
    # Would need to recreate the type, which is complex

