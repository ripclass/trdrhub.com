"""
Pydantic schemas for workspace sharing and team management.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr

from ..models.workspace_sharing import WorkspaceRole


class WorkspaceMemberBase(BaseModel):
    """Base schema for workspace member."""
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberCreate(WorkspaceMemberBase):
    """Schema for adding a member to a workspace."""
    user_id: UUID
    company_id: Optional[UUID] = None


class WorkspaceMemberUpdate(BaseModel):
    """Schema for updating a member's role."""
    role: WorkspaceRole


class WorkspaceMemberRead(WorkspaceMemberBase):
    """Schema for reading a workspace member."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    company_id: Optional[UUID] = None
    invited_by: Optional[UUID] = None
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # User details (populated from relationship)
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class WorkspaceMemberListResponse(BaseModel):
    """Response schema for listing workspace members."""
    items: List[WorkspaceMemberRead]
    total: int


class WorkspaceInvitationCreate(BaseModel):
    """Schema for creating a workspace invitation."""
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.VIEWER
    expires_in_days: int = Field(7, ge=1, le=30)  # Invitation expires in N days


class WorkspaceInvitationRead(BaseModel):
    """Schema for reading a workspace invitation."""
    id: UUID
    workspace_id: UUID
    email: str
    role: WorkspaceRole
    invited_by: UUID
    token: str
    expires_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkspaceInvitationListResponse(BaseModel):
    """Response schema for listing workspace invitations."""
    items: List[WorkspaceInvitationRead]
    total: int


class WorkspaceShareRequest(BaseModel):
    """Request to share a workspace with a user."""
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.VIEWER
    message: Optional[str] = None  # Optional invitation message

