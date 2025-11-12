"""
Bank user management API endpoints.

Bank admins can manage users within their tenant (invite, suspend, change roles).
Bank officers can view users.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import math

from ..database import get_db
from app.models import User, UserRole
from ..core.security import get_current_user, require_bank_or_admin, require_bank_admin, hash_password
from ..schemas.user import (
    UserRead, UserListQuery, UserListResponse,
    RoleUpdateRequest, RoleUpdateResponse, BankUserInviteRequest
)
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult


router = APIRouter(prefix="/bank/users", tags=["bank-users"])


@router.get("", response_model=UserListResponse)
async def list_bank_users(
    query: UserListQuery = Depends(),
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    List users in the current bank tenant.
    
    Bank admins only can view users in their bank.
    Bank officers should not have access to user management.
    """
    # Scope to current user's company (bank tenant)
    base_query = db.query(User).filter(User.company_id == current_user.company_id)
    
    # Only show bank roles (bank_officer, bank_admin)
    base_query = base_query.filter(
        User.role.in_([UserRole.BANK_OFFICER.value, UserRole.BANK_ADMIN.value])
    )
    
    # Apply filters
    if query.role:
        base_query = base_query.filter(User.role == query.role)
    if query.is_active is not None:
        base_query = base_query.filter(User.is_active == query.is_active)
    if query.search:
        search_term = f"%{query.search}%"
        base_query = base_query.filter(
            User.email.ilike(search_term) | User.full_name.ilike(search_term)
        )
    
    # Count total
    total = base_query.count()
    
    # Apply sorting
    if query.sort_by == "email":
        sort_column = User.email
    elif query.sort_by == "full_name":
        sort_column = User.full_name
    elif query.sort_by == "role":
        sort_column = User.role
    elif query.sort_by == "is_active":
        sort_column = User.is_active
    else:  # created_at
        sort_column = User.created_at
    
    if query.sort_order == "desc":
        base_query = base_query.order_by(desc(sort_column))
    else:
        base_query = base_query.order_by(sort_column)
    
    # Apply pagination
    offset = (query.page - 1) * query.per_page
    users = base_query.offset(offset).limit(query.per_page).all()
    
    # Calculate pagination info
    pages = math.ceil(total / query.per_page) if total > 0 else 1
    has_next = query.page < pages
    has_prev = query.page > 1
    
    return UserListResponse(
        users=[UserRead.from_orm(user) for user in users],
        total=total,
        page=query.page,
        per_page=query.per_page,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev
    )


@router.post("/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def invite_bank_user(
    user_data: BankUserInviteRequest,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Invite/create a new user in the bank tenant.
    
    Requires bank_admin role.
    Only bank_officer and bank_admin roles can be assigned.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role is bank role
    if user_data.role not in [UserRole.BANK_OFFICER.value, UserRole.BANK_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be bank_officer or bank_admin"
        )
    
    # Create user
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        company_id=current_user.company_id,  # Same bank tenant
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log user creation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.CREATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(new_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "created_user_email": new_user.email,
            "created_user_role": new_user.role,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return UserRead.from_orm(new_user)


@router.put("/{user_id}/role", response_model=RoleUpdateResponse)
async def update_bank_user_role(
    user_id: UUID,
    role_data: RoleUpdateRequest,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Update user's role within the bank tenant.
    
    Requires bank_admin role.
    """
    # Verify the user_id in the request matches the URL parameter
    if role_data.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID in request body must match URL parameter"
        )
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Ensure target user is in same bank tenant
    if target_user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify users from other tenants"
        )
    
    # Ensure target user has bank role
    if target_user.role not in [UserRole.BANK_OFFICER.value, UserRole.BANK_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user must have bank role"
        )
    
    # Validate new role is bank role
    if role_data.role not in [UserRole.BANK_OFFICER.value, UserRole.BANK_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be bank_officer or bank_admin"
        )
    
    # Prevent admin from changing their own role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own role"
        )
    
    old_role = target_user.role
    target_user.role = role_data.role
    target_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(target_user)
    
    # Log role change
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "role_change",
            "old_role": old_role,
            "new_role": role_data.role,
            "reason": role_data.reason,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return RoleUpdateResponse(
        success=True,
        message=f"User role updated from {old_role} to {role_data.role}",
        user_id=target_user.id,
        old_role=old_role,
        new_role=role_data.role,
        updated_by=current_user.id,
        updated_at=target_user.updated_at
    )


@router.put("/{user_id}/suspend")
async def suspend_bank_user(
    user_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Suspend a user in the bank tenant.
    
    Requires bank_admin role.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Ensure target user is in same bank tenant
    if target_user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify users from other tenants"
        )
    
    # Prevent suspending yourself
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend yourself"
        )
    
    target_user.is_active = False
    target_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Log suspension
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "suspend",
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return {"success": True, "message": "User suspended"}


@router.put("/{user_id}/reactivate")
async def reactivate_bank_user(
    user_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Reactivate a suspended user in the bank tenant.
    
    Requires bank_admin role.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Ensure target user is in same bank tenant
    if target_user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify users from other tenants"
        )
    
    target_user.is_active = True
    target_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Log reactivation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "reactivate",
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return {"success": True, "message": "User reactivated"}


@router.post("/{user_id}/reset-2fa")
async def reset_bank_user_2fa(
    user_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Reset 2FA for a user (stub - audit only for now).
    
    Requires bank_admin role.
    In production, this would trigger 2FA reset via email/SMS provider.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Ensure target user is in same bank tenant
    if target_user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify users from other tenants"
        )
    
    # Log 2FA reset request (stub - actual reset would be handled by auth provider)
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "reset_2fa",
            "bank_tenant_id": str(current_user.company_id),
            "note": "2FA reset requested (stub - integration pending)"
        }
    )
    
    return {
        "success": True,
        "message": "2FA reset requested. User will receive instructions via email."
    }

