"""
API endpoints for workspace sharing and team management.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, UserRole
from ..models.sme_workspace import LCWorkspace
from ..models.workspace_sharing import WorkspaceMember, WorkspaceInvitation, WorkspaceRole
from ..schemas.workspace_sharing import (
    WorkspaceMemberCreate, WorkspaceMemberUpdate, WorkspaceMemberRead, WorkspaceMemberListResponse,
    WorkspaceInvitationCreate, WorkspaceInvitationRead, WorkspaceInvitationListResponse,
    WorkspaceShareRequest
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sme/workspaces", tags=["sme-workspace-sharing"])


def require_sme_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an SME (exporter or importer)."""
    if current_user.role not in [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for SME users (exporter/importer)"
        )
    return current_user


def require_workspace_access(
    workspace_id: UUID,
    required_role: Optional[WorkspaceRole] = None,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
) -> tuple[LCWorkspace, Optional[WorkspaceMember]]:
    """
    Check if user has access to workspace and return workspace + member record.
    
    Args:
        workspace_id: Workspace ID
        required_role: Minimum role required (None = any access)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Tuple of (workspace, member_record)
    """
    workspace = db.query(LCWorkspace).filter(
        and_(
            LCWorkspace.id == workspace_id,
            LCWorkspace.deleted_at.is_(None)
        )
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check if user is workspace owner (creator)
    is_owner = workspace.user_id == current_user.id
    
    # Check if user is a member
    member = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.is_active == True,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).first()
    
    # If not owner and not member, deny access
    if not is_owner and not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace"
        )
    
    # Check role requirement
    if required_role:
        if is_owner:
            # Owner always has access
            pass
        elif member:
            role_hierarchy = {
                WorkspaceRole.OWNER: 4,
                WorkspaceRole.EDITOR: 3,
                WorkspaceRole.VIEWER: 2,
                WorkspaceRole.AUDITOR: 1,
            }
            member_role_level = role_hierarchy.get(WorkspaceRole(member.role), 0)
            required_role_level = role_hierarchy.get(required_role, 0)
            
            if member_role_level < required_role_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This action requires {required_role.value} role or higher"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return workspace, member


@router.get("/{workspace_id}/members", response_model=WorkspaceMemberListResponse)
async def list_workspace_members(
    workspace_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List all members of a workspace."""
    workspace, member = require_workspace_access(workspace_id, None, current_user, db)
    
    # Get all active members
    members = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).all()
    
    # Include workspace owner
    owner_member = WorkspaceMember(
        id=UUID('00000000-0000-0000-0000-000000000000'),  # Placeholder ID
        workspace_id=workspace_id,
        user_id=workspace.user_id,
        role=WorkspaceRole.OWNER.value,
        is_active=True,
        invited_at=workspace.created_at,
        accepted_at=workspace.created_at,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at
    )
    
    # Combine owner and members
    all_members = [owner_member] + members
    
    # Populate user details
    member_reads = []
    for m in all_members:
        user = db.query(User).filter(User.id == m.user_id).first()
        member_read = WorkspaceMemberRead.model_validate(m)
        if user:
            member_read.user_email = user.email
            member_read.user_name = user.full_name or user.username
        member_reads.append(member_read)
    
    return WorkspaceMemberListResponse(
        items=member_reads,
        total=len(member_reads)
    )


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberRead, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: UUID,
    member_data: WorkspaceMemberCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Add a member to a workspace (requires owner or editor role)."""
    workspace, member = require_workspace_access(
        workspace_id, 
        WorkspaceRole.EDITOR, 
        current_user, 
        db
    )
    
    # Check if user is already a member
    existing_member = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == member_data.user_id,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace"
        )
    
    # Check if trying to add workspace owner
    if member_data.user_id == workspace.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace owner is already a member"
        )
    
    # Create member record
    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=member_data.user_id,
        company_id=member_data.company_id or workspace.company_id,
        role=member_data.role.value,
        invited_by=current_user.id,
        is_active=True
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    # Populate user details
    user = db.query(User).filter(User.id == new_member.user_id).first()
    member_read = WorkspaceMemberRead.model_validate(new_member)
    if user:
        member_read.user_email = user.email
        member_read.user_name = user.full_name or user.username
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.CREATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_member",
        resource_id=str(new_member.id),
        details={
            "workspace_id": str(workspace_id),
            "user_id": str(member_data.user_id),
            "role": member_data.role.value
        },
        result=AuditResult.SUCCESS
    )
    
    return member_read


