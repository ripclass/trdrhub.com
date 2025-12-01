"""
Admin API Router

Endpoints for admin functionality including:
- Commodity management (CRUD)
- Commodity requests review
- Audit logs
- API key management
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.database import get_db
from app.models.commodities import Commodity, CommodityRequest, HSCode
from app.models.commodity_prices import PriceVerification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# COMMODITY MANAGEMENT
# =============================================================================

class CommodityCreate(BaseModel):
    """Request model for creating a commodity."""
    code: str = Field(..., description="Unique commodity code (e.g., DRY_FISH)")
    name: str = Field(..., description="Display name")
    category: str = Field(..., description="Category (e.g., agriculture, metals)")
    unit: str = Field(..., description="Default unit (e.g., kg, mt)")
    aliases: List[str] = Field(default=[], description="Alternative names")
    hs_codes: List[str] = Field(default=[], description="HS codes")
    price_low: Optional[float] = Field(None, description="Typical price range low")
    price_high: Optional[float] = Field(None, description="Typical price range high")
    current_estimate: Optional[float] = Field(None, description="Current price estimate")
    verified: bool = Field(default=False)


class CommodityUpdate(BaseModel):
    """Request model for updating a commodity."""
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    aliases: Optional[List[str]] = None
    hs_codes: Optional[List[str]] = None
    price_low: Optional[float] = None
    price_high: Optional[float] = None
    current_estimate: Optional[float] = None
    verified: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("/commodities")
async def list_admin_commodities(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    verified: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List all commodities with admin details.
    Includes unverified and inactive commodities.
    """
    try:
        query = db.query(Commodity)
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(or_(
                func.lower(Commodity.name).like(search_term),
                func.lower(Commodity.code).like(search_term),
            ))
        
        if category:
            query = query.filter(Commodity.category == category)
        
        if verified is not None:
            query = query.filter(Commodity.verified == verified)
        
        total = query.count()
        commodities = query.order_by(Commodity.name).offset(offset).limit(limit).all()
        
        # Get categories for filter
        categories = db.query(Commodity.category).distinct().all()
        categories = [c[0] for c in categories if c[0]]
        
        return {
            "success": True,
            "commodities": [c.to_dict() for c in commodities],
            "total": total,
            "categories": sorted(categories),
        }
        
    except Exception as e:
        logger.error(f"Failed to list commodities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commodities")
