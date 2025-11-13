"""
Authentication API endpoints.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from app.models import User, Company
from ..schemas import UserRegistration, UserLogin, Token, UserProfile
from ..schemas.user import UserCreate
from ..core.security import (
    authenticate_user,
    create_access_token,
    hash_password,
    get_current_user,
    JWT_EXPIRATION_HOURS,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user account."""

    # Check if user already exists
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user with role (safeguard bcrypt length)
    try:
        # Truncate to 72 chars to satisfy bcrypt backend limits
        safe_pw = (user_data.password or '')[:72]
        hashed_password = hash_password(safe_pw)
    except Exception:
        # Fallback: last-resort truncate and hash
        hashed_password = hash_password((user_data.password or '')[:72])
    
    # Create Company record if company info is provided
    company_id = None
    if user_data.company_name:
        company = Company(
            name=user_data.company_name,
            contact_email=user_data.email,
        )
        
        # Store company type and size in event_metadata
        event_metadata = {}
        if user_data.company_type:
            event_metadata["business_type"] = user_data.company_type
        if user_data.company_size:
            event_metadata["company_size"] = user_data.company_size
        if event_metadata:
            company.event_metadata = event_metadata
        
        db.add(company)
        db.flush()  # Flush to get company.id
        company_id = company.id
    
    # Prepare onboarding data
    onboarding_data = {}
    if user_data.business_types:
        onboarding_data["business_types"] = user_data.business_types
    if user_data.company_name:
        onboarding_data["company"] = {
            "name": user_data.company_name,
            "type": user_data.company_type,
            "size": user_data.company_size,
        }
    if user_data.full_name:
        onboarding_data["contact_person"] = user_data.full_name
    
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        company_id=company_id,
        onboarding_data=onboarding_data if onboarding_data else None,
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )
    
    return UserProfile.model_validate(db_user)


@router.post("/login", response_model=Token)
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    
    # For email/password users, verify password
    # For Supabase users (hashed_password=None), they should authenticate via Supabase token, not this endpoint
    user = authenticate_user(user_data.email, user_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token with role information
    token_data = create_access_token(user)

    return Token(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        role=token_data["role"]
    )


@router.get("/csrf-token")
async def get_csrf_token(
    request: Request,
):
    """Generate and return a CSRF token. Available to all users (no auth required)."""
    from ..middleware.csrf import generate_csrf_token
    from ..config import settings
    
    token, cookie_settings = await generate_csrf_token(
        secret_key=settings.SECRET_KEY,
        expiry_seconds=3600  # 1 hour
    )
    
    # Create response with token in JSON body
    from fastapi.responses import JSONResponse
    
    response = JSONResponse({
        "csrf_token": token,
        "expires_in": 3600
    })
    
    # Set CSRF token cookie (must be readable by JS for double-submit pattern)
    response.set_cookie(
        key=cookie_settings["key"],
        value=cookie_settings["value"],
        httponly=False,  # Must be readable by JavaScript
        samesite="none",
        secure=settings.is_production(),  # HTTPS only in production
        max_age=cookie_settings["max_age"],
    )
    
    return response


@router.post("/fix-password")  # TEMPORARY - Remove after fixing passwords
async def fix_password_endpoint(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    TEMPORARY endpoint to fix password hashes.
    TODO: Remove this after all test users have correct password hashes.
    
    Accepts JSON body: {"email": "...", "password": "..."}
    Or form data: email=...&password=...
    """
    from ..core.security import hash_password, verify_password
    
    # Try to get from JSON body first
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
    except:
        # Fallback to form data
        form = await request.form()
        email = form.get("email")
        password = form.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new hash
    new_hash = hash_password(password)
    user.hashed_password = new_hash
    db.commit()
    db.refresh(user)
    
    # Verify it works
    if verify_password(password, new_hash):
        return {"status": "success", "message": f"Password updated for {email}"}
    else:
        db.rollback()
        raise HTTPException(status_code=500, detail="Password hash verification failed")


@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user profile."""
    try:
        # Get current user (this will authenticate via token)
        current_user = await get_current_user(credentials, db)
        
        # Ensure user is refreshed from database
        db.refresh(current_user)
        
        # Normalize role before validation (handle legacy roles)
        role = current_user.role.lower() if current_user.role else "exporter"
        legacy_role_map = {
            "bank": "bank_officer",
            "admin": "system_admin",
        }
        normalized_role = legacy_role_map.get(role, role)
        
        # Ensure role is valid
        valid_roles = ["exporter", "importer", "tenant_admin", "bank_officer", "bank_admin", "system_admin"]
        if normalized_role not in valid_roles:
            normalized_role = "exporter"  # Fallback to exporter
        
        # Ensure required fields exist
        from datetime import datetime, timezone
        created_at = current_user.created_at or datetime.now(timezone.utc)
        updated_at = current_user.updated_at or created_at
        
        # Create profile data dict (don't modify user object)
        profile_data = {
            "id": current_user.id,
            "email": current_user.email or "unknown@example.com",
            "full_name": current_user.full_name or "Unknown User",
            "role": normalized_role,
            "is_active": current_user.is_active if current_user.is_active is not None else True,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        
        return UserProfile.model_validate(profile_data)
            
    except Exception as e:
        # Log the error for debugging
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in /auth/me for user {current_user.id if current_user else 'unknown'}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a basic profile even if validation fails
        try:
            from datetime import datetime, timezone
            return UserProfile(
                id=current_user.id,
                email=current_user.email or "unknown@example.com",
                full_name=current_user.full_name or "Unknown User",
                role="exporter",  # Safe default
                is_active=current_user.is_active if current_user.is_active is not None else True,
                created_at=current_user.created_at or datetime.now(timezone.utc),
                updated_at=current_user.updated_at or datetime.now(timezone.utc),
            )
        except Exception as fallback_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load user profile: {str(e)}. Fallback also failed: {str(fallback_error)}"
            )
