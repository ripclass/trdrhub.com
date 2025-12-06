"""
HS Code Finder API Router

Endpoints for AI-powered HS code classification, duty rates, and FTA eligibility.
"""

import logging
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user, get_optional_user
from app.models.hs_code import (
    HSCodeTariff, DutyRate, FTAAgreement, FTARule,
    HSClassification, HSCodeSearch, ClassificationSource
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hs-code", tags=["hs-code-finder"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ClassifyRequest(BaseModel):
    """Request to classify a product"""
    description: str = Field(..., min_length=3, max_length=2000, description="Product description")
    import_country: str = Field(default="US", description="Import destination (ISO 2-letter)")
    export_country: Optional[str] = Field(default=None, description="Export origin (ISO 2-letter)")
    product_value: Optional[float] = Field(default=None, description="Product value for duty calc")
    quantity: Optional[float] = Field(default=None, description="Quantity")
    quantity_unit: Optional[str] = Field(default=None, description="Unit (kg, pieces, etc.)")


class ClassifyResponse(BaseModel):
    """Classification result"""
    hs_code: str
    description: str
    confidence: float
    chapter: str
    heading: str
    subheading: str
    alternatives: List[Dict[str, Any]]
    duty_rates: Dict[str, Any]
    fta_options: List[Dict[str, Any]]
    restrictions: List[str]
    ai_reasoning: str


class DutyCalculateRequest(BaseModel):
    """Request to calculate duties"""
    hs_code: str
    import_country: str = "US"
    export_country: Optional[str] = None
    product_value: float
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    fta_code: Optional[str] = None


class SaveClassificationRequest(BaseModel):
    """Request to save a classification"""
    product_description: str
    product_name: Optional[str] = None
    hs_code: str
    import_country: str
    export_country: Optional[str] = None
    product_value: Optional[float] = None
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    project_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


# ============================================================================
# AI Classification Service
# ============================================================================

# Import the classification service
try:
    from app.services.hs_classification import HSClassificationService
    CLASSIFICATION_SERVICE_AVAILABLE = True
except ImportError:
    CLASSIFICATION_SERVICE_AVAILABLE = False
    logger.warning("HSClassificationService not available - using fallback")


async def classify_with_ai(db: Session, description: str, import_country: str, export_country: Optional[str] = None) -> Dict[str, Any]:
    """
    AI-powered HS code classification.
    Uses OpenAI when available, falls back to database search.
    """
    # Try to use the classification service
    if CLASSIFICATION_SERVICE_AVAILABLE:
        try:
            service = HSClassificationService(db)
            result = await service.classify_product(
                description=description,
                import_country=import_country,
                export_country=export_country
            )
            
            # Get duty rates
            rates = await service.get_duty_rates(
                result["hs_code"],
                import_country,
                export_country
            )
            result["duty_rates"] = {
                "mfn": rates.get("mfn_rate", 0),
                "preferential": rates.get("preferential_rates", {}),
                "section_301": rates.get("section_301_rate", 0),
                "total": rates.get("total_rate", 0),
            }
            
            return result
        except Exception as e:
            logger.error(f"Classification service error: {e}")
    
    # Fallback to database keyword search
    return await fallback_classify(db, description, import_country)


async def fallback_classify(db: Session, description: str, import_country: str) -> Dict[str, Any]:
    """
    Fallback classification using database keyword search.
    """
    desc_lower = description.lower()
    
    # Try to find matches in database
    results = db.query(HSCodeTariff).filter(
        HSCodeTariff.country_code == import_country,
        HSCodeTariff.is_active == True,
        or_(
            HSCodeTariff.description.ilike(f"%{desc_lower[:50]}%"),
            func.lower(HSCodeTariff.description).contains(desc_lower[:30])
        )
    ).limit(10).all()
    
    if results:
        best = results[0]
        alternatives = []
        for r in results[1:5]:
            alternatives.append({
                "code": r.code,
                "description": r.description,
                "score": 0.5
            })
        
        # Get duty rate
        duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == best.id,
            DutyRate.rate_type == "mfn",
            DutyRate.is_active == True
        ).first()
        
        mfn_rate = duty.ad_valorem_rate if duty else 0
        
        return {
            "hs_code": best.code,
            "description": best.description,
            "confidence": 0.6,
            "chapter": best.chapter_description or f"Chapter {best.code_2}",
            "heading": best.heading_description or "",
            "subheading": best.code_6 or best.code[:6],
            "alternatives": alternatives,
            "duty_rates": {"mfn": mfn_rate},
            "reasoning": f"Matched by keyword search. Found {len(results)} potential matches in database.",
            "source": "database_fallback"
        }
    
    # Return unknown if nothing found
    return {
        "hs_code": "9999.99.9999",
        "description": "Unclassified - requires manual review",
        "confidence": 0.1,
        "chapter": "Chapter 99 - Special classification provisions",
        "heading": "",
        "subheading": "",
        "alternatives": [],
        "duty_rates": {"mfn": 0},
        "reasoning": "No matching classification found. Please provide more detailed product description or contact customs specialist.",
        "source": "fallback_default"
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/classify", response_model=ClassifyResponse)
async def classify_product(
    request: ClassifyRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    AI-powered HS code classification.
    Describe your product in plain language and get the correct HS code.
    """
    start_time = time.time()
    
    # Run AI classification (now uses service)
    result = await classify_with_ai(
        db=db,
        description=request.description,
        import_country=request.import_country,
        export_country=request.export_country
    )
    
    # Get FTA options from database
    fta_options = []
    if request.export_country:
        ftas = db.query(FTAAgreement).filter(
            FTAAgreement.is_active == True,
            FTAAgreement.member_countries.contains([request.export_country]),
            FTAAgreement.member_countries.contains([request.import_country])
        ).all()
        
        for fta in ftas:
            # Get preferential rate if exists
            fta_rule = db.query(FTARule).filter(
                FTARule.fta_id == fta.id,
                FTARule.hs_code_prefix == result["hs_code"][:2]
            ).first()
            
            fta_options.append({
                "code": fta.code,
                "name": fta.name,
                "preferential_rate": fta_rule.preferential_rate if fta_rule else 0,
                "savings_percent": result["duty_rates"].get("mfn", 0) - (fta_rule.preferential_rate if fta_rule else 0),
                "certificate_types": fta.certificate_types,
            })
    
    # Check restrictions (expand with actual database lookup)
    restrictions = []
    desc_lower = request.description.lower()
    
    if any(kw in desc_lower for kw in ["medicine", "drug", "pharmaceutical"]):
        restrictions.append("FDA approval required for pharmaceutical imports")
    if any(kw in desc_lower for kw in ["firearm", "weapon", "ammunition"]):
        restrictions.append("Import license required from ATF")
    if any(kw in desc_lower for kw in ["alcohol", "wine", "beer", "spirits"]):
        restrictions.append("TTB permit and state licensing required")
    if any(kw in desc_lower for kw in ["pesticide", "chemical", "hazardous"]):
        restrictions.append("EPA approval may be required")
    if any(kw in desc_lower for kw in ["food", "meat", "poultry", "dairy"]):
        restrictions.append("USDA/FSIS inspection required")
    
    # Log search for analytics
    response_time = int((time.time() - start_time) * 1000)
    background_tasks.add_task(
        log_search,
        db=db,
        query=request.description,
        user_id=str(current_user.id) if current_user else None,
        result_code=result["hs_code"],
        import_country=request.import_country,
        export_country=request.export_country,
        response_time=response_time,
    )
    
    return ClassifyResponse(
        hs_code=result["hs_code"],
        description=result["description"],
        confidence=result["confidence"],
        chapter=result.get("chapter", ""),
        heading=result.get("heading", ""),
        subheading=result.get("subheading", ""),
        alternatives=result.get("alternatives", []),
        duty_rates=result.get("duty_rates", {}),
        fta_options=fta_options,
        restrictions=restrictions,
        ai_reasoning=result.get("reasoning", ""),
    )


@router.get("/search")
async def search_hs_codes(
    q: str = Query(..., min_length=2, description="Search query (code or description)"),
    country: str = Query(default="US", description="Country schedule"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    Search HS codes by code number or description.
    """
    q_clean = q.strip()
    is_code_search = q_clean.replace(".", "").isdigit()
    
    if is_code_search:
        # Code search - find codes starting with query
        code_prefix = q_clean.replace(".", "")
        tariffs = db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == country,
            HSCodeTariff.is_active == True,
            HSCodeTariff.code.like(f"{code_prefix}%")
        ).order_by(HSCodeTariff.code).limit(limit).all()
    else:
        # Description/keyword search
        tariffs = db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == country,
            HSCodeTariff.is_active == True,
            or_(
                HSCodeTariff.description.ilike(f"%{q_clean}%"),
                HSCodeTariff.heading_description.ilike(f"%{q_clean}%"),
                HSCodeTariff.chapter_description.ilike(f"%{q_clean}%")
            )
        ).limit(limit).all()
    
    results = []
    for t in tariffs:
        # Get MFN duty rate
        duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == t.id,
            DutyRate.rate_type == "mfn"
        ).first()
        
        results.append({
            "code": t.code,
            "description": t.description,
            "chapter": t.chapter_description or f"Chapter {t.code_2}",
            "heading": t.heading_description or "",
            "unit": t.unit_of_quantity,
            "mfn_rate": duty.ad_valorem_rate if duty else 0,
        })
    
    return {
        "query": q,
        "country": country,
        "results": results,
        "count": len(results),
    }


