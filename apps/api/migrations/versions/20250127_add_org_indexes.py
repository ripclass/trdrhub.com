"""Add performance indexes for org-scoped queries

Revision ID: 20250127_add_org_indexes
Revises: 20250127_backfill_org_id
Create Date: 2025-01-27 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250127_add_org_indexes'
down_revision = '20250127_backfill_org_id'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add performance indexes for org-scoped queries on validation_sessions.
    
    Creates:
    - JSONB expression index for org_id lookups in bank_metadata
    - Partial indexes for common status/date filters used in results
    """
    # JSONB expression index for org_id lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_validation_sessions_org_id
        ON validation_sessions ((extracted_data->'bank_metadata'->>'org_id'))
        WHERE extracted_data IS NOT NULL
          AND extracted_data ? 'bank_metadata';
    """)
    
    # Partial index for completed/failed sessions (common in results queries)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_validation_sessions_completed_failed
        ON validation_sessions (created_at DESC, processing_completed_at DESC NULLS LAST)
        WHERE status IN ('completed', 'failed')
          AND deleted_at IS NULL;
    """)
    
    # Composite index for org + status filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_validation_sessions_org_status
        ON validation_sessions (
            (extracted_data->'bank_metadata'->>'org_id'),
            status,
            created_at DESC
        )
        WHERE extracted_data IS NOT NULL
          AND extracted_data ? 'bank_metadata'
          AND deleted_at IS NULL;
    """)


def downgrade():
    """Remove performance indexes."""
    op.drop_index('ix_validation_sessions_org_status', table_name='validation_sessions')
    op.drop_index('ix_validation_sessions_completed_failed', table_name='validation_sessions')
    op.drop_index('ix_validation_sessions_org_id', table_name='validation_sessions')

