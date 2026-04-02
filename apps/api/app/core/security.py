"""
JWT authentication and role-based access control (RBAC) security layer.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid5, NAMESPACE_URL

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status, Request
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
# Support bcrypt_sha256 first, then legacy bcrypt, with PBKDF2 as a pure-Python
# fallback when the runtime bcrypt backend is unhealthy.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt", "pbkdf2_sha256"],
    deprecated="auto",
)
bcrypt_fallback_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pbkdf2_fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer(auto_error=True)


_PROVIDER_CACHE: Optional[List[ProviderConfig]] = None


class ExternalAuthProvisioningError(RuntimeError):
    """Raised when a verified external identity cannot be provisioned locally."""


def _find_existing_external_user(
    db: Session,
    *,
    user_id: UUID,
    auth_user_id: Optional[UUID],
    email: str,
) -> Optional[User]:
    """Look up an external user using the same identity fallback order as provisioning."""

    user = None
    if auth_user_id:
        user = db.query(User).filter(User.auth_user_id == auth_user_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
    if not user:
        user = db.query(User).filter(User.id == user_id).first()
    return user


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


def _build_dynamic_provider_from_issuer(
    issuer: str,
    audience: Optional[Union[str, List[str]]] = None,
) -> Optional[ProviderConfig]:
    """Derive a Supabase JWKS provider directly from a token issuer."""

    normalized_issuer = (issuer or "").rstrip("/")
    if not normalized_issuer.startswith("https://"):
        return None

    if ".supabase.co" not in normalized_issuer or not normalized_issuer.endswith("/auth/v1"):
        return None

    resolved_audience = audience if isinstance(audience, str) and audience.strip() else settings.SUPABASE_AUDIENCE

    return ProviderConfig(
        name="supabase-auto",
        issuer=normalized_issuer,
        jwks_url=f"{normalized_issuer}/.well-known/jwks.json",
        audience=resolved_audience,
    )


def _resolve_external_user_id(subject: str) -> UUID:
    """Convert external subject claim into UUID for local user table."""

    try:
        return UUID(subject)
    except (ValueError, TypeError):
        # Derive deterministic UUID5 so repeated logins map to same user
        return uuid5(NAMESPACE_URL, subject or "external-user")


def _normalise_role_claim(claims: Dict[str, Any]) -> str:
    valid_roles = {
        "exporter",
        "importer",
        "tenant_admin",
        "bank_officer",
        "bank_admin",
        "system_admin",
    }
    candidates = [
        (claims.get("app_metadata") or {}).get("role"),
        (claims.get("user_metadata") or {}).get("role"),
        claims.get("role"),
    ]
    for candidate in candidates:
        normalized = str(candidate or "").lower()
        if normalized in valid_roles:
            return normalized
    return UserRole.EXPORTER.value


def _truncate_password_for_bcrypt(password: str, max_bytes: int = 72) -> str:
    """Safely truncate a password to bcrypt's byte ceiling without splitting UTF-8."""

    normalized = password or ""
    encoded = normalized.encode("utf-8")
    if len(encoded) <= max_bytes:
        return normalized

    truncated = encoded[:max_bytes]
    while truncated:
        try:
            return truncated.decode("utf-8")
        except UnicodeDecodeError as exc:
            truncated = truncated[:exc.start]
    return ""


