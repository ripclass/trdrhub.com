"""Add RBAC tables for company members and invitations

Revision ID: rbac_members_001
Revises: hub_multi_tool_001
Create Date: 2025-12-02

This migration creates:
- company_members: Links users to companies with roles (owner, admin, member, viewer)
- company_invitations: Tracks pending invitations to join a company
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'rbac_members_001'
down_revision = 'hub_multi_tool_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create company_members table
    op.create_table(
        'company_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('tool_access', JSONB, nullable=False, server_default='[]'),
        sa.Column('invited_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        # Constraints
        sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name='valid_member_role'),
        sa.CheckConstraint("status IN ('active', 'pending', 'suspended', 'removed')", name='valid_member_status'),
        sa.UniqueConstraint('company_id', 'user_id', name='unique_company_user'),
    )
    
    # Create indexes for company_members
    op.create_index('ix_company_members_company_id', 'company_members', ['company_id'])
    op.create_index('ix_company_members_user_id', 'company_members', ['user_id'])
    op.create_index('ix_company_members_role', 'company_members', ['role'])
    op.create_index('ix_company_members_status', 'company_members', ['status'])
    
    # Create company_invitations table
    op.create_table(
        'company_invitations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('tool_access', JSONB, nullable=False, server_default='[]'),
        sa.Column('invited_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        # Constraints
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name='valid_invitation_role'),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'expired', 'cancelled')", name='valid_invitation_status'),
    )
    
    # Create indexes for company_invitations
    op.create_index('ix_company_invitations_company_id', 'company_invitations', ['company_id'])
    op.create_index('ix_company_invitations_email', 'company_invitations', ['email'])
    op.create_index('ix_company_invitations_token', 'company_invitations', ['token'])
    op.create_index('ix_company_invitations_status', 'company_invitations', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_company_invitations_status', 'company_invitations')
    op.drop_index('ix_company_invitations_token', 'company_invitations')
    op.drop_index('ix_company_invitations_email', 'company_invitations')
    op.drop_index('ix_company_invitations_company_id', 'company_invitations')
    
    op.drop_index('ix_company_members_status', 'company_members')
    op.drop_index('ix_company_members_role', 'company_members')
    op.drop_index('ix_company_members_user_id', 'company_members')
    op.drop_index('ix_company_members_company_id', 'company_members')
    
    # Drop tables
    op.drop_table('company_invitations')
    op.drop_table('company_members')

