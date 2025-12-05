"""
Document Generator Router

API endpoints for creating and managing shipping documents.
"""

import io
import uuid
import zipfile
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.models.doc_generator import (
    DocumentSet, DocumentLineItem, GeneratedDocument,
    DocumentStatus, DocumentType, UnitType
)
from app.routers.auth import get_current_user
from app.services.document_generator import get_document_generator
from app.utils.usage_tracker import track_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doc-generator", tags=["doc-generator"])


# ============== Pydantic Models ==============

class LineItemCreate(BaseModel):
    """Create a line item"""
    line_number: int
    description: str
    hs_code: Optional[str] = None
    quantity: int
    unit: str = "PCS"
    unit_price: float
    cartons: Optional[int] = None
    carton_dimensions: Optional[str] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    remarks: Optional[str] = None


class LineItemResponse(BaseModel):
    """Line item response"""
    id: str
    line_number: int
    description: str
    hs_code: Optional[str]
    quantity: int
    unit: str
    unit_price: float
    total_price: float
    cartons: Optional[int]
    gross_weight_kg: Optional[float]
    net_weight_kg: Optional[float]

    class Config:
        from_attributes = True


class DocumentSetCreate(BaseModel):
    """Create a document set"""
    name: Optional[str] = None
    
    # LC Reference
    lc_number: Optional[str] = None
    lc_date: Optional[date] = None
    lc_amount: Optional[float] = None
    lc_currency: str = "USD"
    issuing_bank: Optional[str] = None
    advising_bank: Optional[str] = None
    
    # Beneficiary
    beneficiary_name: str
    beneficiary_address: Optional[str] = None
    beneficiary_country: Optional[str] = None
    
    # Applicant
    applicant_name: str
    applicant_address: Optional[str] = None
    applicant_country: Optional[str] = None
    
    # Notify Party
    notify_party_name: Optional[str] = None
    notify_party_address: Optional[str] = None
    
    # Shipment
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    bl_number: Optional[str] = None
    bl_date: Optional[date] = None
    container_number: Optional[str] = None
    seal_number: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    final_destination: Optional[str] = None
    
    # Trade Terms
    incoterms: Optional[str] = None
    incoterms_place: Optional[str] = None
    
    # Packing
    total_cartons: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    cbm: Optional[float] = None
    shipping_marks: Optional[str] = None
    
    # Document Numbers
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    po_number: Optional[str] = None
    
    # Additional
    country_of_origin: Optional[str] = None
    remarks: Optional[str] = None
    
    # Bill of Exchange
    draft_tenor: Optional[str] = None
    drawee_name: Optional[str] = None
    drawee_address: Optional[str] = None
    
    # Line items (optional, can add later)
    line_items: List[LineItemCreate] = []


class DocumentSetUpdate(BaseModel):
    """Update a document set"""
    name: Optional[str] = None
    lc_number: Optional[str] = None
    lc_date: Optional[date] = None
    lc_amount: Optional[float] = None
    lc_currency: Optional[str] = None
    beneficiary_name: Optional[str] = None
    beneficiary_address: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_address: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    bl_number: Optional[str] = None
    bl_date: Optional[date] = None
    container_number: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    incoterms: Optional[str] = None
    total_cartons: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    shipping_marks: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    country_of_origin: Optional[str] = None


class DocumentSetResponse(BaseModel):
    """Document set response"""
    id: str
    name: Optional[str]
    status: str
    lc_number: Optional[str]
    lc_date: Optional[date]
    lc_currency: str
    beneficiary_name: str
    applicant_name: str
    total_quantity: int
    total_amount: float
    total_cartons: Optional[int]
    documents_generated: int
    created_at: datetime
    updated_at: datetime
    line_items: List[LineItemResponse]

    class Config:
        from_attributes = True


class DocumentSetListResponse(BaseModel):
    """List response for document sets"""
    id: str
    name: Optional[str]
    status: str
    lc_number: Optional[str]
    beneficiary_name: str
    applicant_name: str
    total_amount: float
    documents_generated: int
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    """Request to generate documents"""
    document_types: List[str] = ["commercial_invoice", "packing_list"]


