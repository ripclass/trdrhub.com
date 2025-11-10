"""
SME Templates API endpoints for LC and document templates with pre-fill.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, UserRole, Company
from ..models.sme_templates import SMETemplate, TemplateType, DocumentType
from ..models.company_profile import CompanyComplianceInfo, CompanyAddress, DefaultConsigneeShipper
from ..schemas.sme_templates import (
    SMETemplateCreate, SMETemplateUpdate, SMETemplateRead, SMETemplateListResponse,
    TemplatePreFillRequest, TemplatePreFillResponse
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sme/templates", tags=["sme-templates"])


def require_sme_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an SME (exporter or importer)."""
    if current_user.role not in [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for SME users (exporter/importer)"
        )
    return current_user


def _substitute_template_variables(
    fields: dict,
    company: Company,
    compliance_info: Optional[CompanyComplianceInfo] = None,
    addresses: List[CompanyAddress] = None,
    default_consignee_shipper: List[DefaultConsigneeShipper] = None,
    custom_variables: dict = None
) -> dict:
    """Substitute template variables with actual values from company profile."""
    if addresses is None:
        addresses = []
    if default_consignee_shipper is None:
        default_consignee_shipper = []
    if custom_variables is None:
        custom_variables = {}

    # Build variable map
    variables = {
        "company_name": company.name or "",
        "company_email": company.email or "",
        "company_phone": company.phone or "",
        **custom_variables
    }

    # Add compliance info variables
    if compliance_info:
        variables["tax_id"] = compliance_info.tax_id or ""
        variables["vat_number"] = compliance_info.vat_number or ""
        variables["registration_number"] = compliance_info.registration_number or ""

    # Add default addresses
    default_shipping = next((a for a in addresses if a.is_default_shipping), None)
    if default_shipping:
        variables["default_shipping_address"] = f"{default_shipping.street_address}, {default_shipping.city}, {default_shipping.country}"
        variables["default_shipping_city"] = default_shipping.city or ""
        variables["default_shipping_country"] = default_shipping.country or ""

    default_billing = next((a for a in addresses if a.is_default_billing), None)
    if default_billing:
        variables["default_billing_address"] = f"{default_billing.street_address}, {default_billing.city}, {default_billing.country}"

    # Add default consignee/shipper
    default_consignee = next((cs for cs in default_consignee_shipper if cs.type_ == "consignee"), None)
    if default_consignee:
        variables["default_consignee"] = default_consignee.company_name or ""
        variables["default_consignee_address"] = default_consignee.street_address or ""

    default_shipper = next((cs for cs in default_consignee_shipper if cs.type_ == "shipper"), None)
    if default_shipper:
        variables["default_shipper"] = default_shipper.company_name or ""
        variables["default_shipper_address"] = default_shipper.street_address or ""

    # Substitute variables in fields
    def substitute_value(value):
        if isinstance(value, str):
            result = value
            for var_name, var_value in variables.items():
                result = result.replace(f"{{{{{var_name}}}}}", str(var_value))
            return result
        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        else:
            return value

    return substitute_value(fields)


