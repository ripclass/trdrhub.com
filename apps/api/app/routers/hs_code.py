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

# Sample HS codes for demo (in production, these come from database)
SAMPLE_HS_CODES = {
    "6109.10": {
        "code": "6109.10.00",
        "description": "T-shirts, singlets, tank tops and similar garments, knitted or crocheted, of cotton",
        "chapter": "61 - Articles of apparel and clothing accessories, knitted or crocheted",
        "heading": "6109 - T-shirts, singlets, tank tops and similar garments",
        "unit": "DOZ/KG",
        "keywords": ["t-shirt", "tshirt", "cotton", "apparel", "clothing", "knitted", "garment", "singlet", "tank top"],
    },
    "8471.30": {
        "code": "8471.30.01",
        "description": "Portable automatic data processing machines, weighing not more than 10 kg",
        "chapter": "84 - Nuclear reactors, boilers, machinery and mechanical appliances",
        "heading": "8471 - Automatic data processing machines",
        "unit": "NO.",
        "keywords": ["laptop", "notebook", "computer", "portable", "data processing", "pc"],
    },
    "8517.12": {
        "code": "8517.12.00",
        "description": "Telephones for cellular networks or for other wireless networks",
        "chapter": "85 - Electrical machinery and equipment",
        "heading": "8517 - Telephone sets and other apparatus for transmission/reception",
        "unit": "NO.",
        "keywords": ["mobile phone", "cell phone", "smartphone", "cellular", "wireless", "iphone", "android"],
    },
    "0901.21": {
        "code": "0901.21.00",
        "description": "Coffee, roasted, not decaffeinated",
        "chapter": "09 - Coffee, tea, maté and spices",
        "heading": "0901 - Coffee, whether or not roasted or decaffeinated",
        "unit": "KG",
        "keywords": ["coffee", "roasted", "beans", "ground coffee", "arabica", "robusta"],
    },
    "3004.90": {
        "code": "3004.90.92",
        "description": "Medicaments consisting of mixed or unmixed products for therapeutic use",
        "chapter": "30 - Pharmaceutical products",
        "heading": "3004 - Medicaments",
        "unit": "KG",
        "keywords": ["medicine", "pharmaceutical", "drug", "tablet", "capsule", "medicament"],
    },
    "9403.20": {
        "code": "9403.20.00",
        "description": "Other metal furniture",
        "chapter": "94 - Furniture; bedding, mattresses",
        "heading": "9403 - Other furniture and parts thereof",
        "unit": "NO.",
        "keywords": ["furniture", "metal", "steel", "desk", "chair", "cabinet", "shelf"],
    },
    "8703.23": {
        "code": "8703.23.00",
        "description": "Motor vehicles for transport of persons, spark-ignition engine 1500-3000cc",
        "chapter": "87 - Vehicles other than railway",
        "heading": "8703 - Motor cars and other motor vehicles",
        "unit": "NO.",
        "keywords": ["car", "automobile", "vehicle", "sedan", "suv", "motor car"],
    },
    "6204.62": {
        "code": "6204.62.40",
        "description": "Women's or girls' trousers, breeches, of cotton",
        "chapter": "62 - Articles of apparel, not knitted or crocheted",
        "heading": "6204 - Women's or girls' suits, ensembles, jackets",
        "unit": "DOZ",
        "keywords": ["pants", "trousers", "jeans", "cotton", "women", "ladies", "denim"],
    },
}

