"""Add bank orgs and user org access tables

Revision ID: 20250127_add_bank_orgs
Revises: 20250126_add_api_tokens_webhooks
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250127_add_bank_orgs'
down_revision = '20250126_add_api_tokens_webhooks'
branch_labels = None
depends_on = None


def upgrade():
    # Bank Organizations table - hierarchical org units within a bank
    op.create_table(
        'bank_orgs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bank_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Org metadata
        sa.Column('kind', sa.String(50), nullable=False),  # 'group', 'region', 'branch'
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),  # Short code like 'APAC', 'NYC-001'
        sa.Column('path', sa.String(500), nullable=False),  # Materialized path like '/1/2/3'
        
        # Hierarchy metadata
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),  # Depth in tree
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.ForeignKeyConstraint(['bank_company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['bank_orgs.id'], ondelete='CASCADE'),
        
        sa.Index('ix_bank_orgs_bank_company_id', 'bank_orgs', ['bank_company_id']),
        sa.Index('ix_bank_orgs_parent_id', 'bank_orgs', ['parent_id']),
        sa.Index('ix_bank_orgs_path', 'bank_orgs', ['path']),
        sa.Index('ix_bank_orgs_kind', 'bank_orgs', ['kind']),
        sa.Index('ix_bank_orgs_is_active', 'bank_orgs', ['is_active']),
        sa.UniqueConstraint('bank_company_id', 'code', name='uq_bank_orgs_bank_code'),
    )
    
    # User Org Access table - maps users to org units they can access
    op.create_table(
        'user_org_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Access role within this org
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),  # 'admin', 'member', 'viewer'
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['bank_orgs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        
        sa.Index('ix_user_org_access_user_id', 'user_org_access', ['user_id']),
        sa.Index('ix_user_org_access_org_id', 'user_org_access', ['org_id']),
        sa.UniqueConstraint('user_id', 'org_id', name='uq_user_org_access_user_org'),
    )


def downgrade():
    op.drop_index('ix_user_org_access_org_id', table_name='user_org_access')
    op.drop_index('ix_user_org_access_user_id', table_name='user_org_access')
    op.drop_table('user_org_access')
    
    op.drop_index('ix_bank_orgs_is_active', table_name='bank_orgs')
    op.drop_index('ix_bank_orgs_kind', table_name='bank_orgs')
    op.drop_index('ix_bank_orgs_path', table_name='bank_orgs')
    op.drop_index('ix_bank_orgs_parent_id', table_name='bank_orgs')
    op.drop_index('ix_bank_orgs_bank_company_id', table_name='bank_orgs')
    op.drop_table('bank_orgs')

