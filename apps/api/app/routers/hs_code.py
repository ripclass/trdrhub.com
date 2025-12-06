"""
HS Code Finder API Router

Endpoints for AI-powered HS code classification, duty rates, and FTA eligibility.
Phase 2: Bulk classification, PDF export, binding rulings, comparison, rate alerts.
Phase 3: USMCA/RCEP ROO engines, RVC calculator, team collaboration.
"""

import logging
import uuid
import time
import csv
import io
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user, get_optional_user
from app.models.hs_code import (
    HSCodeTariff, DutyRate, FTAAgreement, FTARule,
    HSClassification, HSCodeSearch, ClassificationSource,
    BindingRuling, ChapterNote, Section301Rate, RateAlert,
    ProductSpecificRule, RVCCalculation, OriginDetermination,
    HSCodeTeam, HSCodeTeamMember, HSCodeProject, ClassificationShare
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
# Phase 2: Bulk Classification Models
# ============================================================================

class BulkClassifyItem(BaseModel):
    """Single item in bulk classification request"""
    description: str
    import_country: str = "US"
    export_country: Optional[str] = None
    product_value: Optional[float] = None
    row_id: Optional[str] = None  # For tracking in CSV


class BulkClassifyRequest(BaseModel):
    """Request for bulk classification"""
    items: List[BulkClassifyItem] = Field(..., max_length=500)
    include_fta: bool = True
    include_duty_calc: bool = True


class CompareClassificationsRequest(BaseModel):
    """Request to compare two products' classifications"""
    product_a: str = Field(..., description="First product description")
    product_b: str = Field(..., description="Second product description")
    import_country: str = "US"
    export_country: Optional[str] = None


class RateAlertRequest(BaseModel):
    """Request to create a rate change alert"""
    hs_code: str
    import_country: str = "US"
    export_country: Optional[str] = None
    alert_type: str = Field(default="any", description="any, increase, decrease")
    threshold_percent: Optional[float] = Field(default=None, description="Alert if change exceeds %")
    email_notification: bool = True


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


# ============================================================================
# Phase 2: Bulk Classification Endpoints
# ============================================================================

@router.post("/bulk-classify")
async def bulk_classify_products(
    request: BulkClassifyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classify multiple products at once.
    Maximum 500 products per request.
    """
    start_time = time.time()
    results = []
    errors = []
    
    for idx, item in enumerate(request.items):
        try:
            # Classify each product
            result = await classify_with_ai(
                db=db,
                description=item.description,
                import_country=item.import_country,
                export_country=item.export_country
            )
            
            row_result = {
                "row_id": item.row_id or str(idx + 1),
                "description": item.description,
                "hs_code": result["hs_code"],
                "hs_description": result["description"],
                "confidence": result["confidence"],
                "chapter": result.get("chapter", ""),
                "import_country": item.import_country,
                "export_country": item.export_country,
            }
            
            # Add duty calculation if requested
            if request.include_duty_calc and item.product_value:
                mfn_rate = result.get("duty_rates", {}).get("mfn", 0)
                s301_rate = result.get("duty_rates", {}).get("section_301", 0)
                row_result["mfn_rate"] = mfn_rate
                row_result["section_301_rate"] = s301_rate
                row_result["total_rate"] = mfn_rate + s301_rate
                row_result["estimated_duty"] = round(item.product_value * (mfn_rate + s301_rate) / 100, 2)
            else:
                row_result["mfn_rate"] = result.get("duty_rates", {}).get("mfn", 0)
            
            # Add FTA options if requested
            if request.include_fta and item.export_country:
                ftas = db.query(FTAAgreement).filter(
                    FTAAgreement.is_active == True,
                    FTAAgreement.member_countries.contains([item.export_country]),
                    FTAAgreement.member_countries.contains([item.import_country])
                ).all()
                
                row_result["fta_options"] = [
                    {"code": f.code, "name": f.name}
                    for f in ftas
                ]
            
            results.append(row_result)
            
        except Exception as e:
            logger.error(f"Error classifying row {idx}: {e}")
            errors.append({
                "row_id": item.row_id or str(idx + 1),
                "description": item.description,
                "error": str(e)
            })
    
    processing_time = round(time.time() - start_time, 2)
    
    return {
        "status": "completed",
        "total_items": len(request.items),
        "successful": len(results),
        "failed": len(errors),
        "processing_time_seconds": processing_time,
        "results": results,
        "errors": errors,
    }


@router.post("/bulk-classify/upload")
async def bulk_classify_csv_upload(
    file: UploadFile = File(...),
    import_country: str = Query(default="US"),
    include_fta: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file for bulk classification.
    Expected columns: description, import_country (optional), export_country (optional), product_value (optional)
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read CSV content
    content = await file.read()
    try:
        csv_text = content.decode('utf-8')
    except:
        csv_text = content.decode('latin-1')
    
    reader = csv.DictReader(io.StringIO(csv_text))
    
    items = []
    for row_idx, row in enumerate(reader):
        if row_idx >= 500:  # Limit to 500 rows
            break
            
        description = row.get('description', '').strip()
        if not description:
            continue
        
        items.append(BulkClassifyItem(
            description=description,
            import_country=row.get('import_country', import_country).strip() or import_country,
            export_country=row.get('export_country', '').strip() or None,
            product_value=float(row['product_value']) if row.get('product_value') else None,
            row_id=str(row_idx + 1)
        ))
    
    if not items:
        raise HTTPException(status_code=400, detail="No valid products found in CSV")
    
    # Process using the bulk endpoint
    request = BulkClassifyRequest(
        items=items,
        include_fta=include_fta,
        include_duty_calc=True
    )
    
    return await bulk_classify_products(
        request=request,
        background_tasks=BackgroundTasks(),
        current_user=current_user,
        db=db
    )


@router.get("/bulk-classify/download-template")
async def download_bulk_template():
    """
    Download a CSV template for bulk classification.
    """
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    
    # Header
    writer.writerow(['description', 'import_country', 'export_country', 'product_value'])
    
    # Sample rows
    writer.writerow(['Cotton t-shirts for men', 'US', 'CN', '10000'])
    writer.writerow(['Laptop computers 15 inch', 'US', 'TW', '50000'])
    writer.writerow(['Fresh organic apples', 'US', 'NZ', '5000'])
    writer.writerow(['Stainless steel bolts M8', 'US', 'DE', '2000'])
    writer.writerow(['Leather handbags', 'US', 'IT', '25000'])
    
    csv_content.seek(0)
    
    return StreamingResponse(
        io.BytesIO(csv_content.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_classification_template.csv"}
    )


@router.get("/bulk-classify/export/{job_id}")
async def export_bulk_results(
    job_id: str,
    format: str = Query(default="csv", enum=["csv", "json"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export bulk classification results as CSV or JSON.
    For now, returns user's recent classifications as export.
    """
    # Get user's recent classifications
    classifications = db.query(HSClassification).filter(
        HSClassification.user_id == current_user.id
    ).order_by(desc(HSClassification.created_at)).limit(100).all()
    
    if format == "csv":
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        
        # Header
        writer.writerow([
            'description', 'hs_code', 'hs_description', 'confidence',
            'import_country', 'export_country', 'mfn_rate', 'classified_at'
        ])
        
        # Data rows
        for c in classifications:
            writer.writerow([
                c.product_description,
                c.hs_code,
                c.hs_code_description,
                c.confidence_score,
                c.import_country,
                c.export_country or '',
                c.mfn_rate or 0,
                c.created_at.isoformat()
            ])
        
        csv_content.seek(0)
        
        return StreamingResponse(
            io.BytesIO(csv_content.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=classifications_{job_id}.csv"}
        )
    
    else:  # JSON
        return {
            "job_id": job_id,
            "export_date": datetime.utcnow().isoformat(),
            "total": len(classifications),
            "classifications": [
                {
                    "description": c.product_description,
                    "hs_code": c.hs_code,
                    "hs_description": c.hs_code_description,
                    "confidence": c.confidence_score,
                    "import_country": c.import_country,
                    "export_country": c.export_country,
                    "mfn_rate": c.mfn_rate,
                    "classified_at": c.created_at.isoformat()
                }
                for c in classifications
            ]
        }


# ============================================================================
# Phase 2: PDF Export
# ============================================================================

@router.get("/export/pdf/{classification_id}")
async def export_classification_pdf(
    classification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export a single classification as PDF.
    Returns HTML that can be converted to PDF client-side.
    """
    classification = db.query(HSClassification).filter(
        HSClassification.id == classification_id,
        HSClassification.user_id == current_user.id
    ).first()
    
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Get additional details
    tariff = db.query(HSCodeTariff).filter(
        HSCodeTariff.code == classification.hs_code,
        HSCodeTariff.country_code == classification.import_country
    ).first()
    
    # Build PDF data structure
    pdf_data = {
        "title": "HS Code Classification Report",
        "generated_at": datetime.utcnow().isoformat(),
        "classification": {
            "id": str(classification.id),
            "product_description": classification.product_description,
            "product_name": classification.product_name,
            "hs_code": classification.hs_code,
            "hs_code_description": classification.hs_code_description,
            "chapter": tariff.chapter_description if tariff else f"Chapter {classification.hs_code[:2]}",
            "heading": tariff.heading_description if tariff else None,
            "confidence_score": classification.confidence_score,
            "ai_reasoning": classification.ai_reasoning,
            "import_country": classification.import_country,
            "export_country": classification.export_country,
            "classified_at": classification.created_at.isoformat(),
        },
        "duty_information": {
            "mfn_rate": classification.mfn_rate,
            "preferential_rate": classification.preferential_rate,
            "fta_applied": classification.fta_applied,
            "estimated_duty": classification.estimated_duty,
            "currency": classification.currency,
        },
        "product_details": {
            "value": classification.product_value,
            "quantity": classification.quantity,
            "quantity_unit": classification.quantity_unit,
        },
        "compliance": {
            "requires_license": tariff.requires_license if tariff else False,
            "quota_applicable": tariff.quota_applicable if tariff else False,
            "restrictions": classification.restrictions,
            "licenses_required": classification.licenses_required,
        },
        "verification": {
            "is_verified": classification.is_verified,
            "verified_at": classification.verified_at.isoformat() if classification.verified_at else None,
            "source": classification.source.value if classification.source else "ai",
        },
        "disclaimer": "This classification is provided for informational purposes only. "
                     "Always verify with customs authorities for official rulings."
    }
    
    # Return as JSON (frontend converts to PDF)
    return pdf_data


@router.post("/export/bulk-pdf")
async def export_bulk_pdf(
    classification_ids: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export multiple classifications as PDF report.
    """
    classifications = db.query(HSClassification).filter(
        HSClassification.id.in_(classification_ids),
        HSClassification.user_id == current_user.id
    ).all()
    
    if not classifications:
        raise HTTPException(status_code=404, detail="No classifications found")
    
    items = []
    for c in classifications:
        tariff = db.query(HSCodeTariff).filter(
            HSCodeTariff.code == c.hs_code,
            HSCodeTariff.country_code == c.import_country
        ).first()
        
        items.append({
            "product": c.product_description[:100],
            "hs_code": c.hs_code,
            "description": c.hs_code_description,
            "chapter": tariff.chapter_description if tariff else f"Chapter {c.hs_code[:2]}",
            "confidence": c.confidence_score,
            "mfn_rate": c.mfn_rate,
            "import_country": c.import_country,
            "export_country": c.export_country,
        })
    
    return {
        "title": "Bulk Classification Report",
        "generated_at": datetime.utcnow().isoformat(),
        "total_items": len(items),
        "items": items,
        "summary": {
            "unique_chapters": len(set(i["hs_code"][:2] for i in items)),
            "avg_confidence": sum(i["confidence"] or 0 for i in items) / len(items) if items else 0,
            "countries": list(set(i["import_country"] for i in items)),
        }
    }


# ============================================================================
# Phase 2: Binding Rulings Search
# ============================================================================

@router.get("/rulings/search")
async def search_binding_rulings(
    q: str = Query(..., min_length=2, description="Search query"),
    hs_code: Optional[str] = None,
    country: str = "US",
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    Search CBP binding rulings for classification precedent.
    """
    query = db.query(BindingRuling).filter(
        BindingRuling.country == country,
        BindingRuling.is_active == True
    )
    
    # Filter by HS code if provided
    if hs_code:
        query = query.filter(
            BindingRuling.hs_code.like(f"{hs_code[:4]}%")
        )
    
    # Search by product description
    query = query.filter(
        or_(
            BindingRuling.product_description.ilike(f"%{q}%"),
            BindingRuling.keywords.contains([q.lower()]),
            BindingRuling.ruling_number.ilike(f"%{q}%")
        )
    )
    
    rulings = query.order_by(desc(BindingRuling.ruling_date)).limit(limit).all()
    
    return {
        "query": q,
        "hs_code_filter": hs_code,
        "count": len(rulings),
        "rulings": [
            {
                "ruling_number": r.ruling_number,
                "ruling_type": r.ruling_type,
                "product_description": r.product_description,
                "hs_code": r.hs_code,
                "reasoning": r.reasoning,
                "legal_reference": r.legal_reference,
                "ruling_date": r.ruling_date.isoformat() if r.ruling_date else None,
                "keywords": r.keywords,
            }
            for r in rulings
        ]
    }


@router.get("/rulings/{ruling_number}")
async def get_binding_ruling(
    ruling_number: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific binding ruling.
    """
    ruling = db.query(BindingRuling).filter(
        BindingRuling.ruling_number == ruling_number
    ).first()
    
    if not ruling:
        raise HTTPException(status_code=404, detail="Ruling not found")
    
    # Find related rulings
    related = db.query(BindingRuling).filter(
        BindingRuling.hs_code.like(f"{ruling.hs_code[:4]}%"),
        BindingRuling.ruling_number != ruling_number,
        BindingRuling.is_active == True
    ).limit(5).all()
    
    return {
        "ruling_number": ruling.ruling_number,
        "ruling_type": ruling.ruling_type,
        "product_description": ruling.product_description,
        "hs_code": ruling.hs_code,
        "reasoning": ruling.reasoning,
        "legal_reference": ruling.legal_reference,
        "keywords": ruling.keywords,
        "ruling_date": ruling.ruling_date.isoformat() if ruling.ruling_date else None,
        "effective_date": ruling.effective_date.isoformat() if ruling.effective_date else None,
        "country": ruling.country,
        "related_rulings": [
            {
                "ruling_number": r.ruling_number,
                "product_description": r.product_description[:100],
                "hs_code": r.hs_code
            }
            for r in related
        ]
    }


@router.get("/rulings/by-code/{hs_code}")
async def get_rulings_by_hs_code(
    hs_code: str,
    country: str = "US",
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all binding rulings for a specific HS code.
    """
    code_prefix = hs_code.replace(".", "")[:6]  # At least heading level
    
    rulings = db.query(BindingRuling).filter(
        BindingRuling.hs_code.like(f"{code_prefix}%"),
        BindingRuling.country == country,
        BindingRuling.is_active == True
    ).order_by(desc(BindingRuling.ruling_date)).limit(limit).all()
    
    return {
        "hs_code": hs_code,
        "count": len(rulings),
        "rulings": [
            {
                "ruling_number": r.ruling_number,
                "ruling_type": r.ruling_type,
                "product_description": r.product_description,
                "hs_code": r.hs_code,
                "ruling_date": r.ruling_date.isoformat() if r.ruling_date else None,
            }
            for r in rulings
        ]
    }


# ============================================================================
# Phase 2: Classification Comparison Tool
# ============================================================================

@router.post("/compare")
async def compare_classifications(
    request: CompareClassificationsRequest,
    db: Session = Depends(get_db)
):
    """
    Compare classifications for two products side-by-side.
    Useful for determining if products belong to the same HS code.
    """
    # Classify both products
    result_a = await classify_with_ai(
        db=db,
        description=request.product_a,
        import_country=request.import_country,
        export_country=request.export_country
    )
    
    result_b = await classify_with_ai(
        db=db,
        description=request.product_b,
        import_country=request.import_country,
        export_country=request.export_country
    )
    
    # Determine similarity
    same_chapter = result_a["hs_code"][:2] == result_b["hs_code"][:2]
    same_heading = result_a["hs_code"][:4] == result_b["hs_code"][:4]
    same_subheading = result_a["hs_code"][:6] == result_b["hs_code"][:6]
    same_code = result_a["hs_code"] == result_b["hs_code"]
    
    # Calculate duty difference
    rate_a = result_a.get("duty_rates", {}).get("mfn", 0) or 0
    rate_b = result_b.get("duty_rates", {}).get("mfn", 0) or 0
    rate_difference = abs(rate_a - rate_b)
    
    # Determine consolidation recommendation
    can_consolidate = same_code
    consolidation_note = None
    if same_code:
        consolidation_note = "Products can be shipped under the same HS code."
    elif same_subheading:
        consolidation_note = "Products are in the same subheading but may have different rates at 8-digit level."
    elif same_heading:
        consolidation_note = "Products are in the same heading. Check if duty rates differ."
    elif same_chapter:
        consolidation_note = "Products are in the same chapter but classified differently."
    else:
        consolidation_note = "Products are in different chapters - separate classification required."
    
    return {
        "product_a": {
            "description": request.product_a,
            "hs_code": result_a["hs_code"],
            "hs_description": result_a["description"],
            "confidence": result_a["confidence"],
            "chapter": result_a.get("chapter", ""),
            "mfn_rate": rate_a,
            "reasoning": result_a.get("reasoning", ""),
        },
        "product_b": {
            "description": request.product_b,
            "hs_code": result_b["hs_code"],
            "hs_description": result_b["description"],
            "confidence": result_b["confidence"],
            "chapter": result_b.get("chapter", ""),
            "mfn_rate": rate_b,
            "reasoning": result_b.get("reasoning", ""),
        },
        "comparison": {
            "same_chapter": same_chapter,
            "same_heading": same_heading,
            "same_subheading": same_subheading,
            "same_code": same_code,
            "rate_difference_percent": rate_difference,
            "can_consolidate": can_consolidate,
            "consolidation_note": consolidation_note,
        },
        "import_country": request.import_country,
        "export_country": request.export_country,
    }


# ============================================================================
# Phase 2: Rate Alerts / Change Notifications
# ============================================================================

@router.post("/alerts/subscribe")
async def subscribe_rate_alert(
    request: RateAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscribe to rate change alerts for an HS code.
    """
    # Check if already subscribed
    existing = db.query(RateAlert).filter(
        RateAlert.user_id == current_user.id,
        RateAlert.hs_code == request.hs_code,
        RateAlert.import_country == request.import_country,
        RateAlert.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Already subscribed to alerts for this HS code"
        )
    
    # Get current rate for baseline
    tariff = db.query(HSCodeTariff).filter(
        HSCodeTariff.code == request.hs_code,
        HSCodeTariff.country_code == request.import_country
    ).first()
    
    if not tariff:
        # Try partial match
        code_prefix = request.hs_code.replace(".", "")[:6]
        tariff = db.query(HSCodeTariff).filter(
            HSCodeTariff.country_code == request.import_country,
            HSCodeTariff.code.like(f"{code_prefix}%")
        ).first()
    
    current_rate = 0
    if tariff:
        duty = db.query(DutyRate).filter(
            DutyRate.hs_code_id == tariff.id,
            DutyRate.rate_type == "mfn"
        ).first()
        current_rate = duty.ad_valorem_rate if duty else 0
    
    # Create the alert subscription
    alert = RateAlert(
        user_id=current_user.id,
        hs_code=request.hs_code,
        import_country=request.import_country,
        export_country=request.export_country,
        alert_type=request.alert_type,
        threshold_percent=request.threshold_percent,
        baseline_rate=current_rate,
        email_notification=request.email_notification,
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return {
        "status": "subscribed",
        "alert_id": str(alert.id),
        "hs_code": alert.hs_code,
        "import_country": alert.import_country,
        "export_country": alert.export_country,
        "alert_type": alert.alert_type,
        "threshold_percent": alert.threshold_percent,
        "baseline_rate": alert.baseline_rate,
        "email_notification": alert.email_notification,
        "created_at": alert.created_at.isoformat(),
        "message": f"You will be notified when rates change for HS {alert.hs_code}",
    }


@router.get("/alerts")
async def list_rate_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's rate change alert subscriptions.
    """
    alerts = db.query(RateAlert).filter(
        RateAlert.user_id == current_user.id,
        RateAlert.is_active == True
    ).order_by(desc(RateAlert.created_at)).all()
    
    alert_list = []
    for alert in alerts:
        # Get current rate for comparison
        tariff = db.query(HSCodeTariff).filter(
            HSCodeTariff.code == alert.hs_code,
            HSCodeTariff.country_code == alert.import_country
        ).first()
        
        current_rate = alert.baseline_rate or 0
        if tariff:
            duty = db.query(DutyRate).filter(
                DutyRate.hs_code_id == tariff.id,
                DutyRate.rate_type == "mfn"
            ).first()
            if duty:
                current_rate = duty.ad_valorem_rate or 0
        
        rate_changed = current_rate != alert.baseline_rate
        rate_change = current_rate - (alert.baseline_rate or 0)
        
        alert_list.append({
            "id": str(alert.id),
            "hs_code": alert.hs_code,
            "import_country": alert.import_country,
            "export_country": alert.export_country,
            "alert_type": alert.alert_type,
            "threshold_percent": alert.threshold_percent,
            "baseline_rate": alert.baseline_rate,
            "current_rate": current_rate,
            "rate_changed": rate_changed,
            "rate_change": round(rate_change, 2),
            "email_notification": alert.email_notification,
            "last_notified": alert.last_notified.isoformat() if alert.last_notified else None,
            "notification_count": alert.notification_count,
            "created_at": alert.created_at.isoformat(),
        })
    
    return {
        "total": len(alert_list),
        "alerts": alert_list,
    }


@router.delete("/alerts/{alert_id}")
async def unsubscribe_rate_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe from a rate change alert.
    """
    alert = db.query(RateAlert).filter(
        RateAlert.id == alert_id,
        RateAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_active = False
    db.commit()
    
    return {
        "status": "unsubscribed",
        "alert_id": alert_id,
        "hs_code": alert.hs_code,
    }


@router.put("/alerts/{alert_id}")
async def update_rate_alert(
    alert_id: str,
    alert_type: Optional[str] = None,
    threshold_percent: Optional[float] = None,
    email_notification: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update alert settings.
    """
    alert = db.query(RateAlert).filter(
        RateAlert.id == alert_id,
        RateAlert.user_id == current_user.id,
        RateAlert.is_active == True
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert_type is not None:
        alert.alert_type = alert_type
    if threshold_percent is not None:
        alert.threshold_percent = threshold_percent
    if email_notification is not None:
        alert.email_notification = email_notification
    
    db.commit()
    db.refresh(alert)
    
    return {
        "status": "updated",
        "alert_id": str(alert.id),
        "hs_code": alert.hs_code,
        "alert_type": alert.alert_type,
        "threshold_percent": alert.threshold_percent,
        "email_notification": alert.email_notification,
    }


@router.get("/rate-changes")
async def get_recent_rate_changes(
    country: str = Query(default="US"),
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db)
):
    """
    Get recent duty rate changes.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Find recently updated rates
    recent_rates = db.query(DutyRate).filter(
        DutyRate.updated_at >= cutoff_date,
        DutyRate.is_active == True
    ).order_by(desc(DutyRate.updated_at)).limit(50).all()
    
    changes = []
    for rate in recent_rates:
        hs_code = db.query(HSCodeTariff).filter(
            HSCodeTariff.id == rate.hs_code_id
        ).first()
        
        if hs_code:
            changes.append({
                "hs_code": hs_code.code,
                "description": hs_code.description[:100],
                "rate_type": rate.rate_type,
                "current_rate": rate.ad_valorem_rate,
                "effective_from": rate.effective_from.isoformat() if rate.effective_from else None,
                "updated_at": rate.updated_at.isoformat(),
            })
    
    # Also check Section 301 changes for US
    if country == "US":
        s301_changes = db.query(Section301Rate).filter(
            Section301Rate.is_active == True
        ).order_by(desc(Section301Rate.effective_from)).limit(20).all()
        
        for s in s301_changes:
            changes.append({
                "hs_code": s.hs_code,
                "description": f"Section 301 - {s.list_number}",
                "rate_type": "section_301",
                "current_rate": s.additional_rate,
                "effective_from": s.effective_from.isoformat() if s.effective_from else None,
                "is_excluded": s.is_excluded,
            })
    
    return {
        "country": country,
        "period_days": days,
        "changes_count": len(changes),
        "changes": changes,
    }


# ============================================================================
# Phase 3: USMCA/RCEP Rules of Origin Engine
# ============================================================================

class RVCCalculationRequest(BaseModel):
    """Request to calculate Regional Value Content"""
    product_description: str
    hs_code: str
    fta_code: str = Field(default="USMCA", description="USMCA, RCEP, etc.")
    transaction_value: float = Field(..., description="FOB sale price")
    vom_value: float = Field(..., description="Value of non-originating materials")
    vom_breakdown: Optional[List[Dict[str, Any]]] = None
    direct_labor_cost: Optional[float] = None
    direct_overhead: Optional[float] = None
    profit: Optional[float] = None
    method: str = Field(default="transaction_value", description="transaction_value, net_cost")
    # For USMCA auto sector
    is_automotive: bool = False
    steel_from_na: Optional[float] = None
    high_wage_labor: Optional[float] = None


class OriginDeterminationRequest(BaseModel):
    """Request for full origin determination"""
    product_description: str
    product_name: Optional[str] = None
    hs_code: str
    fta_code: str
    export_country: str
    import_country: str
    # Optional RVC data
    transaction_value: Optional[float] = None
    vom_value: Optional[float] = None
    # Producer info
    producer_name: Optional[str] = None
    producer_address: Optional[str] = None


@router.get("/roo/rules/{fta_code}/{hs_code}")
async def get_rules_of_origin(
    fta_code: str,
    hs_code: str,
    db: Session = Depends(get_db)
):
    """
    Get applicable Rules of Origin for an HS code under a specific FTA.
    Supports USMCA, RCEP, and other major FTAs.
    """
    # Get FTA
    fta = db.query(FTAAgreement).filter(
        FTAAgreement.code == fta_code.upper(),
        FTAAgreement.is_active == True
    ).first()
    
    if not fta:
        raise HTTPException(status_code=404, detail=f"FTA {fta_code} not found")
    
    # Get product-specific rules
    code_clean = hs_code.replace(".", "")
    
    # Try exact match first, then broader matches
    psr = None
    for prefix_len in [8, 6, 4, 2]:
        if len(code_clean) >= prefix_len:
            psr = db.query(ProductSpecificRule).filter(
                ProductSpecificRule.fta_id == fta.id,
                ProductSpecificRule.hs_code_from <= code_clean[:prefix_len],
                or_(
                    ProductSpecificRule.hs_code_to >= code_clean[:prefix_len],
                    ProductSpecificRule.hs_code_to == None
                ),
                ProductSpecificRule.is_active == True
            ).first()
            if psr:
                break
    
    # Also get general FTA rules
    general_rule = db.query(FTARule).filter(
        FTARule.fta_id == fta.id,
        or_(
            FTARule.hs_code_prefix == code_clean[:2],
            FTARule.hs_code_prefix == code_clean[:4],
            FTARule.hs_code_prefix == code_clean[:6]
        )
    ).first()
    
    response = {
        "fta_code": fta_code.upper(),
        "fta_name": fta.name,
        "hs_code": hs_code,
        "member_countries": fta.member_countries,
        "certificate_types": fta.certificate_types,
        "cumulation_type": fta.cumulation_type,
        "de_minimis_threshold": fta.de_minimis_threshold,
    }
    
    if psr:
        response["product_specific_rule"] = {
            "rule_type": psr.rule_type,
            "rule_text": psr.rule_text,
            "ctc_type": psr.ctc_type,
            "ctc_exceptions": psr.ctc_exceptions,
            "rvc_required": psr.rvc_required,
            "rvc_threshold": psr.rvc_threshold,
            "rvc_method": psr.rvc_method,
            "lvc_required": psr.lvc_required,
            "lvc_threshold": psr.lvc_threshold,
            "steel_aluminum_required": psr.steel_aluminum_required,
            "process_requirements": psr.process_requirements,
            "annex_reference": psr.annex_reference,
            "rule_notes": psr.rule_notes,
        }
    elif general_rule:
        response["general_rule"] = {
            "rule_type": general_rule.rule_type,
            "rule_text": general_rule.rule_text,
            "ctc_requirement": general_rule.ctc_requirement,
            "rvc_threshold": general_rule.rvc_threshold,
            "rvc_method": general_rule.rvc_method,
            "preferential_rate": general_rule.preferential_rate,
        }
    else:
        # Return default rules for the FTA
        response["default_rule"] = _get_default_fta_rules(fta_code.upper())
    
    return response


def _get_default_fta_rules(fta_code: str) -> Dict[str, Any]:
    """Get default rules for common FTAs when PSR not found."""
    defaults = {
        "USMCA": {
            "rule_type": "CTC or RVC",
            "ctc_type": "CTSH",
            "rvc_threshold": 60,
            "rvc_method": "transaction_value",
            "rvc_alternative": 50,
            "rvc_alternative_method": "net_cost",
            "de_minimis": 10,
            "note": "Default rule. Check specific annex for your product category."
        },
        "RCEP": {
            "rule_type": "CTC or RVC",
            "ctc_type": "CTH",
            "rvc_threshold": 40,
            "rvc_method": "build_down",
            "de_minimis": 10,
            "note": "Default rule. Some products have stricter requirements."
        },
        "CPTPP": {
            "rule_type": "CTC or RVC",
            "ctc_type": "CTH",
            "rvc_threshold": 45,
            "rvc_method": "build_down",
            "de_minimis": 10,
        },
        "KORUS": {
            "rule_type": "CTC or RVC",
            "ctc_type": "CTH",
            "rvc_threshold": 35,
            "rvc_method": "build_down",
        },
    }
    return defaults.get(fta_code, {
        "rule_type": "CTC",
        "ctc_type": "CTH",
        "note": "Consult FTA text for specific requirements"
    })


@router.post("/roo/calculate-rvc")
async def calculate_rvc(
    request: RVCCalculationRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Calculate Regional Value Content (RVC) for origin determination.
    Supports Transaction Value and Net Cost methods.
    """
    # Get applicable rules
    fta = db.query(FTAAgreement).filter(
        FTAAgreement.code == request.fta_code.upper()
    ).first()
    
    if not fta:
        raise HTTPException(status_code=404, detail=f"FTA {request.fta_code} not found")
    
    # Calculate RVC based on method
    if request.method == "transaction_value":
        # RVC = ((TV - VNM) / TV) × 100
        rvc_percent = ((request.transaction_value - request.vom_value) / request.transaction_value) * 100
    else:  # net_cost
        # RVC = ((NC - VNM) / NC) × 100
        net_cost = request.transaction_value - (request.profit or 0)
        rvc_percent = ((net_cost - request.vom_value) / net_cost) * 100
    
    rvc_percent = round(rvc_percent, 2)
    
    # Determine threshold based on FTA and product
    threshold = 60 if request.fta_code.upper() == "USMCA" else 40
    
    # Check product-specific rules for threshold
    code_clean = request.hs_code.replace(".", "")
    psr = db.query(ProductSpecificRule).filter(
        ProductSpecificRule.fta_id == fta.id,
        ProductSpecificRule.hs_code_from <= code_clean[:4],
        or_(
            ProductSpecificRule.hs_code_to >= code_clean[:4],
            ProductSpecificRule.hs_code_to == None
        ),
        ProductSpecificRule.rvc_required == True
    ).first()
    
    if psr and psr.rvc_threshold:
        threshold = psr.rvc_threshold
    
    meets_requirement = rvc_percent >= threshold
    
    # Additional USMCA automotive checks
    lvc_result = None
    if request.is_automotive and request.fta_code.upper() == "USMCA":
        if request.high_wage_labor and request.transaction_value:
            lvc_percent = (request.high_wage_labor / request.transaction_value) * 100
            lvc_result = {
                "lvc_percent": round(lvc_percent, 2),
                "threshold": 40,
                "meets_requirement": lvc_percent >= 40,
            }
    
    result = {
        "fta_code": request.fta_code.upper(),
        "hs_code": request.hs_code,
        "product_description": request.product_description,
        "method": request.method,
        "calculation": {
            "transaction_value": request.transaction_value,
            "vom_value": request.vom_value,
            "originating_content": round(request.transaction_value - request.vom_value, 2),
        },
        "rvc_result": {
            "rvc_percent": rvc_percent,
            "threshold": threshold,
            "meets_requirement": meets_requirement,
        },
        "lvc_result": lvc_result,
        "overall_eligible": meets_requirement and (lvc_result is None or lvc_result["meets_requirement"]),
    }
    
    # Save calculation if user is logged in
    if current_user:
        calc = RVCCalculation(
            user_id=current_user.id,
            product_description=request.product_description,
            hs_code=request.hs_code,
            fta_code=request.fta_code.upper(),
            transaction_value=request.transaction_value,
            vom_value=request.vom_value,
            vom_breakdown=request.vom_breakdown,
            direct_labor_cost=request.direct_labor_cost,
            direct_overhead=request.direct_overhead,
            profit=request.profit,
            rvc_percent=rvc_percent,
            method_used=request.method,
            threshold_required=threshold,
            meets_requirement=meets_requirement,
        )
        db.add(calc)
        db.commit()
        result["calculation_id"] = str(calc.id)
    
    return result


@router.post("/roo/determine-origin")
async def determine_origin(
    request: OriginDeterminationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete origin determination for FTA claims.
    Returns eligibility and generates determination record.
    """
    # Get FTA details
    fta = db.query(FTAAgreement).filter(
        FTAAgreement.code == request.fta_code.upper(),
        FTAAgreement.is_active == True
    ).first()
    
    if not fta:
        raise HTTPException(status_code=404, detail=f"FTA {request.fta_code} not found")
    
    # Check if countries are members
    if request.export_country not in (fta.member_countries or []):
        return {
            "is_originating": False,
            "reason": f"{request.export_country} is not a member of {request.fta_code}",
            "fta_code": request.fta_code,
        }
    
    # Get applicable rules
    code_clean = request.hs_code.replace(".", "")
    
    psr = db.query(ProductSpecificRule).filter(
        ProductSpecificRule.fta_id == fta.id,
        ProductSpecificRule.hs_code_from <= code_clean[:4],
        or_(
            ProductSpecificRule.hs_code_to >= code_clean[:4],
            ProductSpecificRule.hs_code_to == None
        ),
        ProductSpecificRule.is_active == True
    ).first()
    
    # Determine eligibility
    is_originating = True
    rule_applied = "CTC"  # Default to change in tariff classification
    determination_reason = ""
    
    # If RVC is required and values provided, calculate
    rvc_calc_id = None
    if psr and psr.rvc_required and request.transaction_value and request.vom_value:
        rvc_percent = ((request.transaction_value - request.vom_value) / request.transaction_value) * 100
        threshold = psr.rvc_threshold or 40
        
        if rvc_percent < threshold:
            is_originating = False
            determination_reason = f"RVC of {rvc_percent:.1f}% does not meet {threshold}% threshold"
        else:
            determination_reason = f"RVC of {rvc_percent:.1f}% meets {threshold}% threshold"
            rule_applied = "RVC"
        
        # Save RVC calculation
        rvc_calc = RVCCalculation(
            user_id=current_user.id,
            product_description=request.product_description,
            hs_code=request.hs_code,
            fta_code=request.fta_code.upper(),
            transaction_value=request.transaction_value,
            vom_value=request.vom_value,
            rvc_percent=rvc_percent,
            method_used="transaction_value",
            threshold_required=threshold,
            meets_requirement=is_originating,
        )
        db.add(rvc_calc)
        db.flush()
        rvc_calc_id = rvc_calc.id
    else:
        determination_reason = "Assumed CTC compliance - provide cost data for RVC verification"
    
    # Create origin determination record
    determination = OriginDetermination(
        user_id=current_user.id,
        product_description=request.product_description,
        product_name=request.product_name,
        hs_code=request.hs_code,
        fta_code=request.fta_code.upper(),
        export_country=request.export_country,
        import_country=request.import_country,
        rule_applied=rule_applied,
        psr_id=psr.id if psr else None,
        rvc_calculation_id=rvc_calc_id,
        is_originating=is_originating,
        determination_reason=determination_reason,
        certificate_type=fta.certificate_types[0] if fta.certificate_types else "Certificate of Origin",
        producer_name=request.producer_name,
        producer_address=request.producer_address,
        status="draft",
    )
    
    db.add(determination)
    db.commit()
    db.refresh(determination)
    
    return {
        "determination_id": str(determination.id),
        "is_originating": is_originating,
        "fta_code": request.fta_code.upper(),
        "fta_name": fta.name,
        "hs_code": request.hs_code,
        "product_description": request.product_description,
        "rule_applied": rule_applied,
        "determination_reason": determination_reason,
        "certificate_type": determination.certificate_type,
        "status": determination.status,
        "next_steps": [
            "Verify CTC requirements with bill of materials",
            "Document production process if specific processing required",
            "Complete certificate of origin form",
            "Maintain records for 5 years (USMCA) or per FTA requirements",
        ] if is_originating else [
            "Review product sourcing for more originating content",
            "Consider alternative suppliers in FTA territory",
            "Consult with customs broker for other qualifying options",
        ],
    }


@router.get("/roo/determinations")
async def list_origin_determinations(
    fta_code: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's origin determination history."""
    query = db.query(OriginDetermination).filter(
        OriginDetermination.user_id == current_user.id,
        OriginDetermination.is_active == True
    )
    
    if fta_code:
        query = query.filter(OriginDetermination.fta_code == fta_code.upper())
    
    determinations = query.order_by(desc(OriginDetermination.created_at)).limit(limit).all()
    
    return {
        "total": len(determinations),
        "determinations": [
            {
                "id": str(d.id),
                "product_name": d.product_name,
                "product_description": d.product_description[:100],
                "hs_code": d.hs_code,
                "fta_code": d.fta_code,
                "is_originating": d.is_originating,
                "rule_applied": d.rule_applied,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
            }
            for d in determinations
        ]
    }


# ============================================================================
# Phase 3: Team Collaboration
# ============================================================================

class CreateTeamRequest(BaseModel):
    """Request to create a team"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    default_import_country: str = "US"


class InviteTeamMemberRequest(BaseModel):
    """Request to invite a team member"""
    email: str
    role: str = Field(default="editor", description="owner, admin, editor, viewer")


class ShareClassificationRequest(BaseModel):
    """Request to share a classification"""
    classification_id: str
    share_with_user_id: Optional[str] = None
    share_with_team_id: Optional[str] = None
    share_with_email: Optional[str] = None
    can_edit: bool = False
    can_comment: bool = True
    expires_days: Optional[int] = None


@router.post("/teams")
async def create_team(
    request: CreateTeamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new team."""
    team = HSCodeTeam(
        name=request.name,
        description=request.description,
        owner_id=current_user.id,
        default_import_country=request.default_import_country,
    )
    db.add(team)
    db.flush()
    
    # Add creator as owner member
    member = HSCodeTeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role="owner",
        can_classify=True,
        can_edit=True,
        can_delete=True,
        can_share=True,
        can_export=True,
        can_invite=True,
        status="active",
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    db.commit()
    db.refresh(team)
    
    return {
        "id": str(team.id),
        "name": team.name,
        "description": team.description,
        "owner_id": str(team.owner_id),
        "created_at": team.created_at.isoformat(),
    }


@router.get("/teams")
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List teams the user belongs to."""
    memberships = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.user_id == current_user.id,
        HSCodeTeamMember.is_active == True
    ).all()
    
    teams = []
    for m in memberships:
        team = db.query(HSCodeTeam).filter(HSCodeTeam.id == m.team_id).first()
        if team and team.is_active:
            member_count = db.query(HSCodeTeamMember).filter(
                HSCodeTeamMember.team_id == team.id,
                HSCodeTeamMember.is_active == True
            ).count()
            
            teams.append({
                "id": str(team.id),
                "name": team.name,
                "description": team.description,
                "role": m.role,
                "member_count": member_count,
                "plan": team.plan,
                "created_at": team.created_at.isoformat(),
            })
    
    return {"teams": teams}


@router.get("/teams/{team_id}")
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get team details with members."""
    # Verify membership
    membership = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.team_id == team_id,
        HSCodeTeamMember.user_id == current_user.id,
        HSCodeTeamMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    
    team = db.query(HSCodeTeam).filter(
        HSCodeTeam.id == team_id,
        HSCodeTeam.is_active == True
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get all members
    members = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.team_id == team_id,
        HSCodeTeamMember.is_active == True
    ).all()
    
    # Get projects
    projects = db.query(HSCodeProject).filter(
        HSCodeProject.team_id == team_id,
        HSCodeProject.is_active == True
    ).all()
    
    return {
        "id": str(team.id),
        "name": team.name,
        "description": team.description,
        "owner_id": str(team.owner_id),
        "default_import_country": team.default_import_country,
        "plan": team.plan,
        "max_members": team.max_members,
        "members": [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "role": m.role,
                "status": m.status,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ],
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "status": p.status,
                "classification_count": p.classification_count,
            }
            for p in projects
        ],
        "your_role": membership.role,
    }


@router.post("/teams/{team_id}/invite")
async def invite_team_member(
    team_id: str,
    request: InviteTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a new member to the team."""
    # Verify permission
    membership = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.team_id == team_id,
        HSCodeTeamMember.user_id == current_user.id,
        HSCodeTeamMember.can_invite == True,
        HSCodeTeamMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="No permission to invite members")
    
    team = db.query(HSCodeTeam).filter(HSCodeTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check member limit
    current_count = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.team_id == team_id,
        HSCodeTeamMember.is_active == True
    ).count()
    
    if current_count >= team.max_members:
        raise HTTPException(status_code=400, detail=f"Team has reached maximum members ({team.max_members})")
    
    # Look up user by email (simplified - in production would send email invite)
    from app.models.user import User as UserModel
    invitee = db.query(UserModel).filter(UserModel.email == request.email).first()
    
    if invitee:
        # Check if already member
        existing = db.query(HSCodeTeamMember).filter(
            HSCodeTeamMember.team_id == team_id,
            HSCodeTeamMember.user_id == invitee.id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="User is already a team member")
        
        # Create membership
        role_permissions = {
            "admin": {"classify": True, "edit": True, "delete": True, "share": True, "export": True, "invite": True},
            "editor": {"classify": True, "edit": True, "delete": False, "share": True, "export": True, "invite": False},
            "viewer": {"classify": False, "edit": False, "delete": False, "share": False, "export": True, "invite": False},
        }
        perms = role_permissions.get(request.role, role_permissions["viewer"])
        
        new_member = HSCodeTeamMember(
            team_id=team_id,
            user_id=invitee.id,
            role=request.role,
            can_classify=perms["classify"],
            can_edit=perms["edit"],
            can_delete=perms["delete"],
            can_share=perms["share"],
            can_export=perms["export"],
            can_invite=perms["invite"],
            status="active",
            invited_by=current_user.id,
            invited_at=datetime.utcnow(),
            joined_at=datetime.utcnow(),
        )
        db.add(new_member)
        db.commit()
        
        return {
            "status": "added",
            "member_id": str(new_member.id),
            "user_id": str(invitee.id),
            "role": request.role,
        }
    else:
        # User not found - would send email invite in production
        return {
            "status": "invited",
            "email": request.email,
            "message": "Invitation sent. User will be added when they sign up.",
        }


@router.post("/teams/{team_id}/projects")
async def create_project(
    team_id: str,
    name: str,
    description: Optional[str] = None,
    target_fta: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a project within a team."""
    # Verify membership with edit permission
    membership = db.query(HSCodeTeamMember).filter(
        HSCodeTeamMember.team_id == team_id,
        HSCodeTeamMember.user_id == current_user.id,
        HSCodeTeamMember.can_edit == True,
        HSCodeTeamMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="No permission to create projects")
    
    project = HSCodeProject(
        team_id=team_id,
        created_by=current_user.id,
        name=name,
        description=description,
        target_fta=target_fta,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "target_fta": project.target_fta,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
    }


@router.post("/share")
async def share_classification(
    request: ShareClassificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a classification with another user, team, or via link."""
    # Verify ownership
    classification = db.query(HSClassification).filter(
        HSClassification.id == request.classification_id,
        HSClassification.user_id == current_user.id
    ).first()
    
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Generate share link
    share_link = secrets.token_urlsafe(16)
    
    # Calculate expiry
    expires_at = None
    if request.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
    
    share = ClassificationShare(
        classification_id=classification.id,
        shared_by=current_user.id,
        shared_with_user=request.share_with_user_id,
        shared_with_team=request.share_with_team_id,
        shared_with_email=request.share_with_email,
        can_view=True,
        can_edit=request.can_edit,
        can_comment=request.can_comment,
        share_link=share_link,
        requires_auth=request.share_with_email is None,
        expires_at=expires_at,
    )
    
    db.add(share)
    
    # Update classification shared status
    classification.is_shared = True
    if request.share_with_user_id:
        shared_with = classification.shared_with or []
        if request.share_with_user_id not in shared_with:
            shared_with.append(request.share_with_user_id)
            classification.shared_with = shared_with
    
    db.commit()
    db.refresh(share)
    
    share_url = f"/hs-code/shared/{share_link}"
    
    return {
        "share_id": str(share.id),
        "classification_id": request.classification_id,
        "share_link": share_link,
        "share_url": share_url,
        "can_edit": request.can_edit,
        "can_comment": request.can_comment,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@router.get("/shared/{share_link}")
async def get_shared_classification(
    share_link: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Access a shared classification via link."""
    share = db.query(ClassificationShare).filter(
        ClassificationShare.share_link == share_link,
        ClassificationShare.is_active == True
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    
    # Check expiry
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link has expired")
    
    # Check auth requirement
    if share.requires_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get classification
    classification = db.query(HSClassification).filter(
        HSClassification.id == share.classification_id
    ).first()
    
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    
    # Update view count
    share.view_count = (share.view_count or 0) + 1
    share.last_viewed = datetime.utcnow()
    db.commit()
    
    return {
        "classification": {
            "id": str(classification.id),
            "product_description": classification.product_description,
            "product_name": classification.product_name,
            "hs_code": classification.hs_code,
            "hs_code_description": classification.hs_code_description,
            "import_country": classification.import_country,
            "export_country": classification.export_country,
            "confidence_score": classification.confidence_score,
            "mfn_rate": classification.mfn_rate,
            "ai_reasoning": classification.ai_reasoning,
            "is_verified": classification.is_verified,
            "created_at": classification.created_at.isoformat(),
        },
        "permissions": {
            "can_view": share.can_view,
            "can_edit": share.can_edit,
            "can_comment": share.can_comment,
        },
        "view_count": share.view_count,
    }

