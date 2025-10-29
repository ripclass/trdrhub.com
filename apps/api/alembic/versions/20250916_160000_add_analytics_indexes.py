"""Add indexes for analytics performance

Revision ID: 20250916_160000
Revises: 20250916_150000
Create Date: 2025-09-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20250916_160000'
down_revision = '20250916_150000'
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes to optimize analytics queries."""

    # Indexes for validation_sessions (jobs) analytics
    op.create_index(
        'idx_validation_sessions_status',
        'validation_sessions',
        ['status']
    )

    op.create_index(
        'idx_validation_sessions_user_status',
        'validation_sessions',
        ['user_id', 'status']
    )

    op.create_index(
        'idx_validation_sessions_created_at',
        'validation_sessions',
        ['created_at']
    )

    op.create_index(
        'idx_validation_sessions_user_created',
        'validation_sessions',
        ['user_id', 'created_at']
    )

    op.create_index(
        'idx_validation_sessions_processing_times',
        'validation_sessions',
        ['processing_started_at', 'processing_completed_at']
    )

    # Indexes for audit_log analytics
    op.create_index(
        'idx_audit_log_timestamp',
        'audit_log',
        ['timestamp']
    )

    op.create_index(
        'idx_audit_log_user_timestamp',
        'audit_log',
        ['user_id', 'timestamp']
    )

    op.create_index(
        'idx_audit_log_action_timestamp',
        'audit_log',
        ['action', 'timestamp']
    )

    op.create_index(
        'idx_audit_log_result_timestamp',
        'audit_log',
        ['result', 'timestamp']
    )

    op.create_index(
        'idx_audit_log_action_result',
        'audit_log',
        ['action', 'result']
    )

    # Indexes for documents analytics
    op.create_index(
        'idx_documents_type_created',
        'documents',
        ['document_type', 'created_at']
    )

    op.create_index(
        'idx_documents_session_type',
        'documents',
        ['validation_session_id', 'document_type']
    )

    # Indexes for discrepancies analytics
    op.create_index(
        'idx_discrepancies_type_severity',
        'discrepancies',
        ['discrepancy_type', 'severity']
    )

    op.create_index(
        'idx_discrepancies_session_created',
        'discrepancies',
        ['validation_session_id', 'created_at']
    )


def downgrade():
    """Remove analytics indexes."""

    # Drop validation_sessions indexes
    op.drop_index('idx_validation_sessions_status')
    op.drop_index('idx_validation_sessions_user_status')
    op.drop_index('idx_validation_sessions_created_at')
    op.drop_index('idx_validation_sessions_user_created')
    op.drop_index('idx_validation_sessions_processing_times')

    # Drop audit_log indexes
    op.drop_index('idx_audit_log_timestamp')
    op.drop_index('idx_audit_log_user_timestamp')
    op.drop_index('idx_audit_log_action_timestamp')
    op.drop_index('idx_audit_log_result_timestamp')
    op.drop_index('idx_audit_log_action_result')

    # Drop documents indexes
    op.drop_index('idx_documents_type_created')
    op.drop_index('idx_documents_session_type')

    # Drop discrepancies indexes
    op.drop_index('idx_discrepancies_type_severity')
    op.drop_index('idx_discrepancies_session_created')