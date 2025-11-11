"""Add saved_views table for bank search filters

Revision ID: 20250124_add_saved_views
Revises: 20250123_add_exporter_submissions
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250124_add_saved_views'
down_revision = '20250123_add_exporter_submissions'
branch_labels = None
depends_on = None


def upgrade():
    # Create saved_views table
    op.create_table(
        'saved_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('resource', sa.String(50), nullable=False),  # 'results', 'jobs', 'evidence'
        sa.Column('query_params', postgresql.JSONB, nullable=False),
        sa.Column('columns', postgresql.JSONB, nullable=True),  # Visible columns configuration
        sa.Column('is_org_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('shared', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_saved_views_company_id', 'saved_views', ['company_id'])
    op.create_index('ix_saved_views_owner_id', 'saved_views', ['owner_id'])
    op.create_index('ix_saved_views_resource', 'saved_views', ['resource'])
    op.create_index('ix_saved_views_company_resource', 'saved_views', ['company_id', 'resource'])
    op.create_index('ix_saved_views_org_default', 'saved_views', ['company_id', 'resource', 'is_org_default'])


def downgrade():
    op.drop_index('ix_saved_views_org_default', table_name='saved_views')
    op.drop_index('ix_saved_views_company_resource', table_name='saved_views')
    op.drop_index('ix_saved_views_resource', table_name='saved_views')
    op.drop_index('ix_saved_views_owner_id', table_name='saved_views')
    op.drop_index('ix_saved_views_company_id', table_name='saved_views')
    op.drop_table('saved_views')