# Sample duty rates
SAMPLE_DUTY_RATES = {
    "US": {
        "6109.10.00": {"mfn": 16.5, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "8471.30.01": {"mfn": 0, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "8517.12.00": {"mfn": 0, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "0901.21.00": {"mfn": 0, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "3004.90.92": {"mfn": 0, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "9403.20.00": {"mfn": 0, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "8703.23.00": {"mfn": 2.5, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        "6204.62.40": {"mfn": 16.6, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
    },
    "EU": {
        "6109.10.00": {"mfn": 12.0, "gsp": 9.6, "fta_uk": 0},
        "8471.30.01": {"mfn": 0, "gsp": 0, "fta_uk": 0},
        "8517.12.00": {"mfn": 0, "gsp": 0, "fta_uk": 0},
    },
}

# Sample FTAs
SAMPLE_FTAS = [
    {"code": "USMCA", "name": "US-Mexico-Canada Agreement", "countries": ["US", "CA", "MX"]},
    {"code": "RCEP", "name": "Regional Comprehensive Economic Partnership", "countries": ["CN", "JP", "KR", "AU", "NZ", "SG", "MY", "TH", "VN", "ID", "PH", "BN", "KH", "LA", "MM"]},
    {"code": "CPTPP", "name": "Comprehensive and Progressive TPP", "countries": ["AU", "BN", "CA", "CL", "JP", "MY", "MX", "NZ", "PE", "SG", "VN"]},
    {"code": "EU-UK", "name": "EU-UK Trade and Cooperation Agreement", "countries": ["EU", "UK"]},
    {"code": "GSP", "name": "Generalized System of Preferences", "countries": ["BD", "PK", "KH", "LK", "ET"]},
]


def classify_with_ai(description: str, import_country: str) -> Dict[str, Any]:
    """
    AI-powered HS code classification.
    In production, this calls OpenAI/Claude for classification.
    For demo, uses keyword matching.
    """
    desc_lower = description.lower()
    
    best_match = None
    best_score = 0
    alternatives = []
    
    for code_prefix, data in SAMPLE_HS_CODES.items():
        # Calculate keyword match score
        score = 0
        matched_keywords = []
        for kw in data["keywords"]:
            if kw in desc_lower:
                score += 1
                matched_keywords.append(kw)
        
        # Boost for exact matches
        if data["description"].lower() in desc_lower:
            score += 5
        
        if score > 0:
            alternatives.append({
                "code": data["code"],
                "description": data["description"],
                "score": score,
                "keywords_matched": matched_keywords,
            })
        
        if score > best_score:
            best_score = score
            best_match = data
    
    # Sort alternatives by score
    alternatives = sorted(alternatives, key=lambda x: x["score"], reverse=True)[:5]
    
    if not best_match:
        # Default fallback
        best_match = {
            "code": "9999.99.99",
            "description": "Other goods not elsewhere specified",
            "chapter": "99 - Special classification provisions",
            "heading": "9999 - Other",
            "unit": "KG",
            "keywords": [],
        }
        alternatives = []
    
    # Calculate confidence
    confidence = min(0.98, 0.5 + (best_score * 0.1)) if best_score > 0 else 0.3
    
    # Get duty rates
    country_rates = SAMPLE_DUTY_RATES.get(import_country, SAMPLE_DUTY_RATES.get("US", {}))
    rates = country_rates.get(best_match["code"], {"mfn": 0})
    
    # Build reasoning
    reasoning = f"Based on the description '{description}', the product appears to be {best_match['description']}. "
    if alternatives:
        reasoning += f"Key terms identified: {', '.join(alternatives[0].get('keywords_matched', []))}. "
    reasoning += f"Classified under Chapter {best_match.get('chapter', 'N/A')}."
    
    return {
        "hs_code": best_match["code"],
        "description": best_match["description"],
        "confidence": confidence,
        "chapter": best_match.get("chapter", ""),
        "heading": best_match.get("heading", ""),
        "subheading": best_match["code"][:6] if len(best_match["code"]) >= 6 else "",
        "unit": best_match.get("unit", ""),
        "alternatives": alternatives[1:] if len(alternatives) > 1 else [],
        "duty_rates": rates,
        "reasoning": reasoning,
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
    
    # Run AI classification
    result = classify_with_ai(request.description, request.import_country)
    
    # Get FTA options
    fta_options = []
    if request.export_country:
        for fta in SAMPLE_FTAS:
            if (request.export_country in fta["countries"] and 
                request.import_country in fta["countries"]):
                fta_options.append({
                    "code": fta["code"],
                    "name": fta["name"],
                    "preferential_rate": 0,  # Would look up actual rate
                    "savings_percent": result["duty_rates"].get("mfn", 0),
                })
    
    # Check restrictions (demo - would query actual restriction database)
    restrictions = []
    if "medicine" in request.description.lower() or "drug" in request.description.lower():
        restrictions.append("FDA approval may be required for pharmaceutical imports")
    if "firearm" in request.description.lower() or "weapon" in request.description.lower():
        restrictions.append("Import license required from ATF")
    
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
        chapter=result["chapter"],
        heading=result["heading"],
        subheading=result["subheading"],
        alternatives=result["alternatives"],
        duty_rates=result["duty_rates"],
        fta_options=fta_options,
        restrictions=restrictions,
        ai_reasoning=result["reasoning"],
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
    q_lower = q.lower()
    results = []
    
    # Check if searching by code
    is_code_search = q.replace(".", "").isdigit()
    
    for code_prefix, data in SAMPLE_HS_CODES.items():
        score = 0
        
        if is_code_search:
            # Code search
            if data["code"].startswith(q.replace(".", "")):
                score = 100
        else:
            # Description/keyword search
            if q_lower in data["description"].lower():
                score = 50
            for kw in data["keywords"]:
                if q_lower in kw:
                    score += 10
        
        if score > 0:
            results.append({
                "code": data["code"],
                "description": data["description"],
                "chapter": data.get("chapter", ""),
                "score": score,
            })
    
    # Sort by score
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
    
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
    # Normalize code
    code_normalized = hs_code.replace(".", "")
    
    # Find code
    found = None
    for code_prefix, data in SAMPLE_HS_CODES.items():
        if data["code"].replace(".", "").startswith(code_normalized):
            found = data
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"HS code {hs_code} not found")
    
    # Get duty rates
    country_rates = SAMPLE_DUTY_RATES.get(import_country, {})
    rates = country_rates.get(found["code"], {"mfn": 0})
    
    # Get FTA options
    fta_options = []
    if export_country:
        for fta in SAMPLE_FTAS:
            if export_country in fta["countries"] and import_country in fta["countries"]:
                fta_options.append({
                    "code": fta["code"],
                    "name": fta["name"],
                    "preferential_rate": 0,
                })
    
    return {
        "code": found["code"],
        "description": found["description"],
        "chapter": found.get("chapter", ""),
        "heading": found.get("heading", ""),
        "unit_of_quantity": found.get("unit", ""),
        "duty_rates": {
            "import_country": import_country,
            "mfn_rate": rates.get("mfn", 0),
            "rates_by_origin": rates,
        },
        "fta_options": fta_options,
        "related_codes": [],
    }


@router.post("/calculate-duty")
async def calculate_duty(
    request: DutyCalculateRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate import duties for a product.
    """
    # Get duty rate
    country_rates = SAMPLE_DUTY_RATES.get(request.import_country, {})
    rates = country_rates.get(request.hs_code, {"mfn": 0})
    
    # Determine applicable rate
    applicable_rate = rates.get("mfn", 0)
    rate_type = "MFN"
    
    if request.fta_code:
        fta_key = f"fta_{request.fta_code.lower()}"
        if fta_key in rates:
            applicable_rate = rates[fta_key]
            rate_type = request.fta_code
    elif request.export_country:
        # Check for GSP or other preferential
        gsp_rate = rates.get("gsp")
        if gsp_rate is not None and request.export_country in ["BD", "PK", "KH", "LK"]:
            applicable_rate = gsp_rate
            rate_type = "GSP"
    
    # Calculate duty
    duty_amount = request.product_value * (applicable_rate / 100)
    
    # Potential savings
    mfn_duty = request.product_value * (rates.get("mfn", 0) / 100)
    savings = mfn_duty - duty_amount
    
    return {
        "hs_code": request.hs_code,
        "import_country": request.import_country,
        "export_country": request.export_country,
        "product_value": request.product_value,
        "currency": "USD",
        "duty_calculation": {
            "rate_type": rate_type,
            "rate_percent": applicable_rate,
            "duty_amount": round(duty_amount, 2),
        },
        "mfn_comparison": {
            "mfn_rate": rates.get("mfn", 0),
            "mfn_duty": round(mfn_duty, 2),
            "savings": round(savings, 2),
        },
        "landed_cost_estimate": {
            "product_value": request.product_value,
            "duty": round(duty_amount, 2),
            "estimated_freight": round(request.product_value * 0.05, 2),  # 5% estimate
            "total": round(request.product_value + duty_amount + (request.product_value * 0.05), 2),
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
    eligible_ftas = []
    
    for fta in SAMPLE_FTAS:
        if export_country in fta["countries"] and import_country in fta["countries"]:
            # Get duty rates
            country_rates = SAMPLE_DUTY_RATES.get(import_country, {})
            rates = country_rates.get(hs_code, {"mfn": 0})
            
            eligible_ftas.append({
                "fta_code": fta["code"],
                "fta_name": fta["name"],
                "mfn_rate": rates.get("mfn", 0),
                "preferential_rate": 0,  # Would look up actual
                "savings_percent": rates.get("mfn", 0),
                "rules_of_origin": {
                    "requirement": "Change in Tariff Classification (CTC) at 4-digit level",
                    "rvc_threshold": "40% Regional Value Content",
                    "certificate_required": "Certificate of Origin Form D" if fta["code"] == "RCEP" else "Certificate of Origin",
                },
                "documentation": [
                    "Certificate of Origin",
                    "Commercial Invoice showing origin",
                    "Bill of Lading",
                    "Packing List",
                ],
            })
    
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
async def list_ftas():
    """
    List supported Free Trade Agreements.
    """
    return {
        "ftas": [
            {
                "code": fta["code"],
                "name": fta["name"],
                "member_count": len(fta["countries"]),
                "members": fta["countries"],
            }
            for fta in SAMPLE_FTAS
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
    result = classify_with_ai(request.product_description, request.import_country)
    
    classification = HSClassification(
        user_id=current_user.id,
        product_description=request.product_description,
        product_name=request.product_name,
        hs_code=request.hs_code,
        hs_code_description=result["description"],
        import_country=request.import_country,
        export_country=request.export_country,
        source=ClassificationSource.AI,
        confidence_score=result["confidence"],
        alternative_codes=result["alternatives"],
        ai_reasoning=result["reasoning"],
        mfn_rate=result["duty_rates"].get("mfn"),
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

