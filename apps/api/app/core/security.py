"""
JWT authentication and role-based access control (RBAC) security layer.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid5, NAMESPACE_URL

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User, UserRole
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult
from .jwt_verifier import ProviderConfig, verify_jwt


# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing (supports >72B passwords via pre-hash)
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer(auto_error=True)


_PROVIDER_CACHE: Optional[List[ProviderConfig]] = None


def _build_provider_configs() -> List[ProviderConfig]:
    global _PROVIDER_CACHE  # pylint: disable=global-statement
    if _PROVIDER_CACHE is not None:
        return _PROVIDER_CACHE

    providers: List[ProviderConfig] = []
    if settings.supabase_configured():
        providers.append(
            ProviderConfig(
                name="supabase",
                issuer=settings.SUPABASE_ISSUER or "",
                jwks_url=settings.SUPABASE_JWKS_URL or "",
                audience=settings.SUPABASE_AUDIENCE,
            )
        )
    if settings.auth0_configured():
        providers.append(
            ProviderConfig(
                name="auth0",
                issuer=settings.AUTH0_ISSUER or "",
                jwks_url=settings.AUTH0_JWKS_URL or "",
                audience=settings.AUTH0_AUDIENCE,
            )
        )

    _PROVIDER_CACHE = providers
    return providers


def _resolve_external_user_id(subject: str) -> UUID:
    """Convert external subject claim into UUID for local user table."""

    try:
        return UUID(subject)
    except (ValueError, TypeError):
        # Derive deterministic UUID5 so repeated logins map to same user
        return uuid5(NAMESPACE_URL, subject or "external-user")


def _normalise_role_claim(claims: Dict[str, Any]) -> str:
    role = (
        claims.get("role")
        or (claims.get("app_metadata") or {}).get("role")
        or (claims.get("user_metadata") or {}).get("role")
    )
    if role and str(role).lower() in {
        "exporter",
        "importer",
        "tenant_admin",
        "bank_officer",
        "bank_admin",
        "system_admin",
    }:
        return str(role).lower()
    return UserRole.EXPORTER.value


def _upsert_external_user(db: Session, claims: Dict[str, Any]) -> User:
    user_id = _resolve_external_user_id(str(claims.get("sub")))
    email = claims.get("email") or claims.get("preferred_username") or f"user-{user_id}@external"
    metadata = claims.get("user_metadata") or {}
    full_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or claims.get("name")
        or email
    )
    role_value = _normalise_role_claim(claims)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=email,
            full_name=full_name,
            role=role_value,
            hashed_password=hash_password("external-auth"),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.email = email
        if full_name:
            user.full_name = full_name
        if role_value:
            user.role = role_value
        user.is_active = True

    return user


async def _authenticate_external_token(token: str, db: Session) -> Optional[User]:
    providers = _build_provider_configs()
    if not providers:
        return None

    # Fast-path: Supabase projects often issue HS256 tokens (no JWKS). Try HS256 if issuer matches.
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        iss = (unverified or {}).get("iss", "").rstrip("/")
    except Exception:  # pragma: no cover
        iss = ""

    supabase_issuer = (settings.SUPABASE_ISSUER or "").rstrip("/")
    if iss and supabase_issuer and iss == supabase_issuer:
        hs_secret = (
            os.getenv("SUPABASE_JWT_SECRET")
            or getattr(settings, "SUPABASE_JWT_SECRET", None)
            or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
        )
        if hs_secret:
            try:
                claims = jwt.decode(
                    token,
                    hs_secret,
                    algorithms=["HS256"],
                    audience=getattr(settings, "SUPABASE_AUDIENCE", None),
                    options={"verify_aud": bool(getattr(settings, "SUPABASE_AUDIENCE", None))},
                )
                user = _upsert_external_user(db, claims)
                db.commit()
                db.refresh(user)
                return user
            except (InvalidTokenError, ExpiredSignatureError):
                # Fall through to JWKS providers below
                pass

    for provider in providers:
        try:
            result = await verify_jwt(token, [provider])
        except Exception:  # pragma: no cover - rely on other providers
            continue
        claims = result.get("claims", {})
        if not claims.get("sub"):
            continue
        user = _upsert_external_user(db, claims)
        db.commit()
        db.refresh(user)
        return user

    return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # bcrypt_sha256 pre-hashes, so no 72-byte limit; keep light truncation as guard
    safe_password = (password or "")[:512]
    return pwd_context.hash(safe_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify((plain_password or "")[:512], hashed_password)


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
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
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
    token = credentials.credentials
    payload = None
    try:
        payload = decode_access_token(token)
    except HTTPException:
        payload = None

    if payload:
        user_id = payload.get("sub")
        token_role = payload.get("role")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        try:
            user_uuid = UUID(str(user_id))
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

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated"
            )

        if user.role != token_role:
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

    # External providers (Supabase/Auth0...)
    external_user = await _authenticate_external_token(token, db)
    if external_user:
        if not external_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated"
            )
        return external_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed"
    )


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


def require_sysadmin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require system administrator role.

    Args:
        user: Current authenticated user

    Returns:
        User if system admin role

    Raises:
        HTTPException: 403 if not admin
    """
    if not user.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator access required",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Backwards-compatible dependency alias for system admin access.
    """
    return require_sysadmin(user)  # type: ignore[arg-type]


def require_bank(user: User = Depends(get_current_user)) -> User:
    """Dependency to require a bank officer/administrator."""
    if not (user.is_bank_officer() or user.is_bank_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank role required",
        )
    return user


def require_tenant_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to require tenant administrator or system admin."""
    if not (user.is_tenant_admin() or user.is_system_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant administrator access required",
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
    if not (user.is_bank_officer() or user.is_bank_admin() or user.is_system_admin()):
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
    if user.is_system_admin() or user.is_bank_admin() or user.is_bank_officer():
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
        "upload_docs": [
            UserRole.EXPORTER,
            UserRole.IMPORTER,
            UserRole.TENANT_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],
        "validate_docs": [
            UserRole.EXPORTER,
            UserRole.IMPORTER,
            UserRole.TENANT_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # View own jobs/results
        "view_own_jobs": [
            UserRole.EXPORTER,
            UserRole.IMPORTER,
            UserRole.TENANT_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # View all jobs/results (system-wide)
        "view_all_jobs": [
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # Query audit logs (system-wide)
        "query_audit_logs": [
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # Download evidence packs
        "download_evidence": [
            UserRole.EXPORTER,
            UserRole.IMPORTER,
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # Compliance reports (system-wide)
        "compliance_reports": [
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],

        # Assign/modify user roles
        "manage_roles": [UserRole.SYSTEM_ADMIN],

        # Admin functions
        "admin_access": [UserRole.SYSTEM_ADMIN],

        # System monitoring
        "system_monitoring": [
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ],
    }

    # Check if role has permission
    allowed_roles = permissions.get(permission, [])

    if role not in allowed_roles:
        return False

    # For owner-based permissions, check ownership
    if permission in ["view_own_jobs", "download_evidence"] and resource_owner_id:
        # Privileged roles can access all resources
        if role in [
            UserRole.BANK_OFFICER,
            UserRole.BANK_ADMIN,
            UserRole.SYSTEM_ADMIN,
        ]:
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
