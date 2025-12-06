"""Add HS Code Finder tables

Revision ID: hs_code_finder_001
Revises: e02d1cb
Create Date: 2025-12-06

Tables:
- hs_code_tariffs: Main HS code reference (18,000+ US HTS codes)
- duty_rates: MFN, preferential, special rates
- fta_agreements: USMCA, RCEP, CPTPP, etc.
- fta_rules: Product-specific rules of origin
- hs_classifications: User classification history
- hs_code_searches: Analytics
- binding_rulings: CBP CROSS rulings for AI context
- chapter_notes: GRI notes for classification
- section_301_rates: US-China additional tariffs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = 'hs_code_finder_001'
down_revision = 'lc_builder_001'  # Fixed: reference actual migration ID, not git commit
branch_labels = None
depends_on = None


def upgrade() -> None:
    # HS Code Tariffs - Main reference table
    op.create_table(
        'hs_code_tariffs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(15), nullable=False, index=True),
        sa.Column('code_2', sa.String(2)),
        sa.Column('code_4', sa.String(4)),
        sa.Column('code_6', sa.String(6)),
        sa.Column('code_8', sa.String(8)),
        sa.Column('code_10', sa.String(10)),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('chapter_description', sa.Text),
        sa.Column('heading_description', sa.Text),
        sa.Column('subheading_description', sa.Text),
        sa.Column('country_code', sa.String(2), nullable=False, default='US', index=True),
        sa.Column('schedule_type', sa.String(20), default='HTS'),
        sa.Column('unit_of_quantity', sa.String(50)),
        sa.Column('unit_of_quantity_2', sa.String(50)),
        sa.Column('general_notes', sa.Text),
        sa.Column('special_notes', sa.Text),
        sa.Column('requires_license', sa.Boolean, default=False),
        sa.Column('quota_applicable', sa.Boolean, default=False),
        sa.Column('keywords', JSONB, default=list),
        sa.Column('related_codes', JSONB, default=list),
        sa.Column('effective_date', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_hs_code_tariffs_code_country', 'hs_code_tariffs', ['code', 'country_code'])
    op.create_index('ix_hs_code_tariffs_code_6', 'hs_code_tariffs', ['code_6'])

    # Duty Rates
    op.create_table(
        'duty_rates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('hs_code_id', UUID(as_uuid=True), sa.ForeignKey('hs_code_tariffs.id'), nullable=False, index=True),
        sa.Column('rate_type', sa.String(20), nullable=False),
        sa.Column('rate_code', sa.String(20)),
        sa.Column('origin_country', sa.String(2)),
        sa.Column('ad_valorem_rate', sa.Float),
        sa.Column('specific_rate', sa.Float),
        sa.Column('specific_rate_unit', sa.String(20)),
        sa.Column('compound_rate', sa.String(100)),
        sa.Column('additional_duty', sa.Float, default=0),
        sa.Column('additional_duty_type', sa.String(50)),
        sa.Column('in_quota_rate', sa.Float),
        sa.Column('out_quota_rate', sa.Float),
        sa.Column('quota_quantity', sa.Float),
        sa.Column('quota_unit', sa.String(20)),
        sa.Column('effective_from', sa.DateTime),
        sa.Column('effective_to', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # FTA Agreements
    op.create_table(
        'fta_agreements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('full_name', sa.Text),
        sa.Column('member_countries', JSONB, default=list),
        sa.Column('certificate_types', JSONB, default=list),
        sa.Column('cumulation_type', sa.String(50)),
        sa.Column('de_minimis_threshold', sa.Float),
        sa.Column('effective_from', sa.DateTime),
        sa.Column('effective_to', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # FTA Rules
    op.create_table(
        'fta_rules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('fta_id', UUID(as_uuid=True), sa.ForeignKey('fta_agreements.id'), nullable=False),
        sa.Column('hs_code_prefix', sa.String(6), nullable=False, index=True),
        sa.Column('rule_type', sa.String(50)),
        sa.Column('rule_text', sa.Text),
        sa.Column('ctc_requirement', sa.String(50)),
        sa.Column('rvc_threshold', sa.Float),
        sa.Column('rvc_method', sa.String(50)),
        sa.Column('preferential_rate', sa.Float),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # HS Classifications (user history)
    op.create_table(
        'hs_classifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('product_description', sa.Text, nullable=False),
        sa.Column('product_name', sa.String(200)),
        sa.Column('hs_code', sa.String(15), nullable=False, index=True),
        sa.Column('hs_code_description', sa.Text),
        sa.Column('import_country', sa.String(2), nullable=False),
        sa.Column('export_country', sa.String(2)),
        sa.Column('source', sa.String(20), default='ai'),
        sa.Column('confidence_score', sa.Float),
        sa.Column('alternative_codes', JSONB, default=list),
        sa.Column('ai_reasoning', sa.Text),
        sa.Column('mfn_rate', sa.Float),
        sa.Column('preferential_rate', sa.Float),
        sa.Column('fta_applied', sa.String(50)),
        sa.Column('estimated_duty', sa.Float),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('product_value', sa.Float),
        sa.Column('quantity', sa.Float),
        sa.Column('quantity_unit', sa.String(20)),
        sa.Column('restrictions', JSONB, default=list),
        sa.Column('licenses_required', JSONB, default=list),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('verified_by', UUID(as_uuid=True)),
        sa.Column('verified_at', sa.DateTime),
        sa.Column('project_name', sa.String(200)),
        sa.Column('tags', JSONB, default=list),
        sa.Column('notes', sa.Text),
        sa.Column('is_shared', sa.Boolean, default=False),
        sa.Column('shared_with', JSONB, default=list),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_hs_classifications_user_created', 'hs_classifications', ['user_id', 'created_at'])

    # HS Code Searches (analytics)
    op.create_table(
        'hs_code_searches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('search_query', sa.Text, nullable=False),
        sa.Column('search_type', sa.String(20), default='description'),
        sa.Column('user_id', UUID(as_uuid=True)),
        sa.Column('results_count', sa.Integer, default=0),
        sa.Column('top_result_code', sa.String(15)),
        sa.Column('selected_code', sa.String(15)),
        sa.Column('import_country', sa.String(2)),
        sa.Column('export_country', sa.String(2)),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Binding Rulings (CBP CROSS)
    op.create_table(
        'binding_rulings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ruling_number', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('ruling_type', sa.String(20)),
        sa.Column('product_description', sa.Text, nullable=False),
        sa.Column('hs_code', sa.String(15), nullable=False, index=True),
        sa.Column('country', sa.String(2), default='US'),
        sa.Column('legal_reference', sa.Text),
        sa.Column('reasoning', sa.Text),
        sa.Column('keywords', JSONB, default=list),
        sa.Column('ruling_date', sa.DateTime),
        sa.Column('effective_date', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Chapter Notes (GRI)
    op.create_table(
        'chapter_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('chapter', sa.String(2), nullable=False, index=True),
        sa.Column('note_type', sa.String(20), nullable=False),
        sa.Column('note_number', sa.Integer),
        sa.Column('note_text', sa.Text, nullable=False),
        sa.Column('country_code', sa.String(2), default='US'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_chapter_notes_chapter', 'chapter_notes', ['chapter', 'country_code'])

    # Section 301 Rates
    op.create_table(
        'section_301_rates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('hs_code', sa.String(15), nullable=False, index=True),
        sa.Column('origin_country', sa.String(2), nullable=False, default='CN'),
        sa.Column('list_number', sa.String(10)),
        sa.Column('additional_rate', sa.Float, nullable=False),
        sa.Column('is_excluded', sa.Boolean, default=False),
        sa.Column('exclusion_number', sa.String(50)),
        sa.Column('exclusion_expiry', sa.DateTime),
        sa.Column('effective_from', sa.DateTime),
        sa.Column('effective_to', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_section_301_hs_origin', 'section_301_rates', ['hs_code', 'origin_country'])


def downgrade() -> None:
    op.drop_table('section_301_rates')
    op.drop_table('chapter_notes')
    op.drop_table('binding_rulings')
    op.drop_table('hs_code_searches')
    op.drop_table('hs_classifications')
    op.drop_table('fta_rules')
    op.drop_table('fta_agreements')
    op.drop_table('duty_rates')
    op.drop_table('hs_code_tariffs')

