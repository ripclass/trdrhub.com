"""
Price Verification API Router

Endpoints for verifying trade document prices against market data.
Includes document upload with OCR extraction.
"""

import io
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Request, File, UploadFile, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.price_verification import (
    get_price_verification_service,
    COMMODITIES_DATABASE,
)
from app.services.price_extraction import get_price_extraction_service
from app.services.ocr_service import get_ocr_service
from app.services.pdf_export import generate_verification_pdf, generate_batch_verification_pdf

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
async def search_commodities(
    request: CommoditySearchRequest,
    use_ai: bool = Query(True, description="Use AI for typo correction and suggestions"),
):
    """
    Search for commodities by name, alias, or HS code.
    
    Supports fuzzy matching and AI-powered suggestions for:
    - Typo correction (e.g., "coton" → "cotton")
    - Trade name variations (e.g., "black gold" → "crude oil")
    - Regional names (e.g., "maize" → "corn")
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
    
    # Get basic suggestions
    suggestions = service._suggest_commodities(request.query)
    
    # If no good suggestions and AI is enabled, try AI suggestion
    ai_suggestion = None
    if use_ai and (not suggestions or suggestions[0].get("score", 0) < 0.5):
        try:
            ai_suggestion = await service.get_ai_commodity_suggestion(request.query)
        except Exception as e:
            logger.warning(f"AI suggestion failed: {e}")
    
    return {
        "success": True,
        "match_type": "ai_suggestion" if ai_suggestion and ai_suggestion.get("matched_commodity") else "suggestions",
        "suggestions": suggestions,
        "ai_suggestion": ai_suggestion,
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


# =============================================================================
# PDF EXPORT
# =============================================================================

@router.post("/verify/pdf")
async def verify_and_export_pdf(
    request: SingleVerificationRequest,
    company_name: Optional[str] = Query(None, description="Company name for report header"),
    include_market_details: bool = Query(True, description="Include market data details"),
):
    """
    Verify a price and export the result as a PDF compliance report.
    
    Returns a downloadable PDF file with:
    - Verification verdict and details
    - Commodity information
    - Price comparison (document vs market)
    - Variance analysis
    - Risk assessment
    - TBML warnings if applicable
    """
    service = get_price_verification_service()
    
    try:
        # First, verify the price
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
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Verification failed")
            )
        
        # Generate PDF
        pdf_bytes = generate_verification_pdf(
            result,
            company_name=company_name,
            include_market_details=include_market_details,
        )
        
        if not pdf_bytes:
            raise HTTPException(
                status_code=500,
                detail="PDF generation failed. ReportLab may not be installed."
            )
        
        # Generate filename
        commodity_code = result.get("commodity", {}).get("code", "unknown")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"price_verify_{commodity_code}_{timestamp}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/batch/pdf")
async def verify_batch_and_export_pdf(
    request: BatchVerificationRequest,
    company_name: Optional[str] = Query(None, description="Company name for report header"),
):
    """
    Verify multiple prices and export results as a PDF compliance report.
    
    Returns a downloadable PDF file with:
    - Summary of all verifications
    - Results table with verdicts
    - Overall compliance assessment
    """
    service = get_price_verification_service()
    
    try:
        items = [item.model_dump() for item in request.items]
        
        result = await service.verify_batch(
            items=items,
            document_type=request.document_type,
            document_reference=request.document_reference,
        )
        
        # Generate PDF
        pdf_bytes = generate_batch_verification_pdf(
            result,
            company_name=company_name,
        )
        
        if not pdf_bytes:
            raise HTTPException(
                status_code=500,
                detail="PDF generation failed. ReportLab may not be installed."
            )
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        item_count = len(request.items)
        filename = f"price_verify_batch_{item_count}items_{timestamp}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/explain-variance")
async def explain_variance_with_ai(request: SingleVerificationRequest):
    """
    Get an AI-generated explanation for a price variance.
    
    Returns professional compliance-ready explanation including:
    - Summary assessment
    - Possible legitimate reasons for variance
    - Documentation recommendations
    - Action recommendation (approve/review/escalate)
    """
    service = get_price_verification_service()
    
    try:
        # First verify to get variance data
        result = await service.verify_price(
            commodity_input=request.commodity,
            document_price=request.price,
            document_unit=request.unit,
            document_currency=request.currency,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        # Get AI explanation (already included in result if verdict is warning/fail)
        ai_explanation = result.get("ai_explanation")
        
        if not ai_explanation:
            # Generate explanation for any result
            from app.services.price_ai import get_price_ai_service
            ai_service = get_price_ai_service()
            
            ai_explanation = await ai_service.explain_variance(
                commodity_name=result["commodity"]["name"],
                commodity_code=result["commodity"]["code"],
                category=result["commodity"]["category"],
                doc_price=result["document_price"]["normalized_price"],
                market_price=result["market_price"]["price"],
                unit=result["document_price"]["normalized_unit"],
                variance_percent=result["variance"]["percent"],
                risk_level=result["risk"]["risk_level"],
            )
        
        return {
            "success": True,
            "verification_summary": {
                "commodity": result["commodity"]["name"],
                "variance_percent": result["variance"]["percent"],
                "verdict": result["verdict"],
                "risk_level": result["risk"]["risk_level"],
            },
            "ai_explanation": ai_explanation,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI explanation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/tbml-assessment")
async def get_tbml_assessment(request: SingleVerificationRequest):
    """
    Get an AI-generated TBML (Trade-Based Money Laundering) risk assessment.
    
    Returns professional compliance narrative including:
    - TBML type identification (over/under invoicing)
    - Risk score (1-10)
    - Detailed compliance narrative
    - Red flags identified
    - Recommended due diligence steps
    - Regulatory references
    
    Note: This is only meaningful for high-variance transactions (>50%).
    """
    service = get_price_verification_service()
    
    try:
        # First verify to get variance data
        result = await service.verify_price(
            commodity_input=request.commodity,
            document_price=request.price,
            document_unit=request.unit,
            document_currency=request.currency,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        variance_percent = result["variance"]["percent"]
        
        # Check if TBML assessment is warranted
        if abs(variance_percent) < 30:
            return {
                "success": True,
                "tbml_assessment_needed": False,
                "message": f"Variance of {abs(variance_percent):.1f}% is below TBML threshold (30%). No TBML assessment required.",
                "verification_summary": {
                    "commodity": result["commodity"]["name"],
                    "variance_percent": variance_percent,
                    "verdict": result["verdict"],
                },
            }
        
        # Get TBML assessment (may already be in result)
        tbml_assessment = result.get("tbml_assessment")
        
        if not tbml_assessment:
            from app.services.price_ai import get_price_ai_service
            ai_service = get_price_ai_service()
            
            tbml_assessment = await ai_service.generate_tbml_narrative(
                commodity_name=result["commodity"]["name"],
                doc_price=result["document_price"]["normalized_price"],
                market_price=result["market_price"]["price"],
                unit=result["document_price"]["normalized_unit"],
                variance_percent=variance_percent,
                risk_flags=result["risk"].get("risk_flags", []),
            )
        
        return {
            "success": True,
            "tbml_assessment_needed": True,
            "verification_summary": {
                "commodity": result["commodity"]["name"],
                "variance_percent": variance_percent,
                "verdict": result["verdict"],
                "risk_level": result["risk"]["risk_level"],
                "risk_flags": result["risk"].get("risk_flags", []),
            },
            "tbml_assessment": tbml_assessment,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TBML assessment error: {e}", exc_info=True)
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


@router.get("/currencies")
async def list_supported_currencies():
    """
    List supported currencies with their exchange rates to USD.
    
    Rates are fetched from external APIs when available,
    falling back to cached values.
    """
    from app.services.price_verification import get_fx_rates, FALLBACK_FX_RATES, _fx_rate_cache
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            rates = await get_fx_rates(client)
    except Exception:
        rates = FALLBACK_FX_RATES
    
    currencies = []
    for code, rate in rates.items():
        currencies.append({
            "code": code,
            "rate_to_usd": rate,
            "usd_to_rate": round(1 / rate, 6) if rate != 0 else 0,
        })
    
    return {
        "success": True,
        "base_currency": "USD",
        "rate_source": _fx_rate_cache.get("source", "fallback"),
        "last_updated": _fx_rate_cache.get("timestamp").isoformat() if _fx_rate_cache.get("timestamp") else None,
        "currencies": sorted(currencies, key=lambda x: x["code"]),
    }


@router.get("/convert")
async def convert_currency_endpoint(
    amount: float = Query(..., gt=0, description="Amount to convert"),
    from_currency: str = Query(..., description="Source currency code (e.g., EUR, GBP)"),
    to_currency: str = Query("USD", description="Target currency code"),
):
    """
    Convert an amount between currencies.
    
    Uses real-time exchange rates when available.
    """
    from app.services.price_verification import get_fx_rates, convert_currency, _fx_rate_cache
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            rates = await get_fx_rates(client)
    except Exception:
        from app.services.price_verification import FALLBACK_FX_RATES
        rates = FALLBACK_FX_RATES
    
    converted_amount, source = convert_currency(
        amount,
        from_currency,
        to_currency,
        rates
    )
    
    return {
        "success": True,
        "original": {
            "amount": amount,
            "currency": from_currency.upper(),
        },
        "converted": {
            "amount": converted_amount,
            "currency": to_currency.upper(),
        },
        "rate_source": source,
        "timestamp": datetime.utcnow().isoformat(),
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
    
    from app.services.price_verification import FALLBACK_FX_RATES
    
    return {
        "success": True,
        "stats": {
            "total_commodities": len(COMMODITIES_DATABASE),
            "categories": category_counts,
            "data_sources": list(sources),
            "supported_currencies": list(FALLBACK_FX_RATES.keys()),
            "api_status": "operational",
        },
    }


# =============================================================================
# DOCUMENT UPLOAD + OCR EXTRACTION
# =============================================================================

@router.post("/extract")
async def extract_prices_from_document(
    file: UploadFile = File(..., description="Invoice, LC, or contract document"),
    auto_verify: bool = Form(True, description="Automatically verify extracted prices"),
):
    """
    Upload a trade document and extract commodity prices using OCR + AI.
    
    **Supported Documents:**
    - Commercial Invoices (PDF, JPG, PNG)
    - Letters of Credit (PDF)
    - Purchase Contracts (PDF)
    - Proforma Invoices (PDF)
    
    **Process:**
    1. OCR extracts text from document
    2. AI identifies commodities, quantities, and prices
    3. (Optional) Auto-verifies prices against market data
    
    **Returns:**
    - Extracted line items with commodity, price, quantity, unit
    - Document metadata (seller, buyer, reference)
    - Verification results if auto_verify=true
    """
    # Validate file type
    allowed_types = {
        'application/pdf', 
        'image/jpeg', 
        'image/png', 
        'image/tiff',
    }
    
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        # Check file extension as fallback
        filename = file.filename or ""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext not in ["pdf", "jpg", "jpeg", "png", "tiff"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, JPG, PNG, TIFF"
            )
    
    # Read file content
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size: 20MB"
        )
    
    logger.info(f"Processing price extraction: file={file.filename}, size={len(content)} bytes")
    
    try:
        # Step 1: OCR extraction
        ocr_service = get_ocr_service()
        ocr_result = await ocr_service.extract_text(
            content=content,
            filename=file.filename,
            content_type=content_type,
        )
        
        if not ocr_result.get("text"):
            error_detail = ocr_result.get("error", "Unknown OCR error")
            provider = ocr_result.get("provider", "unknown")
            
            # Provide helpful error message
            if "image-based" in error_detail.lower() or "scanned" in error_detail.lower():
                detail = "This PDF appears to be scanned/image-based. Please try uploading a text-based PDF or use manual entry."
            elif "not available" in error_detail.lower():
                detail = "OCR service is temporarily unavailable. Please try manual entry instead."
            else:
                detail = f"Could not extract text from document ({provider}). {error_detail}"
            
            logger.warning(f"OCR failed for {file.filename}: {error_detail}")
            raise HTTPException(status_code=422, detail=detail)
        
        raw_text = ocr_result.get("text", "")
        logger.info(f"OCR extracted {len(raw_text)} characters")
        
        # Step 2: AI price extraction
        price_service = get_price_extraction_service()
        extraction_result = await price_service.extract_prices_from_text(
            raw_text=raw_text,
            filename=file.filename,
        )
        
        response = {
            "success": extraction_result.success,
            "extraction": extraction_result.to_dict(),
            "ocr_metadata": {
                "chars_extracted": len(raw_text),
                "confidence": ocr_result.get("confidence", 0),
            },
        }
        
        # Step 3: Auto-verify if requested
        if auto_verify and extraction_result.success and extraction_result.line_items:
            verification_service = get_price_verification_service()
            verification_results = []
            
            for item in extraction_result.line_items:
                if item.unit_price and item.commodity_name:
                    try:
                        verification = await verification_service.verify_price(
                            commodity_input=item.commodity_name,
                            document_price=item.unit_price,
                            document_unit=item.unit or "kg",
                            document_currency=item.currency,
                            quantity=item.quantity,
                            document_type=extraction_result.document_type,
                        )
                        verification_results.append(verification)
                    except Exception as e:
                        logger.warning(f"Verification failed for {item.commodity_name}: {e}")
                        verification_results.append({
                            "commodity_input": item.commodity_name,
                            "error": str(e),
                            "verdict": "UNKNOWN",
                        })
            
            response["verifications"] = verification_results
            
            # Summary
            if verification_results:
                passed = sum(1 for v in verification_results if v.get("verdict") == "PASS")
                warnings = sum(1 for v in verification_results if v.get("verdict") == "WARNING")
                failed = sum(1 for v in verification_results if v.get("verdict") == "FAIL")
                
                response["summary"] = {
                    "total_items": len(verification_results),
                    "passed": passed,
                    "warnings": warnings,
                    "failed": failed,
                    "tbml_flags": sum(1 for v in verification_results if v.get("tbml_flag")),
                }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Price extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/extract/batch")
async def extract_batch_documents(
    files: List[UploadFile] = File(..., description="Multiple trade documents"),
    auto_verify: bool = Form(True, description="Automatically verify extracted prices"),
):
    """
    Upload multiple documents for batch price extraction.
    
    Processes up to 10 documents in a single request.
    Returns extraction results and optional verification for each document.
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 documents per batch"
        )
    
    results = []
    
    for file in files:
        try:
            # Process each file
            content = await file.read()
            await file.seek(0)  # Reset for potential reprocessing
            
            # Simplified extraction for batch (skip detailed OCR metadata)
            ocr_service = get_ocr_service()
            ocr_result = await ocr_service.extract_text(
                content=content,
                filename=file.filename,
                content_type=file.content_type,
            )
            
            raw_text = ocr_result.get("text", "")
            
            price_service = get_price_extraction_service()
            extraction_result = await price_service.extract_prices_from_text(
                raw_text=raw_text,
                filename=file.filename,
            )
            
            file_result = {
                "filename": file.filename,
                "success": extraction_result.success,
                "line_items": [item.to_dict() for item in extraction_result.line_items],
                "document_type": extraction_result.document_type,
            }
            
            # Auto-verify if requested
            if auto_verify and extraction_result.line_items:
                verification_service = get_price_verification_service()
                verifications = []
                
                for item in extraction_result.line_items:
                    if item.unit_price and item.commodity_name:
                        try:
                            verification = await verification_service.verify_price(
                                commodity_input=item.commodity_name,
                                document_price=item.unit_price,
                                document_unit=item.unit or "kg",
                                document_currency=item.currency,
                            )
                            verifications.append({
                                "commodity": item.commodity_name,
                                "verdict": verification.get("verdict"),
                                "variance_percent": verification.get("variance", {}).get("percent"),
                            })
                        except Exception as e:
                            logger.warning(f"Batch verification error: {e}")
                
                file_result["verifications"] = verifications
            
            results.append(file_result)
            
        except Exception as e:
            logger.error(f"Batch extraction error for {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })
    
    # Overall summary
    total_items = sum(len(r.get("line_items", [])) for r in results if r.get("success"))
    successful_files = sum(1 for r in results if r.get("success"))
    
    return {
        "success": True,
        "batch_summary": {
            "total_files": len(files),
            "successful_files": successful_files,
            "failed_files": len(files) - successful_files,
            "total_line_items_extracted": total_items,
        },
        "results": results,
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

