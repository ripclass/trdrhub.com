"""
API router for Company Profile endpoints (addresses, compliance info, default consignee/shipper).
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, UserRole
from ..models.company_profile import (
    CompanyAddress, CompanyComplianceInfo, DefaultConsigneeShipper,
    AddressType, ComplianceStatus
)
from ..schemas.company_profile import (
    CompanyAddressCreate, CompanyAddressUpdate, CompanyAddressRead, CompanyAddressListResponse,
    CompanyComplianceInfoCreate, CompanyComplianceInfoUpdate, CompanyComplianceInfoRead,
    DefaultConsigneeShipperCreate, DefaultConsigneeShipperUpdate, DefaultConsigneeShipperRead,
    DefaultConsigneeShipperListResponse
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/company-profile", tags=["company-profile"])


def require_sme_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an SME (exporter or importer) or tenant admin."""
    if current_user.role not in [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for SME users (exporter/importer/tenant_admin)"
        )
    return current_user


# ===== CompanyAddress Endpoints =====

@router.post("/addresses", response_model=CompanyAddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(
    address_data: CompanyAddressCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new address for the current user's company."""
    try:
        # Ensure company_id matches current user's company
        if address_data.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create address for a different company"
            )

        # If setting as default, unset other defaults of the same type
        if address_data.is_default_shipping:
            db.query(CompanyAddress).filter(
                and_(
                    CompanyAddress.company_id == current_user.company_id,
                    CompanyAddress.is_default_shipping == True,
                    CompanyAddress.deleted_at.is_(None)
                )
            ).update({"is_default_shipping": False})
        
        if address_data.is_default_billing:
            db.query(CompanyAddress).filter(
                and_(
                    CompanyAddress.company_id == current_user.company_id,
                    CompanyAddress.is_default_billing == True,
                    CompanyAddress.deleted_at.is_(None)
                )
            ).update({"is_default_billing": False})

        address = CompanyAddress(
            **address_data.model_dump()
        )

        db.add(address)
        db.commit()
        db.refresh(address)

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(request) if request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="company_address",
            resource_id=str(address.id),
            result=AuditResult.SUCCESS
        )

        return CompanyAddressRead.model_validate(address)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create address: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create address"
        )


@router.get("/addresses", response_model=CompanyAddressListResponse)
async def list_addresses(
    address_type: Optional[AddressType] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List addresses for the current user's company."""
    query = db.query(CompanyAddress).filter(
        and_(
            CompanyAddress.company_id == current_user.company_id,
            CompanyAddress.deleted_at.is_(None)
        )
    )

    if address_type:
        query = query.filter(CompanyAddress.address_type == address_type)

    if active_only:
        query = query.filter(CompanyAddress.is_active == True)

    total = query.count()
    items = query.order_by(CompanyAddress.created_at.desc()).offset(skip).limit(limit).all()

    return CompanyAddressListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        items=[CompanyAddressRead.model_validate(item) for item in items]
    )


