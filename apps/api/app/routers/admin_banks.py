"""
Admin Bank Management API - Endpoints for managing bank accounts (invite-only)

This module provides:
- GET /admin/banks - List all bank companies
- POST /admin/banks - Create a new bank company and owner account
- GET /admin/banks/:id - Get bank details
- PUT /admin/banks/:id - Update bank details
- POST /admin/banks/:id/invite - Invite additional bank users
- DELETE /admin/banks/:id - Deactivate a bank
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
import secrets
import os

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import User, Company
from app.models.rbac import (
    CompanyMember,
    CompanyInvitation,
    MemberRole,
    MemberStatus,
    InvitationStatus,
    DEFAULT_TOOL_ACCESS,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin/banks", tags=["admin-banks"])


# ─────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────

class CreateBankRequest(BaseModel):
    """Request to create a new bank company"""
    bank_name: str
    legal_name: Optional[str] = None
    country: str
    contact_email: EmailStr
    contact_name: str
    regulator_id: Optional[str] = None
    # Initial owner account
    owner_email: EmailStr
    owner_name: str
    owner_password: Optional[str] = None  # If not provided, send invite


class BankUserInviteRequest(BaseModel):
    """Request to invite a user to a bank"""
    email: EmailStr
    name: str
    role: str = "bank_officer"  # bank_officer, bank_admin
    message: Optional[str] = None


class UpdateBankRequest(BaseModel):
    """Request to update bank details"""
    bank_name: Optional[str] = None
    legal_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    regulator_id: Optional[str] = None
    status: Optional[str] = None  # active, suspended


class BankResponse(BaseModel):
    id: str
    name: str
    legal_name: Optional[str]
    type: str
    country: Optional[str]
    contact_email: Optional[str]
    regulator_id: Optional[str]
    status: str
    created_at: str
    user_count: int
    
    class Config:
        from_attributes = True


class BankUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str
    joined_at: Optional[str]
    last_login: Optional[str]


# ─────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────

def require_system_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user is a system admin"""
    if current_user.role not in ["system_admin", "super_admin", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only system administrators can manage banks"
        )
    return current_user