@router.get("/code/{hs_code}")
async def get_hs_code_details(
    hs_code: str,
    import_country: str = Query(default="US"),
    export_country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific HS code.
    """
    # Find the tariff code in database
    tariff = db.query(HSCodeTariff).filter(
        HSCodeTariff.code == hs_code,
        HSCodeTariff.country_code == import_country,
        HSCodeTariff.is_active == True
    ).first()
    
    # Try partial match if exact not found
    if not tariff:
        code_prefix = hs_code.replace(".", "")
        tariff = db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == import_country,
            HSCodeTariff.is_active == True,
            HSCodeTariff.code.like(f"{code_prefix}%")
        ).first()
    
    if not tariff:
        raise HTTPException(status_code=404, detail=f"HS code {hs_code} not found")
    
    # Get all duty rates for this code
    duty_rates = db.query(DutyRate).filter(
        DutyRate.hs_code_id == tariff.id,
        DutyRate.is_active == True
    ).all()
    
    rates_by_origin = {}
    mfn_rate = 0
    for rate in duty_rates:
        if rate.rate_type == "mfn":
            mfn_rate = rate.ad_valorem_rate or 0
        elif rate.origin_country:
            rates_by_origin[rate.origin_country] = {
                "rate": rate.ad_valorem_rate or 0,
                "code": rate.rate_code
            }
    
    # Check Section 301 rates (US-China)
    from app.models.hs_code import Section301Rate
    section_301 = None
    if import_country == "US" and export_country == "CN":
        s301 = db.query(Section301Rate).filter(
            Section301Rate.hs_code == hs_code,
            Section301Rate.origin_country == "CN",
            Section301Rate.is_active == True,
            Section301Rate.is_excluded == False
        ).first()
        if s301:
            section_301 = {
                "list": s301.list_number,
                "rate": s301.additional_rate
            }
    
    # Get FTA options
    fta_options = []
    if export_country:
        ftas = db.query(FTAAgreement).filter(
            FTAAgreement.is_active == True,
            FTAAgreement.member_countries.contains([export_country]),
            FTAAgreement.member_countries.contains([import_country])
        ).all()
        
        for fta in ftas:
            fta_rule = db.query(FTARule).filter(
                FTARule.fta_id == fta.id,
                or_(
                    FTARule.hs_code_prefix == tariff.code_2,
                    FTARule.hs_code_prefix == tariff.code_4,
                    FTARule.hs_code_prefix == tariff.code_6
                )
            ).first()
            
            fta_options.append({
                "code": fta.code,
                "name": fta.name,
                "preferential_rate": fta_rule.preferential_rate if fta_rule else 0,
                "certificate_types": fta.certificate_types,
                "rule_of_origin": {
                    "type": fta_rule.rule_type if fta_rule else None,
                    "text": fta_rule.rule_text if fta_rule else None,
                } if fta_rule else None
            })
    
    # Get related codes (same chapter)
    related = db.query(HSCodeTariff).filter(
        HSCodeTariff.code_4 == tariff.code_4,
        HSCodeTariff.id != tariff.id,
        HSCodeTariff.country_code == import_country
    ).limit(5).all()
    
    return {
        "code": tariff.code,
        "description": tariff.description,
        "chapter": tariff.chapter_description or f"Chapter {tariff.code_2}",
        "heading": tariff.heading_description or "",
        "subheading": tariff.subheading_description or "",
        "unit_of_quantity": tariff.unit_of_quantity,
        "unit_of_quantity_2": tariff.unit_of_quantity_2,
        "general_notes": tariff.general_notes,
        "special_notes": tariff.special_notes,
        "requires_license": tariff.requires_license,
        "quota_applicable": tariff.quota_applicable,
        "duty_rates": {
            "import_country": import_country,
            "mfn_rate": mfn_rate,
            "rates_by_origin": rates_by_origin,
            "section_301": section_301,
        },
        "fta_options": fta_options,
        "related_codes": [{"code": r.code, "description": r.description} for r in related],
    }


@router.post("/calculate-duty")
async def calculate_duty(
    request: DutyCalculateRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate import duties for a product.
    """
    from app.models.hs_code import Section301Rate
    
    # Find the tariff code
    tariff = db.query(HSCodeTariff).filter(
        HSCodeTariff.code == request.hs_code,
        HSCodeTariff.country_code == request.import_country,
        HSCodeTariff.is_active == True
    ).first()
    
    if not tariff:
        # Try partial match
        code_prefix = request.hs_code.replace(".", "")[:8]
        tariff = db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == request.import_country,
            HSCodeTariff.is_active == True,
            HSCodeTariff.code.like(f"{code_prefix}%")
        ).first()
    
    # Get MFN rate
    mfn_rate = 0
    if tariff:
        mfn_duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == tariff.id,
            DutyRate.rate_type == "mfn",
            DutyRate.is_active == True
        ).first()
        if mfn_duty:
            mfn_rate = mfn_duty.ad_valorem_rate or 0
    
    # Determine applicable rate
    applicable_rate = mfn_rate
    rate_type = "MFN"
    
    # Check FTA preferential rate
    if request.fta_code:
        fta = db.query(FTAAgreement).filter(
            FTAAgreement.code == request.fta_code,
            FTAAgreement.is_active == True
        ).first()
        if fta:
            fta_rule = db.query(FTARule).filter(
                FTARule.fta_id == fta.id,
                or_(
                    FTARule.hs_code_prefix == request.hs_code[:2],
                    FTARule.hs_code_prefix == request.hs_code[:4]
                )
            ).first()
            if fta_rule and fta_rule.preferential_rate is not None:
                applicable_rate = fta_rule.preferential_rate
                rate_type = request.fta_code
    elif request.export_country and tariff:
        # Check for GSP or other preferential
        pref_duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == tariff.id,
            DutyRate.origin_country == request.export_country,
            DutyRate.is_active == True
        ).first()
        if pref_duty and pref_duty.ad_valorem_rate is not None:
            applicable_rate = pref_duty.ad_valorem_rate
            rate_type = pref_duty.rate_code or "Preferential"
    
    # Check Section 301 additional tariff
    section_301_rate = 0
    section_301_list = None
    if request.import_country == "US" and request.export_country == "CN":
        s301 = db.query(Section301Rate).filter(
            Section301Rate.hs_code == request.hs_code,
            Section301Rate.origin_country == "CN",
            Section301Rate.is_active == True,
            Section301Rate.is_excluded == False
        ).first()
        if s301:
            section_301_rate = s301.additional_rate
            section_301_list = s301.list_number
    
    # Calculate duties
    base_duty = request.product_value * (applicable_rate / 100)
    additional_duty = request.product_value * (section_301_rate / 100)
    total_duty = base_duty + additional_duty
    
    # MFN comparison
    mfn_duty_amount = request.product_value * (mfn_rate / 100) + additional_duty
    savings = mfn_duty_amount - total_duty
    
    # Landed cost estimate
    estimated_freight = request.product_value * 0.05  # 5% estimate
    estimated_insurance = request.product_value * 0.005  # 0.5%
    
    return {
        "hs_code": request.hs_code,
        "import_country": request.import_country,
        "export_country": request.export_country,
        "product_value": request.product_value,
        "currency": "USD",
        "duty_calculation": {
            "rate_type": rate_type,
            "rate_percent": applicable_rate,
            "base_duty": round(base_duty, 2),
            "section_301_rate": section_301_rate,
            "section_301_list": section_301_list,
            "section_301_duty": round(additional_duty, 2),
            "total_duty": round(total_duty, 2),
        },
        "mfn_comparison": {
            "mfn_rate": mfn_rate,
            "mfn_duty": round(mfn_duty_amount, 2),
            "savings": round(max(0, savings), 2),
        },
        "landed_cost_estimate": {
            "product_value": request.product_value,
            "freight": round(estimated_freight, 2),
            "insurance": round(estimated_insurance, 2),
            "cif_value": round(request.product_value + estimated_freight + estimated_insurance, 2),
            "duty": round(total_duty, 2),
            "total": round(request.product_value + estimated_freight + estimated_insurance + total_duty, 2),
        },
    }