@router.get("/addresses/{address_id}", response_model=CompanyAddressRead)
async def get_address(
    address_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific address for the current user's company."""
    address = db.query(CompanyAddress).filter(
        and_(
            CompanyAddress.id == address_id,
            CompanyAddress.company_id == current_user.company_id,
            CompanyAddress.deleted_at.is_(None)
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or does not belong to your company"
        )

    return CompanyAddressRead.model_validate(address)


@router.patch("/addresses/{address_id}", response_model=CompanyAddressRead)
async def update_address(
    address_id: UUID,
    address_data: CompanyAddressUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update an address for the current user's company."""
    address = db.query(CompanyAddress).filter(
        and_(
            CompanyAddress.id == address_id,
            CompanyAddress.company_id == current_user.company_id,
            CompanyAddress.deleted_at.is_(None)
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or does not belong to your company"
        )

    update_fields = address_data.model_dump(exclude_unset=True)
    
    # Handle default flags
    if update_fields.get("is_default_shipping") == True:
        db.query(CompanyAddress).filter(
            and_(
                CompanyAddress.company_id == current_user.company_id,
                CompanyAddress.id != address_id,
                CompanyAddress.is_default_shipping == True,
                CompanyAddress.deleted_at.is_(None)
            )
        ).update({"is_default_shipping": False})
    
    if update_fields.get("is_default_billing") == True:
        db.query(CompanyAddress).filter(
            and_(
                CompanyAddress.company_id == current_user.company_id,
                CompanyAddress.id != address_id,
                CompanyAddress.is_default_billing == True,
                CompanyAddress.deleted_at.is_(None)
            )
        ).update({"is_default_billing": False})

    for key, value in update_fields.items():
        setattr(address, key, value)

    db.add(address)
    db.commit()
    db.refresh(address)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="company_address",
        resource_id=str(address.id),
        details={"updated_fields": list(update_fields.keys())},
        result=AuditResult.SUCCESS
    )

    return CompanyAddressRead.model_validate(address)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Soft delete an address for the current user's company."""
    address = db.query(CompanyAddress).filter(
        and_(
            CompanyAddress.id == address_id,
            CompanyAddress.company_id == current_user.company_id,
            CompanyAddress.deleted_at.is_(None)
        )
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or does not belong to your company"
        )

    address.deleted_at = func.now()
    address.is_active = False
    db.add(address)
    db.commit()

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="company_address",
        resource_id=str(address.id),
        result=AuditResult.SUCCESS
    )


# ===== CompanyComplianceInfo Endpoints =====

@router.get("/compliance", response_model=CompanyComplianceInfoRead)
async def get_compliance_info(
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get compliance information for the current user's company."""
    compliance = db.query(CompanyComplianceInfo).filter(
        and_(
            CompanyComplianceInfo.company_id == current_user.company_id,
            CompanyComplianceInfo.deleted_at.is_(None)
        )
    ).first()

        if not compliance:
            # Return empty compliance info if none exists
            return CompanyComplianceInfoRead(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                company_id=current_user.company_id,
                compliance_status=ComplianceStatus.PENDING,
                compliance_documents=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

    return CompanyComplianceInfoRead.model_validate(compliance)


@router.post("/compliance", response_model=CompanyComplianceInfoRead, status_code=status.HTTP_201_CREATED)
@router.put("/compliance", response_model=CompanyComplianceInfoRead)
async def upsert_compliance_info(
    compliance_data: CompanyComplianceInfoCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create or update compliance information for the current user's company."""
    try:
        # Ensure company_id matches current user's company
        if compliance_data.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create compliance info for a different company"
            )

        # Check if compliance info already exists
        existing = db.query(CompanyComplianceInfo).filter(
            and_(
                CompanyComplianceInfo.company_id == current_user.company_id,
                CompanyComplianceInfo.deleted_at.is_(None)
            )
        ).first()

        if existing:
            # Update existing
            update_fields = compliance_data.model_dump(exclude_unset=True, exclude={"company_id"})
            for key, value in update_fields.items():
                setattr(existing, key, value)
            compliance = existing
        else:
            # Create new
            compliance = CompanyComplianceInfo(**compliance_data.model_dump())
            db.add(compliance)

        db.commit()
        db.refresh(compliance)

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(request) if request else {}
        audit_service.log_action(
            action=AuditAction.UPDATE if existing else AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="company_compliance_info",
            resource_id=str(compliance.id),
            result=AuditResult.SUCCESS
        )

        return CompanyComplianceInfoRead.model_validate(compliance)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert compliance info: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save compliance information"
        )


@router.patch("/compliance", response_model=CompanyComplianceInfoRead)
async def update_compliance_info(
    compliance_data: CompanyComplianceInfoUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update compliance information for the current user's company."""
    compliance = db.query(CompanyComplianceInfo).filter(
        and_(
            CompanyComplianceInfo.company_id == current_user.company_id,
            CompanyComplianceInfo.deleted_at.is_(None)
        )
    ).first()

    if not compliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance information not found. Use POST to create it first."
        )

    update_fields = compliance_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(compliance, key, value)

    db.add(compliance)
    db.commit()
    db.refresh(compliance)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="company_compliance_info",
        resource_id=str(compliance.id),
        details={"updated_fields": list(update_fields.keys())},
        result=AuditResult.SUCCESS
    )

    return CompanyComplianceInfoRead.model_validate(compliance)


# ===== DefaultConsigneeShipper Endpoints =====

@router.post("/consignee-shipper", response_model=DefaultConsigneeShipperRead, status_code=status.HTTP_201_CREATED)
async def create_consignee_shipper(
    consignee_shipper_data: DefaultConsigneeShipperCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create default consignee/shipper information for the current user's company."""
    try:
        # Ensure company_id matches current user's company
        if consignee_shipper_data.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create consignee/shipper for a different company"
            )

        # Validate type
        if consignee_shipper_data.type_ not in ["consignee", "shipper"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="type_ must be 'consignee' or 'shipper'"
            )

        consignee_shipper = DefaultConsigneeShipper(**consignee_shipper_data.model_dump())

        db.add(consignee_shipper)
        db.commit()
        db.refresh(consignee_shipper)

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(request) if request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="default_consignee_shipper",
            resource_id=str(consignee_shipper.id),
            result=AuditResult.SUCCESS
        )

        return DefaultConsigneeShipperRead.model_validate(consignee_shipper)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create consignee/shipper: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create consignee/shipper"
        )


