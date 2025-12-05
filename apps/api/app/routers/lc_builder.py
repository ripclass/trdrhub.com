"""
LC Builder API Router

Endpoints for creating and managing LC applications.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.lc_builder import (
    LCApplication, LCDocumentRequirement, LCApplicationVersion,
    LCClause, LCTemplate, ApplicantProfile, BeneficiaryProfile,
    LCType, LCStatus, PaymentTerms, ConfirmationInstructions
)
from app.routers.auth import get_current_user, get_optional_user
from app.services.lc_clause_library import (
    LCClauseLibrary, ClauseCategory, RiskLevel, BiasIndicator
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lc-builder", tags=["lc-builder"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PartyInfo(BaseModel):
    name: str
    address: Optional[str] = None
    country: Optional[str] = None
    contact: Optional[str] = None


class BankInfo(BaseModel):
    name: Optional[str] = None
    swift: Optional[str] = None


class DocumentRequirementCreate(BaseModel):
    document_type: str
    description: Optional[str] = None
    copies_original: int = 1
    copies_copy: int = 0
    specific_requirements: Optional[str] = None
    is_required: bool = True


class LCApplicationCreate(BaseModel):
    """Create a new LC application"""
    name: Optional[str] = None
    lc_type: str = "documentary"
    
    # Amount
    currency: str = "USD"
    amount: float
    tolerance_plus: float = 0
    tolerance_minus: float = 0
    
    # Parties
    applicant: PartyInfo
    beneficiary: PartyInfo
    issuing_bank: Optional[BankInfo] = None
    advising_bank: Optional[BankInfo] = None
    
    # Shipment
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    place_of_delivery: Optional[str] = None
    latest_shipment_date: Optional[datetime] = None
    incoterms: Optional[str] = None
    incoterms_place: Optional[str] = None
    partial_shipments: bool = True
    transhipment: bool = True
    
    # Goods
    goods_description: str
    hs_code: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    
    # Payment
    payment_terms: str = "sight"
    usance_days: Optional[int] = None
    usance_from: Optional[str] = None
    
    # Validity
    expiry_date: datetime
    expiry_place: Optional[str] = None
    presentation_period: int = 21
    confirmation_instructions: str = "without"
    
    # Documents & Clauses
    documents_required: List[DocumentRequirementCreate] = []
    additional_conditions: List[str] = []
    selected_clause_ids: List[str] = []
    
    # Template
    template_id: Optional[str] = None


class LCApplicationUpdate(BaseModel):
    """Update LC application"""
    name: Optional[str] = None
    lc_type: Optional[str] = None
    status: Optional[str] = None
    
    # Amount
    currency: Optional[str] = None
    amount: Optional[float] = None
    tolerance_plus: Optional[float] = None
    tolerance_minus: Optional[float] = None
    
    # Parties
    applicant_name: Optional[str] = None
    applicant_address: Optional[str] = None
    applicant_country: Optional[str] = None
    beneficiary_name: Optional[str] = None
    beneficiary_address: Optional[str] = None
    beneficiary_country: Optional[str] = None
    
    # Banks
    issuing_bank_name: Optional[str] = None
    issuing_bank_swift: Optional[str] = None
    advising_bank_name: Optional[str] = None
    advising_bank_swift: Optional[str] = None
    
    # Shipment
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    latest_shipment_date: Optional[datetime] = None
    incoterms: Optional[str] = None
    incoterms_place: Optional[str] = None
    partial_shipments: Optional[bool] = None
    transhipment: Optional[bool] = None
    
    # Goods
    goods_description: Optional[str] = None
    hs_code: Optional[str] = None
    
    # Payment
    payment_terms: Optional[str] = None
    usance_days: Optional[int] = None
    
    # Validity
    expiry_date: Optional[datetime] = None
    expiry_place: Optional[str] = None
    presentation_period: Optional[int] = None
    confirmation_instructions: Optional[str] = None
    
    # Documents & Clauses
    documents_required: Optional[List[DocumentRequirementCreate]] = None
    additional_conditions: Optional[List[str]] = None
    selected_clause_ids: Optional[List[str]] = None


class ValidationIssue(BaseModel):
    field: str
    severity: str  # error, warning, info
    message: str
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue]
    risk_score: float
    risk_details: Dict[str, Any]


class ClauseResponse(BaseModel):
    code: str
    category: str
    subcategory: str
    title: str
    clause_text: str
    plain_english: str
    risk_level: str
    bias: str
    risk_notes: str
    bank_acceptance: float
    tags: List[str]


# ============================================================================
# Helper Functions
# ============================================================================

def generate_reference_number() -> str:
    """Generate unique LC reference number"""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"LC-{timestamp}-{unique_id}"


def validate_lc_application(lc: LCApplication) -> ValidationResult:
    """Validate LC application and calculate risk score"""
    issues = []
    risk_factors = []
    
    # Date validations
    if lc.latest_shipment_date and lc.expiry_date:
        days_between = (lc.expiry_date - lc.latest_shipment_date).days
        if days_between < 21:
            issues.append(ValidationIssue(
                field="expiry_date",
                severity="warning",
                message=f"Only {days_between} days between shipment and expiry (minimum 21 recommended)",
                suggestion="Extend expiry date to allow time for document preparation and presentation"
            ))
            risk_factors.append(("tight_timeline", 15))
        
        if days_between < 0:
            issues.append(ValidationIssue(
                field="expiry_date",
                severity="error",
                message="Expiry date is before shipment date",
                suggestion="Expiry must be after latest shipment date"
            ))
    
    # Amount validations
    if lc.amount <= 0:
        issues.append(ValidationIssue(
            field="amount",
            severity="error",
            message="Amount must be greater than zero"
        ))
    
    if lc.tolerance_plus > 10 or lc.tolerance_minus > 10:
        issues.append(ValidationIssue(
            field="tolerance",
            severity="warning",
            message="Tolerance exceeds 10% which may cause issues with some banks",
            suggestion="Consider using standard 5% or 10% tolerance"
        ))
        risk_factors.append(("high_tolerance", 10))
    
    # Party validations
    if not lc.applicant_name:
        issues.append(ValidationIssue(
            field="applicant_name",
            severity="error",
            message="Applicant name is required"
        ))
    
    if not lc.beneficiary_name:
        issues.append(ValidationIssue(
            field="beneficiary_name",
            severity="error",
            message="Beneficiary name is required"
        ))
    
    # Goods description
    if not lc.goods_description or len(lc.goods_description) < 10:
        issues.append(ValidationIssue(
            field="goods_description",
            severity="warning",
            message="Goods description is too short",
            suggestion="Provide detailed goods description including quantity and specifications"
        ))
    
    # Incoterms + Insurance check
    if lc.incoterms in ["FOB", "CFR", "FCA"]:
        # Check if insurance document is required
        docs = lc.documents_required or []
        has_insurance = any("insurance" in str(d).lower() for d in docs)
        if not has_insurance:
            issues.append(ValidationIssue(
                field="documents_required",
                severity="info",
                message=f"With {lc.incoterms} terms, insurance is buyer's responsibility",
                suggestion="Consider whether insurance certificate should be required from seller"
            ))
    
    # Payment terms validation
    if lc.payment_terms == PaymentTerms.USANCE and not lc.usance_days:
        issues.append(ValidationIssue(
            field="usance_days",
            severity="error",
            message="Usance days required for deferred payment",
            suggestion="Specify number of days (e.g., 30, 60, 90)"
        ))
    
    # Presentation period
    if lc.presentation_period and lc.presentation_period < 14:
        issues.append(ValidationIssue(
            field="presentation_period",
            severity="warning",
            message=f"Presentation period of {lc.presentation_period} days is shorter than typical",
            suggestion="Consider extending to at least 21 days (UCP600 default)"
        ))
        risk_factors.append(("short_presentation", 10))
    
    # Calculate risk score (0-100, lower is better)
    base_score = 0
    for factor, points in risk_factors:
        base_score += points
    
    # Clause-based risk
    if lc.selected_clause_ids:
        for code in lc.selected_clause_ids:
            clause = LCClauseLibrary.get_clause_by_code(code)
            if clause:
                if clause.risk_level == RiskLevel.HIGH:
                    base_score += 15
                elif clause.risk_level == RiskLevel.MEDIUM:
                    base_score += 5
    
    # Error count increases risk
    error_count = len([i for i in issues if i.severity == "error"])
    base_score += error_count * 20
    
    risk_score = min(100, max(0, base_score))
    
    return ValidationResult(
        is_valid=error_count == 0,
        issues=issues,
        risk_score=risk_score,
        risk_details={
            "factors": [f[0] for f in risk_factors],
            "error_count": error_count,
            "warning_count": len([i for i in issues if i.severity == "warning"]),
            "clause_risk_contribution": sum(
                15 if LCClauseLibrary.get_clause_by_code(c) and 
                LCClauseLibrary.get_clause_by_code(c).risk_level == RiskLevel.HIGH else
                5 if LCClauseLibrary.get_clause_by_code(c) and
                LCClauseLibrary.get_clause_by_code(c).risk_level == RiskLevel.MEDIUM else 0
                for c in (lc.selected_clause_ids or [])
            )
        }
    )


# ============================================================================
# LC Application Endpoints
# ============================================================================

@router.post("/applications")
async def create_lc_application(
    data: LCApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new LC application"""
    
    # Create application
    lc = LCApplication(
        user_id=current_user.id,
        reference_number=generate_reference_number(),
        name=data.name,
        lc_type=LCType(data.lc_type),
        status=LCStatus.DRAFT,
        
        # Amount
        currency=data.currency,
        amount=data.amount,
        tolerance_plus=data.tolerance_plus,
        tolerance_minus=data.tolerance_minus,
        
        # Applicant
        applicant_name=data.applicant.name,
        applicant_address=data.applicant.address,
        applicant_country=data.applicant.country,
        applicant_contact=data.applicant.contact,
        
        # Beneficiary
        beneficiary_name=data.beneficiary.name,
        beneficiary_address=data.beneficiary.address,
        beneficiary_country=data.beneficiary.country,
        beneficiary_contact=data.beneficiary.contact,
        
        # Banks
        issuing_bank_name=data.issuing_bank.name if data.issuing_bank else None,
        issuing_bank_swift=data.issuing_bank.swift if data.issuing_bank else None,
        advising_bank_name=data.advising_bank.name if data.advising_bank else None,
        advising_bank_swift=data.advising_bank.swift if data.advising_bank else None,
        
        # Shipment
        port_of_loading=data.port_of_loading,
        port_of_discharge=data.port_of_discharge,
        place_of_delivery=data.place_of_delivery,
        latest_shipment_date=data.latest_shipment_date,
        incoterms=data.incoterms,
        incoterms_place=data.incoterms_place,
        partial_shipments=data.partial_shipments,
        transhipment=data.transhipment,
        
        # Goods
        goods_description=data.goods_description,
        hs_code=data.hs_code,
        quantity=data.quantity,
        unit_price=data.unit_price,
        
        # Payment
        payment_terms=PaymentTerms(data.payment_terms),
        usance_days=data.usance_days,
        usance_from=data.usance_from,
        
        # Validity
        expiry_date=data.expiry_date,
        expiry_place=data.expiry_place,
        presentation_period=data.presentation_period,
        confirmation_instructions=ConfirmationInstructions(data.confirmation_instructions),
        
        # Documents & Conditions
        documents_required=[d.dict() for d in data.documents_required],
        additional_conditions=data.additional_conditions,
        selected_clause_ids=data.selected_clause_ids,
    )
    
    db.add(lc)
    db.commit()
    db.refresh(lc)
    
    # Validate and update risk score
    validation = validate_lc_application(lc)
    lc.validation_issues = [i.dict() for i in validation.issues]
    lc.risk_score = validation.risk_score
    lc.risk_details = validation.risk_details
    db.commit()
    
    return {
        "id": str(lc.id),
        "reference_number": lc.reference_number,
        "status": lc.status.value,
        "validation": validation.dict(),
        "created_at": lc.created_at.isoformat()
    }


