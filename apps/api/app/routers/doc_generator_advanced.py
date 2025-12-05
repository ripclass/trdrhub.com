"""
Doc Generator Advanced Router

API endpoints for Phase 3 features:
- Digital signatures
- Multi-language documents
- Bank-specific formats
- GSP Form A / EUR.1 certificates
- Word/Excel export
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import io

from app.database import get_db
from app.models import User
from app.models.doc_generator import DocumentSet
from app.routers.auth import get_current_user
from app.services.digital_signature import (
    get_signature_service,
    SignatureProvider,
    SignatureRequest,
)
from app.services.bank_format_registry import get_bank_format_registry
from app.services.document_translation import get_translation_service
from app.services.certificate_generators import (
    get_gsp_generator,
    get_eur1_generator,
    get_export_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doc-generator/advanced", tags=["doc-generator-advanced"])


# ============== Pydantic Schemas ==============

class SignatureRequestCreate(BaseModel):
    document_set_id: str
    document_type: str
    provider: str = "local"  # local, docusign, adobe_sign
    signers: List[dict] = Field(default_factory=list)  # [{"name": "...", "email": "..."}]
    subject: str = "Document for Signature"
    message: str = "Please review and sign this document."


class LocalSignatureApply(BaseModel):
    document_set_id: str
    document_type: str
    signature_image_base64: str
    position: dict = Field(default={"page": 0, "x": 400, "y": 100, "width": 150, "height": 50})
    stamp_image_base64: Optional[str] = None
    stamp_position: Optional[dict] = None


class TranslationRequest(BaseModel):
    keys: List[str]
    language: str


class BankValidationRequest(BaseModel):
    document_set_id: str
    bank_code: str
    document_type: str


class CertificateGenerateRequest(BaseModel):
    document_set_id: str
    certificate_type: str  # gsp_form_a, eur1
    additional_data: Optional[dict] = None


class ExportRequest(BaseModel):
    document_set_id: str
    format: str  # docx, xlsx
    document_type: Optional[str] = None


# ============== Signature Endpoints ==============

@router.get("/signatures/providers")
async def list_signature_providers(
    current_user: User = Depends(get_current_user),
):
    """List available signature providers"""
    service = get_signature_service()
    return {
        "providers": service.get_available_providers(),
        "docusign_configured": service.is_docusign_configured(),
        "adobe_configured": service.is_adobe_configured(),
    }


@router.post("/signatures/request")
async def create_signature_request(
    request: SignatureRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a signature request (DocuSign or Adobe Sign)"""
    
    # Get document set
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == request.document_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Generate the document first
    from app.services.document_generator import get_document_service
    doc_service = get_document_service()
    pdf_bytes = doc_service.generate(doc_set, request.document_type)
    
    # Create signature request
    service = get_signature_service()
    sig_request = SignatureRequest(
        document_set_id=request.document_set_id,
        document_bytes=pdf_bytes,
        document_name=f"{request.document_type}_{doc_set.invoice_number or 'doc'}.pdf",
        signers=request.signers,
        provider=SignatureProvider(request.provider),
    )
    
    try:
        if request.provider == "docusign":
            result = await service.create_docusign_envelope(
                sig_request,
                subject=request.subject,
                message=request.message
            )
        elif request.provider == "adobe_sign":
            result = await service.create_adobe_agreement(
                sig_request,
                name=request.subject,
                message=request.message
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider for remote signing")
        
        return {
            "status": "sent",
            "request_id": sig_request.id,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Signature request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signatures/local")
async def apply_local_signature(
    request: LocalSignatureApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a local signature image to a document"""
    import base64
    
    # Get document set
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == request.document_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Generate base document
    from app.services.document_generator import get_document_service
    doc_service = get_document_service()
    pdf_bytes = doc_service.generate(doc_set, request.document_type)
    
    # Decode signature image
    try:
        signature_image = base64.b64decode(request.signature_image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature image")
    
    stamp_image = None
    if request.stamp_image_base64:
        try:
            stamp_image = base64.b64decode(request.stamp_image_base64)
        except Exception:
            pass
    
    # Apply signature
    service = get_signature_service()
    signed_pdf = await service.apply_local_signature(
        pdf_bytes,
        signature_image,
        request.position,
        stamp_image,
        request.stamp_position
    )
    
    return StreamingResponse(
        io.BytesIO(signed_pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="signed_{request.document_type}.pdf"'
        }
    )


# ============== Multi-Language Endpoints ==============

@router.get("/languages")
async def list_languages():
    """List supported languages"""
    service = get_translation_service()
    return {"languages": service.list_supported_languages()}


@router.post("/translate")
async def translate_keys(
    request: TranslationRequest,
):
    """Translate document field keys"""
    service = get_translation_service()
    
    translations = {}
    for key in request.keys:
        translations[key] = service.translate(key, request.language)
    
    return {
        "language": request.language,
        "is_rtl": service.is_rtl(request.language),
        "font": service.get_font_for_language(request.language),
        "translations": translations
    }


@router.get("/translate/{key}")
async def translate_single(
    key: str,
    language: str = Query(...),
):
    """Translate a single key"""
    service = get_translation_service()
    return {
        "key": key,
        "language": language,
        "translation": service.translate(key, language),
        "english": service.translate(key, "en"),
    }


# ============== Bank Format Endpoints ==============

@router.get("/banks")
async def list_banks():
    """List all registered banks with format requirements"""
    registry = get_bank_format_registry()
    return {"banks": registry.list_banks()}


@router.get("/banks/{bank_code}")
async def get_bank_profile(bank_code: str):
    """Get bank profile with all requirements"""
    registry = get_bank_format_registry()
    profile = registry.get_bank_profile(bank_code)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    return {
        "code": profile.code,
        "name": profile.name,
        "country": profile.country,
        "swift": profile.swift_code,
        "general_requirements": profile.general_requirements,
        "document_formats": {
            doc_type: {
                "fields": [
                    {
                        "field_name": f.field_name,
                        "required": f.is_required,
                        "format": f.format_regex,
                        "notes": f.notes,
                    }
                    for f in fmt.fields
                ],
                "certification_text": fmt.certification_text,
                "special_instructions": fmt.special_instructions,
            }
            for doc_type, fmt in profile.document_formats.items()
        }
    }


@router.get("/banks/country/{country}")
async def list_banks_by_country(country: str):
    """List banks for a specific country"""
    registry = get_bank_format_registry()
    return {"banks": registry.list_banks_by_country(country)}


@router.post("/banks/validate")
async def validate_against_bank(
    request: BankValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate document against bank-specific requirements"""
    
    # Get document set
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == request.document_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Build document data for validation
    doc_data = {
        "invoice_number": doc_set.invoice_number,
        "lc_number": doc_set.lc_number,
        "goods_description": "",  # Would need to aggregate from line items
        "shipping_marks": doc_set.shipping_marks,
        "net_weight": float(doc_set.net_weight_kg) if doc_set.net_weight_kg else None,
        "incoterms": doc_set.incoterms,
        "beneficiary_name": doc_set.beneficiary_name,
        "applicant_name": doc_set.applicant_name,
    }
    
    # Validate
    registry = get_bank_format_registry()
    issues = registry.validate_document(
        request.bank_code,
        request.document_type,
        doc_data
    )
    
    # Get certification text
    cert_text = registry.get_certification_text(request.bank_code, request.document_type)
    
    return {
        "bank_code": request.bank_code,
        "document_type": request.document_type,
        "valid": len(issues) == 0,
        "issues": issues,
        "certification_text": cert_text,
    }


# ============== Certificate Endpoints ==============

@router.post("/certificates/generate")
async def generate_certificate(
    request: CertificateGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate GSP Form A or EUR.1 certificate"""
    
    # Get document set
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == request.document_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Build data from document set
    cert_data = {
        "reference_number": f"GSP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        "exporter_name": doc_set.beneficiary_name,
        "exporter_address": doc_set.beneficiary_address or "",
        "consignee_name": doc_set.applicant_name,
        "consignee_address": doc_set.applicant_address or "",
        "country_of_origin": doc_set.country_of_origin or "Bangladesh",
        "destination_country": doc_set.applicant_country or "",
        "goods_description": "",  # Aggregate from line items
        "hs_code": "",
        "gross_weight": str(doc_set.gross_weight_kg) if doc_set.gross_weight_kg else "",
        "invoice_number": doc_set.invoice_number or "",
        "invoice_date": doc_set.invoice_date.strftime("%Y-%m-%d") if doc_set.invoice_date else "",
        "transport_details": f"Vessel: {doc_set.vessel_name or ''}, From: {doc_set.port_of_loading or ''} To: {doc_set.port_of_discharge or ''}",
        "shipping_marks": doc_set.shipping_marks or "N/M",
        "origin_criterion": "P",  # Wholly obtained
        "place": doc_set.port_of_loading or "",
        "date": datetime.now().strftime("%Y-%m-%d"),
        **(request.additional_data or {})
    }
    
    # Aggregate goods description and HS codes from line items
    if doc_set.line_items:
        descriptions = []
        hs_codes = []
        for item in doc_set.line_items:
            descriptions.append(item.description or "")
            if item.hs_code:
                hs_codes.append(item.hs_code)
        cert_data["goods_description"] = "\n".join(descriptions[:3])  # Limit
        cert_data["hs_code"] = hs_codes[0] if hs_codes else ""
    
    # Generate certificate
    if request.certificate_type == "gsp_form_a":
        generator = get_gsp_generator()
        pdf_bytes = generator.generate(cert_data)
        filename = f"GSP_Form_A_{cert_data['reference_number']}.pdf"
    elif request.certificate_type == "eur1":
        generator = get_eur1_generator()
        cert_data["certificate_number"] = f"EUR1-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        pdf_bytes = generator.generate(cert_data)
        filename = f"EUR1_{cert_data['certificate_number']}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid certificate type. Use 'gsp_form_a' or 'eur1'")
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============== Export Endpoints ==============

@router.post("/export")
async def export_document(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export document data to Word or Excel"""
    
    # Get document set
    doc_set = db.query(DocumentSet).filter(
        DocumentSet.id == request.document_set_id,
        DocumentSet.user_id == current_user.id
    ).first()
    
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")
    
    # Build export data
    export_data = {
        "beneficiary_name": doc_set.beneficiary_name,
        "beneficiary_address": doc_set.beneficiary_address or "",
        "applicant_name": doc_set.applicant_name,
        "applicant_address": doc_set.applicant_address or "",
        "port_of_loading": doc_set.port_of_loading or "",
        "port_of_discharge": doc_set.port_of_discharge or "",
        "vessel_name": doc_set.vessel_name or "",
        "bl_number": doc_set.bl_number or "",
        "invoice_number": doc_set.invoice_number or "",
        "lc_number": doc_set.lc_number or "",
        "line_items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit.value if item.unit else "PCS",
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_price": float(item.total_price) if item.total_price else 0,
            }
            for item in doc_set.line_items
        ] if doc_set.line_items else []
    }
    
    template_name = request.document_type or "document_set"
    service = get_export_service()
    
    try:
        if request.format == "docx":
            file_bytes = service.export_to_docx(export_data, template_name)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif request.format == "xlsx":
            file_bytes = service.export_to_xlsx(export_data, template_name)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'docx' or 'xlsx'")
        
        filename = f"{template_name}_{doc_set.invoice_number or 'export'}.{ext}"
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except ImportError as e:
        raise HTTPException(
            status_code=501, 
            detail=f"Export format not available: {str(e)}"
        )

