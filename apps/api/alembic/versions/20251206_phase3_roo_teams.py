"""Add Phase 3 tables: ROO engines, team collaboration

Revision ID: phase3_roo_teams_001
Revises: rate_alerts_001
Create Date: 2025-12-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase3_roo_teams_001'
down_revision = 'rate_alerts_001'
branch_labels = None
depends_on = None


def upgrade():
    # Product Specific Rules (PSR) for USMCA/RCEP
    op.create_table(
        'product_specific_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fta_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hs_code_from', sa.String(10), nullable=False),
        sa.Column('hs_code_to', sa.String(10), nullable=True),
        sa.Column('chapter', sa.String(2), nullable=True),
        sa.Column('rule_type', sa.String(20), nullable=False),
        sa.Column('ctc_type', sa.String(10), nullable=True),
        sa.Column('ctc_exceptions', sa.Text(), nullable=True),
        sa.Column('rvc_required', sa.Boolean(), server_default='false'),
        sa.Column('rvc_threshold', sa.Float(), nullable=True),
        sa.Column('rvc_method', sa.String(30), nullable=True),
        sa.Column('rvc_alternative_threshold', sa.Float(), nullable=True),
        sa.Column('lvc_required', sa.Boolean(), server_default='false'),
        sa.Column('lvc_threshold', sa.Float(), nullable=True),
        sa.Column('steel_aluminum_required', sa.Boolean(), server_default='false'),
        sa.Column('steel_requirement', sa.Float(), nullable=True),
        sa.Column('process_requirements', sa.Text(), nullable=True),
        sa.Column('rule_text', sa.Text(), nullable=False),
        sa.Column('rule_notes', sa.Text(), nullable=True),
        sa.Column('annex_reference', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['fta_id'], ['fta_agreements.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_psr_fta_hs', 'product_specific_rules', ['fta_id', 'hs_code_from'], if_not_exists=True)
    op.create_index('ix_psr_hs_code_from', 'product_specific_rules', ['hs_code_from'], if_not_exists=True)

    # RVC Calculations
    op.create_table(
        'rvc_calculations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('hs_code', sa.String(15), nullable=False),
        sa.Column('fta_code', sa.String(20), nullable=False),
        sa.Column('transaction_value', sa.Float(), nullable=True),
        sa.Column('adjusted_value', sa.Float(), nullable=True),
        sa.Column('vom_value', sa.Float(), nullable=True),
        sa.Column('vom_breakdown', sa.JSON(), nullable=True),
        sa.Column('vdm_value', sa.Float(), nullable=True),
        sa.Column('vdm_breakdown', sa.JSON(), nullable=True),
        sa.Column('direct_labor_cost', sa.Float(), nullable=True),
        sa.Column('direct_overhead', sa.Float(), nullable=True),
        sa.Column('profit', sa.Float(), nullable=True),
        sa.Column('other_costs', sa.Float(), nullable=True),
        sa.Column('net_cost', sa.Float(), nullable=True),
        sa.Column('excluded_costs', sa.JSON(), nullable=True),
        sa.Column('rvc_percent', sa.Float(), nullable=True),
        sa.Column('method_used', sa.String(30), nullable=True),
        sa.Column('threshold_required', sa.Float(), nullable=True),
        sa.Column('meets_requirement', sa.Boolean(), nullable=True),
        sa.Column('lvc_percent', sa.Float(), nullable=True),
        sa.Column('lvc_meets_requirement', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('supporting_docs', sa.JSON(), nullable=True),
        sa.Column('project_name', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rvc_calc_user', 'rvc_calculations', ['user_id', 'created_at'], if_not_exists=True)

    # Origin Determinations
    op.create_table(
        'origin_determinations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=True),
        sa.Column('hs_code', sa.String(15), nullable=False),
        sa.Column('fta_code', sa.String(20), nullable=False),
        sa.Column('export_country', sa.String(2), nullable=False),
        sa.Column('import_country', sa.String(2), nullable=False),
        sa.Column('rule_applied', sa.String(50), nullable=True),
        sa.Column('psr_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rvc_calculation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_originating', sa.Boolean(), nullable=True),
        sa.Column('determination_reason', sa.Text(), nullable=True),
        sa.Column('certificate_type', sa.String(50), nullable=True),
        sa.Column('certificate_number', sa.String(100), nullable=True),
        sa.Column('certificate_date', sa.DateTime(), nullable=True),
        sa.Column('blanket_period_from', sa.DateTime(), nullable=True),
        sa.Column('blanket_period_to', sa.DateTime(), nullable=True),
        sa.Column('producer_name', sa.String(200), nullable=True),
        sa.Column('producer_address', sa.Text(), nullable=True),
        sa.Column('exporter_name', sa.String(200), nullable=True),
        sa.Column('exporter_address', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('supporting_documents', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_shared', sa.Boolean(), server_default='false'),
        sa.Column('shared_with', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['psr_id'], ['product_specific_rules.id'], ),
        sa.ForeignKeyConstraint(['rvc_calculation_id'], ['rvc_calculations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_origin_det_user', 'origin_determinations', ['user_id', 'fta_code'], if_not_exists=True)

    # Teams
    op.create_table(
        'hs_code_teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('default_import_country', sa.String(2), server_default='US'),
        sa.Column('default_ftas', sa.JSON(), nullable=True),
        sa.Column('plan', sa.String(20), server_default='free'),
        sa.Column('max_members', sa.Integer(), server_default='3'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_teams_owner', 'hs_code_teams', ['owner_id'], if_not_exists=True)

    # Team Members
    op.create_table(
        'hs_code_team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('can_classify', sa.Boolean(), server_default='true'),
        sa.Column('can_edit', sa.Boolean(), server_default='false'),
        sa.Column('can_delete', sa.Boolean(), server_default='false'),
        sa.Column('can_share', sa.Boolean(), server_default='false'),
        sa.Column('can_export', sa.Boolean(), server_default='true'),
        sa.Column('can_invite', sa.Boolean(), server_default='false'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['hs_code_teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_team_members_team', 'hs_code_team_members', ['team_id', 'user_id'], if_not_exists=True)

    # Projects
    op.create_table(
        'hs_code_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_import_country', sa.String(2), nullable=True),
        sa.Column('default_export_country', sa.String(2), nullable=True),
        sa.Column('target_fta', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('classification_count', sa.Integer(), server_default='0'),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['hs_code_teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_projects_team', 'hs_code_projects', ['team_id'], if_not_exists=True)

    # Classification Shares
    op.create_table(
        'classification_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('classification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_user', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shared_with_team', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shared_with_email', sa.String(200), nullable=True),
        sa.Column('can_view', sa.Boolean(), server_default='true'),
        sa.Column('can_edit', sa.Boolean(), server_default='false'),
        sa.Column('can_comment', sa.Boolean(), server_default='true'),
        sa.Column('share_link', sa.String(100), unique=True, nullable=True),
        sa.Column('requires_auth', sa.Boolean(), server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('view_count', sa.Integer(), server_default='0'),
        sa.Column('last_viewed', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['classification_id'], ['hs_classifications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_shares_classification', 'classification_shares', ['classification_id'], if_not_exists=True)
    op.create_index('ix_shares_link', 'classification_shares', ['share_link'], if_not_exists=True)


def downgrade():
    op.drop_table('classification_shares')
    op.drop_table('hs_code_projects')
    op.drop_table('hs_code_team_members')
    op.drop_table('hs_code_teams')
    op.drop_table('origin_determinations')
    op.drop_table('rvc_calculations')
    op.drop_table('product_specific_rules')

