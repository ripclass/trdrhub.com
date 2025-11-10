"""
Exporter submission models for bank submissions and customs packs.
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SubmissionStatus(str, Enum):
    """Status of a bank submission."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubmissionEventType(str, Enum):
    """Types of submission events."""
    CREATED = "created"
    BANK_ACK = "bank_ack"
    BANK_REJECT = "bank_reject"
    RETRY = "retry"
    CANCEL = "cancel"
    MANIFEST_GENERATED = "manifest_generated"
    RECEIPT_GENERATED = "receipt_generated"


class ExportSubmission(Base):
    """Bank submission record for exporter LC validations."""
    __tablename__ = "export_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False, index=True)
    
    lc_number = Column(String(100), nullable=False, index=True)
    bank_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to bank/company
    bank_name = Column(String(255), nullable=True)
    
    status = Column(String(50), nullable=False, default=SubmissionStatus.PENDING.value, index=True)
    
    # Manifest and hash
    manifest_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash
    manifest_data = Column(JSONB, nullable=True)  # Full manifest JSON
    
    # Submission metadata
    note = Column(Text, nullable=True)
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    
    # Receipt
    receipt_url = Column(String(512), nullable=True)
    receipt_generated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    result_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company")
    user = relationship("User")
    validation_session = relationship("ValidationSession")
    events = relationship("SubmissionEvent", back_populates="submission", order_by="SubmissionEvent.created_at")

    __table_args__ = (
        Index('ix_export_submissions_lc_status', 'lc_number', 'status'),
        Index('ix_export_submissions_session', 'validation_session_id', 'status'),
    )


class SubmissionEvent(Base):
    """Event timeline for export submissions."""
    __tablename__ = "submission_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("export_submissions.id"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSONB, nullable=True)  # Event-specific data
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Optional actor tracking
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(255), nullable=True)

    # Relationships
    submission = relationship("ExportSubmission", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index('ix_submission_events_submission_type', 'submission_id', 'event_type'),
        Index('ix_submission_events_created', 'created_at'),
    )


class CustomsPack(Base):
    """Customs pack generation record."""
    __tablename__ = "customs_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False, index=True)
    
    lc_number = Column(String(100), nullable=False, index=True)
    
    # Pack metadata
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    sha256_hash = Column(String(64), nullable=True, index=True)
    manifest_data = Column(JSONB, nullable=True)
    
    # Storage
    s3_key = Column(String(512), nullable=True)
    download_url = Column(String(512), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company")
    user = relationship("User")
    validation_session = relationship("ValidationSession")

    __table_args__ = (
        Index('ix_customs_packs_session', 'validation_session_id'),
        Index('ix_customs_packs_lc', 'lc_number'),
    )

