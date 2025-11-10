"""
Bank policy overlay API endpoints.

Bank admins can configure stricter validation rules and exceptions.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from ..database import get_db
from app.models import User, BankPolicyOverlay, BankPolicyException
from ..core.security import get_current_user, require_bank_or_admin
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult


router = APIRouter(prefix="/bank/policy", tags=["bank-policy"])


def require_bank_admin(user: User = Depends(get_current_user)) -> User:
    """Require bank_admin role for mutations."""
    if not user.is_bank_admin() and not user.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank admin access required"
        )
    return user


# Schemas
class PolicyOverlayConfig(BaseModel):
    """Policy overlay configuration."""
    stricter_checks: dict = Field(default_factory=dict)
    thresholds: dict = Field(default_factory=dict)


class PolicyOverlayCreate(BaseModel):
    """Create/update policy overlay."""
    config: PolicyOverlayConfig
    version: Optional[int] = None


class PolicyOverlayRead(BaseModel):
    """Policy overlay response."""
    id: UUID
    bank_id: UUID
    version: int
    active: bool
    config: dict
    created_by_id: UUID
    published_by_id: Optional[UUID]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PolicyExceptionCreate(BaseModel):
    """Create policy exception."""
    rule_code: str = Field(..., max_length=100)
    scope: dict = Field(default_factory=dict)  # {"client": "...", "branch": "...", "product": "..."}
    reason: str
    expires_at: Optional[datetime] = None
    effect: str = Field(default="waive", pattern="^(waive|downgrade|override)$")


class PolicyExceptionRead(BaseModel):
    """Policy exception response."""
    id: UUID
    bank_id: UUID
    overlay_id: Optional[UUID]
    rule_code: str
    scope: dict
    reason: str
    expires_at: Optional[datetime]
    effect: str
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/overlays", response_model=List[PolicyOverlayRead])
async def list_overlays(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    List all policy overlays for the bank tenant.
    
    Bank officers and admins can view overlays.
    """
    overlays = db.query(BankPolicyOverlay).filter(
        BankPolicyOverlay.bank_id == current_user.company_id
    ).order_by(BankPolicyOverlay.version.desc()).all()
    
    return [PolicyOverlayRead.from_orm(o) for o in overlays]