@router.get("/fta-check")
async def check_fta_eligibility(
    hs_code: str,
    import_country: str,
    export_country: str,
    db: Session = Depends(get_db)
):
    """
    Check FTA eligibility and rules of origin requirements.
    """
    # Get MFN rate for comparison
    tariff = db.query(HSCodeTariff).filter(
        HSCodeTariff.code == hs_code,
        HSCodeTariff.country_code == import_country
    ).first()
    
    mfn_rate = 0
    if tariff:
        mfn_duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == tariff.id,
            DutyRate.rate_type == "mfn"
        ).first()
        if mfn_duty:
            mfn_rate = mfn_duty.ad_valorem_rate or 0
    
    # Find eligible FTAs
    ftas = db.query(FTAAgreement).filter(
        FTAAgreement.is_active == True,
        FTAAgreement.member_countries.contains([export_country]),
        FTAAgreement.member_countries.contains([import_country])
    ).all()
    
    eligible_ftas = []
    for fta in ftas:
        # Get rules of origin for this HS code
        fta_rule = db.query(FTARule).filter(
            FTARule.fta_id == fta.id,
            or_(
                FTARule.hs_code_prefix == hs_code[:2],
                FTARule.hs_code_prefix == hs_code[:4],
                FTARule.hs_code_prefix == hs_code[:6]
            )
        ).first()
        
        preferential_rate = fta_rule.preferential_rate if fta_rule else 0
        
        eligible_ftas.append({
            "fta_code": fta.code,
            "fta_name": fta.name,
            "mfn_rate": mfn_rate,
            "preferential_rate": preferential_rate,
            "savings_percent": mfn_rate - preferential_rate,
            "rules_of_origin": {
                "requirement": fta_rule.rule_text if fta_rule else "Change in Tariff Classification (CTC)",
                "rule_type": fta_rule.rule_type if fta_rule else "CTC",
                "ctc_requirement": fta_rule.ctc_requirement if fta_rule else None,
                "rvc_threshold": f"{fta_rule.rvc_threshold}% Regional Value Content" if fta_rule and fta_rule.rvc_threshold else None,
                "rvc_method": fta_rule.rvc_method if fta_rule else None,
                "certificate_required": fta.certificate_types[0] if fta.certificate_types else "Certificate of Origin",
            },
            "documentation": [
                fta.certificate_types[0] if fta.certificate_types else "Certificate of Origin",
                "Commercial Invoice showing origin",
                "Bill of Lading",
                "Packing List",
                "Production/Manufacturing records (if RVC required)",
            ],
            "cumulation_type": fta.cumulation_type,
            "de_minimis": f"{fta.de_minimis_threshold}%" if fta.de_minimis_threshold else None,
        })
    
    # Sort by savings
    eligible_ftas.sort(key=lambda x: x["savings_percent"], reverse=True)
    
    return {
        "hs_code": hs_code,
        "import_country": import_country,
        "export_country": export_country,
        "eligible_ftas": eligible_ftas,
        "recommendation": eligible_ftas[0]["fta_code"] if eligible_ftas else None,
    }


