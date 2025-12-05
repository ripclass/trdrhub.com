"""
Document Generator Models

Models for generating LC-compliant shipping documents:
- Document Sets (container for all related docs)
- Line Items (goods being shipped)
- Generated Documents (PDF outputs)
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, ForeignKey, Numeric, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentStatus(str, Enum):
    """Status of a document set"""
    DRAFT = "draft"
    GENERATED = "generated"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class ValidationStatus(str, Enum):
    """Document validation status"""
    NOT_VALIDATED = "not_validated"
    PASSED = "passed"
    WARNINGS = "warnings"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Types of shipping documents"""
    COMMERCIAL_INVOICE = "commercial_invoice"
    PACKING_LIST = "packing_list"
    BENEFICIARY_CERTIFICATE = "beneficiary_certificate"
    BILL_OF_EXCHANGE = "bill_of_exchange"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    SHIPPING_INSTRUCTIONS = "shipping_instructions"
    WEIGHT_CERTIFICATE = "weight_certificate"
    INSURANCE_DECLARATION = "insurance_declaration"


class UnitType(str, Enum):
    """Common units for goods"""
    PCS = "PCS"      # Pieces
    KG = "KG"        # Kilograms
    MT = "MT"        # Metric Tons
    MTR = "MTR"      # Meters
    YDS = "YDS"      # Yards
    SET = "SET"      # Sets
    DOZ = "DOZ"      # Dozen
    CTN = "CTN"      # Cartons
    PKG = "PKG"      # Packages
    UNIT = "UNIT"    # Units