def _upsert_external_user(db: Session, claims: Dict[str, Any]) -> User:
    logger = logging.getLogger(__name__)
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
    
    # Extract auth_user_id from token sub claim (Supabase auth user UUID)
    auth_user_id = None
    try:
        sub_claim = claims.get("sub")
        if sub_claim:
            from uuid import UUID
            auth_user_id = UUID(str(sub_claim))
    except (ValueError, TypeError):
        # If sub is not a valid UUID, leave auth_user_id as None
        pass

    user = _find_existing_external_user(
        db,
        user_id=user_id,
        auth_user_id=auth_user_id,
        email=email,
    )

    if not user:
        try:
            user = User(
                id=user_id,
                email=email,
                full_name=full_name,
                role=role_value,
                # Live public.users still enforces NOT NULL here, so keep an empty
                # local password marker for externally authenticated users.
                hashed_password="",
                is_active=True,
                auth_user_id=auth_user_id,
            )
            db.add(user)
            db.flush()
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to create external user {email}: {error_msg}")
            db.rollback()
            user = _find_existing_external_user(
                db,
                user_id=user_id,
                auth_user_id=auth_user_id,
                email=email,
            )
            if not user:
                raise ExternalAuthProvisioningError(
                    f"Failed to provision external user {email}: {error_msg}"
                ) from e

    user.email = email
    if full_name:
        user.full_name = full_name
    if role_value and not user.role:
        user.role = role_value
    user.is_active = True
    if user.hashed_password is None:
        user.hashed_password = ""
    if auth_user_id and user.auth_user_id != auth_user_id:
        user.auth_user_id = auth_user_id

    return user


def infer_effective_role(user: User) -> str:
    """
    Determine the most accurate role for a user based on onboarding metadata,
    company metadata, and naming signals.
    """
    role = (user.role or UserRole.EXPORTER.value).lower()
    onboarding_data = user.onboarding_data or {}
    company_data = onboarding_data.get("company") or {}
    business_types = onboarding_data.get("business_types") or []
    business_types_normalized = [
        str(bt).strip().lower() for bt in business_types if isinstance(bt, str)
    ]

    company_type = str(company_data.get("type") or "").strip().lower()
    company_size = str(company_data.get("size") or "").strip().lower()
    company_name = str(company_data.get("name") or "").strip().lower()

    event_meta = {}
    if getattr(user, "company", None):
        company = user.company
        company_name = (company.name or company_name).strip().lower()
        if isinstance(company.event_metadata, dict):
            event_meta = {
                str(k).strip().lower(): v for k, v in company.event_metadata.items()
            }
            meta_business_type = str(
                event_meta.get("business_type")
                or event_meta.get("company_type")
                or ""
            ).strip().lower()
            meta_company_size = str(
                event_meta.get("company_size") or ""
            ).strip().lower()
            tenant_type = str(event_meta.get("tenant_type") or "").strip().lower()
            if not company_type and meta_business_type:
                company_type = meta_business_type
            if not company_size and meta_company_size:
                company_size = meta_company_size
            if tenant_type == "bank" and company_type != "bank":
                company_type = "bank"

    def _contains_bank(text: str) -> bool:
        return isinstance(text, str) and "bank" in text.lower()

    is_bank = (
        role in {"bank_officer", "bank_admin"}
        or company_type == "bank"
        or "bank" in business_types_normalized
        or _contains_bank(company_name)
        or _contains_bank(user.email or "")
    )

    if is_bank:
        return "bank_admin" if role == "bank_admin" else "bank_officer"

    importer_only = (
        "importer" in business_types_normalized
        and "exporter" not in business_types_normalized
    )
    if importer_only or company_type == "importer":
        return "importer"

    if company_type == "both":
        if role == "importer":
            return "importer"
        if company_size in {"medium", "large"}:
            return "tenant_admin"
        return "exporter"

    valid_roles = {
        "exporter",
        "importer",
        "tenant_admin",
        "bank_officer",
        "bank_admin",
        "system_admin",
    }
    if role not in valid_roles:
        return "exporter"
    return role


