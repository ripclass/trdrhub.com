"""Add LC Builder tables

Revision ID: lc_builder_001
Revises: doc_gen_new_types
Create Date: 2024-12-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'lc_builder_001'
down_revision = 'doc_gen_new_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    lc_type_enum = postgresql.ENUM(
        'documentary', 'standby', 'revolving', 'transferable',
        name='lc_type_enum', create_type=False
    )
    lc_status_enum = postgresql.ENUM(
        'draft', 'review', 'submitted', 'approved', 'rejected', 'amended',
        name='lc_status_enum', create_type=False
    )
    payment_terms_enum = postgresql.ENUM(
        'sight', 'usance', 'deferred', 'mixed',
        name='payment_terms_enum', create_type=False
    )
    confirmation_enum = postgresql.ENUM(
        'without', 'may_add', 'confirm',
        name='confirmation_instructions_enum', create_type=False
    )
    clause_category_enum = postgresql.ENUM(
        'shipment', 'documents', 'payment', 'special', 'amendments', 'red_green',
        name='clause_category_enum', create_type=False
    )
    risk_level_enum = postgresql.ENUM(
        'low', 'medium', 'high',
        name='risk_level_enum', create_type=False
    )
    bias_enum = postgresql.ENUM(
        'beneficiary', 'applicant', 'neutral',
        name='bias_indicator_enum', create_type=False
    )
    
    # Create enums in DB
    op.execute("CREATE TYPE lc_type_enum AS ENUM ('documentary', 'standby', 'revolving', 'transferable')")
    op.execute("CREATE TYPE lc_status_enum AS ENUM ('draft', 'review', 'submitted', 'approved', 'rejected', 'amended')")
    op.execute("CREATE TYPE payment_terms_enum AS ENUM ('sight', 'usance', 'deferred', 'mixed')")
    op.execute("CREATE TYPE confirmation_instructions_enum AS ENUM ('without', 'may_add', 'confirm')")
    op.execute("CREATE TYPE clause_category_enum AS ENUM ('shipment', 'documents', 'payment', 'special', 'amendments', 'red_green')")
    op.execute("CREATE TYPE risk_level_enum AS ENUM ('low', 'medium', 'high')")
    op.execute("CREATE TYPE bias_indicator_enum AS ENUM ('beneficiary', 'applicant', 'neutral')")
    
    # Create lc_templates table first (referenced by lc_applications)
    op.create_table(
        'lc_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('trade_route', sa.String(100)),
        sa.Column('industry', sa.String(100)),
        sa.Column('template_data', postgresql.JSONB, nullable=False),
        sa.Column('default_clause_ids', postgresql.JSONB, default=[]),
        sa.Column('default_documents', postgresql.JSONB, default=[]),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create lc_applications table
    op.create_table(
        'lc_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('reference_number', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200)),
        sa.Column('lc_type', lc_type_enum, default='documentary'),
        sa.Column('status', lc_status_enum, default='draft'),
        
        # Amount
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('tolerance_plus', sa.Float, default=0),
        sa.Column('tolerance_minus', sa.Float, default=0),
        
        # Applicant
        sa.Column('applicant_name', sa.String(200), nullable=False),
        sa.Column('applicant_address', sa.Text),
        sa.Column('applicant_country', sa.String(100)),
        sa.Column('applicant_contact', sa.String(200)),
        
        # Beneficiary
        sa.Column('beneficiary_name', sa.String(200), nullable=False),
        sa.Column('beneficiary_address', sa.Text),
        sa.Column('beneficiary_country', sa.String(100)),
        sa.Column('beneficiary_contact', sa.String(200)),
        
        # Banks
        sa.Column('issuing_bank_name', sa.String(200)),
        sa.Column('issuing_bank_swift', sa.String(11)),
        sa.Column('advising_bank_name', sa.String(200)),
        sa.Column('advising_bank_swift', sa.String(11)),
        sa.Column('confirming_bank_name', sa.String(200)),
        sa.Column('confirming_bank_swift', sa.String(11)),
        
        # Shipment
        sa.Column('port_of_loading', sa.String(200)),
        sa.Column('port_of_discharge', sa.String(200)),
        sa.Column('place_of_delivery', sa.String(200)),
        sa.Column('latest_shipment_date', sa.DateTime),
        sa.Column('incoterms', sa.String(10)),
        sa.Column('incoterms_place', sa.String(200)),
        sa.Column('partial_shipments', sa.Boolean, default=True),
        sa.Column('transhipment', sa.Boolean, default=True),
        
        # Goods
        sa.Column('goods_description', sa.Text, nullable=False),
        sa.Column('hs_code', sa.String(20)),
        sa.Column('quantity', sa.String(100)),
        sa.Column('unit_price', sa.String(100)),
        
        # Payment
        sa.Column('payment_terms', payment_terms_enum, default='sight'),
        sa.Column('usance_days', sa.Integer),
        sa.Column('usance_from', sa.String(50)),
        
        # Validity
        sa.Column('expiry_date', sa.DateTime, nullable=False),
        sa.Column('expiry_place', sa.String(200)),
        sa.Column('presentation_period', sa.Integer, default=21),
        sa.Column('confirmation_instructions', confirmation_enum, default='without'),
        
        # Documents & Conditions
        sa.Column('documents_required', postgresql.JSONB, default=[]),
        sa.Column('additional_conditions', postgresql.JSONB, default=[]),
        sa.Column('selected_clause_ids', postgresql.JSONB, default=[]),
        
        # Validation
        sa.Column('validation_issues', postgresql.JSONB, default=[]),
        sa.Column('risk_score', sa.Float),
        sa.Column('risk_details', postgresql.JSONB),
        
        # Template
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lc_templates.id')),
        
        # Metadata
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('submitted_at', sa.DateTime),
    )
    
    # Create lc_document_requirements table
    op.create_table(
        'lc_document_requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lc_application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lc_applications.id'), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('copies_original', sa.Integer, default=1),
        sa.Column('copies_copy', sa.Integer, default=0),
        sa.Column('specific_requirements', sa.Text),
        sa.Column('is_required', sa.Boolean, default=True),
    )
    
    # Create lc_application_versions table
    op.create_table(
        'lc_application_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lc_application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lc_applications.id'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('snapshot', postgresql.JSONB, nullable=False),
        sa.Column('change_summary', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
    )
    
    # Create lc_clauses table
    op.create_table(
        'lc_clauses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('category', clause_category_enum, nullable=False),
        sa.Column('subcategory', sa.String(100)),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('clause_text', sa.Text, nullable=False),
        sa.Column('plain_english', sa.Text),
        sa.Column('risk_level', risk_level_enum, default='medium'),
        sa.Column('bias', bias_enum, default='neutral'),
        sa.Column('risk_notes', sa.Text),
        sa.Column('bank_acceptance', sa.Float, default=0.95),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('tags', postgresql.JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create applicant profiles table
    op.create_table(
        'lc_applicant_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.Text),
        sa.Column('country', sa.String(100)),
        sa.Column('contact_name', sa.String(200)),
        sa.Column('contact_email', sa.String(200)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('bank_name', sa.String(200)),
        sa.Column('bank_swift', sa.String(11)),
        sa.Column('bank_account', sa.String(50)),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create beneficiary profiles table
    op.create_table(
        'lc_beneficiary_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.Text),
        sa.Column('country', sa.String(100)),
        sa.Column('contact_name', sa.String(200)),
        sa.Column('contact_email', sa.String(200)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('bank_name', sa.String(200)),
        sa.Column('bank_swift', sa.String(11)),
        sa.Column('bank_account', sa.String(50)),
        sa.Column('trade_history_count', sa.Integer, default=0),
        sa.Column('first_trade_date', sa.DateTime),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_lc_applications_reference', 'lc_applications', ['reference_number'])
    op.create_index('ix_lc_applications_status', 'lc_applications', ['status'])
    op.create_index('ix_lc_clauses_code', 'lc_clauses', ['code'])
    op.create_index('ix_lc_clauses_category', 'lc_clauses', ['category'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_lc_clauses_category')
    op.drop_index('ix_lc_clauses_code')
    op.drop_index('ix_lc_applications_status')
    op.drop_index('ix_lc_applications_reference')
    
    # Drop tables
    op.drop_table('lc_beneficiary_profiles')
    op.drop_table('lc_applicant_profiles')
    op.drop_table('lc_clauses')
    op.drop_table('lc_application_versions')
    op.drop_table('lc_document_requirements')
    op.drop_table('lc_applications')
    op.drop_table('lc_templates')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS bias_indicator_enum")
    op.execute("DROP TYPE IF EXISTS risk_level_enum")
    op.execute("DROP TYPE IF EXISTS clause_category_enum")
    op.execute("DROP TYPE IF EXISTS confirmation_instructions_enum")
    op.execute("DROP TYPE IF EXISTS payment_terms_enum")
    op.execute("DROP TYPE IF EXISTS lc_status_enum")
    op.execute("DROP TYPE IF EXISTS lc_type_enum")