@router.get("/applications")
async def list_lc_applications(
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's LC applications"""
    
    query = db.query(LCApplication).filter(
        LCApplication.user_id == current_user.id
    )
    
    if status:
        query = query.filter(LCApplication.status == LCStatus(status))
    
    total = query.count()
    applications = query.order_by(
        LCApplication.updated_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "applications": [
            {
                "id": str(app.id),
                "reference_number": app.reference_number,
                "name": app.name,
                "status": app.status.value,
                "lc_type": app.lc_type.value,
                "amount": app.amount,
                "currency": app.currency,
                "beneficiary_name": app.beneficiary_name,
                "expiry_date": app.expiry_date.isoformat() if app.expiry_date else None,
                "risk_score": app.risk_score,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
            }
            for app in applications
        ]
    }


@router.get("/applications/{application_id}")
async def get_lc_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific LC application"""
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    return {
        "id": str(lc.id),
        "reference_number": lc.reference_number,
        "name": lc.name,
        "status": lc.status.value,
        "lc_type": lc.lc_type.value,
        
        # Amount
        "currency": lc.currency,
        "amount": lc.amount,
        "tolerance_plus": lc.tolerance_plus,
        "tolerance_minus": lc.tolerance_minus,
        
        # Parties
        "applicant": {
            "name": lc.applicant_name,
            "address": lc.applicant_address,
            "country": lc.applicant_country,
            "contact": lc.applicant_contact,
        },
        "beneficiary": {
            "name": lc.beneficiary_name,
            "address": lc.beneficiary_address,
            "country": lc.beneficiary_country,
            "contact": lc.beneficiary_contact,
        },
        "issuing_bank": {
            "name": lc.issuing_bank_name,
            "swift": lc.issuing_bank_swift,
        } if lc.issuing_bank_name else None,
        "advising_bank": {
            "name": lc.advising_bank_name,
            "swift": lc.advising_bank_swift,
        } if lc.advising_bank_name else None,
        
        # Shipment
        "port_of_loading": lc.port_of_loading,
        "port_of_discharge": lc.port_of_discharge,
        "place_of_delivery": lc.place_of_delivery,
        "latest_shipment_date": lc.latest_shipment_date.isoformat() if lc.latest_shipment_date else None,
        "incoterms": lc.incoterms,
        "incoterms_place": lc.incoterms_place,
        "partial_shipments": lc.partial_shipments,
        "transhipment": lc.transhipment,
        
        # Goods
        "goods_description": lc.goods_description,
        "hs_code": lc.hs_code,
        "quantity": lc.quantity,
        "unit_price": lc.unit_price,
        
        # Payment
        "payment_terms": lc.payment_terms.value,
        "usance_days": lc.usance_days,
        "usance_from": lc.usance_from,
        
        # Validity
        "expiry_date": lc.expiry_date.isoformat() if lc.expiry_date else None,
        "expiry_place": lc.expiry_place,
        "presentation_period": lc.presentation_period,
        "confirmation_instructions": lc.confirmation_instructions.value,
        
        # Documents & Conditions
        "documents_required": lc.documents_required,
        "additional_conditions": lc.additional_conditions,
        "selected_clause_ids": lc.selected_clause_ids,
        
        # Validation
        "validation_issues": lc.validation_issues,
        "risk_score": lc.risk_score,
        "risk_details": lc.risk_details,
        
        # Metadata
        "created_at": lc.created_at.isoformat(),
        "updated_at": lc.updated_at.isoformat(),
    }


@router.put("/applications/{application_id}")
async def update_lc_application(
    application_id: str,
    data: LCApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an LC application"""
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    if lc.status not in [LCStatus.DRAFT, LCStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Cannot edit submitted LC application")
    
    # Update fields
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field == "documents_required" and value:
                value = [d.dict() if hasattr(d, 'dict') else d for d in value]
            setattr(lc, field, value)
    
    lc.updated_at = datetime.utcnow()
    
    # Re-validate
    validation = validate_lc_application(lc)
    lc.validation_issues = [i.dict() for i in validation.issues]
    lc.risk_score = validation.risk_score
    lc.risk_details = validation.risk_details
    
    db.commit()
    
    return {
        "id": str(lc.id),
        "status": "updated",
        "validation": validation.dict()
    }


@router.delete("/applications/{application_id}")
async def delete_lc_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an LC application"""
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    if lc.status == LCStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cannot delete submitted LC application")
    
    db.delete(lc)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/applications/{application_id}/validate")
async def validate_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate an LC application"""
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    validation = validate_lc_application(lc)
    
    # Update stored validation
    lc.validation_issues = [i.dict() for i in validation.issues]
    lc.risk_score = validation.risk_score
    lc.risk_details = validation.risk_details
    db.commit()
    
    return validation.dict()


@router.post("/applications/{application_id}/duplicate")
async def duplicate_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an LC application"""
    
    original = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    # Create copy
    new_lc = LCApplication(
        user_id=current_user.id,
        reference_number=generate_reference_number(),
        name=f"Copy of {original.name}" if original.name else None,
        lc_type=original.lc_type,
        status=LCStatus.DRAFT,
        
        currency=original.currency,
        amount=original.amount,
        tolerance_plus=original.tolerance_plus,
        tolerance_minus=original.tolerance_minus,
        
        applicant_name=original.applicant_name,
        applicant_address=original.applicant_address,
        applicant_country=original.applicant_country,
        
        beneficiary_name=original.beneficiary_name,
        beneficiary_address=original.beneficiary_address,
        beneficiary_country=original.beneficiary_country,
        
        port_of_loading=original.port_of_loading,
        port_of_discharge=original.port_of_discharge,
        incoterms=original.incoterms,
        partial_shipments=original.partial_shipments,
        transhipment=original.transhipment,
        
        goods_description=original.goods_description,
        hs_code=original.hs_code,
        
        payment_terms=original.payment_terms,
        usance_days=original.usance_days,
        
        presentation_period=original.presentation_period,
        confirmation_instructions=original.confirmation_instructions,
        
        documents_required=original.documents_required,
        additional_conditions=original.additional_conditions,
        selected_clause_ids=original.selected_clause_ids,
    )
    
    db.add(new_lc)
    db.commit()
    db.refresh(new_lc)
    
    return {
        "id": str(new_lc.id),
        "reference_number": new_lc.reference_number,
        "status": "created"
    }


# ============================================================================
# Clause Library Endpoints
# ============================================================================

@router.get("/clauses")
async def list_clauses(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    bias: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0
):
    """List clauses from the library"""
    
    cat = ClauseCategory(category) if category else None
    risk = RiskLevel(risk_level) if risk_level else None
    bi = BiasIndicator(bias) if bias else None
    
    clauses = LCClauseLibrary.search_clauses(
        query=search or "",
        category=cat,
        risk_level=risk,
        bias=bi
    )
    
    total = len(clauses)
    paged = clauses[offset:offset + limit]
    
    return {
        "total": total,
        "clauses": [
            {
                "code": c.code,
                "category": c.category.value,
                "subcategory": c.subcategory,
                "title": c.title,
                "clause_text": c.clause_text,
                "plain_english": c.plain_english,
                "risk_level": c.risk_level.value,
                "bias": c.bias.value,
                "risk_notes": c.risk_notes,
                "bank_acceptance": c.bank_acceptance,
                "tags": c.tags,
            }
            for c in paged
        ]
    }


@router.get("/clauses/categories")
async def get_clause_categories():
    """Get clause category counts"""
    stats = LCClauseLibrary.get_statistics()
    return {
        "total": stats["total_clauses"],
        "categories": stats["categories"],
        "by_risk_level": stats["by_risk_level"],
        "by_bias": stats["by_bias"],
    }


@router.get("/clauses/{code}")
async def get_clause(code: str):
    """Get a specific clause by code"""
    
    clause = LCClauseLibrary.get_clause_by_code(code)
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    
    return {
        "code": clause.code,
        "category": clause.category.value,
        "subcategory": clause.subcategory,
        "title": clause.title,
        "clause_text": clause.clause_text,
        "plain_english": clause.plain_english,
        "risk_level": clause.risk_level.value,
        "bias": clause.bias.value,
        "risk_notes": clause.risk_notes,
        "bank_acceptance": clause.bank_acceptance,
        "tags": clause.tags,
    }


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates")
async def list_templates(
    trade_route: Optional[str] = None,
    industry: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """List available templates"""
    
    query = db.query(LCTemplate)
    
    # Include public/system templates and user's own
    if current_user:
        query = query.filter(
            (LCTemplate.is_public == True) |
            (LCTemplate.is_system == True) |
            (LCTemplate.user_id == current_user.id)
        )
    else:
        query = query.filter(
            (LCTemplate.is_public == True) |
            (LCTemplate.is_system == True)
        )
    
    if trade_route:
        query = query.filter(LCTemplate.trade_route.ilike(f"%{trade_route}%"))
    
    if industry:
        query = query.filter(LCTemplate.industry.ilike(f"%{industry}%"))
    
    templates = query.all()
    
    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "trade_route": t.trade_route,
                "industry": t.industry,
                "is_system": t.is_system,
                "usage_count": t.usage_count,
            }
            for t in templates
        ]
    }


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Get template details"""
    
    template = db.query(LCTemplate).filter(LCTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "trade_route": template.trade_route,
        "industry": template.industry,
        "template_data": template.template_data,
        "default_clause_ids": template.default_clause_ids,
        "default_documents": template.default_documents,
    }


# ============================================================================
# Profile Endpoints
# ============================================================================

@router.get("/profiles/applicants")
async def list_applicant_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List saved applicant profiles"""
    
    profiles = db.query(ApplicantProfile).filter(
        ApplicantProfile.user_id == current_user.id
    ).all()
    
    return {
        "profiles": [
            {
                "id": str(p.id),
                "name": p.name,
                "address": p.address,
                "country": p.country,
                "is_default": p.is_default,
            }
            for p in profiles
        ]
    }


@router.get("/profiles/beneficiaries")
async def list_beneficiary_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List saved beneficiary profiles"""
    
    profiles = db.query(BeneficiaryProfile).filter(
        BeneficiaryProfile.user_id == current_user.id
    ).all()
    
    return {
        "profiles": [
            {
                "id": str(p.id),
                "name": p.name,
                "address": p.address,
                "country": p.country,
                "trade_history_count": p.trade_history_count,
            }
            for p in profiles
        ]
    }


# ============================================================================
# Export Endpoints
# ============================================================================

@router.post("/applications/{application_id}/export/mt700")
async def export_mt700(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export LC application as MT700 SWIFT message"""
    from app.services.mt700_generator import MT700Generator
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    # Build LC data dict
    lc_data = {
        "reference_number": lc.reference_number,
        "lc_type": lc.lc_type.value,
        "currency": lc.currency,
        "amount": lc.amount,
        "tolerance_plus": lc.tolerance_plus,
        "tolerance_minus": lc.tolerance_minus,
        "applicant": {
            "name": lc.applicant_name,
            "address": lc.applicant_address,
            "country": lc.applicant_country,
        },
        "beneficiary": {
            "name": lc.beneficiary_name,
            "address": lc.beneficiary_address,
            "country": lc.beneficiary_country,
        },
        "port_of_loading": lc.port_of_loading,
        "port_of_discharge": lc.port_of_discharge,
        "place_of_delivery": lc.place_of_delivery,
        "latest_shipment_date": lc.latest_shipment_date,
        "incoterms": lc.incoterms,
        "incoterms_place": lc.incoterms_place,
        "partial_shipments": lc.partial_shipments,
        "transhipment": lc.transhipment,
        "goods_description": lc.goods_description,
        "payment_terms": lc.payment_terms.value,
        "usance_days": lc.usance_days,
        "usance_from": lc.usance_from,
        "expiry_date": lc.expiry_date,
        "expiry_place": lc.expiry_place,
        "presentation_period": lc.presentation_period,
        "confirmation_instructions": lc.confirmation_instructions.value,
        "documents_required": lc.documents_required,
        "additional_conditions": lc.additional_conditions,
    }
    
    generator = MT700Generator(lc_data)
    result = generator.build()
    
    return result


@router.get("/mt700/fields")
async def get_mt700_field_reference():
    """Get MT700 field reference for UI"""
    from app.services.mt700_generator import MT700Generator
    return {"fields": MT700Generator.field_reference()}


@router.post("/applications/{application_id}/export/pdf")
async def export_pdf(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export LC application as PDF"""
    from fastapi.responses import Response
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    
    lc = db.query(LCApplication).filter(
        LCApplication.id == application_id,
        LCApplication.user_id == current_user.id
    ).first()
    
    if not lc:
        raise HTTPException(status_code=404, detail="LC application not found")
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # Center
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#1e40af")
    )
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph("DOCUMENTARY CREDIT APPLICATION", title_style))
    elements.append(Paragraph(f"Reference: {lc.reference_number}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Basic Info
    elements.append(Paragraph("1. BASIC INFORMATION", heading_style))
    basic_data = [
        ["Type of Credit:", lc.lc_type.value.upper()],
        ["Currency & Amount:", f"{lc.currency} {lc.amount:,.2f}"],
        ["Tolerance:", f"+{lc.tolerance_plus}% / -{lc.tolerance_minus}%"],
    ]
    basic_table = Table(basic_data, colWidths=[2*inch, 4*inch])
    basic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(basic_table)
    
    # Parties
    elements.append(Paragraph("2. PARTIES", heading_style))
    parties_data = [
        ["APPLICANT:", "BENEFICIARY:"],
        [lc.applicant_name or "", lc.beneficiary_name or ""],
        [lc.applicant_address or "", lc.beneficiary_address or ""],
        [lc.applicant_country or "", lc.beneficiary_country or ""],
    ]
    parties_table = Table(parties_data, colWidths=[3*inch, 3*inch])
    parties_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(parties_table)
    
    # Shipment
    elements.append(Paragraph("3. SHIPMENT DETAILS", heading_style))
    ship_data = [
        ["Port of Loading:", lc.port_of_loading or "Any Port"],
        ["Port of Discharge:", lc.port_of_discharge or ""],
        ["Latest Shipment:", lc.latest_shipment_date.strftime("%d %B %Y") if lc.latest_shipment_date else ""],
        ["Incoterms:", f"{lc.incoterms} {lc.incoterms_place or ''}" if lc.incoterms else ""],
        ["Partial Shipments:", "ALLOWED" if lc.partial_shipments else "NOT ALLOWED"],
        ["Transhipment:", "ALLOWED" if lc.transhipment else "NOT ALLOWED"],
    ]
    ship_table = Table(ship_data, colWidths=[2*inch, 4*inch])
    ship_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(ship_table)
    
    # Goods
    elements.append(Paragraph("4. GOODS DESCRIPTION", heading_style))
    elements.append(Paragraph(lc.goods_description or "", normal_style))
    
    # Payment
    elements.append(Paragraph("5. PAYMENT TERMS", heading_style))
    payment_text = lc.payment_terms.value.upper()
    if lc.payment_terms.value == "usance" and lc.usance_days:
        payment_text = f"{lc.usance_days} DAYS FROM {lc.usance_from or 'B/L DATE'}"
    pay_data = [
        ["Payment:", payment_text],
        ["Expiry Date:", lc.expiry_date.strftime("%d %B %Y") if lc.expiry_date else ""],
        ["Expiry Place:", lc.expiry_place or ""],
        ["Presentation Period:", f"{lc.presentation_period} days after shipment"],
        ["Confirmation:", lc.confirmation_instructions.value.upper()],
    ]
    pay_table = Table(pay_data, colWidths=[2*inch, 4*inch])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(pay_table)
    
    # Documents
    elements.append(Paragraph("6. DOCUMENTS REQUIRED", heading_style))
    if lc.documents_required:
        for i, doc in enumerate(lc.documents_required, 1):
            if isinstance(doc, dict):
                doc_text = f"{i}. {doc.get('document_type', '')} - {doc.get('copies_original', 1)} original(s)"
                if doc.get('specific_requirements'):
                    doc_text += f"\n   {doc['specific_requirements']}"
            else:
                doc_text = f"{i}. {doc}"
            elements.append(Paragraph(doc_text, normal_style))
    
    # Additional Conditions
    if lc.additional_conditions:
        elements.append(Paragraph("7. ADDITIONAL CONDITIONS", heading_style))
        for cond in lc.additional_conditions:
            elements.append(Paragraph(f"• {cond}", normal_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')} by TRDR Hub LC Builder",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.gray)
    ))
    
    doc.build(elements)
    
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=LC_{lc.reference_number}.pdf"
        }
    )