@router.get("", response_model=SMETemplateListResponse)
async def list_templates(
    type: Optional[TemplateType] = Query(None, description="Filter by template type"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    active_only: bool = Query(True, description="Show only active templates"),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List templates for the current user's company."""
    query = db.query(SMETemplate).filter(
        and_(
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None)
        )
    )

    if type:
        query = query.filter(SMETemplate.type == type)
    if document_type:
        query = query.filter(SMETemplate.document_type == document_type)
    if active_only:
        query = query.filter(SMETemplate.is_active == True)

    templates = query.order_by(SMETemplate.created_at.desc()).all()

    return SMETemplateListResponse(
        items=[SMETemplateRead.model_validate(t) for t in templates],
        total=len(templates)
    )


@router.get("/{template_id}", response_model=SMETemplateRead)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific template."""
    template = db.query(SMETemplate).filter(
        and_(
            SMETemplate.id == template_id,
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return SMETemplateRead.model_validate(template)


@router.post("", response_model=SMETemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: SMETemplateCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new template."""
    # Ensure company_id and user_id match current user
    if template_data.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create template for different company"
        )

    # If setting as default, unset other defaults of same type
    if template_data.is_default:
        db.query(SMETemplate).filter(
            and_(
                SMETemplate.company_id == current_user.company_id,
                SMETemplate.type == template_data.type,
                SMETemplate.is_default == True,
                SMETemplate.deleted_at.is_(None)
            )
        ).update({"is_default": False})

    template = SMETemplate(
        company_id=template_data.company_id,
        user_id=current_user.id,
        name=template_data.name,
        type=template_data.type,
        document_type=template_data.document_type,
        description=template_data.description,
        fields=template_data.fields,
        is_default=template_data.is_default,
        is_active=True
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.CREATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="sme_template",
        resource_id=str(template.id),
        details={"name": template.name, "type": template.type.value},
        result=AuditResult.SUCCESS
    )

    return SMETemplateRead.model_validate(template)


@router.put("/{template_id}", response_model=SMETemplateRead)
async def update_template(
    template_id: UUID,
    template_data: SMETemplateUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update a template."""
    template = db.query(SMETemplate).filter(
        and_(
            SMETemplate.id == template_id,
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # If setting as default, unset other defaults of same type
    if template_data.is_default is True:
        db.query(SMETemplate).filter(
            and_(
                SMETemplate.company_id == current_user.company_id,
                SMETemplate.type == template.type,
                SMETemplate.id != template_id,
                SMETemplate.is_default == True,
                SMETemplate.deleted_at.is_(None)
            )
        ).update({"is_default": False})

    # Update fields
    update_data = template_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="sme_template",
        resource_id=str(template.id),
        details={"name": template.name},
        result=AuditResult.SUCCESS
    )

    return SMETemplateRead.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Delete a template (soft delete)."""
    template = db.query(SMETemplate).filter(
        and_(
            SMETemplate.id == template_id,
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    template.deleted_at = datetime.utcnow()
    template.is_active = False
    db.commit()

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="sme_template",
        resource_id=str(template_id),
        details={"name": template.name},
        result=AuditResult.SUCCESS
    )


@router.post("/{template_id}/use", response_model=SMETemplateRead)
async def use_template(
    template_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Mark a template as used (increment usage count)."""
    template = db.query(SMETemplate).filter(
        and_(
            SMETemplate.id == template_id,
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    template.usage_count += 1
    template.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    return SMETemplateRead.model_validate(template)


@router.post("/prefill", response_model=TemplatePreFillResponse)
async def prefill_template(
    request: TemplatePreFillRequest,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Pre-fill template fields with company profile data."""
    template = db.query(SMETemplate).filter(
        and_(
            SMETemplate.id == request.template_id,
            SMETemplate.company_id == current_user.company_id,
            SMETemplate.deleted_at.is_(None),
            SMETemplate.is_active == True
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Load company profile data
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    compliance_info = db.query(CompanyComplianceInfo).filter(
        CompanyComplianceInfo.company_id == current_user.company_id
    ).first()

    addresses = db.query(CompanyAddress).filter(
        and_(
            CompanyAddress.company_id == current_user.company_id,
            CompanyAddress.is_active == True,
            CompanyAddress.deleted_at.is_(None)
        )
    ).all()

    consignee_shipper = db.query(DefaultConsigneeShipper).filter(
        and_(
            DefaultConsigneeShipper.company_id == current_user.company_id,
            DefaultConsigneeShipper.is_active == True,
            DefaultConsigneeShipper.deleted_at.is_(None)
        )
    ).all()

    # Substitute variables
    prefilled_fields = _substitute_template_variables(
        template.fields,
        company,
        compliance_info,
        addresses,
        consignee_shipper,
        request.variables
    )

    return TemplatePreFillResponse(
        fields=prefilled_fields,
        template_name=template.name
    )

