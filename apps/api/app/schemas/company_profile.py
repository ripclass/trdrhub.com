"""
Pydantic schemas for Company Profile API endpoints.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr

from ..models.company_profile import AddressType, ComplianceStatus


# ===== CompanyAddress Schemas =====

class CompanyAddressBase(BaseModel):
    label: str = Field(..., max_length=255, description="Address label (e.g., 'Main Warehouse')")
    address_type: AddressType = Field(AddressType.BUSINESS, description="Type of address")
    street_address: str = Field(..., description="Street address")
    city: str = Field(..., max_length=100, description="City")
    state_province: Optional[str] = Field(None, max_length=100, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=50, description="Postal/ZIP code")
    country: str = Field(..., max_length=100, description="Country")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    is_default_shipping: bool = Field(False, description="Is this the default shipping address?")
    is_default_billing: bool = Field(False, description="Is this the default billing address?")
    metadata_: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CompanyAddressCreate(CompanyAddressBase):
    company_id: UUID


class CompanyAddressRead(CompanyAddressBase):
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyAddressUpdate(BaseModel):
    label: Optional[str] = None
    address_type: Optional[AddressType] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_default_shipping: Optional[bool] = None
    is_default_billing: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata_: Optional[Dict[str, Any]] = None


class CompanyAddressListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CompanyAddressRead]


# ===== CompanyComplianceInfo Schemas =====

class CompanyComplianceInfoBase(BaseModel):
    tax_id: Optional[str] = Field(None, max_length=100, description="TIN/VAT number")
    vat_number: Optional[str] = Field(None, max_length=100, description="VAT registration number")
    registration_number: Optional[str] = Field(None, max_length=128, description="Business registration number")
    regulator_id: Optional[str] = Field(None, max_length=128, description="Industry regulator ID")
    compliance_status: ComplianceStatus = Field(ComplianceStatus.PENDING, description="Compliance verification status")
    expiry_date: Optional[datetime] = Field(None, description="Compliance expiry date")
    compliance_documents: List[Dict[str, Any]] = Field(default_factory=list, description="List of compliance document references")
    notes: Optional[str] = Field(None, description="Additional notes")


class CompanyComplianceInfoCreate(CompanyComplianceInfoBase):
    company_id: UUID


class CompanyComplianceInfoRead(CompanyComplianceInfoBase):
    id: UUID
    company_id: UUID
    verified_at: Optional[datetime]
    verified_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyComplianceInfoUpdate(BaseModel):
    tax_id: Optional[str] = None
    vat_number: Optional[str] = None
    registration_number: Optional[str] = None
    regulator_id: Optional[str] = None
    compliance_status: Optional[ComplianceStatus] = None
    expiry_date: Optional[datetime] = None
    compliance_documents: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


# ===== DefaultConsigneeShipper Schemas =====

class DefaultConsigneeShipperBase(BaseModel):
    type_: str = Field(..., description="Type: 'consignee' (for exporters) or 'shipper' (for importers)")
    company_name: str = Field(..., max_length=255, description="Company/entity name")
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    address_id: Optional[UUID] = Field(None, description="Reference to CompanyAddress")
    street_address: Optional[str] = Field(None, description="Street address (if not using address_id)")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(None, max_length=100, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=50, description="Postal/ZIP code")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    bank_name: Optional[str] = Field(None, max_length=255, description="Bank name")
    bank_account: Optional[str] = Field(None, max_length=100, description="Bank account number")
    swift_code: Optional[str] = Field(None, max_length=50, description="SWIFT/BIC code")
    metadata_: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DefaultConsigneeShipperCreate(DefaultConsigneeShipperBase):
    company_id: UUID


class DefaultConsigneeShipperRead(DefaultConsigneeShipperBase):
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DefaultConsigneeShipperUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address_id: Optional[UUID] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    swift_code: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_: Optional[Dict[str, Any]] = None


class DefaultConsigneeShipperListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DefaultConsigneeShipperRead]

