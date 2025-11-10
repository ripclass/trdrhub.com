"""Add exporter submission tables

Revision ID: 20250123_add_exporter_submissions
Revises: 20250122_add_bank_policy_application_events
Create Date: 2025-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250123_add_exporter_submissions'
down_revision = '20250122_add_bank_policy_application_events'
branch_labels = None
depends_on = None


def upgrade():
    # Create export_submissions table
    op.create_table(
        'export_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lc_number', sa.String(100), nullable=False),
        sa.Column('bank_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bank_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('manifest_hash', sa.String(64), nullable=True),
        sa.Column('manifest_data', postgresql.JSONB, nullable=True),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('idempotency_key', sa.String(128), nullable=True, unique=True),
        sa.Column('receipt_url', sa.String(512), nullable=True),
        sa.Column('receipt_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['validation_session_id'], ['validation_sessions.id'], ),
    )
    op.create_index('ix_export_submissions_company_id', 'export_submissions', ['company_id'])
    op.create_index('ix_export_submissions_user_id', 'export_submissions', ['user_id'])
    op.create_index('ix_export_submissions_validation_session_id', 'export_submissions', ['validation_session_id'])
    op.create_index('ix_export_submissions_lc_number', 'export_submissions', ['lc_number'])
    op.create_index('ix_export_submissions_bank_id', 'export_submissions', ['bank_id'])
    op.create_index('ix_export_submissions_status', 'export_submissions', ['status'])
    op.create_index('ix_export_submissions_manifest_hash', 'export_submissions', ['manifest_hash'])
    op.create_index('ix_export_submissions_idempotency_key', 'export_submissions', ['idempotency_key'])
    op.create_index('ix_export_submissions_lc_status', 'export_submissions', ['lc_number', 'status'])
    op.create_index('ix_export_submissions_session', 'export_submissions', ['validation_session_id', 'status'])

    # Create submission_events table
    op.create_table(
        'submission_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_name', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['submission_id'], ['export_submissions.id'], ),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    )
    op.create_index('ix_submission_events_submission_id', 'submission_events', ['submission_id'])
    op.create_index('ix_submission_events_event_type', 'submission_events', ['event_type'])
    op.create_index('ix_submission_events_submission_type', 'submission_events', ['submission_id', 'event_type'])
    op.create_index('ix_submission_events_created', 'submission_events', ['created_at'])

    # Create customs_packs table
    op.create_table(
        'customs_packs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lc_number', sa.String(100), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        sa.Column('manifest_data', postgresql.JSONB, nullable=True),
        sa.Column('s3_key', sa.String(512), nullable=True),
        sa.Column('download_url', sa.String(512), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['validation_session_id'], ['validation_sessions.id'], ),
    )
    op.create_index('ix_customs_packs_company_id', 'customs_packs', ['company_id'])
    op.create_index('ix_customs_packs_user_id', 'customs_packs', ['user_id'])
    op.create_index('ix_customs_packs_validation_session_id', 'customs_packs', ['validation_session_id'])
    op.create_index('ix_customs_packs_lc_number', 'customs_packs', ['lc_number'])
    op.create_index('ix_customs_packs_sha256_hash', 'customs_packs', ['sha256_hash'])
    op.create_index('ix_customs_packs_session', 'customs_packs', ['validation_session_id'])
    op.create_index('ix_customs_packs_lc', 'customs_packs', ['lc_number'])


def downgrade():
    op.drop_index('ix_customs_packs_lc', table_name='customs_packs')
    op.drop_index('ix_customs_packs_session', table_name='customs_packs')
    op.drop_index('ix_customs_packs_sha256_hash', table_name='customs_packs')
    op.drop_index('ix_customs_packs_lc_number', table_name='customs_packs')
    op.drop_index('ix_customs_packs_validation_session_id', table_name='customs_packs')
    op.drop_index('ix_customs_packs_user_id', table_name='customs_packs')
    op.drop_index('ix_customs_packs_company_id', table_name='customs_packs')
    op.drop_table('customs_packs')
    
    op.drop_index('ix_submission_events_created', table_name='submission_events')
    op.drop_index('ix_submission_events_submission_type', table_name='submission_events')
    op.drop_index('ix_submission_events_event_type', table_name='submission_events')
    op.drop_index('ix_submission_events_submission_id', table_name='submission_events')
    op.drop_table('submission_events')
    
    op.drop_index('ix_export_submissions_session', table_name='export_submissions')
    op.drop_index('ix_export_submissions_lc_status', table_name='export_submissions')
    op.drop_index('ix_export_submissions_idempotency_key', table_name='export_submissions')
    op.drop_index('ix_export_submissions_manifest_hash', table_name='export_submissions')
    op.drop_index('ix_export_submissions_status', table_name='export_submissions')
    op.drop_index('ix_export_submissions_bank_id', table_name='export_submissions')
    op.drop_index('ix_export_submissions_lc_number', table_name='export_submissions')
    op.drop_index('ix_export_submissions_validation_session_id', table_name='export_submissions')
    op.drop_index('ix_export_submissions_user_id', table_name='export_submissions')
    op.drop_index('ix_export_submissions_company_id', table_name='export_submissions')
    op.drop_table('export_submissions')

