"""
Authentication API endpoints.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from app.models import User
from ..schemas import UserRegistration, UserLogin, Token, UserProfile
from ..schemas.user import UserCreate
from ..core.security import (
    authenticate_user,
    create_access_token,
    hash_password,
    get_current_user,
    JWT_EXPIRATION_HOURS
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
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
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
    current_user: User = Depends(get_current_user),
):
    """Generate and return a CSRF token for the authenticated user."""
    from ..middleware.csrf import generate_csrf_token
    from ..config import settings
    
    token, cookie_settings = generate_csrf_token(
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
        samesite="lax",
        secure=settings.is_production(),  # HTTPS only in production
        max_age=cookie_settings["max_age"],
    )
    
    return response


@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return UserProfile.model_validate(current_user)
