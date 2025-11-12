"""
Admin API endpoints for user and role management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from app.models import User, UserRole
from ..core.security import get_current_user, require_admin
from ..core.rbac import RBACPolicyEngine, Permission, get_role_capabilities
from ..schemas.user import (
    UserRead, UserCreateAdmin, UserListQuery, UserListResponse,
    RoleUpdateRequest, RoleUpdateResponse, UserStats,
    RolePermissions, PermissionCheck, PermissionResult
)
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult


router = APIRouter(prefix="/admin", tags=["admin-users"])

# Include admin sub-routers
from .admin import ops, jobs, audit as admin_audit, dr, governance
from .admin.db_audit import router as db_audit_router

router.include_router(ops.router)
router.include_router(jobs.router)
router.include_router(admin_audit.router)
router.include_router(dr.router)
router.include_router(governance.router)
router.include_router(db_audit_router)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    query: UserListQuery = Depends(),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all users with filtering and pagination.

    Requires admin privileges.
    """
    # Build query
    base_query = db.query(User)

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
    import math
    pages = math.ceil(total / query.per_page)
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


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get user details by ID.

    Requires admin privileges.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserRead.from_orm(user)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateAdmin,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only).

    Requires admin privileges.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    from ..core.security import hash_password

    # Create user
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
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
            "created_user_role": new_user.role
        }
    )

    return UserRead.from_orm(new_user)


@router.put("/users/{user_id}/role", response_model=RoleUpdateResponse)
async def update_user_role(
    user_id: UUID,
    role_data: RoleUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user's role.

    Requires admin privileges.
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

    # Prevent admin from changing their own role (safety measure)
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
        action=AuditAction.ROLE_CHANGE,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "target_user_email": target_user.email,
            "old_role": old_role,
            "new_role": role_data.role,
            "reason": role_data.reason
        }
    )

    return RoleUpdateResponse(
        success=True,
        message=f"Role updated from {old_role} to {role_data.role}",
        user_id=target_user.id,
        old_role=old_role,
        new_role=role_data.role,
        updated_by=current_user.id,
        updated_at=datetime.utcnow()
    )


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    reason: Optional[str] = Query(None, max_length=500),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account.

    Requires admin privileges.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deactivating themselves
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    target_user.is_active = False
    target_user.updated_at = datetime.utcnow()

    db.commit()

    # Log deactivation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.DEACTIVATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "target_user_email": target_user.email,
            "reason": reason
        }
    )

    return {
        "success": True,
        "message": f"User {target_user.email} has been deactivated",
        "user_id": target_user.id
    }


@router.put("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: UUID,
    reason: Optional[str] = Query(None, max_length=500),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reactivate a user account.

    Requires admin privileges.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    target_user.is_active = True
    target_user.updated_at = datetime.utcnow()

    db.commit()

    # Log reactivation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.REACTIVATE_USER,
        user=current_user,
        resource_type="user",
        resource_id=str(target_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "target_user_email": target_user.email,
            "reason": reason
        }
    )

    return {
        "success": True,
        "message": f"User {target_user.email} has been reactivated",
        "user_id": target_user.id
    }


@router.get("/users/stats", response_model=UserStats)
async def get_user_statistics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get user statistics for admin dashboard.

    Requires admin privileges.
    """
    from datetime import timedelta

    # Total users
    total_users = db.query(func.count(User.id)).scalar()

    # Active users
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()

    # Users by role
    role_counts = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    users_by_role = {role: count for role, count in role_counts}

    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.query(func.count(User.id)).filter(
        User.created_at >= thirty_days_ago
    ).scalar()

    # Recent role changes (from audit log)
    audit_service = AuditService(db)
    recent_role_changes = len(audit_service.get_recent_actions(
        action=AuditAction.ROLE_CHANGE,
        days=30
    ))

    return UserStats(
        total_users=total_users,
        active_users=active_users,
        users_by_role=users_by_role,
        recent_registrations=recent_registrations,
        recent_role_changes=recent_role_changes
    )


@router.get("/roles/permissions", response_model=List[RolePermissions])
async def get_role_permissions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get permissions matrix for all roles.

    Requires admin privileges.
    """
    capabilities = get_role_capabilities()

    role_permissions = []
    for role_name, permissions in capabilities.items():
        role_permissions.append(RolePermissions(
            role=role_name,
            permissions=permissions,
            description=_get_role_description(role_name)
        ))

    return role_permissions


@router.post("/permissions/check", response_model=PermissionResult)
async def check_permission(
    permission_check: PermissionCheck,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Check if current user has specific permission.

    Requires admin privileges.
    """
    # This is a utility endpoint for testing permissions
    # Map common action names to Permission enum values
    permission_mapping = {
        "upload_docs": Permission.UPLOAD_OWN_DOCS,
        "view_all_jobs": Permission.VIEW_ALL_JOBS,
        "view_own_jobs": Permission.VIEW_OWN_JOBS,
        "admin_access": Permission.ADMIN_ACCESS,
        "manage_roles": Permission.MANAGE_ROLES,
        "view_audit_logs": Permission.VIEW_ALL_AUDIT_LOGS,
        "system_monitoring": Permission.SYSTEM_MONITORING
    }

    permission_enum = permission_mapping.get(permission_check.action)
    if not permission_enum:
        return PermissionResult(
            allowed=False,
            reason=f"Unknown permission: {permission_check.action}",
            user_role=current_user.role
        )

    allowed = RBACPolicyEngine.has_permission(current_user.role, permission_enum)

    return PermissionResult(
        allowed=allowed,
        reason="Permission granted" if allowed else "Permission denied",
        user_role=current_user.role
    )


def _get_role_description(role: str) -> str:
    """Get human-readable description for role."""
    descriptions = {
        "exporter": "Can upload documents, create sessions, and view own data",
        "importer": "Can upload documents, create sessions, and view own data",
        "bank": "Can view all transactions, audit logs, and generate compliance reports",
        "admin": "Full system access including user management and system configuration"
    }
    return descriptions.get(role, "Unknown role")