async def authenticate_external_token(token: str, db: Session) -> Optional[User]:
    """Authenticate user via external provider token (Supabase uses ES256/JWKS, Auth0, etc.)."""
    logger = logging.getLogger(__name__)
    
    # Extract issuer from token to help with provider detection
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        iss = (unverified or {}).get("iss", "").rstrip("/")
        aud = (unverified or {}).get("aud")
        logger.debug(f"Token issuer: {iss}")
    except Exception as e:
        logger.debug(f"Failed to decode token (unverified): {str(e)}")
        iss = ""
        aud = None

    providers = _build_provider_configs()
    dynamic_providers: List[ProviderConfig] = []
    dynamic_provider = _build_dynamic_provider_from_issuer(iss, aud)
    if dynamic_provider:
        dynamic_providers.append(dynamic_provider)
        if dynamic_provider.audience is not None:
            dynamic_providers.append(
                ProviderConfig(
                    name=f"{dynamic_provider.name}-noaud",
                    issuer=dynamic_provider.issuer,
                    jwks_url=dynamic_provider.jwks_url,
                    audience=None,
                )
            )

    for dynamic in dynamic_providers:
        if not any(
            provider.issuer == dynamic.issuer
            and provider.jwks_url == dynamic.jwks_url
            and provider.audience == dynamic.audience
            for provider in providers
        ):
            providers = [*providers, dynamic]
            logger.info(
                "Auto-derived Supabase JWKS provider from token issuer: %s (aud=%s)",
                dynamic.issuer,
                dynamic.audience or "none",
            )

    if not providers:
        logger.warning("No external providers configured")
        return None

    # Try JWKS providers (Supabase uses ES256 via JWKS)
    logger.debug(f"Trying {len(providers)} JWKS provider(s) for ES256/RS256 validation")
    for provider in providers:
        try:
            logger.debug(f"Attempting verification via provider: {provider.name} ({provider.issuer})")
            result = await verify_jwt(token, [provider])
            claims = result.get("claims", {})
            if not claims.get("sub"):
                logger.warning(f"Provider {provider.name} returned token without 'sub' claim")
                continue
            logger.info(f"Successfully verified token via provider: {provider.name} ({provider.issuer})")
            logger.info(f"Token claims: email={claims.get('email', 'unknown')}, sub={claims.get('sub', 'unknown')}")
            user = _upsert_external_user(db, claims)
            db.commit()
            db.refresh(user)
            logger.info(f"Created/updated external user: {user.email} (ID: {user.id})")
            return user
        except ExternalAuthProvisioningError:
            raise
        except Exception as e:
            logger.warning(f"Provider {provider.name} ({provider.issuer}) failed: {str(e)}")
            logger.debug(f"Provider failure details: {type(e).__name__}: {str(e)}", exc_info=True)
            continue

    logger.warning("No external provider could authenticate the token")
    logger.warning(f"Token issuer: {iss}")
    logger.warning(f"Configured providers: {[p.name for p in providers]}")
    return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    if not password:
        password = ""

    # Prefer bcrypt_sha256 for new hashes, then fall back to plain bcrypt, and
    # finally a pure-Python PBKDF2 hash if the runtime bcrypt backend is broken.
    try:
        return pwd_context.hash(password)
    except Exception as primary_error:
        logging.warning(
            "Primary password hashing failed: %s",
            type(primary_error).__name__,
        )
        safe_password = _truncate_password_for_bcrypt(password)
        try:
            return bcrypt_fallback_context.hash(safe_password)
        except Exception as bcrypt_error:
            logging.warning(
                "bcrypt fallback hashing failed: %s",
                type(bcrypt_error).__name__,
            )
            try:
                return pbkdf2_fallback_context.hash(password)
            except Exception as pbkdf2_error:
                raise ValueError(
                    f"Failed to hash password: {primary_error}"
                ) from pbkdf2_error


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not plain_password or not hashed_password:
        return False
    
    # Truncate password to prevent issues with long passwords
    safe_password = (plain_password or "")[:512]
    
    try:
        # Try with the main context (supports both bcrypt_sha256 and bcrypt)
        return pwd_context.verify(safe_password, hashed_password)
    except Exception as e:
        # If verification fails due to bcrypt version issues, try direct bcrypt verification
        # This handles cases where passlib can't identify the hash format
        try:
            import bcrypt
            # Direct bcrypt verification for $2a$, $2b$, $2y$ hashes
            if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
                # Extract the salt and hash from the bcrypt hash
                return bcrypt.checkpw(
                    safe_password.encode('utf-8'),
                    hashed_password.encode('utf-8')
                )
        except Exception:
            pass
        
        # Log the error for debugging but don't expose it
        logging.warning(f"Password verification failed: {type(e).__name__}")
        return False


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
    try:
        external_user = await authenticate_external_token(token, db)
    except ExternalAuthProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"External authentication provisioning failed: {exc}",
        ) from exc
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


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token if provided, otherwise return None.
    
    This allows endpoints to work for both authenticated and anonymous users.
    Use this for endpoints where authentication is optional (e.g., public search
    with enhanced features for logged-in users).
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    if not token:
        return None
    
    # Try to decode and validate token
    try:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                try:
                    user_uuid = UUID(str(user_id))
                    user = db.query(User).filter(User.id == user_uuid).first()
                    if user and user.is_active:
                        return user
                except ValueError:
                    pass
    except Exception:
        pass
    
    # Try external provider
    try:
        external_user = await authenticate_external_token(token, db)
        if external_user and external_user.is_active:
            return external_user
    except Exception:
        pass
    
    return None


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


