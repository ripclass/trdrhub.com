"""
Sanctions Screening API Router

Endpoints for screening parties, vessels, and goods against sanctions lists.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
import io

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user, get_optional_user
from app.services.sanctions_screening import (
    get_screening_service,
    ScreeningInput,
    ComprehensiveScreeningResult,
    normalize_name,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sanctions", tags=["sanctions-screener"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PartyScreenRequest(BaseModel):
    """Request to screen a party/entity."""
    name: str = Field(..., min_length=2, max_length=500, description="Party name to screen")
    country: Optional[str] = Field(default=None, max_length=2, description="Country code (ISO 2-letter)")
    lists: List[str] = Field(default=[], description="Specific lists to screen against (empty = all)")


class VesselScreenRequest(BaseModel):
    """Request to screen a vessel."""
    name: str = Field(..., min_length=2, max_length=200, description="Vessel name")
    imo: Optional[str] = Field(default=None, description="IMO number")
    mmsi: Optional[str] = Field(default=None, description="MMSI number")
    flag_state: Optional[str] = Field(default=None, description="Flag state name")
    flag_code: Optional[str] = Field(default=None, max_length=2, description="Flag state ISO code")
    lists: List[str] = Field(default=[], description="Specific lists to screen against")


class GoodsScreenRequest(BaseModel):
    """Request to screen goods."""
    description: str = Field(..., min_length=3, max_length=2000, description="Goods description")
    hs_code: Optional[str] = Field(default=None, description="HS code if known")
    destination_country: Optional[str] = Field(default=None, max_length=2, description="Destination country code")


class BatchScreenRequest(BaseModel):
    """Request for batch screening."""
    items: List[Dict[str, Any]] = Field(..., max_length=100, description="Items to screen")
    screening_type: str = Field(default="party", description="Type: party, vessel, goods")
    lists: List[str] = Field(default=[], description="Lists to screen against")


class ScreeningMatch(BaseModel):
    """Individual match in results."""
    list_code: str
    list_name: str
    matched_name: str
    matched_type: str
    match_type: str
    match_score: float
    match_method: str
    programs: List[str] = []
    country: Optional[str] = None
    source_id: Optional[str] = None
    listed_date: Optional[str] = None
    remarks: Optional[str] = None


class ScreeningResponse(BaseModel):
    """Screening result response."""
    query: str
    screening_type: str
    screened_at: str
    status: str
    risk_level: str
    lists_screened: List[str]
    matches: List[ScreeningMatch]
    total_matches: int
    highest_score: float
    flags: List[str]
    recommendation: str
    certificate_id: str
    processing_time_ms: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/lists")
async def get_available_lists():
    """
    Get available sanctions lists for screening.
    """
    service = get_screening_service()
    lists = service.get_available_lists()
    
    return {
        "lists": [
            {
                "code": code,
                "name": info["name"],
                "jurisdiction": info["jurisdiction"],
            }
            for code, info in lists.items()
        ],
        "default_lists": list(lists.keys()),
    }


@router.post("/screen/party", response_model=ScreeningResponse)
async def screen_party(
    request: PartyScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen a party/entity name against sanctions lists.
    
    Returns match results with confidence scores and recommendations.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.name,
        screening_type="party",
        country=request.country,
        lists=request.lists,
    )
    
    result = await service.screen(input_data)
    
    # TODO: Save to database if user authenticated
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/vessel", response_model=ScreeningResponse)
async def screen_vessel(
    request: VesselScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen a vessel against sanctions lists.
    
    Includes flag state risk assessment.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.name,
        screening_type="vessel",
        lists=request.lists,
        additional_data={
            "imo": request.imo,
            "mmsi": request.mmsi,
            "flag_state": request.flag_state,
            "flag_code": request.flag_code,
        },
    )
    
    result = await service.screen(input_data)
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/goods", response_model=ScreeningResponse)
async def screen_goods(
    request: GoodsScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen goods for export control and sanctions implications.
    
    Checks destination country sanctions and dual-use indicators.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.description,
        screening_type="goods",
        country=request.destination_country,
        additional_data={
            "hs_code": request.hs_code,
        },
    )
    
    result = await service.screen(input_data)
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/batch")
async def batch_screen(
    request: BatchScreenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch screening for multiple entities.
    
    Requires authentication. Max 100 items per request.
    """
    service = get_screening_service()
    
    results = []
    for item in request.items:
        query = item.get("name") or item.get("query") or item.get("description")
        if not query:
            results.append({"error": "Missing name/query field", "item": item})
            continue
        
        input_data = ScreeningInput(
            query=query,
            screening_type=request.screening_type,
            country=item.get("country"),
            lists=request.lists,
            additional_data=item,
        )
        
        try:
            result = await service.screen(input_data)
            results.append({
                "query": result.query,
                "status": result.status,
                "risk_level": result.risk_level,
                "total_matches": result.total_matches,
                "highest_score": result.highest_score,
                "certificate_id": result.certificate_id,
            })
        except Exception as e:
            logger.error(f"Error screening {query}: {e}")
            results.append({"error": str(e), "query": query})
    
    # Summary
    clear_count = sum(1 for r in results if r.get("status") == "clear")
    match_count = sum(1 for r in results if r.get("status") == "match")
    potential_count = sum(1 for r in results if r.get("status") == "potential_match")
    
    return {
        "total": len(results),
        "clear": clear_count,
        "potential_match": potential_count,
        "match": match_count,
        "errors": sum(1 for r in results if "error" in r),
        "results": results,
    }


