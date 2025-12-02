"""
Member Management API - RBAC endpoints for team management

This module provides:
- GET /members - List all members in the user's company
- POST /members/invite - Send invitation to join company
- PUT /members/:id/role - Update member's role
- DELETE /members/:id - Remove member from company
- GET /me/permissions - Get current user's role and permissions
- POST /invitations/:token/accept - Accept an invitation
- DELETE /invitations/:id - Cancel an invitation
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
import secrets

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import User
from app.models.rbac import (
    CompanyMember,
    CompanyInvitation,
    MemberRole,
    MemberStatus,
    InvitationStatus,
    DEFAULT_TOOL_ACCESS,
    get_role_permissions,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/members", tags=["members"])


# ─────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────

class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str
    role: str
    tool_access: List[str]
    status: str
    joined_at: Optional[str]
    is_owner: bool
    is_admin: bool
    
    class Config:
        from_attributes = True


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"
    tool_access: List[str] = []
    message: Optional[str] = None


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    tool_access: List[str]
    status: str
    expires_at: str
    invited_by_name: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class UpdateRoleRequest(BaseModel):
    role: str
    tool_access: Optional[List[str]] = None


class PermissionsResponse(BaseModel):
    user_id: str
    company_id: str
    role: str
    tool_access: List[str]
    permissions: dict
    is_owner: bool
    is_admin: bool
    can_manage_team: bool
    can_view_billing: bool
    can_manage_billing: bool


class AcceptInvitationRequest(BaseModel):
    token: str


# ─────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────

def get_member_or_403(user: User, db: Session) -> CompanyMember:
    """Get the current user's company membership or raise 403"""
    if not user.company_id:
        raise HTTPException(status_code=403, detail="User does not belong to a company")
    
    member = db.query(CompanyMember).filter(
        and_(
            CompanyMember.user_id == user.id,
            CompanyMember.company_id == user.company_id,
            CompanyMember.status == MemberStatus.ACTIVE.value
        )
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="User is not an active member of this company")
    
    return member


def require_admin(member: CompanyMember):
    """Raise 403 if member is not owner or admin"""
    if not member.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="You must be an owner or admin to perform this action"
        )


def require_owner(member: CompanyMember):
    """Raise 403 if member is not owner"""
    if not member.is_owner:
        raise HTTPException(
            status_code=403, 
            detail="Only the owner can perform this action"
        )


# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[MemberResponse])
async def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all members in the current user's company.
    Requires: Active membership in a company
    """
    member = get_member_or_403(current_user, db)
    
    # Get all members of the company
    members = db.query(CompanyMember).filter(
        and_(
            CompanyMember.company_id == member.company_id,
            CompanyMember.status.in_([MemberStatus.ACTIVE.value, MemberStatus.PENDING.value])
        )
    ).all()
    
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            result.append(MemberResponse(
                id=str(m.id),
                user_id=str(m.user_id),
                email=user.email,
                full_name=user.full_name or user.email.split("@")[0],
                role=m.role,
                tool_access=m.tool_access or [],
                status=m.status,
                joined_at=m.joined_at.isoformat() if m.joined_at else None,
                is_owner=m.is_owner,
                is_admin=m.is_admin,
            ))
    
    return result


@router.post("/invite", response_model=InvitationResponse)
async def invite_member(
    request: InviteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send an invitation to join the company.
    Requires: Owner or Admin role
    """
    member = get_member_or_403(current_user, db)
    require_admin(member)
    
    # Validate role
    if request.role not in [MemberRole.ADMIN.value, MemberRole.MEMBER.value, MemberRole.VIEWER.value]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, member, or viewer")
    
    # Check if user already exists in the company
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        existing_member = db.query(CompanyMember).filter(
            and_(
                CompanyMember.user_id == existing_user.id,
                CompanyMember.company_id == member.company_id
            )
        ).first()
        if existing_member and existing_member.status == MemberStatus.ACTIVE.value:
            raise HTTPException(status_code=400, detail="User is already a member of this company")
    
    # Check for existing pending invitation
    existing_invitation = db.query(CompanyInvitation).filter(
        and_(
            CompanyInvitation.email == request.email,
            CompanyInvitation.company_id == member.company_id,
            CompanyInvitation.status == InvitationStatus.PENDING.value
        )
    ).first()
    if existing_invitation:
        raise HTTPException(status_code=400, detail="An invitation has already been sent to this email")
    
    # Determine tool access
    tool_access = request.tool_access if request.tool_access else DEFAULT_TOOL_ACCESS.get(
        MemberRole(request.role), []
    )
    
    # Create invitation
    invitation = CompanyInvitation(
        company_id=member.company_id,
        email=request.email,
        role=request.role,
        tool_access=tool_access,
        invited_by=current_user.id,
        token=CompanyInvitation.generate_token(),
        message=request.message,
        expires_at=CompanyInvitation.default_expiry(days=7),
        status=InvitationStatus.PENDING.value,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # TODO: Send invitation email in background
    # background_tasks.add_task(send_invitation_email, invitation, current_user)
    
    return InvitationResponse(
        id=str(invitation.id),
        email=invitation.email,
        role=invitation.role,
        tool_access=invitation.tool_access or [],
        status=invitation.status,
        expires_at=invitation.expires_at.isoformat(),
        invited_by_name=current_user.full_name,
        created_at=invitation.created_at.isoformat(),
    )


@router.get("/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all pending invitations for the company.
    Requires: Owner or Admin role
    """
    member = get_member_or_403(current_user, db)
    require_admin(member)
    
    invitations = db.query(CompanyInvitation).filter(
        and_(
            CompanyInvitation.company_id == member.company_id,
            CompanyInvitation.status == InvitationStatus.PENDING.value
        )
    ).all()
    
    result = []
    for inv in invitations:
        inviter = db.query(User).filter(User.id == inv.invited_by).first() if inv.invited_by else None
        result.append(InvitationResponse(
            id=str(inv.id),
            email=inv.email,
            role=inv.role,
            tool_access=inv.tool_access or [],
            status=inv.status,
            expires_at=inv.expires_at.isoformat(),
            invited_by_name=inviter.full_name if inviter else None,
            created_at=inv.created_at.isoformat(),
        ))
    
    return result


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a pending invitation.
    Requires: Owner or Admin role
    """
    member = get_member_or_403(current_user, db)
    require_admin(member)
    
    invitation = db.query(CompanyInvitation).filter(
        and_(
            CompanyInvitation.id == invitation_id,
            CompanyInvitation.company_id == member.company_id
        )
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    invitation.status = InvitationStatus.CANCELLED.value
    db.commit()
    
    return {"message": "Invitation cancelled"}


@router.put("/{member_id}/role")
async def update_member_role(
    member_id: UUID,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a member's role or tool access.
    Requires: Owner role (for role changes), Admin role (for tool access)
    """
    actor = get_member_or_403(current_user, db)
    
    # Get target member
    target = db.query(CompanyMember).filter(
        and_(
            CompanyMember.id == member_id,
            CompanyMember.company_id == actor.company_id
        )
    ).first()
    
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot modify the owner's role
    if target.is_owner and request.role != MemberRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Cannot change owner's role")
    
    # Only owner can change roles
    if request.role != target.role:
        require_owner(actor)
        
        # Validate new role
        if request.role not in [r.value for r in MemberRole]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        target.role = request.role
    
    # Admin can change tool access
    if request.tool_access is not None:
        require_admin(actor)
        target.tool_access = request.tool_access
    
    target.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Member updated", "role": target.role, "tool_access": target.tool_access}


@router.delete("/{member_id}")
async def remove_member(
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a member from the company.
    Requires: Owner or Admin role (cannot remove owner)
    """
    actor = get_member_or_403(current_user, db)
    require_admin(actor)
    
    # Get target member
    target = db.query(CompanyMember).filter(
        and_(
            CompanyMember.id == member_id,
            CompanyMember.company_id == actor.company_id
        )
    ).first()
    
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot remove the owner
    if target.is_owner:
        raise HTTPException(status_code=403, detail="Cannot remove the owner")
    
    # Cannot remove yourself
    if target.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself. Leave the company instead.")
    
    # Admin cannot remove other admins (only owner can)
    if target.role == MemberRole.ADMIN.value and not actor.is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can remove admins")
    
    target.status = MemberStatus.REMOVED.value
    target.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Member removed"}


@router.get("/me/permissions", response_model=PermissionsResponse)
async def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current user's role and permissions in their company.
    Returns all permission flags for frontend use.
    """
    member = get_member_or_403(current_user, db)
    
    return PermissionsResponse(
        user_id=str(current_user.id),
        company_id=str(member.company_id),
        role=member.role,
        tool_access=member.tool_access or [],
        permissions=get_role_permissions(member.role),
        is_owner=member.is_owner,
        is_admin=member.is_admin,
        can_manage_team=member.can_manage_team,
        can_view_billing=member.can_view_billing,
        can_manage_billing=member.can_manage_billing,
    )


@router.get("/me/tools")
async def get_my_tools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the list of tools the current user can access.
    """
    member = get_member_or_403(current_user, db)
    
    # Owner/Admin can access all tools
    if member.is_admin:
        all_tools = ["lcopilot", "price_verify", "hscode", "sanctions", "container_track"]
        return {
            "tools": all_tools,
            "role": member.role,
        }
    
    return {
        "tools": member.tool_access or [],
        "role": member.role,
    }


# ─────────────────────────────────────────────────────────────
# Invitation Acceptance (Public)
# ─────────────────────────────────────────────────────────────

@router.post("/accept-invitation")
async def accept_invitation(
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept an invitation and join a company.
    The invitation email must match the logged-in user's email.
    """
    invitation = db.query(CompanyInvitation).filter(
        CompanyInvitation.token == request.token
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if not invitation.is_valid:
        if invitation.is_expired:
            raise HTTPException(status_code=400, detail="Invitation has expired")
        raise HTTPException(status_code=400, detail="Invitation is no longer valid")
    
    # Email must match
    if invitation.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=403, 
            detail="This invitation was sent to a different email address"
        )
    
    # Check if already a member
    existing = db.query(CompanyMember).filter(
        and_(
            CompanyMember.user_id == current_user.id,
            CompanyMember.company_id == invitation.company_id
        )
    ).first()
    
    if existing and existing.status == MemberStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="You are already a member of this company")
    
    # Create or reactivate membership
    if existing:
        existing.status = MemberStatus.ACTIVE.value
        existing.role = invitation.role
        existing.tool_access = invitation.tool_access
        existing.joined_at = datetime.utcnow()
        member = existing
    else:
        member = CompanyMember(
            company_id=invitation.company_id,
            user_id=current_user.id,
            role=invitation.role,
            tool_access=invitation.tool_access,
            invited_by=invitation.invited_by,
            invited_at=invitation.created_at,
            joined_at=datetime.utcnow(),
            status=MemberStatus.ACTIVE.value,
        )
        db.add(member)
    
    # Update user's company_id
    current_user.company_id = invitation.company_id
    
    # Mark invitation as accepted
    invitation.status = InvitationStatus.ACCEPTED.value
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Successfully joined the company",
        "company_id": str(invitation.company_id),
        "role": member.role,
    }


# ─────────────────────────────────────────────────────────────
# Admin: Seed Initial Members (One-time setup)
# ─────────────────────────────────────────────────────────────

@router.post("/admin/seed-existing-users")
async def seed_existing_users(
    secret: str = None,
    db: Session = Depends(get_db),
):
    """
    One-time admin endpoint to create company_members records for existing users.
    Makes each user the OWNER of their associated company.
    
    Requires: Secret key (from environment)
    """
    import os
    import traceback
    
    expected_secret = os.getenv("ADMIN_SEED_SECRET", "trdr-seed-2024")
    
    if secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    try:
        # First check if table exists
        from sqlalchemy import text
        try:
            db.execute(text("SELECT 1 FROM company_members LIMIT 1"))
        except Exception as table_err:
            return {
                "error": "Table does not exist",
                "detail": "company_members table not found. Migration may not have run yet.",
                "hint": "Check Render deploy logs for migration errors",
                "raw_error": str(table_err)
            }
        
        # Get all users with company_id who don't have a member record
        users_without_membership = db.query(User).filter(
            User.company_id.isnot(None),
            User.is_active == True
        ).all()
        
        created = 0
        skipped = 0
        errors = []
        
        for user in users_without_membership:
            try:
                # Check if member record already exists
                existing = db.query(CompanyMember).filter(
                    CompanyMember.user_id == user.id,
                    CompanyMember.company_id == user.company_id
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Determine role based on user's role field
                if user.role in ["system_admin", "admin", "tenant_admin"]:
                    member_role = MemberRole.OWNER.value
                elif user.role in ["bank_admin"]:
                    member_role = MemberRole.ADMIN.value
                else:
                    # First user in company becomes owner
                    existing_members = db.query(CompanyMember).filter(
                        CompanyMember.company_id == user.company_id,
                        CompanyMember.role == MemberRole.OWNER.value
                    ).first()
                    
                    member_role = MemberRole.MEMBER.value if existing_members else MemberRole.OWNER.value
                
                # Create member record
                member = CompanyMember(
                    company_id=user.company_id,
                    user_id=user.id,
                    role=member_role,
                    tool_access=DEFAULT_TOOL_ACCESS.get(MemberRole(member_role), []),
                    joined_at=user.created_at or datetime.utcnow(),
                    status=MemberStatus.ACTIVE.value,
                )
                db.add(member)
                created += 1
            except Exception as user_err:
                errors.append(f"User {user.email}: {str(user_err)}")
        
        db.commit()
        
        return {
            "message": f"Seeded {created} member records, skipped {skipped} existing",
            "created": created,
            "skipped": skipped,
            "errors": errors if errors else None,
        }
    except Exception as e:
        return {
            "error": "Seed failed",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }

