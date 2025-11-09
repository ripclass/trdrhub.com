"""
SME Workspace models for LC Workspace, Drafts, and Amendments.
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class DraftStatus(str, Enum):
    """Draft status enumeration."""
    DRAFT = "draft"
    READY_FOR_SUBMISSION = "ready_for_submission"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class AmendmentStatus(str, Enum):
    """Amendment status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class DocumentChecklistStatus(str, Enum):
    """Document checklist item status."""
    MISSING = "missing"
    UPLOADED = "uploaded"
    VALID = "valid"
    INVALID = "invalid"
    PENDING_REVIEW = "pending_review"


class LCWorkspace(Base):
    """LC Workspace model - tracks per-LC document checklist and status."""
    __tablename__ = "lc_workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_number = Column(String(100), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    
    # Workspace metadata
    client_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Document checklist - JSONB array of required documents with status
    # Format: [{"document_type": "letter_of_credit", "required": true, "status": "missing", "document_id": null, "uploaded_at": null}, ...]
    document_checklist = Column(JSONB, nullable=False, default=list)
    
    # Validation session reference (latest validation)
    latest_validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    completion_percentage = Column(Integer, default=0, nullable=False)  # 0-100
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    company = relationship("Company")
    latest_validation_session = relationship("ValidationSession", foreign_keys=[latest_validation_session_id])

    __table_args__ = (
        # Ensure one active workspace per LC per user
        # Note: This is a soft constraint - we'll enforce in application logic
    )


class Draft(Base):
    """Draft model - stores draft LC validations before submission."""
    __tablename__ = "drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    
    # Draft metadata
    lc_number = Column(String(100), nullable=True, index=True)
    client_name = Column(String(255), nullable=True)
    draft_type = Column(String(50), nullable=False)  # "importer_draft", "exporter_draft", "importer_supplier"
    
    # Status
    status = Column(
        String(20),
        nullable=False,
        default=DraftStatus.DRAFT.value,
        index=True
    )
    
    # File references - JSONB array of file metadata
    # Format: [{"file_id": "uuid", "filename": "...", "document_type": "...", "uploaded_at": "..."}, ...]
    uploaded_docs = Column(JSONB, nullable=False, default=list)
    
    # Validation session reference (if validated)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=True)
    
    # Notes and metadata
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True, default=dict)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    company = relationship("Company")
    validation_session = relationship("ValidationSession", foreign_keys=[validation_session_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready_for_submission', 'submitted', 'archived')",
            name="ck_drafts_status"
        ),
    )


class Amendment(Base):
    """Amendment model - tracks LC amendments with versioning and diffs."""
    __tablename__ = "amendments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_number = Column(String(100), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    
    # Version tracking
    version = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    previous_version_id = Column(UUID(as_uuid=True), ForeignKey("amendments.id"), nullable=True)  # Self-reference
    
    # Validation session references
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False)
    previous_validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=True)
    
    # Status
    status = Column(
        String(20),
        nullable=False,
        default=AmendmentStatus.PENDING.value,
        index=True
    )
    
    # Change tracking - JSONB diff of changes
    # Format: {"added_fields": [...], "removed_fields": [...], "modified_fields": [{"field": "...", "old": "...", "new": "..."}], ...}
    changes_diff = Column(JSONB, nullable=True)
    
    # Document changes - JSONB array of document-level changes
    document_changes = Column(JSONB, nullable=True, default=list)
    
    # Notes and metadata
    notes = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True, default=dict)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    company = relationship("Company")
    validation_session = relationship("ValidationSession", foreign_keys=[validation_session_id])
    previous_validation_session = relationship("ValidationSession", foreign_keys=[previous_validation_session_id])
    previous_version = relationship("Amendment", remote_side=[id], foreign_keys=[previous_version_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'archived')",
            name="ck_amendments_status"
        ),
    )