@router.get("/certificate/{certificate_id}")
async def get_certificate(
    certificate_id: str,
    format: str = Query(default="json", regex="^(json|pdf)$"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve screening certificate by ID.
    
    Returns compliance certificate in JSON or PDF format.
    """
    # TODO: Look up certificate from database
    # For now, return a sample certificate structure
    
    return {
        "certificate_id": certificate_id,
        "type": "sanctions_screening_certificate",
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "valid_for_hours": 24,
        "disclaimer": (
            "This certificate confirms that a sanctions screening was performed "
            "at the specified time. Results should be verified with your compliance team. "
            "TRDR Sanctions Screener is a screening aid, not legal advice."
        ),
        "status": "Certificate lookup not yet implemented",
    }


@router.get("/history")
async def get_screening_history(
    limit: int = Query(default=20, le=100),
    screening_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's screening history.
    
    Requires authentication.
    """
    # TODO: Query from database
    # For now, return empty history
    
    return {
        "total": 0,
        "screenings": [],
        "note": "Screening history not yet implemented - results are not persisted",
    }


@router.get("/countries/sanctioned")
async def get_sanctioned_countries():
    """
    Get list of comprehensively sanctioned countries.
    """
    from app.services.sanctions_screening import SANCTIONED_COUNTRIES
    
    return {
        "countries": [
            {
                "code": code,
                "name": info["name"],
                "type": info["type"],
                "programs": info["programs"],
            }
            for code, info in SANCTIONED_COUNTRIES.items()
        ],
    }


@router.post("/quick-screen")
async def quick_screen(
    query: str = Query(..., min_length=2, description="Name to screen"),
    type: str = Query(default="party", regex="^(party|vessel|goods)$"),
    country: Optional[str] = Query(default=None, max_length=2),
):
    """
    Quick screening endpoint for simple lookups.
    
    No authentication required. For quick checks.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=query,
        screening_type=type,
        country=country,
    )
    
    result = await service.screen(input_data)
    
    return {
        "query": query,
        "status": result.status,
        "risk_level": result.risk_level,
        "total_matches": result.total_matches,
        "highest_score": result.highest_score,
        "recommendation": result.recommendation,
        "certificate_id": result.certificate_id,
    }


@router.get("/stats")
async def get_screening_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's screening statistics.
    """
    # TODO: Calculate from database
    
    return {
        "total_screenings": 0,
        "this_month": 0,
        "clear_rate": 0,
        "match_rate": 0,
        "most_common_lists": [],
        "note": "Statistics not yet implemented",
    }

