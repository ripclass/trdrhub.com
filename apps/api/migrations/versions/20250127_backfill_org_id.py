"""Backfill org_id in validation_sessions bank_metadata

Revision ID: 20250127_backfill_org_id
Revises: 20250127_add_bank_orgs
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250127_backfill_org_id'
down_revision = '20250127_add_bank_orgs'
branch_labels = None
depends_on = None


def upgrade():
    """
    Backfill org_id in validation_sessions.extracted_data.bank_metadata.
    
    For historical data:
    - Sets org_id to NULL (org filtering only applied when org_id present)
    - New sessions will have org_id set from request.state.org_id
    
    This migration ensures the structure exists but leaves historical data
    without org_id, which is acceptable since org filtering is optional.
    """
    # Use raw SQL to update JSONB structure
    # This ensures bank_metadata.org_id exists (as null) for all bank sessions
    op.execute("""
        UPDATE validation_sessions
        SET extracted_data = jsonb_set(
            COALESCE(extracted_data, '{}'::jsonb),
            '{bank_metadata,org_id}',
            'null'::jsonb,
            true  -- create if missing
        )
        WHERE extracted_data IS NOT NULL
          AND extracted_data ? 'bank_metadata'
          AND (extracted_data->'bank_metadata'->>'org_id') IS NULL;
    """)


def downgrade():
    """
    Remove org_id from bank_metadata (optional - usually not needed).
    """
    # Remove org_id from bank_metadata if it exists
    op.execute("""
        UPDATE validation_sessions
        SET extracted_data = extracted_data #- '{bank_metadata,org_id}'
        WHERE extracted_data IS NOT NULL
          AND extracted_data ? 'bank_metadata'
          AND (extracted_data->'bank_metadata'->>'org_id') IS NOT NULL;
    """)