class CompanyBranding(Base):
    """
    Company branding for document generation.
    
    Stores logo, letterhead, colors, and other branding elements.
    """
    __tablename__ = "company_brandings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, unique=True)
    
    # Logo & Letterhead
    logo_url = Column(String(500))  # S3 URL for company logo
    logo_width = Column(Integer, default=150)  # Logo width in pixels
    letterhead_url = Column(String(500))  # Full letterhead template
    
    # Company Info (for documents)
    company_name = Column(String(500))
    company_address = Column(Text)
    company_phone = Column(String(100))
    company_email = Column(String(200))
    company_website = Column(String(200))
    
    # Registration Details
    tax_id = Column(String(100))  # VAT/GST number
    registration_number = Column(String(100))  # Company registration
    export_license = Column(String(100))  # IEC, ERC, etc.
    
    # Bank Details (for invoices)
    bank_name = Column(String(300))
    bank_account = Column(String(100))
    bank_swift = Column(String(20))
    bank_address = Column(Text)
    
    # Styling
    primary_color = Column(String(10), default="#1e40af")  # Hex color
    secondary_color = Column(String(10), default="#64748b")
    
    # Signature/Stamp
    signature_url = Column(String(500))  # Authorized signature image
    stamp_url = Column(String(500))  # Company stamp/seal image
    signatory_name = Column(String(200))
    signatory_title = Column(String(200))
    
    # Footer
    footer_text = Column(Text)  # Custom footer for documents
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentSet(Base):
    """
    A set of related shipping documents.
    
    Contains all the data needed to generate various trade documents
    (Commercial Invoice, Packing List, CoO, etc.) from a single entry.
    """
    __tablename__ = "document_sets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    
    # Document Set Metadata
    name = Column(String(200))  # User-friendly name
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT)
    
    # ========== LCopilot Integration ==========
    lcopilot_session_id = Column(UUID(as_uuid=True))  # Source LCopilot session
    imported_from_lcopilot = Column(Boolean, default=False)
    
    # ========== Validation Status ==========
    validation_status = Column(SQLEnum(ValidationStatus), default=ValidationStatus.NOT_VALIDATED)
    validation_errors = Column(JSON)  # List of validation errors
    validation_warnings = Column(JSON)  # List of warnings
    last_validated_at = Column(DateTime)
    
    # ========== LC Reference ==========
    lc_number = Column(String(100))
    lc_date = Column(Date)
    lc_amount = Column(Numeric(15, 2))
    lc_currency = Column(String(3), default="USD")
    issuing_bank = Column(String(300))
    advising_bank = Column(String(300))
    
    # ========== Parties ==========
    # Beneficiary (Seller/Exporter)
    beneficiary_name = Column(String(500), nullable=False)
    beneficiary_address = Column(Text)
    beneficiary_country = Column(String(100))
    beneficiary_contact = Column(String(200))
    
    # Applicant (Buyer/Importer)
    applicant_name = Column(String(500), nullable=False)
    applicant_address = Column(Text)
    applicant_country = Column(String(100))
    
    # Notify Party
    notify_party_name = Column(String(500))
    notify_party_address = Column(Text)
    
    # ========== Shipment Details ==========
    vessel_name = Column(String(200))
    voyage_number = Column(String(50))
    bl_number = Column(String(100))
    bl_date = Column(Date)
    container_number = Column(String(50))
    seal_number = Column(String(50))
    port_of_loading = Column(String(200))
    port_of_loading_code = Column(String(10))
    port_of_discharge = Column(String(200))
    port_of_discharge_code = Column(String(10))
    final_destination = Column(String(200))
    
    # Trade Terms
    incoterms = Column(String(10))  # FOB, CIF, CFR, etc.
    incoterms_place = Column(String(200))  # Named place
    
    # ========== Packing Details ==========
    total_cartons = Column(Integer)
    gross_weight_kg = Column(Numeric(12, 3))
    net_weight_kg = Column(Numeric(12, 3))
    cbm = Column(Numeric(10, 3))  # Cubic meters
    shipping_marks = Column(Text)
    
    # ========== Document Numbers ==========
    invoice_number = Column(String(100))
    invoice_date = Column(Date)
    proforma_number = Column(String(100))
    proforma_date = Column(Date)
    po_number = Column(String(100))  # Purchase Order
    
    # ========== Additional Fields ==========
    country_of_origin = Column(String(100))
    remarks = Column(Text)
    
    # Bill of Exchange specific
    draft_tenor = Column(String(50))  # "AT SIGHT", "30 DAYS", "60 DAYS"
    drawee_name = Column(String(500))  # Usually the issuing bank
    drawee_address = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = relationship("DocumentLineItem", back_populates="document_set", cascade="all, delete-orphan")
    generated_documents = relationship("GeneratedDocument", back_populates="document_set", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DocumentSet {self.id}: {self.lc_number or 'No LC'}>"
    
    @property
    def total_quantity(self) -> int:
        """Calculate total quantity from line items"""
        return sum(item.quantity or 0 for item in self.line_items)
    
    @property
    def total_amount(self) -> float:
        """Calculate total amount from line items"""
        return sum(float(item.total_price or 0) for item in self.line_items)
    
    @property
    def total_cartons_from_items(self) -> int:
        """Calculate total cartons from line items"""
        return sum(item.cartons or 0 for item in self.line_items)


class DocumentLineItem(Base):
    """
    Line items for a document set (goods being shipped).
    
    Each line item represents a type of goods with quantity, price, and packing details.
    """
    __tablename__ = "document_line_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("document_sets.id", ondelete="CASCADE"), nullable=False)
    
    # Item Details
    line_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    hs_code = Column(String(20))
    
    # Quantity & Price
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default="PCS")
    unit_price = Column(Numeric(12, 4))
    total_price = Column(Numeric(15, 2))
    
    # Packing Details
    cartons = Column(Integer)
    carton_dimensions = Column(String(100))  # e.g., "60x40x30 CM"
    gross_weight_kg = Column(Numeric(12, 3))
    net_weight_kg = Column(Numeric(12, 3))
    
    # Additional
    remarks = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document_set = relationship("DocumentSet", back_populates="line_items")
    
    def __repr__(self):
        return f"<LineItem {self.line_number}: {self.description[:30]}...>"


class GeneratedDocument(Base):
    """
    Generated PDF documents from a document set.
    
    Tracks each generated document with its file path, version, and metadata.
    """
    __tablename__ = "generated_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("document_sets.id", ondelete="CASCADE"), nullable=False)
    
    # Document Info
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    file_name = Column(String(300))
    file_path = Column(String(500))  # S3 key or local path
    file_size = Column(Integer)
    
    # Version Control
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)
    
    # Generation Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Validation
    validation_passed = Column(Boolean)
    validation_errors = Column(JSON)  # List of validation issues
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document_set = relationship("DocumentSet", back_populates="generated_documents")
    
    def __repr__(self):
        return f"<GeneratedDoc {self.document_type.value}: v{self.version}>"


# Helper for accessing models
__all__ = [
    "DocumentSet",
    "DocumentLineItem",
    "GeneratedDocument",
    "CompanyBranding",
    "DocumentStatus",
    "DocumentType",
    "UnitType",
    "ValidationStatus",
]

