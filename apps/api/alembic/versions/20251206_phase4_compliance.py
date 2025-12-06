"""phase4_compliance_suite

Revision ID: hs_code_finder_004
Revises: hs_code_finder_003
Create Date: 2025-12-06 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hs_code_finder_004'
down_revision = 'phase3_roo_teams_001'
branch_labels = None
depends_on = None


def upgrade():
    # Export Control Items (EAR/ECCN)
    op.create_table('export_control_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('eccn', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=5), nullable=True),
        sa.Column('product_group', sa.String(length=5), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('technical_description', sa.Text(), nullable=True),
        sa.Column('control_reasons', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('license_requirements', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('license_exceptions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('hs_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('related_definitions', sa.Text(), nullable=True),
        sa.Column('itar_category', sa.String(length=50), nullable=True),
        sa.Column('is_itar', sa.Boolean(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_control_items_eccn'), 'export_control_items', ['eccn'], unique=False, if_not_exists=True)
    op.create_index('ix_eccn_category', 'export_control_items', ['category', 'product_group'], unique=False, if_not_exists=True)
    
    # ITAR Items (USML)
    op.create_table('itar_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('usml_category', sa.String(length=10), nullable=False),
        sa.Column('subcategory', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('technical_notes', sa.Text(), nullable=True),
        sa.Column('significant_military_equipment', sa.Boolean(), nullable=True),
        sa.Column('missile_technology', sa.Boolean(), nullable=True),
        sa.Column('hs_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('license_required', sa.Boolean(), nullable=True),
        sa.Column('exemptions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_itar_items_usml_category'), 'itar_items', ['usml_category'], unique=False, if_not_exists=True)
    op.create_index('ix_usml_category', 'itar_items', ['usml_category'], unique=False, if_not_exists=True)
    
    # Section 301 Exclusions
    op.create_table('section_301_exclusions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exclusion_number', sa.String(length=50), nullable=False),
        sa.Column('list_number', sa.String(length=10), nullable=False),
        sa.Column('hs_code', sa.String(length=15), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('product_scope', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_to', sa.DateTime(), nullable=False),
        sa.Column('original_expiry', sa.DateTime(), nullable=True),
        sa.Column('extensions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fr_citation', sa.String(length=100), nullable=True),
        sa.Column('fr_date', sa.DateTime(), nullable=True),
        sa.Column('requestor_type', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exclusion_number')
    )
    op.create_index(op.f('ix_section_301_exclusions_exclusion_number'), 'section_301_exclusions', ['exclusion_number'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_section_301_exclusions_hs_code'), 'section_301_exclusions', ['hs_code'], unique=False, if_not_exists=True)
    op.create_index('ix_301_excl_hs_list', 'section_301_exclusions', ['hs_code', 'list_number'], unique=False, if_not_exists=True)
    
    # AD/CVD Orders
    op.create_table('ad_cvd_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_number', sa.String(length=50), nullable=False),
        sa.Column('order_type', sa.String(length=10), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('country_name', sa.String(length=100), nullable=True),
        sa.Column('hs_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('scope_description', sa.Text(), nullable=True),
        sa.Column('all_others_rate', sa.Float(), nullable=True),
        sa.Column('company_rates', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('current_deposit_rate', sa.Float(), nullable=True),
        sa.Column('deposit_effective_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('order_date', sa.DateTime(), nullable=True),
        sa.Column('revocation_date', sa.DateTime(), nullable=True),
        sa.Column('last_review_period', sa.String(length=50), nullable=True),
        sa.Column('next_review_due', sa.DateTime(), nullable=True),
        sa.Column('sunset_review_due', sa.DateTime(), nullable=True),
        sa.Column('order_fr_citation', sa.String(length=100), nullable=True),
        sa.Column('latest_rate_fr', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number')
    )
    op.create_index(op.f('ix_ad_cvd_orders_case_number'), 'ad_cvd_orders', ['case_number'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_ad_cvd_orders_country'), 'ad_cvd_orders', ['country'], unique=False, if_not_exists=True)
    op.create_index('ix_adcvd_country_type', 'ad_cvd_orders', ['country', 'order_type'], unique=False, if_not_exists=True)
    
    # Tariff Quotas
    op.create_table('tariff_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quota_number', sa.String(length=50), nullable=False),
        sa.Column('quota_name', sa.String(length=200), nullable=False),
        sa.Column('hs_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('product_description', sa.Text(), nullable=True),
        sa.Column('applicable_countries', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fta_code', sa.String(length=20), nullable=True),
        sa.Column('quota_quantity', sa.Float(), nullable=False),
        sa.Column('quota_unit', sa.String(length=20), nullable=True),
        sa.Column('quota_period', sa.String(length=20), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('quantity_used', sa.Float(), nullable=True),
        sa.Column('fill_rate_percent', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('in_quota_rate', sa.Float(), nullable=True),
        sa.Column('over_quota_rate', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('alert_threshold_percent', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tariff_quotas_quota_number'), 'tariff_quotas', ['quota_number'], unique=False, if_not_exists=True)
    op.create_index('ix_quota_hs', 'tariff_quotas', ['quota_number'], unique=False, if_not_exists=True)
    
    # Compliance Screenings (user history)
    op.create_table('compliance_screenings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('hs_code', sa.String(length=15), nullable=True),
        sa.Column('export_country', sa.String(length=2), nullable=True),
        sa.Column('import_country', sa.String(length=2), nullable=True),
        sa.Column('end_use', sa.String(length=200), nullable=True),
        sa.Column('end_user', sa.String(length=200), nullable=True),
        sa.Column('export_control_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('itar_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sanctions_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ad_cvd_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('section_301_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('quota_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('overall_risk', sa.String(length=20), nullable=True),
        sa.Column('flags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_screenings_user_id'), 'compliance_screenings', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_screening_user', 'compliance_screenings', ['user_id', 'created_at'], unique=False, if_not_exists=True)


def downgrade():
    op.drop_index('ix_screening_user', table_name='compliance_screenings')
    op.drop_index(op.f('ix_compliance_screenings_user_id'), table_name='compliance_screenings')
    op.drop_table('compliance_screenings')
    
    op.drop_index('ix_quota_hs', table_name='tariff_quotas')
    op.drop_index(op.f('ix_tariff_quotas_quota_number'), table_name='tariff_quotas')
    op.drop_table('tariff_quotas')
    
    op.drop_index('ix_adcvd_country_type', table_name='ad_cvd_orders')
    op.drop_index(op.f('ix_ad_cvd_orders_country'), table_name='ad_cvd_orders')
    op.drop_index(op.f('ix_ad_cvd_orders_case_number'), table_name='ad_cvd_orders')
    op.drop_table('ad_cvd_orders')
    
    op.drop_index('ix_301_excl_hs_list', table_name='section_301_exclusions')
    op.drop_index(op.f('ix_section_301_exclusions_hs_code'), table_name='section_301_exclusions')
    op.drop_index(op.f('ix_section_301_exclusions_exclusion_number'), table_name='section_301_exclusions')
    op.drop_table('section_301_exclusions')
    
    op.drop_index('ix_usml_category', table_name='itar_items')
    op.drop_index(op.f('ix_itar_items_usml_category'), table_name='itar_items')
    op.drop_table('itar_items')
    
    op.drop_index('ix_eccn_category', table_name='export_control_items')
    op.drop_index(op.f('ix_export_control_items_eccn'), table_name='export_control_items')
    op.drop_table('export_control_items')