@router.put("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberRead)
async def update_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    member_data: WorkspaceMemberUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update a member's role (requires owner role)."""
    workspace, member = require_workspace_access(
        workspace_id,
        WorkspaceRole.OWNER,
        current_user,
        db
    )
    
    # Find the member to update
    target_member = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Cannot change owner's role
    if target_member.user_id == workspace.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change workspace owner's role"
        )
    
    # Update role
    target_member.role = member_data.role.value
    target_member.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(target_member)
    
    # Populate user details
    user = db.query(User).filter(User.id == target_member.user_id).first()
    member_read = WorkspaceMemberRead.model_validate(target_member)
    if user:
        member_read.user_email = user.email
        member_read.user_name = user.full_name or user.username
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_member",
        resource_id=str(member_id),
        details={
            "workspace_id": str(workspace_id),
            "role": member_data.role.value
        },
        result=AuditResult.SUCCESS
    )
    
    return member_read


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Remove a member from a workspace (requires owner or editor role)."""
    workspace, member = require_workspace_access(
        workspace_id,
        WorkspaceRole.EDITOR,
        current_user,
        db
    )
    
    # Find the member to remove
    target_member = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Cannot remove workspace owner
    if target_member.user_id == workspace.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove workspace owner"
        )
    
    # Soft delete
    target_member.deleted_at = datetime.utcnow()
    target_member.is_active = False
    db.commit()
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_member",
        resource_id=str(member_id),
        details={
            "workspace_id": str(workspace_id),
            "user_id": str(target_member.user_id)
        },
        result=AuditResult.SUCCESS
    )


@router.post("/{workspace_id}/invite", response_model=WorkspaceInvitationRead, status_code=status.HTTP_201_CREATED)
async def invite_to_workspace(
    workspace_id: UUID,
    invitation_data: WorkspaceShareRequest,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Invite a user to join a workspace via email (requires owner or editor role)."""
    workspace, member = require_workspace_access(
        workspace_id,
        WorkspaceRole.EDITOR,
        current_user,
        db
    )
    
    # Check if user with this email already exists and is a member
    existing_user = db.query(User).filter(User.email == invitation_data.email).first()
    if existing_user:
        existing_member = db.query(WorkspaceMember).filter(
            and_(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == existing_user.id,
                WorkspaceMember.deleted_at.is_(None)
            )
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this workspace"
            )
    
    # Check for existing pending invitation
    existing_invitation = db.query(WorkspaceInvitation).filter(
        and_(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.email == invitation_data.email,
            WorkspaceInvitation.status == "pending",
            WorkspaceInvitation.expires_at > datetime.utcnow()
        )
    ).first()
    
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active invitation already exists for this email"
        )
    
    # Generate invitation token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)  # Default 7 days
    
    # Create invitation
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=invitation_data.email,
        role=invitation_data.role.value,
        invited_by=current_user.id,
        token=token,
        expires_at=expires_at,
        status="pending"
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # TODO: Send invitation email with token link
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.CREATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_invitation",
        resource_id=str(invitation.id),
        details={
            "workspace_id": str(workspace_id),
            "email": invitation_data.email,
            "role": invitation_data.role.value
        },
        result=AuditResult.SUCCESS
    )
    
    return WorkspaceInvitationRead.model_validate(invitation)


@router.get("/{workspace_id}/invitations", response_model=WorkspaceInvitationListResponse)
async def list_workspace_invitations(
    workspace_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, accepted, expired, cancelled"),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List invitations for a workspace (requires owner or editor role)."""
    workspace, member = require_workspace_access(
        workspace_id,
        WorkspaceRole.EDITOR,
        current_user,
        db
    )
    
    query = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.workspace_id == workspace_id
    )
    
    if status_filter:
        query = query.filter(WorkspaceInvitation.status == status_filter)
    
    invitations = query.order_by(WorkspaceInvitation.created_at.desc()).all()
    
    return WorkspaceInvitationListResponse(
        items=[WorkspaceInvitationRead.model_validate(inv) for inv in invitations],
        total=len(invitations)
    )


@router.post("/invitations/{invitation_id}/accept", response_model=WorkspaceMemberRead)
async def accept_invitation(
    invitation_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Accept a workspace invitation."""
    invitation = db.query(WorkspaceInvitation).filter(
        and_(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.email == current_user.email,
            WorkspaceInvitation.status == "pending"
        )
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already accepted"
        )
    
    # Check if invitation expired
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check if user is already a member
    existing_member = db.query(WorkspaceMember).filter(
        and_(
            WorkspaceMember.workspace_id == invitation.workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.deleted_at.is_(None)
        )
    ).first()
    
    if existing_member:
        # Mark invitation as accepted anyway
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this workspace"
        )
    
    # Create member record
    workspace = db.query(LCWorkspace).filter(LCWorkspace.id == invitation.workspace_id).first()
    new_member = WorkspaceMember(
        workspace_id=invitation.workspace_id,
        user_id=current_user.id,
        company_id=workspace.company_id if workspace else None,
        role=invitation.role,
        invited_by=invitation.invited_by,
        is_active=True,
        accepted_at=datetime.utcnow()
    )
    db.add(new_member)
    
    # Mark invitation as accepted
    invitation.status = "accepted"
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_member)
    
    # Populate user details
    member_read = WorkspaceMemberRead.model_validate(new_member)
    member_read.user_email = current_user.email
    member_read.user_name = current_user.full_name or current_user.username
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_invitation",
        resource_id=str(invitation_id),
        details={
            "action": "accept",
            "workspace_id": str(invitation.workspace_id)
        },
        result=AuditResult.SUCCESS
    )
    
    return member_read


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Cancel a workspace invitation (requires owner or editor role)."""
    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.id == invitation_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check access
    workspace, member = require_workspace_access(
        invitation.workspace_id,
        WorkspaceRole.EDITOR,
        current_user,
        db
    )
    
    # Cancel invitation
    invitation.status = "cancelled"
    invitation.updated_at = datetime.utcnow()
    db.commit()
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="workspace_invitation",
        resource_id=str(invitation_id),
        details={
            "workspace_id": str(invitation.workspace_id),
            "email": invitation.email
        },
        result=AuditResult.SUCCESS
    )

