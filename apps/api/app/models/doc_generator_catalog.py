"""
Doc Generator Catalog Models

Models for templates, product catalog, and buyer directory.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, ForeignKey, Numeric, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ============== Audit Trail ==============

class AuditAction(str, Enum):
    """Types of audit actions"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    GENERATED = "generated"
    DOWNLOADED = "downloaded"
    VALIDATED = "validated"
    DUPLICATED = "duplicated"
    IMPORTED = "imported"
    SHARED = "shared"


class DocumentAuditLog(Base):
    """
    Audit trail for document operations.
    
    Records all changes to document sets for compliance.
    """
    __tablename__ = "document_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("document_sets.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False)
    action_detail = Column(String(200))  # e.g., "Generated commercial_invoice"
    
    # Field changes (for updates)
    field_changed = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    
    # Context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_audit_doc_set_time', 'document_set_id', 'created_at'),
        Index('ix_audit_user_time', 'user_id', 'created_at'),
    )


# ============== Document Templates ==============

class DocumentTemplate(Base):
    """
    Reusable document templates.
    
    Stores common configurations for quick document creation.
    """
    __tablename__ = "document_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Creator
    
    # Template metadata
    name = Column(String(200), nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)
    
    # Beneficiary defaults (usually the exporter's company)
    beneficiary_name = Column(String(500))
    beneficiary_address = Column(Text)
    beneficiary_country = Column(String(100))
    beneficiary_contact = Column(String(200))
    
    # Bank details
    bank_name = Column(String(300))
    bank_account = Column(String(100))
    bank_swift = Column(String(20))
    bank_address = Column(Text)
    
    # Common shipment settings
    default_port_of_loading = Column(String(200))
    default_incoterms = Column(String(10))
    default_country_of_origin = Column(String(100))
    
    # Document preferences
    preferred_document_types = Column(JSON)  # List of doc types to generate
    default_draft_tenor = Column(String(50))  # "AT SIGHT", "30 DAYS", etc.
    
    # Packing defaults
    default_shipping_marks = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_template_company', 'company_id'),
    )


# ============== Product Catalog ==============

class ProductCatalogItem(Base):
    """
    Catalog of frequently shipped products.
    
    Enables quick line item entry with pre-filled data.
    """
    __tablename__ = "product_catalog"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Product identification
    sku = Column(String(50))  # Internal SKU
    product_code = Column(String(50))  # External/buyer code
    name = Column(String(300), nullable=False)
    
    # Trade details
    hs_code = Column(String(20))
    description = Column(Text, nullable=False)  # Full description for documents
    short_description = Column(String(200))  # For dropdown display
    
    # Pricing
    default_unit_price = Column(Numeric(15, 4))
    currency = Column(String(3), default="USD")
    
    # Units
    default_unit = Column(String(20), default="PCS")  # PCS, KG, MT, etc.
    units_per_carton = Column(Integer)
    weight_per_unit_kg = Column(Numeric(10, 4))
    
    # Packing
    carton_dimensions = Column(String(100))  # "40x30x25 cm"
    carton_weight_kg = Column(Numeric(10, 4))
    cbm_per_carton = Column(Numeric(10, 6))
    
    # Origin
    country_of_origin = Column(String(100))
    
    # Status
    is_active = Column(Boolean, default=True)
    use_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_product_company', 'company_id'),
        Index('ix_product_hs_code', 'hs_code'),
        Index('ix_product_name', 'name'),
    )


# ============== Buyer Directory ==============

class BuyerProfile(Base):
    """
    Directory of frequent buyers/applicants.
    
    Stores buyer information for quick selection.
    """
    __tablename__ = "buyer_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Buyer identification
    buyer_code = Column(String(50))  # Internal code
    company_name = Column(String(500), nullable=False)
    country = Column(String(100))
    
    # Address
    address_line1 = Column(String(300))
    address_line2 = Column(String(300))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    
    # Contact
    contact_person = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    fax = Column(String(50))
    
    # Notify party (if different)
    notify_party_name = Column(String(500))
    notify_party_address = Column(Text)
    
    # Trade preferences
    preferred_incoterms = Column(String(10))
    preferred_port_of_discharge = Column(String(200))
    default_currency = Column(String(3), default="USD")
    
    # Banking
    buyer_bank_name = Column(String(300))
    buyer_bank_swift = Column(String(20))
    
    # Notes
    notes = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    use_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_buyer_company', 'company_id'),
        Index('ix_buyer_name', 'company_name'),
        Index('ix_buyer_country', 'country'),
    )


# ============== Generated Document Storage ==============

class StoredDocument(Base):
    """
    Stored document files in S3.
    
    Tracks all generated PDF versions.
    """
    __tablename__ = "stored_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("document_sets.id", ondelete="CASCADE"))
    generated_document_id = Column(UUID(as_uuid=True), ForeignKey("generated_documents.id", ondelete="SET NULL"))
    
    # S3 storage
    s3_bucket = Column(String(100))
    s3_key = Column(String(500), nullable=False)
    s3_region = Column(String(20))
    
    # File metadata
    document_type = Column(String(50), nullable=False)  # commercial_invoice, etc.
    file_name = Column(String(255))
    file_size = Column(Integer)  # bytes
    content_type = Column(String(100), default="application/pdf")
    checksum = Column(String(64))  # SHA256 hash
    
    # Version tracking
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)
    
    # Access
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime)
    
    # Expiry (for compliance)
    expires_at = Column(DateTime)  # Optional document expiry
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_stored_doc_set', 'document_set_id'),
        Index('ix_stored_doc_type', 'document_type'),
        Index('ix_stored_doc_s3_key', 's3_key'),
    )


# Exports
__all__ = [
    "DocumentAuditLog",
    "AuditAction",
    "DocumentTemplate",
    "ProductCatalogItem",
    "BuyerProfile",
    "StoredDocument",
]

