"""
Workspace sharing models for SME team collaboration.
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class WorkspaceRole(str, Enum):
    """Workspace-level roles for team collaboration."""
    OWNER = "owner"  # Full control, can delete workspace, manage members
    EDITOR = "editor"  # Can edit workspace, upload documents, create drafts
    VIEWER = "viewer"  # Read-only access, can view workspace and results
    AUDITOR = "auditor"  # Read-only access for external auditors, can view audit trail


class WorkspaceMember(Base):
    """Workspace member model - tracks team members and their roles in LC workspaces."""
    __tablename__ = "workspace_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("lc_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    
    # Role in this workspace
    role = Column(
        String(20),
        nullable=False,
        default=WorkspaceRole.VIEWER.value,
        index=True
    )
    
    # Invitation tracking
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Access control
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace = relationship("LCWorkspace", backref="members")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])
    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
        CheckConstraint(
            "role IN ('owner', 'editor', 'viewer', 'auditor')",
            name="ck_workspace_member_role"
        ),
    )


class WorkspaceInvitation(Base):
    """Workspace invitation model - tracks pending invitations."""
    __tablename__ = "workspace_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("lc_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(
        String(20),
        nullable=False,
        default=WorkspaceRole.VIEWER.value
    )
    
    # Invitation details
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True, index=True)  # Unique invitation token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    status = Column(
        String(20),
        nullable=False,
        default="pending",  # pending, accepted, expired, cancelled
        index=True
    )
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace = relationship("LCWorkspace", backref="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'editor', 'viewer', 'auditor')",
            name="ck_workspace_invitation_role"
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'cancelled')",
            name="ck_workspace_invitation_status"
        ),
    )