@router.get("/consignee-shipper", response_model=DefaultConsigneeShipperListResponse)
async def list_consignee_shipper(
    type_: Optional[str] = Query(None, alias="type"),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List default consignee/shipper information for the current user's company."""
    query = db.query(DefaultConsigneeShipper).filter(
        and_(
            DefaultConsigneeShipper.company_id == current_user.company_id,
            DefaultConsigneeShipper.deleted_at.is_(None)
        )
    )

    if type_:
        query = query.filter(DefaultConsigneeShipper.type_ == type_)

    if active_only:
        query = query.filter(DefaultConsigneeShipper.is_active == True)

    total = query.count()
    items = query.order_by(DefaultConsigneeShipper.created_at.desc()).offset(skip).limit(limit).all()

    return DefaultConsigneeShipperListResponse(
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        items=[DefaultConsigneeShipperRead.model_validate(item) for item in items]
    )


@router.get("/consignee-shipper/{consignee_shipper_id}", response_model=DefaultConsigneeShipperRead)
async def get_consignee_shipper(
    consignee_shipper_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific consignee/shipper for the current user's company."""
    consignee_shipper = db.query(DefaultConsigneeShipper).filter(
        and_(
            DefaultConsigneeShipper.id == consignee_shipper_id,
            DefaultConsigneeShipper.company_id == current_user.company_id,
            DefaultConsigneeShipper.deleted_at.is_(None)
        )
    ).first()

    if not consignee_shipper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consignee/shipper not found or does not belong to your company"
        )

    return DefaultConsigneeShipperRead.model_validate(consignee_shipper)


@router.patch("/consignee-shipper/{consignee_shipper_id}", response_model=DefaultConsigneeShipperRead)
async def update_consignee_shipper(
    consignee_shipper_id: UUID,
    consignee_shipper_data: DefaultConsigneeShipperUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update consignee/shipper information for the current user's company."""
    consignee_shipper = db.query(DefaultConsigneeShipper).filter(
        and_(
            DefaultConsigneeShipper.id == consignee_shipper_id,
            DefaultConsigneeShipper.company_id == current_user.company_id,
            DefaultConsigneeShipper.deleted_at.is_(None)
        )
    ).first()

    if not consignee_shipper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consignee/shipper not found or does not belong to your company"
        )

    update_fields = consignee_shipper_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(consignee_shipper, key, value)

    db.add(consignee_shipper)
    db.commit()
    db.refresh(consignee_shipper)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="default_consignee_shipper",
        resource_id=str(consignee_shipper.id),
        details={"updated_fields": list(update_fields.keys())},
        result=AuditResult.SUCCESS
    )

    return DefaultConsigneeShipperRead.model_validate(consignee_shipper)


@router.delete("/consignee-shipper/{consignee_shipper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consignee_shipper(
    consignee_shipper_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Soft delete consignee/shipper information for the current user's company."""
    consignee_shipper = db.query(DefaultConsigneeShipper).filter(
        and_(
            DefaultConsigneeShipper.id == consignee_shipper_id,
            DefaultConsigneeShipper.company_id == current_user.company_id,
            DefaultConsigneeShipper.deleted_at.is_(None)
        )
    ).first()

    if not consignee_shipper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consignee/shipper not found or does not belong to your company"
        )

    consignee_shipper.deleted_at = func.now()
    consignee_shipper.is_active = False
    db.add(consignee_shipper)
    db.commit()

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.DELETE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="default_consignee_shipper",
        resource_id=str(consignee_shipper.id),
        result=AuditResult.SUCCESS
    )

