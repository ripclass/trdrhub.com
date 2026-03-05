"""
Hub Usage API Router

Endpoints for managing and viewing usage across all TRDR Hub tools.

Endpoints:
- GET /usage/current - Current month's usage
- GET /usage/limits - Remaining limits for all operations
- GET /usage/history - Historical usage data
- GET /usage/logs - Detailed usage log entries
- POST /usage/check - Check if operation is allowed (internal)
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.usage_service import get_usage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["Usage"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UsageCheckRequest(BaseModel):
    """Request to check if operation is allowed."""
    operation: str
    quantity: int = 1


class UsageCheckResponse(BaseModel):
    """Response for usage check."""
    allowed: bool
    message: str
    plan: Optional[str] = None
    limit: Optional[int] = None
    used: Optional[int] = None
    remaining: Optional[int] = None
    overage_cost: Optional[float] = None


class RecordUsageRequest(BaseModel):
    """Request to record usage (internal use)."""
    operation: str
    tool: str
    quantity: int = 1
    description: Optional[str] = None
    log_data: Optional[dict] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/current")
async def get_current_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current month's usage summary.
    
    Returns usage counts for all operations and any overage charges.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        usage = await service.get_current_usage(current_user.company_id)
        
        if "error" in usage:
            raise HTTPException(status_code=500, detail=usage["error"])
        
        return usage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limits")
async def get_remaining_limits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get remaining limits for all operations.
    
    Shows plan limits, current usage, and remaining quota for each tool.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        limits = await service.get_remaining_limits(current_user.company_id)
        
        if "error" in limits:
            raise HTTPException(status_code=500, detail=limits["error"])
        
        return limits
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get remaining limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_usage_history(
    months: int = Query(6, ge=1, le=24, description="Number of months to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get usage history for past N months.
    
    Returns monthly usage summaries and overage charges.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        history = await service.get_usage_history(current_user.company_id, months)
        return {"history": history, "months_requested": months}
        
    except Exception as e:
        logger.error(f"Failed to get usage history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_usage_logs(
    limit: int = Query(50, ge=1, le=200, description="Number of log entries"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    tool: Optional[str] = Query(None, description="Filter by tool (lcopilot, price_verify, etc.)"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed usage log entries.
    
    Shows individual operations with timestamps, costs, and metadata.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        logs = await service.get_usage_logs(
            current_user.company_id,
            limit=limit,
            offset=offset,
            tool=tool,
            operation=operation
        )
        return {"logs": logs, "limit": limit, "offset": offset}
        
    except Exception as e:
        logger.error(f"Failed to get usage logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check")
async def check_usage_limit(
    request: UsageCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if an operation is allowed based on current usage and limits.
    
    This endpoint is called before performing billable operations to:
    1. Verify user hasn't exceeded limits
    2. Calculate potential overage charges
    3. Allow frontend to show confirmation for overages
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        allowed, message, info = await service.check_limit(
            current_user.company_id,
            request.operation,
            request.quantity
        )
        
        return UsageCheckResponse(
            allowed=allowed,
            message=message,
            plan=info.get("plan"),
            limit=info.get("limit") if isinstance(info.get("limit"), int) else None,
            used=info.get("used"),
            remaining=info.get("remaining") if isinstance(info.get("remaining"), int) else None,
            overage_cost=info.get("overage_cost")
        )
        
    except Exception as e:
        logger.error(f"Failed to check usage limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record", include_in_schema=False)
async def record_usage(
    request: RecordUsageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a usage event (internal endpoint).
    
    This is typically called automatically by tool endpoints after
    completing billable operations. Not intended for direct use.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        service = get_usage_service(db)
        success, message, overage_cost = await service.record_usage(
            company_id=current_user.company_id,
            user_id=current_user.id,
            operation=request.operation,
            tool=request.tool,
            quantity=request.quantity,
            log_data=request.log_data,
            description=request.description
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return {
            "success": True,
            "message": message,
            "overage_cost": float(overage_cost) if overage_cost else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================================

@router.get("/subscription")
async def get_subscription_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current subscription information.
    
    Returns plan details, status, and billing information.
    """
    from app.models.hub import HubSubscription, HubPlan
    from sqlalchemy import select, and_
    
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    try:
        # Get active subscription
        query = select(HubSubscription).where(
            and_(
                HubSubscription.company_id == current_user.company_id,
                HubSubscription.status == "active"
            )
        )
        result = db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            # No subscription = PAYG
            payg_query = select(HubPlan).where(HubPlan.slug == "payg")
            payg_result = db.execute(payg_query)
            payg_plan = payg_result.scalar_one_or_none()
            
            return {
                "has_subscription": False,
                "plan": {
                    "slug": "payg",
                    "name": "Pay-as-you-go",
                    "description": payg_plan.description if payg_plan else "No monthly commitment"
                },
                "message": "You are on pay-as-you-go. Operations are charged individually."
            }
        
        plan = subscription.plan
        
        return {
            "has_subscription": True,
            "plan": {
                "slug": plan.slug,
                "name": plan.name,
                "description": plan.description,
                "price_monthly": float(plan.price_monthly) if plan.price_monthly else None,
                "limits": plan.limits,
                "features": plan.features
            },
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end
        }
        
    except Exception as e:
        logger.error(f"Failed to get subscription info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def list_available_plans(db: Session = Depends(get_db)):
    """
    List all available subscription plans.
    
    Public endpoint - no authentication required.
    """
    from app.models.hub import HubPlan
    from sqlalchemy import select
    
    try:
        query = select(HubPlan).where(HubPlan.is_active == True).order_by(HubPlan.price_monthly)
        result = db.execute(query)
        plans = result.scalars().all()
        
        return {
            "plans": [
                {
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                    "price_monthly": float(p.price_monthly) if p.price_monthly else 0,
                    "price_yearly": float(p.price_yearly) if p.price_yearly else None,
                    "limits": p.limits,
                    "overage_rates": p.overage_rates,
                    "features": p.features,
                    "max_users": p.max_users
                }
                for p in plans
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

