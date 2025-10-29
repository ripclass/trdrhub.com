"""add_audit_log_table

Revision ID: 20250916_140000
Revises: 20250916_135025
Create Date: 2025-09-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250916_140000'
down_revision = '20250916_135025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_log table for compliance traceability."""

    # Create audit_log table
    op.create_table('audit_log',
        # Primary key
        sa.Column('id', sa.UUID(), nullable=False),

        # Correlation and tracking
        sa.Column('correlation_id', sa.String(length=100), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=True),

        # WHO: User information
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_role', sa.String(length=50), nullable=True),

        # WHAT: Action details
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),

        # LC-specific fields
        sa.Column('lc_number', sa.String(length=100), nullable=True),
        sa.Column('lc_version', sa.String(length=10), nullable=True),

        # WHEN: Timing information
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),

        # WHERE: Request information
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('http_method', sa.String(length=10), nullable=True),

        # RESULT: Outcome information
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Evidence and integrity
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_count', sa.Integer(), nullable=True),

        # Metadata and context (using JSON for PostgreSQL, fallback to Text for SQLite)
        sa.Column('request_data', sa.JSON().with_variant(sa.Text(), "sqlite"), nullable=True),
        sa.Column('response_data', sa.JSON().with_variant(sa.Text(), "sqlite"), nullable=True),
        sa.Column('audit_metadata', sa.JSON().with_variant(sa.Text(), "sqlite"), nullable=True),

        # Compliance fields
        sa.Column('retention_until', sa.DateTime(), nullable=True),
        sa.Column('archived', sa.String(length=20), nullable=True),

        # Primary key constraint
        sa.PrimaryKeyConstraint('id'),

        # Foreign key constraint
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )

    # Performance indexes
    op.create_index('ix_audit_log_id', 'audit_log', ['id'])
    op.create_index('ix_audit_log_correlation_id', 'audit_log', ['correlation_id'])
    op.create_index('ix_audit_log_session_id', 'audit_log', ['session_id'])
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_user_email', 'audit_log', ['user_email'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_resource_type', 'audit_log', ['resource_type'])
    op.create_index('ix_audit_log_resource_id', 'audit_log', ['resource_id'])
    op.create_index('ix_audit_log_lc_number', 'audit_log', ['lc_number'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('ix_audit_log_ip_address', 'audit_log', ['ip_address'])
    op.create_index('ix_audit_log_result', 'audit_log', ['result'])

    # Composite indexes for common queries
    op.create_index('ix_audit_log_user_action', 'audit_log', ['user_id', 'action'])
    op.create_index('ix_audit_log_lc_timestamp', 'audit_log', ['lc_number', 'timestamp'])
    op.create_index('ix_audit_log_action_timestamp', 'audit_log', ['action', 'timestamp'])
    op.create_index('ix_audit_log_result_timestamp', 'audit_log', ['result', 'timestamp'])


def downgrade() -> None:
    """Drop audit_log table and indexes."""

    # Drop indexes first
    op.drop_index('ix_audit_log_result_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_action_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_lc_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_user_action', table_name='audit_log')
    op.drop_index('ix_audit_log_result', table_name='audit_log')
    op.drop_index('ix_audit_log_ip_address', table_name='audit_log')
    op.drop_index('ix_audit_log_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_lc_number', table_name='audit_log')
    op.drop_index('ix_audit_log_resource_id', table_name='audit_log')
    op.drop_index('ix_audit_log_resource_type', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_index('ix_audit_log_user_email', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_index('ix_audit_log_session_id', table_name='audit_log')
    op.drop_index('ix_audit_log_correlation_id', table_name='audit_log')
    op.drop_index('ix_audit_log_id', table_name='audit_log')

    # Drop table
    op.drop_table('audit_log')