async def create_commodity(
    request: CommodityCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new commodity in the database.
    """
    try:
        # Check for existing code
        existing = db.query(Commodity).filter(Commodity.code == request.code.upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Commodity with code {request.code} already exists")
        
        commodity = Commodity(
            id=uuid4(),
            code=request.code.upper(),
            name=request.name,
            category=request.category.lower(),
            unit=request.unit.lower(),
            aliases=request.aliases,
            hs_codes=request.hs_codes,
            price_low=request.price_low,
            price_high=request.price_high,
            current_estimate=request.current_estimate,
            verified=request.verified,
            is_active=True,
            created_by="admin",
        )
        
        db.add(commodity)
        db.commit()
        db.refresh(commodity)
        
        logger.info(f"Created commodity: {commodity.code}")
        
        return {
            "success": True,
            "commodity": commodity.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create commodity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/commodities/{commodity_id}")
async def update_commodity(
    commodity_id: str,
    request: CommodityUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing commodity.
    """
    try:
        commodity = db.query(Commodity).filter(Commodity.id == commodity_id).first()
        if not commodity:
            raise HTTPException(status_code=404, detail="Commodity not found")
        
        # Update fields that were provided
        if request.name is not None:
            commodity.name = request.name
        if request.category is not None:
            commodity.category = request.category.lower()
        if request.unit is not None:
            commodity.unit = request.unit.lower()
        if request.aliases is not None:
            commodity.aliases = request.aliases
        if request.hs_codes is not None:
            commodity.hs_codes = request.hs_codes
        if request.price_low is not None:
            commodity.price_low = request.price_low
        if request.price_high is not None:
            commodity.price_high = request.price_high
        if request.current_estimate is not None:
            commodity.current_estimate = request.current_estimate
        if request.verified is not None:
            commodity.verified = request.verified
        if request.is_active is not None:
            commodity.is_active = request.is_active
        
        commodity.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(commodity)
        
        logger.info(f"Updated commodity: {commodity.code}")
        
        return {
            "success": True,
            "commodity": commodity.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update commodity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/commodities/{commodity_id}")
async def delete_commodity(
    commodity_id: str,
    db: Session = Depends(get_db),
    hard_delete: bool = Query(False, description="Permanently delete instead of deactivating"),
):
    """
    Delete or deactivate a commodity.
    By default, soft deletes (deactivates). Use hard_delete=true to permanently remove.
    """
    try:
        commodity = db.query(Commodity).filter(Commodity.id == commodity_id).first()
        if not commodity:
            raise HTTPException(status_code=404, detail="Commodity not found")
        
        if hard_delete:
            db.delete(commodity)
            db.commit()
            logger.info(f"Hard deleted commodity: {commodity.code}")
            return {"success": True, "message": f"Commodity {commodity.code} permanently deleted"}
        else:
            commodity.is_active = False
            commodity.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Deactivated commodity: {commodity.code}")
            return {"success": True, "message": f"Commodity {commodity.code} deactivated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete commodity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMMODITY REQUESTS
# =============================================================================

@router.get("/commodity-requests")
async def list_commodity_requests(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List commodity requests submitted by users.
    """
    try:
        query = db.query(CommodityRequest)
        
        if status:
            query = query.filter(CommodityRequest.status == status)
        
        total = query.count()
        requests = query.order_by(desc(CommodityRequest.created_at)).offset(offset).limit(limit).all()
        
        # Get status counts
        status_counts = {
            "pending": db.query(func.count(CommodityRequest.id)).filter(CommodityRequest.status == "pending").scalar() or 0,
            "approved": db.query(func.count(CommodityRequest.id)).filter(CommodityRequest.status == "approved").scalar() or 0,
            "rejected": db.query(func.count(CommodityRequest.id)).filter(CommodityRequest.status == "rejected").scalar() or 0,
        }
        
        return {
            "success": True,
            "requests": [r.to_dict() for r in requests],
            "total": total,
            "status_counts": status_counts,
        }
        
    except Exception as e:
        logger.error(f"Failed to list commodity requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ReviewRequest(BaseModel):
    """Request model for reviewing a commodity request."""
    action: str = Field(..., description="Action: approve, reject")
    admin_notes: Optional[str] = None
    # If approving, optionally create/link commodity
    create_commodity: bool = Field(default=False)
    commodity_id: Optional[str] = Field(None, description="Existing commodity to link to")


@router.post("/commodity-requests/{request_id}/review")
async def review_commodity_request(
    request_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
):
    """
    Review a commodity request (approve or reject).
    """
    try:
        req = db.query(CommodityRequest).filter(CommodityRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if req.status != "pending":
            raise HTTPException(status_code=400, detail=f"Request already {req.status}")
        
        if review.action == "approve":
            req.status = "approved"
            
            if review.create_commodity:
                # Create new commodity from request
                code = req.requested_name.upper().replace(" ", "_")[:50]
                # Check if code exists
                existing = db.query(Commodity).filter(Commodity.code == code).first()
                if existing:
                    code = f"{code}_{uuid4().hex[:4].upper()}"
                
                commodity = Commodity(
                    id=uuid4(),
                    code=code,
                    name=req.requested_name,
                    category=req.suggested_category or "other",
                    unit=req.suggested_unit or "kg",
                    aliases=[req.requested_name.lower()],
                    hs_codes=[req.suggested_hs_code] if req.suggested_hs_code else [],
                    price_low=req.suggested_price_low,
                    price_high=req.suggested_price_high,
                    verified=True,
                    is_active=True,
                    created_by="admin_from_request",
                )
                db.add(commodity)
                db.flush()
                req.resolved_commodity_id = commodity.id
                
            elif review.commodity_id:
                req.resolved_commodity_id = review.commodity_id
                
        elif review.action == "reject":
            req.status = "rejected"
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
        req.admin_notes = review.admin_notes
        req.reviewed_by = "admin"
        req.reviewed_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(f"Reviewed commodity request {request_id}: {review.action}")
        
        return {
            "success": True,
            "request": req.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to review request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AUDIT LOGS
# =============================================================================

@router.get("/audit-logs")
async def get_audit_logs(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get audit log of price verifications.
    In production, this would query a dedicated audit_logs table.
    For now, we derive from PriceVerification records.
    """
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        verifications = db.query(PriceVerification).filter(
            PriceVerification.created_at >= since
        ).order_by(desc(PriceVerification.created_at)).limit(limit).all()
        
        logs = []
        for v in verifications:
            logs.append({
                "id": str(v.id),
                "timestamp": v.created_at.isoformat() if v.created_at else None,
                "action": "price_verification",
                "resource": f"commodity:{v.commodity_code}",
                "user_id": str(v.user_id) if v.user_id else None,
                "ip_address": v.ip_address,
                "details": {
                    "commodity": v.commodity_name,
                    "document_price": float(v.document_price) if v.document_price else None,
                    "market_price": float(v.market_price) if v.market_price else None,
                    "verdict": v.verdict,
                    "risk_level": v.risk_level,
                },
            })
        
        return {
            "success": True,
            "logs": logs,
            "period_days": days,
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DASHBOARD STATS
# =============================================================================

@router.get("/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
):
    """
    Get admin dashboard statistics.
    """
    try:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Commodity stats
        total_commodities = db.query(func.count(Commodity.id)).scalar() or 0
        verified_commodities = db.query(func.count(Commodity.id)).filter(Commodity.verified == True).scalar() or 0
        
        # Request stats
        pending_requests = db.query(func.count(CommodityRequest.id)).filter(
            CommodityRequest.status == "pending"
        ).scalar() or 0
        
        # Verification stats
        verifications_24h = db.query(func.count(PriceVerification.id)).filter(
            PriceVerification.created_at >= day_ago
        ).scalar() or 0
        
        verifications_7d = db.query(func.count(PriceVerification.id)).filter(
            PriceVerification.created_at >= week_ago
        ).scalar() or 0
        
        high_risk_7d = db.query(func.count(PriceVerification.id)).filter(
            PriceVerification.created_at >= week_ago,
            PriceVerification.risk_level.in_(["high", "critical"])
        ).scalar() or 0
        
        return {
            "success": True,
            "stats": {
                "commodities": {
                    "total": total_commodities,
                    "verified": verified_commodities,
                    "unverified": total_commodities - verified_commodities,
                },
                "requests": {
                    "pending": pending_requests,
                },
                "verifications": {
                    "last_24h": verifications_24h,
                    "last_7d": verifications_7d,
                    "high_risk_7d": high_risk_7d,
                },
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get admin stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
