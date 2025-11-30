"""
Price Verification API Router

Endpoints for verifying trade document prices against market data.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.services.price_verification import (
    get_price_verification_service,
    COMMODITIES_DATABASE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/price-verify", tags=["Price Verification"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SingleVerificationRequest(BaseModel):
    """Request model for single price verification."""
    commodity: str = Field(..., description="Commodity name, code, or HS code")
    price: float = Field(..., gt=0, description="Price per unit from document")
    unit: str = Field(..., description="Unit of measure (kg, mt, bbl, pcs, etc.)")
    currency: str = Field(default="USD", description="Currency code")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity (optional)")
    document_type: Optional[str] = Field(None, description="Type: invoice, lc, contract")
    document_reference: Optional[str] = Field(None, description="Document reference number")
    origin_country: Optional[str] = Field(None, description="ISO 2-letter country code")
    destination_country: Optional[str] = Field(None, description="ISO 2-letter country code")


class BatchItem(BaseModel):
    """Single item in a batch verification request."""
    commodity: str
    price: float = Field(..., gt=0)
    unit: str
    currency: str = Field(default="USD")
    quantity: Optional[float] = Field(None, gt=0)


class BatchVerificationRequest(BaseModel):
    """Request model for batch price verification."""
    items: List[BatchItem] = Field(..., min_length=1, max_length=50)
    document_type: Optional[str] = None
    document_reference: Optional[str] = None


class CommoditySearchRequest(BaseModel):
    """Request model for commodity search."""
    query: str = Field(..., min_length=2, description="Search query")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/commodities")
async def list_commodities(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    List all supported commodities.
    
    Returns list of commodities with their codes, names, categories, and current estimates.
    """
    service = get_price_verification_service()
    commodities = service.list_commodities(category=category)
    
    return {
        "success": True,
        "count": len(commodities),
        "commodities": commodities,
    }


@router.get("/commodities/categories")
async def list_categories():
    """
    List commodity categories.
    
    Returns list of categories with counts.
    """
    service = get_price_verification_service()
    categories = service.get_categories()
    
    return {
        "success": True,
        "categories": categories,
    }


@router.get("/commodities/{code}")
async def get_commodity(code: str):
    """
    Get details for a specific commodity by code.
    """
    commodity = COMMODITIES_DATABASE.get(code.upper())
    if not commodity:
        raise HTTPException(status_code=404, detail=f"Commodity not found: {code}")
    
    return {
        "success": True,
        "commodity": {
            "code": code.upper(),
            **commodity,
        },
    }


@router.post("/commodities/search")
async def search_commodities(request: CommoditySearchRequest):
    """
    Search for commodities by name, alias, or HS code.
    
    Supports fuzzy matching and returns best matches.
    """
    service = get_price_verification_service()
    
    # Try exact match first
    exact_match = service.find_commodity(request.query)
    if exact_match:
        return {
            "success": True,
            "match_type": "exact",
            "commodity": exact_match,
        }
    
    # Get suggestions
    suggestions = service._suggest_commodities(request.query)
    
    return {
        "success": True,
        "match_type": "suggestions",
        "suggestions": suggestions,
    }


@router.get("/market-price/{commodity_code}")
async def get_market_price(commodity_code: str):
    """
    Get current market price for a commodity.
    
    Fetches real-time data from available sources (World Bank, FRED, etc.)
    Falls back to database estimates if APIs unavailable.
    """
    service = get_price_verification_service()
    
    commodity = COMMODITIES_DATABASE.get(commodity_code.upper())
    if not commodity:
        raise HTTPException(status_code=404, detail=f"Commodity not found: {commodity_code}")
    
    result = await service.get_market_price(commodity_code.upper())
    
    return {
        "success": True,
        **result,
    }


