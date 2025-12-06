"""sanctions_tables

Revision ID: sanctions_001
Revises: hs_code_finder_004
Create Date: 2025-12-06 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'sanctions_001'
down_revision = 'hs_code_finder_004'
branch_labels = None
depends_on = None


def upgrade():
    # Sanctions Lists
    op.create_table('sanctions_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('jurisdiction', sa.String(length=10), nullable=True),
        sa.Column('list_type', sa.String(length=20), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=True),
        sa.Column('last_synced', sa.DateTime(), nullable=True),
        sa.Column('last_modified', sa.DateTime(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('entry_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_sanctions_lists_code'), 'sanctions_lists', ['code'], unique=False, if_not_exists=True)
    
    # Sanctioned Entities
    op.create_table('sanctioned_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('list_code', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('entity_type', sa.String(length=20), nullable=True),
        sa.Column('primary_name', sa.Text(), nullable=False),
        sa.Column('name_normalized', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('aliases_normalized', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('identifiers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('programs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sanctions_programs', sa.Text(), nullable=True),
        sa.Column('listed_date', sa.DateTime(), nullable=True),
        sa.Column('delisted_date', sa.DateTime(), nullable=True),
        sa.Column('nationality', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('vessel_type', sa.String(length=50), nullable=True),
        sa.Column('vessel_flag', sa.String(length=50), nullable=True),
        sa.Column('vessel_imo', sa.String(length=20), nullable=True),
        sa.Column('vessel_mmsi', sa.String(length=20), nullable=True),
        sa.Column('vessel_tonnage', sa.String(length=50), nullable=True),
        sa.Column('vessel_owner', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['list_id'], ['sanctions_lists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sanctioned_entities_source_id'), 'sanctioned_entities', ['source_id'], unique=False, if_not_exists=True)
    op.create_index('ix_sanctioned_entities_list_name', 'sanctioned_entities', ['list_code', 'name_normalized'], unique=False, if_not_exists=True)
    op.create_index('ix_sanctioned_entities_type', 'sanctioned_entities', ['entity_type'], unique=False, if_not_exists=True)
    
    # Screening Sessions
    op.create_table('screening_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_type', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('total_screenings', sa.Integer(), nullable=True),
        sa.Column('clear_count', sa.Integer(), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=True),
        sa.Column('potential_match_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('batch_file_name', sa.String(length=200), nullable=True),
        sa.Column('batch_file_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screening_sessions_user', 'screening_sessions', ['user_id', 'created_at'], unique=False, if_not_exists=True)
    
    # Screening Results
    op.create_table('screening_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('screening_type', sa.String(length=20), nullable=False),
        sa.Column('query_value', sa.Text(), nullable=False),
        sa.Column('query_normalized', sa.Text(), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('additional_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('lists_screened', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('total_matches', sa.Integer(), nullable=True),
        sa.Column('highest_match_score', sa.Float(), nullable=True),
        sa.Column('matches', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('certificate_id', sa.String(length=50), nullable=True),
        sa.Column('certificate_generated', sa.Boolean(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('flags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['screening_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('certificate_id')
    )
    op.create_index(op.f('ix_screening_results_user_id'), 'screening_results', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_screening_results_user', 'screening_results', ['user_id', 'created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_screening_results_status', 'screening_results', ['status'], unique=False, if_not_exists=True)
    op.create_index('ix_screening_results_cert', 'screening_results', ['certificate_id'], unique=False, if_not_exists=True)
    
    # Screening Matches
    op.create_table('screening_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('list_code', sa.String(length=50), nullable=False),
        sa.Column('list_name', sa.String(length=200), nullable=True),
        sa.Column('matched_name', sa.Text(), nullable=False),
        sa.Column('matched_type', sa.String(length=20), nullable=True),
        sa.Column('matched_programs', sa.Text(), nullable=True),
        sa.Column('matched_country', sa.String(length=100), nullable=True),
        sa.Column('match_type', sa.String(length=20), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('match_method', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['sanctioned_entities.id'], ),
        sa.ForeignKeyConstraint(['result_id'], ['screening_results.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screening_matches_result', 'screening_matches', ['result_id'], unique=False, if_not_exists=True)
    
    # Watchlist Entries
    op.create_table('watchlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('name_normalized', sa.Text(), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('identifiers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('lists_to_monitor', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('alert_email', sa.Boolean(), nullable=True),
        sa.Column('alert_in_app', sa.Boolean(), nullable=True),
        sa.Column('last_screened', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=20), nullable=True),
        sa.Column('last_result_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_entries_user_id'), 'watchlist_entries', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_watchlist_user', 'watchlist_entries', ['user_id', 'is_active'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_watchlist_entries_name_normalized'), 'watchlist_entries', ['name_normalized'], unique=False, if_not_exists=True)
    
    # Watchlist Alerts
    op.create_table('watchlist_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('watchlist_entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('previous_status', sa.String(length=20), nullable=True),
        sa.Column('new_status', sa.String(length=20), nullable=True),
        sa.Column('match_list', sa.String(length=50), nullable=True),
        sa.Column('match_entity', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=True),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['watchlist_entry_id'], ['watchlist_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_alerts_user_id'), 'watchlist_alerts', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_watchlist_alerts_user', 'watchlist_alerts', ['user_id', 'is_read'], unique=False, if_not_exists=True)


def downgrade():
    op.drop_index('ix_watchlist_alerts_user', table_name='watchlist_alerts')
    op.drop_index(op.f('ix_watchlist_alerts_user_id'), table_name='watchlist_alerts')
    op.drop_table('watchlist_alerts')
    
    op.drop_index(op.f('ix_watchlist_entries_name_normalized'), table_name='watchlist_entries')
    op.drop_index('ix_watchlist_user', table_name='watchlist_entries')
    op.drop_index(op.f('ix_watchlist_entries_user_id'), table_name='watchlist_entries')
    op.drop_table('watchlist_entries')
    
    op.drop_index('ix_screening_matches_result', table_name='screening_matches')
    op.drop_table('screening_matches')
    
    op.drop_index('ix_screening_results_cert', table_name='screening_results')
    op.drop_index('ix_screening_results_status', table_name='screening_results')
    op.drop_index('ix_screening_results_user', table_name='screening_results')
    op.drop_index(op.f('ix_screening_results_user_id'), table_name='screening_results')
    op.drop_table('screening_results')
    
    op.drop_index('ix_screening_sessions_user', table_name='screening_sessions')
    op.drop_table('screening_sessions')
    
    op.drop_index('ix_sanctioned_entities_type', table_name='sanctioned_entities')
    op.drop_index('ix_sanctioned_entities_list_name', table_name='sanctioned_entities')
    op.drop_index(op.f('ix_sanctioned_entities_source_id'), table_name='sanctioned_entities')
    op.drop_table('sanctioned_entities')
    
    op.drop_index(op.f('ix_sanctions_lists_code'), table_name='sanctions_lists')
    op.drop_table('sanctions_lists')