class GeneratedDocumentResponse(BaseModel):
    """Response for generated document info"""
    id: str
    document_type: str
    file_name: str
    file_size: int
    generated_at: datetime
    version: int

    class Config:
        from_attributes = True


# ============== Document Set CRUD ==============

@router.post("/document-sets", response_model=DocumentSetResponse)
@track_usage(operation="doc_generate", tool="doc_generator", description="Create document set")
async def create_document_set(
    request: DocumentSetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new document set"""
    
    # Create document set
    doc_set = DocumentSet(
        id=uuid.uuid4(),
        user_id=current_user.id,
        company_id=getattr(current_user, 'company_id', None),
        name=request.name or f"Doc Set - {request.lc_number or datetime.now().strftime('%Y%m%d')}",
        status=DocumentStatus.DRAFT,
        lc_number=request.lc_number,
        lc_date=request.lc_date,
        lc_amount=Decimal(str(request.lc_amount)) if request.lc_amount else None,
        lc_currency=request.lc_currency,
        issuing_bank=request.issuing_bank,
        advising_bank=request.advising_bank,
        beneficiary_name=request.beneficiary_name,
        beneficiary_address=request.beneficiary_address,
        beneficiary_country=request.beneficiary_country,
        applicant_name=request.applicant_name,
        applicant_address=request.applicant_address,
        applicant_country=request.applicant_country,
        notify_party_name=request.notify_party_name,
        notify_party_address=request.notify_party_address,
        vessel_name=request.vessel_name,
        voyage_number=request.voyage_number,
        bl_number=request.bl_number,
        bl_date=request.bl_date,
        container_number=request.container_number,
        seal_number=request.seal_number,
        port_of_loading=request.port_of_loading,
        port_of_discharge=request.port_of_discharge,
        final_destination=request.final_destination,
        incoterms=request.incoterms,
        incoterms_place=request.incoterms_place,
        total_cartons=request.total_cartons,
        gross_weight_kg=Decimal(str(request.gross_weight_kg)) if request.gross_weight_kg else None,
        net_weight_kg=Decimal(str(request.net_weight_kg)) if request.net_weight_kg else None,
        cbm=Decimal(str(request.cbm)) if request.cbm else None,
        shipping_marks=request.shipping_marks,
        invoice_number=request.invoice_number,
        invoice_date=request.invoice_date,
        po_number=request.po_number,
        country_of_origin=request.country_of_origin,
        remarks=request.remarks,
        draft_tenor=request.draft_tenor,
        drawee_name=request.drawee_name,
        drawee_address=request.drawee_address,
    )
    
    db.add(doc_set)
    db.flush()
    
    # Add line items
    for item_data in request.line_items:
        total_price = Decimal(str(item_data.quantity)) * Decimal(str(item_data.unit_price))
        
        line_item = DocumentLineItem(
            id=uuid.uuid4(),
            document_set_id=doc_set.id,
            line_number=item_data.line_number,
            description=item_data.description,
            hs_code=item_data.hs_code,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=Decimal(str(item_data.unit_price)),
            total_price=total_price,
            cartons=item_data.cartons,
            carton_dimensions=item_data.carton_dimensions,
            gross_weight_kg=Decimal(str(item_data.gross_weight_kg)) if item_data.gross_weight_kg else None,
            net_weight_kg=Decimal(str(item_data.net_weight_kg)) if item_data.net_weight_kg else None,
            remarks=item_data.remarks,
        )
        db.add(line_item)
    
    db.commit()
    db.refresh(doc_set)
    
    logger.info(f"Created document set {doc_set.id} for user {current_user.id}")
    
    return _to_response(doc_set)


@router.get("/document-sets", response_model=List[DocumentSetListResponse])
async def list_document_sets(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's document sets"""
    
    query = db.query(DocumentSet).filter(DocumentSet.user_id == current_user.id)
    
    if status:
        query = query.filter(DocumentSet.status == status)
    
    query = query.order_by(DocumentSet.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    doc_sets = query.all()
    
    return [_to_list_response(ds) for ds in doc_sets]


@router.get("/document-sets/{doc_set_id}", response_model=DocumentSetResponse)
async def get_document_set(
    doc_set_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific document set"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    return _to_response(doc_set)


@router.put("/document-sets/{doc_set_id}", response_model=DocumentSetResponse)
async def update_document_set(
    doc_set_id: str,
    request: DocumentSetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a document set"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(doc_set, field):
            # Convert floats to Decimal for numeric fields
            if field in ['lc_amount', 'gross_weight_kg', 'net_weight_kg'] and value is not None:
                value = Decimal(str(value))
            setattr(doc_set, field, value)
    
    db.commit()
    db.refresh(doc_set)
    
    return _to_response(doc_set)


@router.delete("/document-sets/{doc_set_id}")
async def delete_document_set(
    doc_set_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document set"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    db.delete(doc_set)
    db.commit()
    
    return {"status": "deleted", "id": doc_set_id}


# ============== Line Items ==============

@router.post("/document-sets/{doc_set_id}/line-items", response_model=LineItemResponse)
async def add_line_item(
    doc_set_id: str,
    request: LineItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a line item to a document set"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    total_price = Decimal(str(request.quantity)) * Decimal(str(request.unit_price))
    
    line_item = DocumentLineItem(
        id=uuid.uuid4(),
        document_set_id=doc_set.id,
        line_number=request.line_number,
        description=request.description,
        hs_code=request.hs_code,
        quantity=request.quantity,
        unit=request.unit,
        unit_price=Decimal(str(request.unit_price)),
        total_price=total_price,
        cartons=request.cartons,
        carton_dimensions=request.carton_dimensions,
        gross_weight_kg=Decimal(str(request.gross_weight_kg)) if request.gross_weight_kg else None,
        net_weight_kg=Decimal(str(request.net_weight_kg)) if request.net_weight_kg else None,
        remarks=request.remarks,
    )
    
    db.add(line_item)
    db.commit()
    db.refresh(line_item)
    
    return _to_line_item_response(line_item)


@router.delete("/document-sets/{doc_set_id}/line-items/{item_id}")
async def delete_line_item(
    doc_set_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a line item"""
    
    item = db.query(DocumentLineItem).join(DocumentSet).filter(
        DocumentLineItem.id == item_id,
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    db.delete(item)
    db.commit()
    
    return {"status": "deleted", "id": item_id}


# ============== Document Generation ==============

@router.post("/document-sets/{doc_set_id}/generate")
@track_usage(operation="doc_generate", tool="doc_generator", description="Generate shipping documents")
async def generate_documents(
    doc_set_id: str,
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate documents for a document set"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    if not doc_set.line_items:
        raise HTTPException(status_code=400, detail="Document set has no line items")
    
    # Parse document types
    doc_types = []
    for type_str in request.document_types:
        try:
            doc_types.append(DocumentType(type_str))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {type_str}")
    
    generator = get_document_generator()
    results = generator.generate_all(doc_set, doc_types)
    
    # Store generated documents info
    generated_docs = []
    for doc_type, (pdf_bytes, filename) in results.items():
        # Mark old versions as not current
        db.query(GeneratedDocument).filter(
            GeneratedDocument.document_set_id == doc_set.id,
            GeneratedDocument.document_type == doc_type,
            GeneratedDocument.is_current == True
        ).update({"is_current": False})
        
        # Get next version number
        max_version = db.query(GeneratedDocument).filter(
            GeneratedDocument.document_set_id == doc_set.id,
            GeneratedDocument.document_type == doc_type
        ).count()
        
        gen_doc = GeneratedDocument(
            id=uuid.uuid4(),
            document_set_id=doc_set.id,
            document_type=doc_type,
            file_name=filename,
            file_size=len(pdf_bytes),
            version=max_version + 1,
            is_current=True,
            generated_by=current_user.id,
            validation_passed=True,
        )
        db.add(gen_doc)
        generated_docs.append({
            "document_type": doc_type.value,
            "file_name": filename,
            "file_size": len(pdf_bytes),
            "version": max_version + 1,
        })
    
    # Update document set status
    doc_set.status = DocumentStatus.GENERATED
    db.commit()
    
    return {
        "document_set_id": str(doc_set.id),
        "documents_generated": len(results),
        "documents": generated_docs,
    }


@router.get("/document-sets/{doc_set_id}/download")
async def download_documents(
    doc_set_id: str,
    document_type: Optional[str] = None,
    format: str = Query("zip", regex="^(zip|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download generated documents"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    generator = get_document_generator()
    
    # Determine which documents to generate
    if document_type:
        try:
            doc_types = [DocumentType(document_type)]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")
    else:
        doc_types = [DocumentType.COMMERCIAL_INVOICE, DocumentType.PACKING_LIST]
    
    results = generator.generate_all(doc_set, doc_types)
    
    if not results:
        raise HTTPException(status_code=404, detail="No documents generated")
    
    # Single PDF
    if len(results) == 1 or format == "pdf":
        doc_type, (pdf_bytes, filename) = list(results.items())[0]
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    # ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc_type, (pdf_bytes, filename) in results.items():
            zf.writestr(filename, pdf_bytes)
    
    zip_buffer.seek(0)
    safe_lc = (doc_set.lc_number or "documents").replace("/", "-").replace(" ", "_")
    zip_filename = f"shipping_docs_{safe_lc}_{datetime.now().strftime('%Y%m%d')}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


@router.get("/document-sets/{doc_set_id}/preview/{document_type}")
async def preview_document(
    doc_set_id: str,
    document_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview a single document (returns PDF inline)"""
    
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == doc_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")
    
    generator = get_document_generator()
    pdf_bytes, filename = generator.generate_document(doc_set, doc_type)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


# ============== Helper Functions ==============

def _to_response(doc_set: DocumentSet) -> DocumentSetResponse:
    """Convert DocumentSet to response"""
    return DocumentSetResponse(
        id=str(doc_set.id),
        name=doc_set.name,
        status=doc_set.status.value if doc_set.status else "draft",
        lc_number=doc_set.lc_number,
        lc_date=doc_set.lc_date,
        lc_currency=doc_set.lc_currency or "USD",
        beneficiary_name=doc_set.beneficiary_name,
        applicant_name=doc_set.applicant_name,
        total_quantity=doc_set.total_quantity,
        total_amount=float(doc_set.total_amount),
        total_cartons=doc_set.total_cartons,
        documents_generated=len([d for d in doc_set.generated_documents if d.is_current]),
        created_at=doc_set.created_at,
        updated_at=doc_set.updated_at,
        line_items=[_to_line_item_response(item) for item in doc_set.line_items]
    )


def _to_list_response(doc_set: DocumentSet) -> DocumentSetListResponse:
    """Convert DocumentSet to list response"""
    return DocumentSetListResponse(
        id=str(doc_set.id),
        name=doc_set.name,
        status=doc_set.status.value if doc_set.status else "draft",
        lc_number=doc_set.lc_number,
        beneficiary_name=doc_set.beneficiary_name,
        applicant_name=doc_set.applicant_name,
        total_amount=float(doc_set.total_amount),
        documents_generated=len([d for d in doc_set.generated_documents if d.is_current]),
        created_at=doc_set.created_at
    )


def _to_line_item_response(item: DocumentLineItem) -> LineItemResponse:
    """Convert LineItem to response"""
    return LineItemResponse(
        id=str(item.id),
        line_number=item.line_number,
        description=item.description,
        hs_code=item.hs_code,
        quantity=item.quantity,
        unit=item.unit or "PCS",
        unit_price=float(item.unit_price or 0),
        total_price=float(item.total_price or 0),
        cartons=item.cartons,
        gross_weight_kg=float(item.gross_weight_kg) if item.gross_weight_kg else None,
        net_weight_kg=float(item.net_weight_kg) if item.net_weight_kg else None,
    )

