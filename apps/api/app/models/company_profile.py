"""
Company Profile models for SME dashboards.
Includes compliance information, address book, and default consignee/shipper.
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class AddressType(str, Enum):
    """Types of addresses in the address book."""
    BUSINESS = "business"
    SHIPPING = "shipping"
    BILLING = "billing"
    WAREHOUSE = "warehouse"
    CUSTOM = "custom"


class ComplianceStatus(str, Enum):
    """Compliance verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REJECTED = "rejected"


class CompanyAddress(Base):
    """Address book entries for a company."""
    __tablename__ = "company_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    
    # Address details
    label = Column(String(255), nullable=False)  # e.g., "Main Warehouse", "Head Office"
    address_type = Column(SQLEnum(AddressType), nullable=False, default=AddressType.BUSINESS)
    
    # Address fields
    street_address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(50), nullable=True)
    country = Column(String(100), nullable=False)
    
    # Contact information
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # Flags
    is_default_shipping = Column(Boolean, default=False, nullable=False)
    is_default_billing = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Additional metadata
    metadata_ = Column(JSONB, nullable=True, default=dict)  # e.g., {"notes": "...", "opening_hours": "..."}
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="addresses")


class CompanyComplianceInfo(Base):
    """Compliance and regulatory information for a company."""
    __tablename__ = "company_compliance_info"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    
    # Tax and registration identifiers
    tax_id = Column(String(100), nullable=True)  # TIN/VAT number (can also be in Company model)
    vat_number = Column(String(100), nullable=True)
    registration_number = Column(String(128), nullable=True)  # Business registration
    regulator_id = Column(String(128), nullable=True)  # Industry regulator ID
    
    # Compliance details
    compliance_status = Column(SQLEnum(ComplianceStatus), nullable=False, default=ComplianceStatus.PENDING)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    
    # Additional compliance documents/metadata
    compliance_documents = Column(JSONB, nullable=True, default=list)  # List of document references
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="compliance_info")
    verifier = relationship("User", foreign_keys=[verified_by])


class DefaultConsigneeShipper(Base):
    """Default consignee/shipper information for pre-filling forms."""
    __tablename__ = "default_consignee_shipper"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    
    # Type: consignee (for exporters) or shipper (for importers)
    type_ = Column(String(50), nullable=False)  # "consignee" or "shipper"
    
    # Company/entity details
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # Address (can reference CompanyAddress or be standalone)
    address_id = Column(UUID(as_uuid=True), ForeignKey("company_addresses.id"), nullable=True)
    street_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Additional details
    bank_name = Column(String(255), nullable=True)
    bank_account = Column(String(100), nullable=True)
    swift_code = Column(String(50), nullable=True)
    
    # Flags
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata_ = Column(JSONB, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="default_consignee_shipper")
    address = relationship("CompanyAddress", foreign_keys=[address_id])