@router.post("/overlays", response_model=PolicyOverlayRead, status_code=status.HTTP_201_CREATED)
async def create_or_update_overlay(
    overlay_data: PolicyOverlayCreate,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Create or update the active policy overlay for the bank.
    
    Requires bank_admin role.
    If an active overlay exists, it's deactivated and a new version is created.
    """
    # Deactivate existing active overlay
    existing_active = db.query(BankPolicyOverlay).filter(
        and_(
            BankPolicyOverlay.bank_id == current_user.company_id,
            BankPolicyOverlay.active == True
        )
    ).first()
    
    if existing_active:
        existing_active.active = False
        db.commit()
    
    # Get next version number
    max_version = db.query(BankPolicyOverlay).filter(
        BankPolicyOverlay.bank_id == current_user.company_id
    ).order_by(BankPolicyOverlay.version.desc()).first()
    
    next_version = (max_version.version + 1) if max_version else 1
    if overlay_data.version:
        next_version = overlay_data.version
    
    # Create new overlay
    new_overlay = BankPolicyOverlay(
        bank_id=current_user.company_id,
        version=next_version,
        active=True,
        config=overlay_data.config.model_dump(),
        created_by_id=current_user.id
    )
    
    db.add(new_overlay)
    db.commit()
    db.refresh(new_overlay)
    
    # Log creation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_CONFIG,
        user=current_user,
        resource_type="policy_overlay",
        resource_id=str(new_overlay.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "version": next_version,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return PolicyOverlayRead.from_orm(new_overlay)


@router.post("/overlays/publish", response_model=PolicyOverlayRead)
async def publish_overlay(
    overlay_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Publish (activate) a policy overlay version.
    
    Requires bank_admin role.
    Deactivates current active overlay and activates the specified one.
    """
    overlay = db.query(BankPolicyOverlay).filter(
        and_(
            BankPolicyOverlay.id == overlay_id,
            BankPolicyOverlay.bank_id == current_user.company_id
        )
    ).first()
    
    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overlay not found"
        )
    
    # Deactivate current active
    existing_active = db.query(BankPolicyOverlay).filter(
        and_(
            BankPolicyOverlay.bank_id == current_user.company_id,
            BankPolicyOverlay.active == True,
            BankPolicyOverlay.id != overlay_id
        )
    ).first()
    
    if existing_active:
        existing_active.active = False
    
    # Activate this overlay
    overlay.active = True
    overlay.published_by_id = current_user.id
    overlay.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(overlay)
    
    # Log publication
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_CONFIG,
        user=current_user,
        resource_type="policy_overlay",
        resource_id=str(overlay.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "publish",
            "version": overlay.version,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return PolicyOverlayRead.from_orm(overlay)


@router.post("/overlays/exceptions", response_model=PolicyExceptionRead, status_code=status.HTTP_201_CREATED)
async def create_exception(
    exception_data: PolicyExceptionCreate,
    overlay_id: Optional[UUID] = None,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Add a policy exception.
    
    Requires bank_admin role.
    """
    # Get active overlay if overlay_id not provided
    if not overlay_id:
        active_overlay = db.query(BankPolicyOverlay).filter(
            and_(
                BankPolicyOverlay.bank_id == current_user.company_id,
                BankPolicyOverlay.active == True
            )
        ).first()
        if active_overlay:
            overlay_id = active_overlay.id
    
    new_exception = BankPolicyException(
        bank_id=current_user.company_id,
        overlay_id=overlay_id,
        rule_code=exception_data.rule_code,
        scope=exception_data.scope,
        reason=exception_data.reason,
        expires_at=exception_data.expires_at,
        effect=exception_data.effect,
        created_by_id=current_user.id
    )
    
    db.add(new_exception)
    db.commit()
    db.refresh(new_exception)
    
    # Log exception creation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_CONFIG,
        user=current_user,
        resource_type="policy_exception",
        resource_id=str(new_exception.id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "rule_code": exception_data.rule_code,
            "scope": exception_data.scope,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return PolicyExceptionRead.from_orm(new_exception)


@router.get("/overlays/exceptions", response_model=List[PolicyExceptionRead])
async def list_exceptions(
    rule_code: Optional[str] = None,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    List policy exceptions for the bank tenant.
    
    Bank officers and admins can view exceptions.
    """
    query = db.query(BankPolicyException).filter(
        BankPolicyException.bank_id == current_user.company_id
    )
    
    # Filter by rule_code if provided
    if rule_code:
        query = query.filter(BankPolicyException.rule_code == rule_code)
    
    # Filter out expired exceptions
    query = query.filter(
        or_(
            BankPolicyException.expires_at.is_(None),
            BankPolicyException.expires_at > datetime.utcnow()
        )
    )
    
    exceptions = query.order_by(BankPolicyException.created_at.desc()).all()
    
    return [PolicyExceptionRead.from_orm(e) for e in exceptions]


@router.delete("/overlays/exceptions/{exception_id}")
async def delete_exception(
    exception_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Remove a policy exception.
    
    Requires bank_admin role.
    """
    exception = db.query(BankPolicyException).filter(
        and_(
            BankPolicyException.id == exception_id,
            BankPolicyException.bank_id == current_user.company_id
        )
    ).first()
    
    if not exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exception not found"
        )
    
    db.delete(exception)
    db.commit()
    
    # Log deletion
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        resource_type="policy_exception",
        resource_id=str(exception_id),
        result=AuditResult.SUCCESS,
        audit_metadata={
            "rule_code": exception.rule_code,
            "bank_tenant_id": str(current_user.company_id)
        }
    )
    
    return {"success": True, "message": "Exception removed"}

