"""
Immutable Audit Trail Models
Hash-chained audit entries for complete tamper detection
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
import uuid
import hashlib
import json
from typing import Dict, Any, Optional

from app.models.base import Base


class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    ROTATE = "rotate"
    BACKUP = "backup"
    RESTORE = "restore"


class AuditSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogEntry(Base):
    """
    Immutable audit log entry with hash chain verification
    Each entry contains a hash of the previous entry to detect tampering
    """
    __tablename__ = "audit_log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_number = Column(Integer, nullable=False, unique=True, autoincrement=True)

    # Context
    tenant_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True)  # User who performed the action
    actor_role = Column(String(64), nullable=True)
    actor_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    actor_user_agent = Column(Text, nullable=True)

    # Resource information
    resource_type = Column(String(64), nullable=False)  # e.g., 'lc_session', 'user', 'workflow'
    resource_id = Column(String(128), nullable=False)
    resource_name = Column(String(256), nullable=True)

    # Action details
    action = Column(String(32), nullable=False)
    action_description = Column(Text, nullable=True)
    severity = Column(String(16), nullable=False, default=AuditSeverity.MEDIUM)

    # Data hashes for integrity
    before_hash = Column(String(64), nullable=True)  # SHA256 of data before change
    after_hash = Column(String(64), nullable=True)   # SHA256 of data after change

    # Hash chain for tamper detection
    prev_entry_hash = Column(String(64), nullable=True)  # Hash of previous audit entry
    entry_hash = Column(String(64), nullable=False)      # Hash of this entry

    # Additional context
    event_metadata = Column(JSONB, nullable=True)  # Additional contextual data
    correlation_id = Column(UUID(as_uuid=True), nullable=True)  # Group related actions

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_audit_entries_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_audit_entries_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_entries_actor', 'actor_id'),
        Index('ix_audit_entries_action', 'action'),
        Index('ix_audit_entries_sequence', 'sequence_number'),
        Index('ix_audit_entries_hash_chain', 'prev_entry_hash'),
    )

    def compute_entry_hash(self, prev_hash: Optional[str] = None) -> str:
        """
        Compute hash for this audit entry including chain verification
        """
        hash_data = {
            'sequence_number': self.sequence_number,
            'tenant_id': self.tenant_id,
            'actor_id': str(self.actor_id) if self.actor_id else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'before_hash': self.before_hash,
            'after_hash': self.after_hash,
            'prev_entry_hash': prev_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        hash_string = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode()).hexdigest()


class ComplianceDoc(Base):
    """
    Versioned compliance documents with integrity verification
    """
    __tablename__ = "compliance_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(String(128), nullable=False)  # Logical document identifier

    # Resource link
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)

    # Version information
    version = Column(String(32), nullable=False)
    is_current = Column(Boolean, default=True)

    # Storage information
    storage_path = Column(String(512), nullable=False)  # S3/MinIO path
    file_name = Column(String(256), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(128), nullable=True)

    # Integrity verification
    sha256_hash = Column(String(64), nullable=False)

    # Language and localization
    language = Column(String(8), nullable=False, default='en')

    # Metadata
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)

    # Management
    tenant_id = Column(String(64), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_compliance_docs_resource', 'resource_type', 'resource_id'),
        Index('ix_compliance_docs_doc_version', 'doc_id', 'version', unique=True),
        Index('ix_compliance_docs_current', 'doc_id', 'is_current'),
        Index('ix_compliance_docs_tenant', 'tenant_id'),
        Index('ix_compliance_docs_hash', 'sha256_hash'),
    )


class SecretRotationLog(Base):
    """
    Log of secret rotation events for audit compliance
    """
    __tablename__ = "secret_rotation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Secret identification
    secret_name = Column(String(128), nullable=False, index=True)
    secret_type = Column(String(64), nullable=False)  # jwt_key, db_password, api_key, etc.
    environment = Column(String(32), nullable=False)  # dev, staging, prod

    # Rotation details
    rotation_method = Column(String(64), nullable=False)  # manual, automatic, scheduled
    rotated_by = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(String(256), nullable=True)

    # Fingerprints for verification (never store actual secrets)
    prev_fingerprint = Column(String(64), nullable=True)  # SHA256 of old secret
    new_fingerprint = Column(String(64), nullable=False)  # SHA256 of new secret

    # Impact tracking
    services_restarted = Column(JSONB, nullable=True)  # List of services that were restarted
    downtime_seconds = Column(Integer, nullable=True)

    # Status
    status = Column(String(32), nullable=False)  # completed, failed, rolled_back
    error_message = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Additional context
    notes = Column(Text, nullable=True)
    event_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_secret_rotation_secret_env', 'secret_name', 'environment'),
        Index('ix_secret_rotation_started', 'started_at'),
        Index('ix_secret_rotation_status', 'status'),
    )


class GovernanceApproval(Base):
    """
    Multi-level approval tracking for governance enforcement
    """
    __tablename__ = "governance_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request context
    tenant_id = Column(String(64), nullable=False, index=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, unique=True)

    # Action requiring approval
    action_type = Column(String(64), nullable=False)  # role_change, export_release, etc.
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)

    # Requester
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    request_reason = Column(Text, nullable=True)
    request_context = Column(JSONB, nullable=True)

    # Approval requirements
    required_approvals = Column(Integer, nullable=False, default=2)
    required_roles = Column(JSONB, nullable=True)  # List of roles that can approve

    # Current status
    status = Column(String(32), nullable=False, default='pending')  # pending, approved, rejected, expired
    approvals_received = Column(Integer, nullable=False, default=0)

    # Approval history
    approval_history = Column(JSONB, nullable=True)  # List of approval/rejection events

    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Final action
    executed_by = Column(UUID(as_uuid=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_result = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_governance_approvals_tenant_status', 'tenant_id', 'status'),
        Index('ix_governance_approvals_resource', 'resource_type', 'resource_id'),
        Index('ix_governance_approvals_requester', 'requested_by'),
        Index('ix_governance_approvals_expires', 'expires_at'),
    )