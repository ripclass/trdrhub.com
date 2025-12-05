"""
Doc Generator Catalog Router

API endpoints for templates, product catalog, and buyer directory.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.models.doc_generator_catalog import (
    DocumentTemplate, ProductCatalogItem, BuyerProfile,
    DocumentAuditLog, AuditAction
)
from app.routers.auth import get_current_user
from app.services.document_audit import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doc-generator", tags=["doc-generator-catalog"])


# ============== Pydantic Schemas ==============

# Templates
class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    beneficiary_name: Optional[str] = None
    beneficiary_address: Optional[str] = None
    beneficiary_country: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_swift: Optional[str] = None
    bank_address: Optional[str] = None
    default_port_of_loading: Optional[str] = None
    default_incoterms: Optional[str] = None
    default_country_of_origin: Optional[str] = None
    preferred_document_types: Optional[List[str]] = None
    default_draft_tenor: Optional[str] = None
    default_shipping_marks: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_default: bool
    use_count: int
    beneficiary_name: Optional[str]
    beneficiary_address: Optional[str]
    bank_name: Optional[str]
    default_port_of_loading: Optional[str]
    default_incoterms: Optional[str]
    preferred_document_types: Optional[List[str]]
    created_at: datetime


# Products
class ProductCreate(BaseModel):
    sku: Optional[str] = None
    product_code: Optional[str] = None
    name: str
    hs_code: Optional[str] = None
    description: str
    short_description: Optional[str] = None
    default_unit_price: Optional[float] = None
    currency: str = "USD"
    default_unit: str = "PCS"
    units_per_carton: Optional[int] = None
    weight_per_unit_kg: Optional[float] = None
    carton_dimensions: Optional[str] = None
    carton_weight_kg: Optional[float] = None
    cbm_per_carton: Optional[float] = None
    country_of_origin: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    sku: Optional[str]
    product_code: Optional[str]
    name: str
    hs_code: Optional[str]
    description: str
    short_description: Optional[str]
    default_unit_price: Optional[float]
    currency: str
    default_unit: str
    units_per_carton: Optional[int]
    weight_per_unit_kg: Optional[float]
    country_of_origin: Optional[str]
    is_active: bool
    use_count: int


# Buyers
class BuyerCreate(BaseModel):
    buyer_code: Optional[str] = None
    company_name: str
    country: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notify_party_name: Optional[str] = None
    notify_party_address: Optional[str] = None
    preferred_incoterms: Optional[str] = None
    preferred_port_of_discharge: Optional[str] = None
    default_currency: str = "USD"
    buyer_bank_name: Optional[str] = None
    buyer_bank_swift: Optional[str] = None
    notes: Optional[str] = None


class BuyerResponse(BaseModel):
    id: str
    buyer_code: Optional[str]
    company_name: str
    country: Optional[str]
    address_line1: Optional[str]
    city: Optional[str]
    contact_person: Optional[str]
    email: Optional[str]
    preferred_incoterms: Optional[str]
    default_currency: str
    is_active: bool
    use_count: int


# Audit
class AuditLogResponse(BaseModel):
    id: str
    document_set_id: str
    user_id: str
    action: str
    action_detail: Optional[str]
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    created_at: Optional[str]


# ============== Templates Endpoints ==============

@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new document template"""
    
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    template = DocumentTemplate(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        beneficiary_name=request.beneficiary_name,
        beneficiary_address=request.beneficiary_address,
        beneficiary_country=request.beneficiary_country,
        bank_name=request.bank_name,
        bank_account=request.bank_account,
        bank_swift=request.bank_swift,
        bank_address=request.bank_address,
        default_port_of_loading=request.default_port_of_loading,
        default_incoterms=request.default_incoterms,
        default_country_of_origin=request.default_country_of_origin,
        preferred_document_types=request.preferred_document_types,
        default_draft_tenor=request.default_draft_tenor,
        default_shipping_marks=request.default_shipping_marks,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return _template_to_response(template)


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List company's document templates"""
    
    if not current_user.company_id:
        return []
    
    templates = db.query(DocumentTemplate).filter(
        DocumentTemplate.company_id == current_user.company_id
    ).order_by(
        DocumentTemplate.is_default.desc(),
        DocumentTemplate.use_count.desc()
    ).offset(offset).limit(limit).all()
    
    return [_template_to_response(t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific template"""
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.company_id == current_user.company_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return _template_to_response(template)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a template"""
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.company_id == current_user.company_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    for field, value in request.dict(exclude_unset=True).items():
        if hasattr(template, field):
            setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return _template_to_response(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a template"""
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.company_id == current_user.company_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/templates/{template_id}/set-default")
async def set_default_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a template as the company default"""
    
    # Unset current default
    db.query(DocumentTemplate).filter(
        DocumentTemplate.company_id == current_user.company_id,
        DocumentTemplate.is_default == True
    ).update({"is_default": False})
    
    # Set new default
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.company_id == current_user.company_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_default = True
    db.commit()
    
    return {"status": "success", "default_template_id": template_id}


# ============== Product Catalog Endpoints ==============

@router.post("/catalog/products", response_model=ProductResponse)
async def create_product(
    request: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a product to the catalog"""
    
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    product = ProductCatalogItem(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        sku=request.sku,
        product_code=request.product_code,
        name=request.name,
        hs_code=request.hs_code,
        description=request.description,
        short_description=request.short_description,
        default_unit_price=Decimal(str(request.default_unit_price)) if request.default_unit_price else None,
        currency=request.currency,
        default_unit=request.default_unit,
        units_per_carton=request.units_per_carton,
        weight_per_unit_kg=Decimal(str(request.weight_per_unit_kg)) if request.weight_per_unit_kg else None,
        carton_dimensions=request.carton_dimensions,
        carton_weight_kg=Decimal(str(request.carton_weight_kg)) if request.carton_weight_kg else None,
        cbm_per_carton=Decimal(str(request.cbm_per_carton)) if request.cbm_per_carton else None,
        country_of_origin=request.country_of_origin,
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return _product_to_response(product)


@router.get("/catalog/products", response_model=List[ProductResponse])
async def list_products(
    search: Optional[str] = None,
    hs_code: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List products from catalog"""
    
    if not current_user.company_id:
        return []
    
    query = db.query(ProductCatalogItem).filter(
        ProductCatalogItem.company_id == current_user.company_id,
        ProductCatalogItem.is_active == True
    )
    
    if search:
        query = query.filter(
            (ProductCatalogItem.name.ilike(f"%{search}%")) |
            (ProductCatalogItem.sku.ilike(f"%{search}%")) |
            (ProductCatalogItem.description.ilike(f"%{search}%"))
        )
    
    if hs_code:
        query = query.filter(ProductCatalogItem.hs_code.ilike(f"{hs_code}%"))
    
    products = query.order_by(
        ProductCatalogItem.use_count.desc()
    ).offset(offset).limit(limit).all()
    
    return [_product_to_response(p) for p in products]


@router.get("/catalog/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific product"""
    
    product = db.query(ProductCatalogItem).filter(
        ProductCatalogItem.id == product_id,
        ProductCatalogItem.company_id == current_user.company_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return _product_to_response(product)


@router.put("/catalog/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a product"""
    
    product = db.query(ProductCatalogItem).filter(
        ProductCatalogItem.id == product_id,
        ProductCatalogItem.company_id == current_user.company_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for field, value in request.dict(exclude_unset=True).items():
        if hasattr(product, field):
            if field in ['default_unit_price', 'weight_per_unit_kg', 'carton_weight_kg', 'cbm_per_carton']:
                value = Decimal(str(value)) if value else None
            setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    return _product_to_response(product)


@router.delete("/catalog/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a product (sets is_active=False)"""
    
    product = db.query(ProductCatalogItem).filter(
        ProductCatalogItem.id == product_id,
        ProductCatalogItem.company_id == current_user.company_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    
    return {"status": "deleted"}


# ============== Buyer Directory Endpoints ==============

@router.post("/directory/buyers", response_model=BuyerResponse)
async def create_buyer(
    request: BuyerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a buyer to the directory"""
    
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not associated with a company")
    
    buyer = BuyerProfile(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        buyer_code=request.buyer_code,
        company_name=request.company_name,
        country=request.country,
        address_line1=request.address_line1,
        address_line2=request.address_line2,
        city=request.city,
        state=request.state,
        postal_code=request.postal_code,
        contact_person=request.contact_person,
        email=request.email,
        phone=request.phone,
        notify_party_name=request.notify_party_name,
        notify_party_address=request.notify_party_address,
        preferred_incoterms=request.preferred_incoterms,
        preferred_port_of_discharge=request.preferred_port_of_discharge,
        default_currency=request.default_currency,
        buyer_bank_name=request.buyer_bank_name,
        buyer_bank_swift=request.buyer_bank_swift,
        notes=request.notes,
    )
    
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    
    return _buyer_to_response(buyer)


@router.get("/directory/buyers", response_model=List[BuyerResponse])
async def list_buyers(
    search: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List buyers from directory"""
    
    if not current_user.company_id:
        return []
    
    query = db.query(BuyerProfile).filter(
        BuyerProfile.company_id == current_user.company_id,
        BuyerProfile.is_active == True
    )
    
    if search:
        query = query.filter(
            (BuyerProfile.company_name.ilike(f"%{search}%")) |
            (BuyerProfile.buyer_code.ilike(f"%{search}%")) |
            (BuyerProfile.contact_person.ilike(f"%{search}%"))
        )
    
    if country:
        query = query.filter(BuyerProfile.country == country)
    
    buyers = query.order_by(
        BuyerProfile.use_count.desc()
    ).offset(offset).limit(limit).all()
    
    return [_buyer_to_response(b) for b in buyers]


@router.get("/directory/buyers/{buyer_id}", response_model=BuyerResponse)
async def get_buyer(
    buyer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific buyer"""
    
    buyer = db.query(BuyerProfile).filter(
        BuyerProfile.id == buyer_id,
        BuyerProfile.company_id == current_user.company_id
    ).first()
    
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    return _buyer_to_response(buyer)


@router.put("/directory/buyers/{buyer_id}", response_model=BuyerResponse)
async def update_buyer(
    buyer_id: str,
    request: BuyerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a buyer"""
    
    buyer = db.query(BuyerProfile).filter(
        BuyerProfile.id == buyer_id,
        BuyerProfile.company_id == current_user.company_id
    ).first()
    
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    for field, value in request.dict(exclude_unset=True).items():
        if hasattr(buyer, field):
            setattr(buyer, field, value)
    
    db.commit()
    db.refresh(buyer)
    
    return _buyer_to_response(buyer)


@router.delete("/directory/buyers/{buyer_id}")
async def delete_buyer(
    buyer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a buyer (sets is_active=False)"""
    
    buyer = db.query(BuyerProfile).filter(
        BuyerProfile.id == buyer_id,
        BuyerProfile.company_id == current_user.company_id
    ).first()
    
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    buyer.is_active = False
    db.commit()
    
    return {"status": "deleted"}


# ============== Audit Log Endpoints ==============

@router.get("/document-sets/{doc_set_id}/audit-log", response_model=List[AuditLogResponse])
async def get_audit_log(
    doc_set_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit history for a document set"""
    
    # Verify user has access to the document set
    from app.models.doc_generator import DocumentSet
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    audit_service = get_audit_service(db)
    logs = audit_service.get_history(
        document_set_id=uuid.UUID(doc_set_id),
        limit=limit,
        offset=offset
    )
    
    return [AuditLogResponse(**log) for log in logs]


@router.get("/my-activity", response_model=List[AuditLogResponse])
async def get_my_activity(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's recent activity"""
    
    audit_service = get_audit_service(db)
    logs = audit_service.get_user_activity(
        user_id=current_user.id,
        days=days,
        limit=limit
    )
    
    return [AuditLogResponse(**log) for log in logs]


# ============== Helper Functions ==============

def _template_to_response(t: DocumentTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=str(t.id),
        name=t.name,
        description=t.description,
        is_default=t.is_default,
        use_count=t.use_count,
        beneficiary_name=t.beneficiary_name,
        beneficiary_address=t.beneficiary_address,
        bank_name=t.bank_name,
        default_port_of_loading=t.default_port_of_loading,
        default_incoterms=t.default_incoterms,
        preferred_document_types=t.preferred_document_types,
        created_at=t.created_at,
    )


def _product_to_response(p: ProductCatalogItem) -> ProductResponse:
    return ProductResponse(
        id=str(p.id),
        sku=p.sku,
        product_code=p.product_code,
        name=p.name,
        hs_code=p.hs_code,
        description=p.description,
        short_description=p.short_description,
        default_unit_price=float(p.default_unit_price) if p.default_unit_price else None,
        currency=p.currency,
        default_unit=p.default_unit,
        units_per_carton=p.units_per_carton,
        weight_per_unit_kg=float(p.weight_per_unit_kg) if p.weight_per_unit_kg else None,
        country_of_origin=p.country_of_origin,
        is_active=p.is_active,
        use_count=p.use_count,
    )


def _buyer_to_response(b: BuyerProfile) -> BuyerResponse:
    return BuyerResponse(
        id=str(b.id),
        buyer_code=b.buyer_code,
        company_name=b.company_name,
        country=b.country,
        address_line1=b.address_line1,
        city=b.city,
        contact_person=b.contact_person,
        email=b.email,
        preferred_incoterms=b.preferred_incoterms,
        default_currency=b.default_currency,
        is_active=b.is_active,
        use_count=b.use_count,
    )