@router.get("/countries")
async def list_supported_countries():
    """
    List supported countries and their tariff schedules.
    """
    return {
        "countries": [
            {"code": "US", "name": "United States", "schedule": "HTS", "schedule_name": "Harmonized Tariff Schedule"},
            {"code": "EU", "name": "European Union", "schedule": "TARIC", "schedule_name": "TARIC"},
            {"code": "UK", "name": "United Kingdom", "schedule": "UK Tariff", "schedule_name": "UK Trade Tariff"},
            {"code": "CN", "name": "China", "schedule": "CCTS", "schedule_name": "Customs Tariff"},
            {"code": "JP", "name": "Japan", "schedule": "JTS", "schedule_name": "Japan Tariff Schedule"},
            {"code": "IN", "name": "India", "schedule": "ITC-HS", "schedule_name": "Indian Trade Classification"},
            {"code": "AU", "name": "Australia", "schedule": "Working Tariff", "schedule_name": "Australian Customs Tariff"},
            {"code": "SG", "name": "Singapore", "schedule": "STCCED", "schedule_name": "Trade Classification"},
            {"code": "CA", "name": "Canada", "schedule": "CTS", "schedule_name": "Canadian Customs Tariff"},
            {"code": "MX", "name": "Mexico", "schedule": "TIGIE", "schedule_name": "General Import Tax"},
        ],
    }


