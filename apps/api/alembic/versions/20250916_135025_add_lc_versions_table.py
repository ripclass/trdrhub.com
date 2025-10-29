"""Add LC versions table

Revision ID: 20250916_135025
Revises: 3fb37464b8c2
Create Date: 2025-09-16 13:50:25.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250916_135025'
down_revision = '3fb37464b8c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add lc_versions table with proper constraints and indexes."""
    # Create lc_versions table
    op.create_table(
        'lc_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lc_number', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('validation_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('file_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['validation_session_id'], ['validation_sessions.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.UniqueConstraint('lc_number', 'version', name='_lc_number_version_uc')
    )

    # Create indexes
    op.create_index('idx_lc_versions_lc_number', 'lc_versions', ['lc_number'], unique=False)
    op.create_index('idx_lc_versions_created_at', 'lc_versions', ['created_at'], unique=False)
    op.create_index('idx_lc_versions_status', 'lc_versions', ['status'], unique=False)


def downgrade() -> None:
    """Remove lc_versions table and all associated indexes."""
    # Drop indexes first
    op.drop_index('idx_lc_versions_status', table_name='lc_versions')
    op.drop_index('idx_lc_versions_created_at', table_name='lc_versions')
    op.drop_index('idx_lc_versions_lc_number', table_name='lc_versions')

    # Drop table
    op.drop_table('lc_versions')