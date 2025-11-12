"""
Admin authentication and authorization utilities.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .security import get_current_user
from ..models import User, UserRole
from ..database import get_db


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require system admin or tenant admin role."""
    if not (current_user.is_system_admin() or current_user.is_tenant_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_permissions(required_permissions: list[str]):
    """
    Dependency factory for requiring specific permissions.
    
    Usage:
        _: None = Depends(require_permissions(["jobs:read", "jobs:write"]))
    """
    def permission_checker(
        current_user: User = Depends(get_current_admin_user)
    ) -> None:
        """Check if user has required permissions."""
        # For now, system admins have all permissions
        if current_user.is_system_admin():
            return None
        
        # TODO: Implement actual permission checking against user's role/permissions
        # For now, just check if user is admin
        if not current_user.is_tenant_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(required_permissions)}"
            )
        return None
    
    return permission_checker

