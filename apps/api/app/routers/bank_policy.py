"""
Bank policy overlay API endpoints.

Bank admins can configure stricter validation rules and exceptions.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, extract
from pydantic import BaseModel, Field

from ..database import get_db
from app.models import User
from app.models.bank_policy import BankPolicyOverlay, BankPolicyException, BankPolicyApplicationEvent
from ..core.security import get_current_user, require_bank_or_admin, require_bank_admin
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult


router = APIRouter(prefix="/bank/policy", tags=["bank-policy"])


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


# Analytics Schemas
class PolicyUsageStats(BaseModel):
    """Policy usage statistics."""
    overlay_id: Optional[UUID]
    overlay_version: Optional[int]
    total_applications: int
    unique_sessions: int
    avg_discrepancy_reduction: float
    avg_processing_time_ms: float
    last_applied_at: Optional[datetime]


class ExceptionEffectivenessStats(BaseModel):
    """Exception effectiveness metrics."""
    exception_id: UUID
    rule_code: str
    effect: str
    total_applications: int
    waived_count: int
    downgraded_count: int
    overridden_count: int
    avg_discrepancy_reduction: float
    last_applied_at: Optional[datetime]


class PolicyImpactMetrics(BaseModel):
    """Overall policy impact metrics."""
    total_validations: int
    validations_with_policy: int
    policy_usage_rate: float
    total_discrepancy_reduction: int
    avg_discrepancy_reduction_per_validation: float
    severity_changes: dict
    most_affected_rules: List[dict]


class PolicyAnalyticsResponse(BaseModel):
    """Complete analytics response."""
    time_range: str
    start_date: datetime
    end_date: datetime
    overlay_stats: List[PolicyUsageStats]
    exception_stats: List[ExceptionEffectivenessStats]
    impact_metrics: PolicyImpactMetrics
    top_exceptions: List[dict]
    overlay_adoption: List[dict]


@router.get("/analytics", response_model=PolicyAnalyticsResponse)
async def get_policy_analytics(
    time_range: str = Query(default="30d", description="Time range: 7d, 30d, 90d, 365d"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive policy analytics for the bank tenant.
    
    Returns usage statistics, effectiveness metrics, and impact analysis.
    """
    # Parse time range
    days_mapping = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "365d": 365
    }
    days = days_mapping.get(time_range, 30)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Base query for bank's policy events
    base_query = db.query(BankPolicyApplicationEvent).filter(
        and_(
            BankPolicyApplicationEvent.bank_id == current_user.company_id,
            BankPolicyApplicationEvent.created_at >= start_date,
            BankPolicyApplicationEvent.created_at <= end_date
        )
    )
    
    # Overlay usage statistics
    overlay_stats_query = base_query.filter(
        BankPolicyApplicationEvent.overlay_id.isnot(None)
    ).with_entities(
        BankPolicyApplicationEvent.overlay_id,
        BankPolicyApplicationEvent.overlay_version,
        func.count(BankPolicyApplicationEvent.id).label('total_applications'),
        func.count(func.distinct(BankPolicyApplicationEvent.validation_session_id)).label('unique_sessions'),
        func.avg(
            BankPolicyApplicationEvent.discrepancies_before - BankPolicyApplicationEvent.discrepancies_after
        ).label('avg_reduction'),
        func.avg(BankPolicyApplicationEvent.processing_time_ms).label('avg_processing_time'),
        func.max(BankPolicyApplicationEvent.created_at).label('last_applied')
    ).group_by(
        BankPolicyApplicationEvent.overlay_id,
        BankPolicyApplicationEvent.overlay_version
    )
    
    overlay_stats = []
    for row in overlay_stats_query.all():
        overlay_stats.append(PolicyUsageStats(
            overlay_id=row.overlay_id,
            overlay_version=row.overlay_version,
            total_applications=row.total_applications,
            unique_sessions=row.unique_sessions,
            avg_discrepancy_reduction=float(row.avg_reduction or 0),
            avg_processing_time_ms=float(row.avg_processing_time or 0),
            last_applied_at=row.last_applied
        ))
    
    # Exception effectiveness statistics
    exception_stats_query = base_query.filter(
        BankPolicyApplicationEvent.exception_id.isnot(None)
    ).with_entities(
        BankPolicyApplicationEvent.exception_id,
        BankPolicyApplicationEvent.rule_code,
        BankPolicyApplicationEvent.exception_effect,
        func.count(BankPolicyApplicationEvent.id).label('total_applications'),
        func.sum(
            func.case((BankPolicyApplicationEvent.exception_effect == "waive", 1), else_=0)
        ).label('waived_count'),
        func.sum(
            func.case((BankPolicyApplicationEvent.exception_effect == "downgrade", 1), else_=0)
        ).label('downgraded_count'),
        func.sum(
            func.case((BankPolicyApplicationEvent.exception_effect == "override", 1), else_=0)
        ).label('overridden_count'),
        func.avg(
            BankPolicyApplicationEvent.discrepancies_before - BankPolicyApplicationEvent.discrepancies_after
        ).label('avg_reduction'),
        func.max(BankPolicyApplicationEvent.created_at).label('last_applied')
    ).group_by(
        BankPolicyApplicationEvent.exception_id,
        BankPolicyApplicationEvent.rule_code,
        BankPolicyApplicationEvent.exception_effect
    )
    
    exception_stats = []
    for row in exception_stats_query.all():
        exception_stats.append(ExceptionEffectivenessStats(
            exception_id=row.exception_id,
            rule_code=row.rule_code or "",
            effect=row.exception_effect or "",
            total_applications=row.total_applications,
            waived_count=int(row.waived_count or 0),
            downgraded_count=int(row.downgraded_count or 0),
            overridden_count=int(row.overridden_count or 0),
            avg_discrepancy_reduction=float(row.avg_reduction or 0),
            last_applied_at=row.last_applied
        ))
    
    # Overall impact metrics
    total_validations = db.query(func.count(func.distinct(BankPolicyApplicationEvent.validation_session_id))).filter(
        BankPolicyApplicationEvent.bank_id == current_user.company_id,
        BankPolicyApplicationEvent.created_at >= start_date,
        BankPolicyApplicationEvent.created_at <= end_date
    ).scalar() or 0
    
    validations_with_policy = base_query.with_entities(
        func.count(func.distinct(BankPolicyApplicationEvent.validation_session_id))
    ).scalar() or 0
    
    policy_usage_rate = (validations_with_policy / max(total_validations, 1)) * 100 if total_validations > 0 else 0
    
    # Total discrepancy reduction
    total_reduction = base_query.with_entities(
        func.sum(
            BankPolicyApplicationEvent.discrepancies_before - BankPolicyApplicationEvent.discrepancies_after
        )
    ).scalar() or 0
    
    avg_reduction_per_validation = total_reduction / max(validations_with_policy, 1) if validations_with_policy > 0 else 0
    
    # Aggregate severity changes
    severity_changes = {}
    severity_rows = base_query.with_entities(
        BankPolicyApplicationEvent.severity_changes
    ).all()
    
    for row in severity_rows:
        if row.severity_changes:
            for severity, change in row.severity_changes.items():
                severity_changes[severity] = severity_changes.get(severity, 0) + change
    
    # Most affected rules
    rule_impact_query = base_query.filter(
        BankPolicyApplicationEvent.rule_code.isnot(None)
    ).with_entities(
        BankPolicyApplicationEvent.rule_code,
        func.count(BankPolicyApplicationEvent.id).label('application_count'),
        func.avg(
            BankPolicyApplicationEvent.discrepancies_before - BankPolicyApplicationEvent.discrepancies_after
        ).label('avg_reduction')
    ).group_by(
        BankPolicyApplicationEvent.rule_code
    ).order_by(desc('application_count')).limit(10)
    
    most_affected_rules = [
        {
            "rule_code": row.rule_code,
            "application_count": row.application_count,
            "avg_discrepancy_reduction": float(row.avg_reduction or 0)
        }
        for row in rule_impact_query.all()
    ]
    
    impact_metrics = PolicyImpactMetrics(
        total_validations=total_validations,
        validations_with_policy=validations_with_policy,
        policy_usage_rate=round(policy_usage_rate, 2),
        total_discrepancy_reduction=int(total_reduction),
        avg_discrepancy_reduction_per_validation=round(avg_reduction_per_validation, 2),
        severity_changes=severity_changes,
        most_affected_rules=most_affected_rules
    )
    
    # Top exceptions by usage
    top_exceptions = [
        {
            "exception_id": str(stat.exception_id),
            "rule_code": stat.rule_code,
            "effect": stat.effect,
            "total_applications": stat.total_applications,
            "avg_discrepancy_reduction": stat.avg_discrepancy_reduction
        }
        for stat in sorted(exception_stats, key=lambda x: x.total_applications, reverse=True)[:10]
    ]
    
    # Overlay version adoption
    overlay_adoption_query = base_query.filter(
        BankPolicyApplicationEvent.overlay_id.isnot(None)
    ).with_entities(
        BankPolicyApplicationEvent.overlay_id,
        BankPolicyApplicationEvent.overlay_version,
        func.count(func.distinct(BankPolicyApplicationEvent.validation_session_id)).label('session_count')
    ).group_by(
        BankPolicyApplicationEvent.overlay_id,
        BankPolicyApplicationEvent.overlay_version
    ).order_by(desc('session_count'))
    
    overlay_adoption = [
        {
            "overlay_id": str(row.overlay_id),
            "version": row.overlay_version,
            "session_count": row.session_count
        }
        for row in overlay_adoption_query.all()
    ]
    
    return PolicyAnalyticsResponse(
        time_range=time_range,
        start_date=start_date,
        end_date=end_date,
        overlay_stats=overlay_stats,
        exception_stats=exception_stats,
        impact_metrics=impact_metrics,
        top_exceptions=top_exceptions,
        overlay_adoption=overlay_adoption
    )

