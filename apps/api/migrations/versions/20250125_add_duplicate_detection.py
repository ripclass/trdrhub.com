"""Add duplicate detection tables

Revision ID: 20250125_add_duplicate_detection
Revises: 20250124_add_saved_views
Create Date: 2025-01-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250125_add_duplicate_detection'
down_revision = '20250124_add_saved_views'
branch_labels = None
depends_on = None


def upgrade():
    # LC Fingerprints table - stores content fingerprints for duplicate detection
    op.create_table(
        'lc_fingerprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('validation_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lc_number', sa.String(100), nullable=False),
        sa.Column('client_name', sa.String(255), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Content fingerprint - hash of key LC fields for similarity matching
        sa.Column('content_hash', sa.String(64), nullable=False),  # SHA-256 hash
        sa.Column('fingerprint_data', postgresql.JSONB, nullable=False),  # Normalized LC data for comparison
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['validation_session_id'], ['validation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('validation_session_id', name='uq_lc_fingerprints_session'),
    )
    op.create_index('idx_lc_fingerprints_lc_number', 'lc_fingerprints', ['lc_number'])
    op.create_index('idx_lc_fingerprints_client_name', 'lc_fingerprints', ['client_name'])
    op.create_index('idx_lc_fingerprints_company_id', 'lc_fingerprints', ['company_id'])
    op.create_index('idx_lc_fingerprints_content_hash', 'lc_fingerprints', ['content_hash'])
    op.create_index('idx_lc_fingerprints_lc_client', 'lc_fingerprints', ['lc_number', 'client_name'])
    op.create_index('idx_lc_fingerprints_company_created', 'lc_fingerprints', ['company_id', 'created_at'])
    
    # LC Similarities table - stores similarity scores between LC pairs
    op.create_table(
        'lc_similarities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fingerprint_id_1', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fingerprint_id_2', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id_1', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id_2', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Similarity metrics
        sa.Column('similarity_score', sa.Float(), nullable=False),  # 0.0 to 1.0
        sa.Column('content_similarity', sa.Float(), nullable=True),  # Text content similarity
        sa.Column('metadata_similarity', sa.Float(), nullable=True),  # Metadata fields similarity
        sa.Column('field_matches', postgresql.JSONB, nullable=True),  # Which fields matched
        
        # Detection metadata
        sa.Column('detection_method', sa.String(50), nullable=False, server_default='fingerprint'),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('detected_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.ForeignKeyConstraint(['fingerprint_id_1'], ['lc_fingerprints.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fingerprint_id_2'], ['lc_fingerprints.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id_1'], ['validation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id_2'], ['validation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['detected_by'], ['users.id'], ondelete='SET NULL'),
        
        # Ensure fingerprint_id_1 < fingerprint_id_2 to avoid duplicate pairs
        sa.CheckConstraint('fingerprint_id_1 < fingerprint_id_2', name='chk_similarity_order'),
        sa.UniqueConstraint('fingerprint_id_1', 'fingerprint_id_2', name='uq_lc_similarities_pair'),
    )
    op.create_index('idx_lc_similarities_score', 'lc_similarities', ['similarity_score'])
    op.create_index('idx_lc_similarities_session_1', 'lc_similarities', ['session_id_1'])
    op.create_index('idx_lc_similarities_session_2', 'lc_similarities', ['session_id_2'])
    op.create_index('idx_lc_similarities_detected', 'lc_similarities', ['detected_at'])
    
    # LC Merge History table - tracks when LCs are merged
    op.create_table(
        'lc_merge_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Merge metadata
        sa.Column('merge_type', sa.String(50), nullable=False),
        sa.Column('merge_reason', sa.Text(), nullable=True),
        sa.Column('merged_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merged_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Merge details
        sa.Column('fields_merged', postgresql.JSONB, nullable=True),
        sa.Column('preserved_data', postgresql.JSONB, nullable=True),
        
        sa.ForeignKeyConstraint(['source_session_id'], ['validation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_session_id'], ['validation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merged_by'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('idx_lc_merge_source', 'lc_merge_history', ['source_session_id'])
    op.create_index('idx_lc_merge_target', 'lc_merge_history', ['target_session_id'])
    op.create_index('idx_lc_merge_merged_at', 'lc_merge_history', ['merged_at'])
    op.create_index('idx_lc_merge_type', 'lc_merge_history', ['merge_type'])


def downgrade():
    op.drop_index('idx_lc_merge_type', table_name='lc_merge_history')
    op.drop_index('idx_lc_merge_merged_at', table_name='lc_merge_history')
    op.drop_index('idx_lc_merge_target', table_name='lc_merge_history')
    op.drop_index('idx_lc_merge_source', table_name='lc_merge_history')
    op.drop_table('lc_merge_history')
    
    op.drop_index('idx_lc_similarities_detected', table_name='lc_similarities')
    op.drop_index('idx_lc_similarities_session_2', table_name='lc_similarities')
    op.drop_index('idx_lc_similarities_session_1', table_name='lc_similarities')
    op.drop_index('idx_lc_similarities_score', table_name='lc_similarities')
    op.drop_table('lc_similarities')
    
    op.drop_index('idx_lc_fingerprints_company_created', table_name='lc_fingerprints')
    op.drop_index('idx_lc_fingerprints_lc_client', table_name='lc_fingerprints')
    op.drop_index('idx_lc_fingerprints_content_hash', table_name='lc_fingerprints')
    op.drop_index('idx_lc_fingerprints_company_id', table_name='lc_fingerprints')
    op.drop_index('idx_lc_fingerprints_client_name', table_name='lc_fingerprints')
    op.drop_index('idx_lc_fingerprints_lc_number', table_name='lc_fingerprints')
    op.drop_table('lc_fingerprints')