def generate_temp_password() -> str:
    """Generate a temporary password for new users"""
    return secrets.token_urlsafe(12)


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("", response_model=List[BankResponse])
async def list_banks(
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """List all bank companies"""
    banks = db.query(Company).filter(
        Company.type == "bank"
    ).order_by(Company.created_at.desc()).all()
    
    result = []
    for bank in banks:
        user_count = db.query(User).filter(
            User.company_id == bank.id,
            User.is_active == True
        ).count()
        
        result.append(BankResponse(
            id=str(bank.id),
            name=bank.name,
            legal_name=bank.legal_name,
            type=bank.type or "bank",
            country=bank.country,
            contact_email=bank.contact_email,
            regulator_id=bank.regulator_id,
            status=bank.status.value if hasattr(bank.status, 'value') else str(bank.status) if bank.status else "active",
            created_at=bank.created_at.isoformat() if bank.created_at else "",
            user_count=user_count,
        ))
    
    return result


@router.post("", response_model=dict)
async def create_bank(
    request: CreateBankRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """
    Create a new bank company and owner account.
    
    This creates:
    1. A new Company record with type="bank"
    2. A new User record for the bank owner
    3. A CompanyMember record linking them as owner
    """
    # Check if bank with same name exists
    existing = db.query(Company).filter(
        Company.name == request.bank_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A company named '{request.bank_name}' already exists"
        )
    
    # Check if owner email is already registered
    existing_user = db.query(User).filter(
        User.email == request.owner_email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"User with email '{request.owner_email}' already exists"
        )
    
    # Create the bank company
    bank = Company(
        name=request.bank_name,
        legal_name=request.legal_name or request.bank_name,
        type="bank",
        country=request.country,
        contact_email=request.contact_email,
        regulator_id=request.regulator_id,
    )
    db.add(bank)
    db.flush()  # Get the bank ID
    
    # Generate password if not provided
    temp_password = request.owner_password or generate_temp_password()
    
    # Hash the password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(temp_password)
    
    # Create the owner user
    owner = User(
        email=request.owner_email,
        full_name=request.owner_name,
        name=request.owner_name,
        hashed_password=hashed_password,
        role="bank_admin",
        company_id=bank.id,
        company_name=request.bank_name,
        is_active=True,
        onboarding_completed=True,
        onboarding_data={
            "role": "bank_admin",
            "company": {
                "name": request.bank_name,
                "type": "bank",
            },
            "complete": True,
        }
    )
    db.add(owner)
    db.flush()  # Get the owner ID
    
    # Create the company member record
    member = CompanyMember(
        company_id=bank.id,
        user_id=owner.id,
        role=MemberRole.OWNER.value,
        tool_access=["lcopilot", "price_verify"],  # Banks get full tool access
        joined_at=datetime.utcnow(),
        status=MemberStatus.ACTIVE.value,
    )
    db.add(member)
    
    db.commit()
    
    # TODO: Send welcome email with credentials
    # For now, return the temp password in response (for development)
    
    return {
        "success": True,
        "message": f"Bank '{request.bank_name}' created successfully",
        "bank_id": str(bank.id),
        "owner_id": str(owner.id),
        "owner_email": request.owner_email,
        "temp_password": temp_password if not request.owner_password else None,
        "note": "Please securely share the credentials with the bank contact"
    }


@router.get("/{bank_id}")
async def get_bank(
    bank_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """Get detailed information about a bank"""
    bank = db.query(Company).filter(
        Company.id == bank_id,
        Company.type == "bank"
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Get all users in this bank
    users = db.query(User).filter(
        User.company_id == bank_id,
        User.is_active == True
    ).all()
    
    user_list = []
    for user in users:
        member = db.query(CompanyMember).filter(
            CompanyMember.user_id == user.id,
            CompanyMember.company_id == bank_id
        ).first()
        
        user_list.append(BankUserResponse(
            id=str(user.id),
            email=user.email,
            name=user.full_name or user.name or "",
            role=user.role,
            status="active" if user.is_active else "inactive",
            joined_at=member.joined_at.isoformat() if member and member.joined_at else None,
            last_login=None,  # Would need to track this
        ))
    
    # Get pending invitations
    invitations = db.query(CompanyInvitation).filter(
        CompanyInvitation.company_id == bank_id,
        CompanyInvitation.status == InvitationStatus.PENDING.value
    ).all()
    
    pending_invites = [
        {
            "id": str(inv.id),
            "email": inv.email,
            "role": inv.role,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invitations
    ]
    
    return {
        "id": str(bank.id),
        "name": bank.name,
        "legal_name": bank.legal_name,
        "type": bank.type,
        "country": bank.country,
        "contact_email": bank.contact_email,
        "regulator_id": bank.regulator_id,
        "status": bank.status.value if hasattr(bank.status, 'value') else str(bank.status) if bank.status else "active",
        "created_at": bank.created_at.isoformat() if bank.created_at else "",
        "users": user_list,
        "pending_invitations": pending_invites,
    }


@router.put("/{bank_id}")
async def update_bank(
    bank_id: UUID,
    request: UpdateBankRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """Update bank details"""
    bank = db.query(Company).filter(
        Company.id == bank_id,
        Company.type == "bank"
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    if request.bank_name:
        bank.name = request.bank_name
    if request.legal_name:
        bank.legal_name = request.legal_name
    if request.contact_email:
        bank.contact_email = request.contact_email
    if request.regulator_id:
        bank.regulator_id = request.regulator_id
    
    db.commit()
    
    return {"success": True, "message": "Bank updated successfully"}


@router.post("/{bank_id}/invite")
async def invite_bank_user(
    bank_id: UUID,
    request: BankUserInviteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """
    Invite a new user to join the bank.
    Creates the user account immediately and sends credentials.
    """
    bank = db.query(Company).filter(
        Company.id == bank_id,
        Company.type == "bank"
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()
    
    if existing_user:
        # Check if already in this bank
        if existing_user.company_id == bank_id:
            raise HTTPException(
                status_code=400,
                detail="User is already a member of this bank"
            )
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists in another company"
        )
    
    # Validate role
    valid_roles = ["bank_officer", "bank_admin"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Generate temporary password
    temp_password = generate_temp_password()
    
    # Hash the password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(temp_password)
    
    # Create the user
    user = User(
        email=request.email,
        full_name=request.name,
        name=request.name,
        hashed_password=hashed_password,
        role=request.role,
        company_id=bank_id,
        company_name=bank.name,
        is_active=True,
        onboarding_completed=True,
        onboarding_data={
            "role": request.role,
            "company": {
                "name": bank.name,
                "type": "bank",
            },
            "complete": True,
        }
    )
    db.add(user)
    db.flush()
    
    # Determine member role based on user role
    member_role = MemberRole.ADMIN.value if request.role == "bank_admin" else MemberRole.MEMBER.value
    
    # Create company member record
    member = CompanyMember(
        company_id=bank_id,
        user_id=user.id,
        role=member_role,
        tool_access=["lcopilot", "price_verify"],
        invited_by=admin.id,
        invited_at=datetime.utcnow(),
        joined_at=datetime.utcnow(),
        status=MemberStatus.ACTIVE.value,
    )
    db.add(member)
    
    db.commit()
    
    # TODO: Send email with credentials
    
    return {
        "success": True,
        "message": f"User '{request.email}' added to {bank.name}",
        "user_id": str(user.id),
        "email": request.email,
        "temp_password": temp_password,
        "note": "Please securely share the credentials with the user"
    }


@router.delete("/{bank_id}")
async def deactivate_bank(
    bank_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_system_admin),
):
    """Deactivate a bank (soft delete)"""
    bank = db.query(Company).filter(
        Company.id == bank_id,
        Company.type == "bank"
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Deactivate all users in this bank
    db.query(User).filter(
        User.company_id == bank_id
    ).update({"is_active": False})
    
    # Update company status
    # Note: This depends on your Company model's status field type
    # bank.status = "suspended"
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bank '{bank.name}' has been deactivated"
    }