@router.post("/verify")
async def verify_single_price(
    request: SingleVerificationRequest,
    req: Request,
):
    """
    Verify a single commodity price against market data.
    
    This is the main verification endpoint. It:
    1. Identifies the commodity from name, code, or HS code
    2. Fetches current market price from available sources
    3. Normalizes prices to same unit/currency for comparison
    4. Calculates variance percentage
    5. Assesses risk level (TBML indicators)
    6. Returns verdict: pass / warning / fail
    
    **Risk Levels:**
    - LOW: Variance < 10%
    - MEDIUM: Variance 10-25%
    - HIGH: Variance 25-50%
    - CRITICAL: Variance > 50% (potential TBML)
    
    **Verdicts:**
    - PASS: Price within ±15% of market
    - WARNING: Price 15-30% off market
    - FAIL: Price >30% off market or TBML flags
    """
    service = get_price_verification_service()
    
    try:
        result = await service.verify_price(
            commodity_input=request.commodity,
            document_price=request.price,
            document_unit=request.unit,
            document_currency=request.currency,
            quantity=request.quantity,
            document_type=request.document_type,
            document_reference=request.document_reference,
            origin_country=request.origin_country,
            destination_country=request.destination_country,
        )
        
        # Log for audit
        logger.info(
            "Price verification: commodity=%s verdict=%s variance=%.2f%%",
            result.get("commodity", {}).get("code"),
            result.get("verdict"),
            result.get("variance", {}).get("percent", 0),
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Price verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/batch")
async def verify_batch_prices(
    request: BatchVerificationRequest,
    req: Request,
):
    """
    Verify multiple commodity prices in a single request.
    
    Useful for verifying entire invoices or LCs with multiple line items.
    Returns individual results for each item plus an overall summary.
    
    **Summary includes:**
    - Pass/warning/fail counts
    - Total document value vs market value
    - Overall variance percentage
    - Maximum risk level across all items
    """
    service = get_price_verification_service()
    
    try:
        items = [item.model_dump() for item in request.items]
        
        result = await service.verify_batch(
            items=items,
            document_type=request.document_type,
            document_reference=request.document_reference,
        )
        
        # Log summary
        logger.info(
            "Batch verification: items=%d passed=%d failed=%d variance=%.2f%%",
            result["summary"]["total_items"],
            result["summary"]["passed"],
            result["summary"]["failed"],
            result["summary"]["overall_variance_percent"],
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Batch verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/units")
async def list_supported_units():
    """
    List supported units of measure and their conversion factors.
    """
    from app.services.price_verification import UNIT_CONVERSIONS
    
    units = []
    categories = {
        "weight": ["kg", "mt", "ton", "lb", "oz", "g"],
        "volume": ["bbl", "gal", "l", "mmbtu"],
        "length": ["m", "yd", "ft"],
        "count": ["pcs", "doz", "gross"],
    }
    
    for category, unit_list in categories.items():
        for unit in unit_list:
            if unit in UNIT_CONVERSIONS:
                units.append({
                    "code": unit,
                    "category": category,
                    "conversion_factor": UNIT_CONVERSIONS[unit],
                })
    
    return {
        "success": True,
        "units": units,
    }


@router.get("/stats")
async def get_verification_stats():
    """
    Get statistics about the price verification system.
    
    Returns counts of supported commodities by category,
    available data sources, and system health.
    """
    service = get_price_verification_service()
    
    # Count by category
    category_counts = {}
    for data in COMMODITIES_DATABASE.values():
        cat = data["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Data sources
    sources = set()
    for data in COMMODITIES_DATABASE.values():
        sources.update(data.get("data_sources", []))
    
    return {
        "success": True,
        "stats": {
            "total_commodities": len(COMMODITIES_DATABASE),
            "categories": category_counts,
            "data_sources": list(sources),
            "supported_currencies": ["USD"],  # TODO: Add more
            "api_status": "operational",
        },
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for the price verification service."""
    return {
        "status": "healthy",
        "service": "price_verification",
        "timestamp": datetime.utcnow().isoformat(),
        "commodities_loaded": len(COMMODITIES_DATABASE),
    }

