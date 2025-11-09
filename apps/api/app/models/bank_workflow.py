"""
Bank workflow models for Approvals and Discrepancy Workflow.
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class ApprovalStatus(str, Enum):
    """Approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REOPENED = "reopened"


class ApprovalStage(str, Enum):
    """Approval stage enumeration."""
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    APPROVER = "approver"


class DiscrepancyWorkflowStatus(str, Enum):
    """Discrepancy workflow status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BankApproval(Base):
    """Bank Approval model - tracks approval workflow for validation sessions."""
    __tablename__ = "bank_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False, index=True)
    
    # Approval workflow
    current_stage = Column(String(20), nullable=False, default=ApprovalStage.ANALYST.value, index=True)
    status = Column(
        String(20),
        nullable=False,
        default=ApprovalStatus.PENDING.value,
        index=True
    )
    
    # Assignees per stage
    analyst_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Current assignee
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Decision tracking
    decision = Column(String(20), nullable=True)  # "approve", "reject", null
    decision_reason = Column(Text, nullable=True)
    decided_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    
    # Re-open tracking
    reopened_count = Column(Integer, default=0, nullable=False)
    reopened_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    reopened_reason = Column(Text, nullable=True)
    
    # Metadata
    priority = Column(String(20), default="normal", nullable=False)  # "low", "normal", "high", "urgent"
    metadata = Column(JSONB, nullable=True, default=dict)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    validation_session = relationship("ValidationSession")
    analyst = relationship("User", foreign_keys=[analyst_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    approver = relationship("User", foreign_keys=[approver_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    reopened_by = relationship("User", foreign_keys=[reopened_by_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'reopened')",
            name="ck_bank_approvals_status"
        ),
        CheckConstraint(
            "current_stage IN ('analyst', 'reviewer', 'approver')",
            name="ck_bank_approvals_stage"
        ),
    )


class DiscrepancyWorkflow(Base):
    """Discrepancy Workflow model - tracks assignment, status, and resolution of discrepancies."""
    __tablename__ = "discrepancy_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discrepancy_id = Column(UUID(as_uuid=True), ForeignKey("discrepancies.id"), nullable=False, index=True)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False, index=True)
    
    # Workflow tracking
    status = Column(
        String(20),
        nullable=False,
        default=DiscrepancyWorkflowStatus.OPEN.value,
        index=True
    )
    
    # Assignment
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    assigned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Due date and SLA
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    sla_hours = Column(Integer, nullable=True)  # Expected resolution time in hours
    
    # Resolution tracking
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Comments and attachments - JSONB array
    # Format: [{"user_id": "uuid", "comment": "...", "created_at": "...", "attachments": [...]}, ...]
    comments = Column(JSONB, nullable=False, default=list)
    
    # Metadata
    priority = Column(String(20), default="normal", nullable=False)
    tags = Column(JSONB, nullable=True, default=list)  # Array of tags
    metadata = Column(JSONB, nullable=True, default=dict)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    discrepancy = relationship("Discrepancy")
    validation_session = relationship("ValidationSession")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_discrepancy_workflows_status"
        ),
    )