def can_act_as_workflow_stage(user: User, stage: str, approval: Optional[Any] = None) -> bool:
    """
    Check if user can act in a specific workflow stage.
    
    Workflow stages: analyst, reviewer, approver
    
    Rules:
    - System admins and bank admins can act in any stage
    - Bank officers can act in any stage (flexible assignment)
    - Users assigned to a specific stage can act in that stage
    - For analyst stage: user must be assigned as analyst_id or be bank_officer/admin
    - For reviewer stage: user must be assigned as reviewer_id or be bank_officer/admin
    - For approver stage: user must be assigned as approver_id or be bank_admin/system_admin
    
    Args:
        user: Current authenticated user
        stage: Workflow stage (analyst, reviewer, approver)
        approval: Optional BankApproval object to check assignments
    
    Returns:
        True if user can act in this stage
    """
    from ..models.bank_workflow import ApprovalStage
    
    # System admins and bank admins can act in any stage
    if user.is_system_admin() or user.is_bank_admin():
        return True
    
    # Bank officers can act in analyst and reviewer stages
    if user.is_bank_officer():
        if stage in [ApprovalStage.ANALYST.value, ApprovalStage.REVIEWER.value]:
            return True
        # Bank officers can act as approver only if explicitly assigned
        if stage == ApprovalStage.APPROVER.value and approval:
            return approval.approver_id == user.id
    
    # Check specific assignments if approval object provided
    if approval:
        if stage == ApprovalStage.ANALYST.value:
            return approval.analyst_id == user.id or approval.assigned_to_id == user.id
        elif stage == ApprovalStage.REVIEWER.value:
            return approval.reviewer_id == user.id or approval.assigned_to_id == user.id
        elif stage == ApprovalStage.APPROVER.value:
            return approval.approver_id == user.id or approval.assigned_to_id == user.id
    
    return False


def require_workflow_stage_access(
    stage: str,
    approval: Optional[Any] = None,
    user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require access to a specific workflow stage.
    
    Args:
        stage: Workflow stage (analyst, reviewer, approver)
        approval: Optional BankApproval object to check assignments
        user: Current authenticated user
    
    Returns:
        User if access granted
    
    Raises:
        HTTPException: 403 if access denied
    """
    if not can_act_as_workflow_stage(user, stage, approval):
        stage_name = stage.replace("_", " ").title()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You do not have permission to act as {stage_name}."
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


def require_bank_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require bank_admin role for mutations.

    Args:
        user: Current authenticated user

    Returns:
        User if bank_admin or system_admin role

    Raises:
        HTTPException: 403 if not bank_admin or system_admin
    """
    if not user.is_bank_admin() and not user.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank admin access required"
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

    # If user has no password (Supabase user), cannot authenticate via email/password
    if not user.hashed_password:
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
