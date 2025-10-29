"""Add compliance hardening tables

Revision ID: 20250917_compliance
Revises: 20250917_add_admin_console_tables
Create Date: 2025-09-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250917_compliance'
down_revision = '20250917_add_admin_console_tables'
branch_labels = None
depends_on = None

def upgrade():
    # Data residency policies
    op.create_table(
        'data_residency_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('policy', sa.Enum('BD', 'EU', 'SG', 'GLOBAL', name='residency_policy'), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('configured_by', sa.String(255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_residency_policies_tenant_id', 'tenant_id'),
        sa.Index('ix_residency_policies_effective_from', 'effective_from')
    )

    # Residency violations
    op.create_table(
        'residency_violations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('object_key', sa.String(500), nullable=False),
        sa.Column('attempted_region', sa.String(10), nullable=False),
        sa.Column('policy', sa.Enum('BD', 'EU', 'SG', 'GLOBAL', name='residency_policy'), nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_residency_violations_tenant_id', 'tenant_id'),
        sa.Index('ix_residency_violations_created_at', 'created_at')
    )

    # Encryption events
    op.create_table(
        'encryption_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('object_key', sa.String(500), nullable=False),
        sa.Column('bucket', sa.String(255), nullable=False),
        sa.Column('kms_key_id', sa.String(500), nullable=False),
        sa.Column('checksum_before', sa.String(64), nullable=True),
        sa.Column('checksum_after', sa.String(64), nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('action', sa.Enum('encrypt', 'decrypt', 'reencrypt', name='encryption_action'), nullable=False),
        sa.Column('status', sa.Enum('success', 'failure', name='encryption_status'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_encryption_events_tenant_id', 'tenant_id'),
        sa.Index('ix_encryption_events_object_key', 'object_key'),
        sa.Index('ix_encryption_events_created_at', 'created_at'),
        sa.Index('ix_encryption_events_action', 'action')
    )

    # Object metadata
    op.create_table(
        'object_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('object_key', sa.String(500), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('region', sa.String(10), nullable=False),
        sa.Column('bucket', sa.String(255), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('sse_mode', sa.String(50), nullable=False),
        sa.Column('kms_key_id', sa.String(500), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_modified_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_key', 'tenant_id', name='uq_object_metadata_key_tenant'),
        sa.Index('ix_object_metadata_tenant_id', 'tenant_id'),
        sa.Index('ix_object_metadata_region', 'region'),
        sa.Index('ix_object_metadata_created_at', 'created_at')
    )

    # Backup runs
    op.create_table(
        'backup_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backup_type', sa.Enum('full', 'incremental', 'object_storage', name='backup_type'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('running', 'success', 'failure', 'cancelled', name='backup_status'), nullable=False),
        sa.Column('rpo_seconds', sa.Integer(), nullable=True),
        sa.Column('rto_seconds', sa.Integer(), nullable=True),
        sa.Column('artifact_uri', sa.String(500), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_backup_runs_backup_type', 'backup_type'),
        sa.Index('ix_backup_runs_status', 'status'),
        sa.Index('ix_backup_runs_started_at', 'started_at')
    )

    # DR drills
    op.create_table(
        'dr_drills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('drill_type', sa.Enum('failover', 'restore', 'network', name='drill_type'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('running', 'success', 'failure', 'cancelled', name='drill_status'), nullable=False),
        sa.Column('rpo_achieved_seconds', sa.Integer(), nullable=True),
        sa.Column('rto_achieved_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('report_uri', sa.String(500), nullable=True),
        sa.Column('conducted_by', sa.String(255), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_dr_drills_drill_type', 'drill_type'),
        sa.Index('ix_dr_drills_status', 'status'),
        sa.Index('ix_dr_drills_started_at', 'started_at')
    )

    # Compliance audit trail (separate from main audit_events for compliance-specific tracking)
    op.create_table(
        'compliance_audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=True),
        sa.Column('actor_type', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('outcome', sa.Enum('success', 'failure', 'denied', name='audit_outcome'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_compliance_audit_events_event_type', 'event_type'),
        sa.Index('ix_compliance_audit_events_actor_id', 'actor_id'),
        sa.Index('ix_compliance_audit_events_tenant_id', 'tenant_id'),
        sa.Index('ix_compliance_audit_events_resource_type', 'resource_type'),
        sa.Index('ix_compliance_audit_events_created_at', 'created_at'),
        sa.Index('ix_compliance_audit_events_outcome', 'outcome')
    )

    # SLO metrics tracking
    op.create_table(
        'slo_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slo_name', sa.String(100), nullable=False),
        sa.Column('metric_type', sa.Enum('latency', 'availability', 'error_rate', 'throughput', name='slo_metric_type'), nullable=False),
        sa.Column('measurement_window', sa.String(20), nullable=False),  # e.g., '1h', '24h', '30d'
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=False),
        sa.Column('error_budget_remaining', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('healthy', 'warning', 'critical', name='slo_status'), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=True),  # null for system-wide SLOs
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_slo_metrics_slo_name', 'slo_name'),
        sa.Index('ix_slo_metrics_metric_type', 'metric_type'),
        sa.Index('ix_slo_metrics_measured_at', 'measured_at'),
        sa.Index('ix_slo_metrics_status', 'status')
    )

def downgrade():
    op.drop_table('slo_metrics')
    op.drop_table('compliance_audit_events')
    op.drop_table('dr_drills')
    op.drop_table('backup_runs')
    op.drop_table('object_metadata')
    op.drop_table('encryption_events')
    op.drop_table('residency_violations')
    op.drop_table('data_residency_policies')

    # Drop custom enums
    op.execute('DROP TYPE IF EXISTS residency_policy CASCADE')
    op.execute('DROP TYPE IF EXISTS encryption_action CASCADE')
    op.execute('DROP TYPE IF EXISTS encryption_status CASCADE')
    op.execute('DROP TYPE IF EXISTS backup_type CASCADE')
    op.execute('DROP TYPE IF EXISTS backup_status CASCADE')
    op.execute('DROP TYPE IF EXISTS drill_type CASCADE')
    op.execute('DROP TYPE IF EXISTS drill_status CASCADE')
    op.execute('DROP TYPE IF EXISTS audit_outcome CASCADE')
    op.execute('DROP TYPE IF EXISTS slo_metric_type CASCADE')
    op.execute('DROP TYPE IF EXISTS slo_status CASCADE')