@router.get("/ftas")
async def list_ftas(
    db: Session = Depends(get_db)
):
    """
    List supported Free Trade Agreements.
    """
    ftas = db.query(FTAAgreement).filter(FTAAgreement.is_active == True).all()
    
    return {
        "ftas": [
            {
                "code": fta.code,
                "name": fta.name,
                "full_name": fta.full_name,
                "member_count": len(fta.member_countries) if fta.member_countries else 0,
                "members": fta.member_countries or [],
                "certificate_types": fta.certificate_types or [],
                "cumulation_type": fta.cumulation_type,
                "de_minimis_threshold": fta.de_minimis_threshold,
                "effective_from": fta.effective_from.isoformat() if fta.effective_from else None,
            }
            for fta in ftas
        ],
    }


# ============================================================================
# Classification History (Authenticated)
# ============================================================================

@router.post("/save")
async def save_classification(
    request: SaveClassificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save a classification to user's history.
    """
    # Look up code details
    result = await classify_with_ai(
        db=db,
        description=request.product_description,
        import_country=request.import_country,
        export_country=request.export_country
    )
    
    classification = HSClassification(
        user_id=current_user.id,
        product_description=request.product_description,
        product_name=request.product_name,
        hs_code=request.hs_code,
        hs_code_description=result.get("description", ""),
        import_country=request.import_country,
        export_country=request.export_country,
        source=ClassificationSource.AI,
        confidence_score=result.get("confidence", 0.5),
        alternative_codes=result.get("alternatives", []),
        ai_reasoning=result.get("reasoning", ""),
        mfn_rate=result.get("duty_rates", {}).get("mfn"),
        product_value=request.product_value,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        project_name=request.project_name,
        tags=request.tags,
        notes=request.notes,
    )
    
    db.add(classification)
    db.commit()
    db.refresh(classification)
    
    return {
        "id": str(classification.id),
        "hs_code": classification.hs_code,
        "status": "saved",
        "created_at": classification.created_at.isoformat(),
    }


@router.get("/history")
async def get_classification_history(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    project: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's classification history.
    """
    query = db.query(HSClassification).filter(
        HSClassification.user_id == current_user.id
    )
    
    if project:
        query = query.filter(HSClassification.project_name == project)
    
    total = query.count()
    classifications = query.order_by(
        HSClassification.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "classifications": [
            {
                "id": str(c.id),
                "product_description": c.product_description,
                "product_name": c.product_name,
                "hs_code": c.hs_code,
                "hs_code_description": c.hs_code_description,
                "import_country": c.import_country,
                "export_country": c.export_country,
                "confidence_score": c.confidence_score,
                "mfn_rate": c.mfn_rate,
                "project_name": c.project_name,
                "tags": c.tags,
                "is_verified": c.is_verified,
                "created_at": c.created_at.isoformat(),
            }
            for c in classifications
        ],
    }


@router.delete("/history/{classification_id}")
async def delete_classification(
    classification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a classification from history.
    """
    classification = db.query(HSClassification).filter(
        HSClassification.id == classification_id,
        HSClassification.user_id == current_user.id
    ).first()
    
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    db.delete(classification)
    db.commit()
    
    return {"status": "deleted"}


# ============================================================================
# Analytics Helper
# ============================================================================

def log_search(
    db: Session,
    query: str,
    user_id: Optional[str],
    result_code: str,
    import_country: str,
    export_country: Optional[str],
    response_time: int
):
    """Log search for analytics."""
    try:
        search = HSCodeSearch(
            search_query=query,
            search_type="description",
            user_id=user_id,
            results_count=1,
            top_result_code=result_code,
            import_country=import_country,
            export_country=export_country,
            response_time_ms=response_time,
        )
        db.add(search)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log search: {e}")

