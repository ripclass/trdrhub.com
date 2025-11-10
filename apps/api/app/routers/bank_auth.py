"""
Bank Authentication API endpoints.

Handles bank-specific authentication including 2FA.
"""

import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from app.models import User
from ..core.security import get_current_user, require_bank_or_admin
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult

router = APIRouter(prefix="/bank/auth", tags=["bank-auth"])
logger = logging.getLogger(__name__)

# Feature flag for 2FA
ENABLE_2FA = os.getenv("ENABLE_BANK_2FA", "false").lower() == "true"

# In-memory storage for 2FA codes (in production, use Redis)
# Format: {session_id: {"code": str, "user_id": UUID, "expires_at": float}}
_2FA_CODES: Dict[str, Dict] = {}

# 2FA code expiry (5 minutes)
_2FA_CODE_EXPIRY_SECONDS = 300

# Session timeout (30 minutes idle)
SESSION_IDLE_TIMEOUT_MINUTES = int(os.getenv("BANK_SESSION_IDLE_TIMEOUT_MINUTES", "30"))


def _generate_2fa_code() -> str:
    """Generate a 6-digit 2FA code."""
    return f"{secrets.randbelow(1000000):06d}"


def _cleanup_expired_codes():
    """Remove expired 2FA codes."""
    now = time.time()
    expired_keys = [
        key for key, value in _2FA_CODES.items()
        if value.get("expires_at", 0) < now
    ]
    for key in expired_keys:
        _2FA_CODES.pop(key, None)


@router.post("/request-2fa")
async def request_2fa(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Request 2FA code for bank user.
    
    Generates a 6-digit code and stores it temporarily.
    In production, this would send via SMS/email.
    
    Requires feature flag ENABLE_BANK_2FA=true.
    """
    if not ENABLE_2FA:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="2FA is not enabled. Set ENABLE_BANK_2FA=true to enable."
        )
    
    if not current_user.is_bank_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA is only available for bank users"
        )
    
    # Cleanup expired codes
    _cleanup_expired_codes()
    
    # Generate 2FA code
    code = _generate_2fa_code()
    session_id = secrets.token_urlsafe(32)
    expires_at = time.time() + _2FA_CODE_EXPIRY_SECONDS
    
    # Store code (in production, use Redis)
    _2FA_CODES[session_id] = {
        "code": code,
        "user_id": current_user.id,
        "expires_at": expires_at,
        "created_at": time.time()
    }
    
    # Log 2FA request
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.LOGIN,
        user=current_user,
        resource_type="auth",
        resource_id=str(current_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "request_2fa",
            "bank_tenant_id": str(current_user.company_id),
            "session_id": session_id,
            "note": "2FA code requested (mock - in production would send via SMS/email)"
        }
    )
    
    # In production, send code via SMS/email
    # For now, return it in response (only for development/testing)
    logger.info(f"2FA code for user {current_user.email}: {code} (session: {session_id[:8]}...)")
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "2FA code sent. Check your SMS/email.",
        # Only include code in development
        "code": code if os.getenv("ENV") == "development" else None
    }


@router.post("/verify-2fa")
async def verify_2fa(
    code: str = Query(..., description="6-digit 2FA code"),
    session_id: str = Query(..., description="Session ID from request-2fa"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Verify 2FA code for bank user.
    
    Validates the 6-digit code against the stored session.
    Returns success if code matches and hasn't expired.
    """
    if not ENABLE_2FA:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="2FA is not enabled"
        )
    
    if not current_user.is_bank_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA is only available for bank users"
        )
    
    # Cleanup expired codes
    _cleanup_expired_codes()
    
    # Validate code format
    if not code or len(code) != 6 or not code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code format. Must be 6 digits."
        )
    
    # Retrieve stored code
    stored_data = _2FA_CODES.get(session_id)
    if not stored_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired. Please request a new code."
        )
    
    # Check expiry
    if stored_data.get("expires_at", 0) < time.time():
        _2FA_CODES.pop(session_id, None)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Code expired. Please request a new code."
        )
    
    # Verify user matches
    if stored_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Code does not match current user"
        )
    
    # Verify code
    if stored_data.get("code") != code:
        # Log failed attempt
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.LOGIN,
            user=current_user,
            resource_type="auth",
            resource_id=str(current_user.id),
            result=AuditResult.FAILURE,
            audit_metadata={
                "action": "verify_2fa",
                "bank_tenant_id": str(current_user.company_id),
                "session_id": session_id,
                "note": "Invalid 2FA code provided"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code. Please try again."
        )
    
    # Code is valid - remove it (one-time use)
    _2FA_CODES.pop(session_id, None)
    
    # Log successful verification
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.LOGIN,
        user=current_user,
        resource_type="auth",
        resource_id=str(current_user.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "verify_2fa",
            "bank_tenant_id": str(current_user.company_id),
            "session_id": session_id,
            "note": "2FA verified successfully"
        }
    )
    
    return {
        "success": True,
        "message": "2FA verified successfully",
        "verified_at": datetime.utcnow().isoformat()
    }


@router.get("/session-status")
async def get_session_status(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get current session status including idle timeout information.
    
    Returns session metadata for frontend to implement idle timeout.
    """
    if not current_user.is_bank_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session status is only available for bank users"
        )
    
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "idle_timeout_minutes": SESSION_IDLE_TIMEOUT_MINUTES,
        "2fa_enabled": ENABLE_2FA,
        "session_active": True
    }

