"""
JWT authentication and role-based access control (RBAC) security layer.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Union
from uuid import UUID

import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult


# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user: User) -> dict:
    """
    Create JWT access token with user role.

    Args:
        user: User object from database

    Returns:
        Dictionary with token info
    """
    expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)
    expire_time = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user.id),  # Subject: user ID
        "role": user.role,    # User role for RBAC
        "email": user.email,  # Email for convenience
        "exp": expire_time,   # Expiration time
        "iat": datetime.utcnow()  # Issued at time
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(expires_delta.total_seconds()),
        "role": user.role
    }


def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token with role validation.

    This is the core dependency for authentication. It:
    1. Validates the JWT token
    2. Retrieves user from database
    3. Validates role matches between JWT and database
    4. Returns authenticated user

    Args:
        credentials: Bearer token from request
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Decode JWT token
    payload = decode_access_token(credentials.credentials)

    # Extract user info from token
    user_id = payload.get("sub")
    token_role = payload.get("role")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Get user from database
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Validate user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )

    # SECURITY: Validate role matches between JWT and database
    # This prevents role escalation attacks via token tampering
    if user.role != token_role:
        # Log potential security breach
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ACCESS_DENIED,
            user_id=user.id,
            user_email=user.email,
            result=AuditResult.FAILURE,
            error_message=f"JWT role mismatch: token={token_role}, db={user.role}",
            audit_metadata={
                "security_event": "jwt_role_mismatch",
                "token_role": token_role,
                "database_role": user.role
            }
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed"
        )

    return user


def require_roles(required_roles: List[str]):
    """
    Create a dependency that requires one of the specified roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_roles(["admin"]))):
            ...

    Args:
        required_roles: List of roles that can access the endpoint

    Returns:
        FastAPI dependency function
    """
    def role_dependency(user: User = Depends(get_current_user)):
        if user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return user

    return role_dependency


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin role.

    Args:
        user: Current authenticated user

    Returns:
        User if admin role

    Raises:
        HTTPException: 403 if not admin
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_bank_or_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require bank or admin role.

    Args:
        user: Current authenticated user

    Returns:
        User if bank or admin role

    Raises:
        HTTPException: 403 if not bank or admin
    """
    if user.role not in [UserRole.BANK, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank or admin access required"
        )
    return user


def ensure_owner_or_privileged(user: User, owner_id: Union[str, UUID]) -> bool:
    """
    Check if user can access a resource (owner or privileged role).

    This is a utility function for implementing owner-based access control
    with escalation privileges for bank and admin roles.

    Args:
        user: Current authenticated user
        owner_id: ID of the resource owner

    Returns:
        True if access allowed

    Raises:
        HTTPException: 403 if access denied
    """
    # Convert owner_id to string for comparison
    if isinstance(owner_id, UUID):
        owner_id = str(owner_id)

    # Admin and bank roles can access all resources
    if user.role in [UserRole.ADMIN, UserRole.BANK]:
        return True

    # Owner can access their own resources
    if str(user.id) == str(owner_id):
        return True

    # Access denied
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. You can only access your own resources."
    )


def check_permission(user: User, permission: str, resource_owner_id: Optional[Union[str, UUID]] = None) -> bool:
    """
    Check if user has a specific permission.

    This implements the permission matrix defined in the requirements.

    Args:
        user: Current authenticated user
        permission: Permission to check
        resource_owner_id: ID of resource owner (for owner-based permissions)

    Returns:
        True if permission granted
    """
    role = user.role

    # Permission matrix implementation
    permissions = {
        # Upload/validate own docs
        "upload_docs": [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.ADMIN],
        "validate_docs": [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.ADMIN],

        # View own jobs/results
        "view_own_jobs": [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.ADMIN],

        # View all jobs/results (system-wide)
        "view_all_jobs": [UserRole.BANK, UserRole.ADMIN],

        # Query audit logs (system-wide)
        "query_audit_logs": [UserRole.BANK, UserRole.ADMIN],

        # Download evidence packs
        "download_evidence": [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.BANK, UserRole.ADMIN],

        # Compliance reports (system-wide)
        "compliance_reports": [UserRole.BANK, UserRole.ADMIN],

        # Assign/modify user roles
        "manage_roles": [UserRole.ADMIN],

        # Admin functions
        "admin_access": [UserRole.ADMIN],

        # System monitoring
        "system_monitoring": [UserRole.BANK, UserRole.ADMIN],
    }

    # Check if role has permission
    allowed_roles = permissions.get(permission, [])

    if role not in allowed_roles:
        return False

    # For owner-based permissions, check ownership
    if permission in ["view_own_jobs", "download_evidence"] and resource_owner_id:
        # Privileged roles can access all resources
        if role in [UserRole.BANK, UserRole.ADMIN]:
            return True
        # Others can only access their own resources
        return str(user.id) == str(resource_owner_id)

    return True


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Authenticate user with email and password.

    Args:
        email: User email
        password: Plain text password
        db: Database session

    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# Permission decorators for convenience
def permission_required(permission: str):
    """
    Decorator to require specific permission.

    Usage:
        @permission_required("manage_roles")
        def some_endpoint(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = kwargs.get('user') or args[0]  # Assume user is first arg or in kwargs
            if not check_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Role-specific dependencies for common cases
def require_exporter_or_admin(user: User = Depends(get_current_user)) -> User:
    """Require exporter or admin role."""
    if user.role not in [UserRole.EXPORTER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Exporter or admin access required")
    return user


def require_importer_or_admin(user: User = Depends(get_current_user)) -> User:
    """Require importer or admin role."""
    if user.role not in [UserRole.IMPORTER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Importer or admin access required")
    return user


def require_any_trade_role(user: User = Depends(get_current_user)) -> User:
    """Require any trade role (exporter, importer, bank, admin)."""
    if user.role not in [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.BANK, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Trade role required")
    return user