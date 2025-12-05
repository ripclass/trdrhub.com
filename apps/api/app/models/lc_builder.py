"""
LC Builder Models

SQLAlchemy models for the LC Application Builder.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class LCType(str, enum.Enum):
    """Types of Letter of Credit"""
    DOCUMENTARY = "documentary"
    STANDBY = "standby"
    REVOLVING = "revolving"
    TRANSFERABLE = "transferable"


class LCStatus(str, enum.Enum):
    """Status of LC Application"""
    DRAFT = "draft"
    REVIEW = "review"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    AMENDED = "amended"


class PaymentTerms(str, enum.Enum):
    """Payment terms for LC"""
    SIGHT = "sight"
    USANCE = "usance"
    DEFERRED = "deferred"
    MIXED = "mixed"


class ConfirmationInstructions(str, enum.Enum):
    """Confirmation instructions"""
    WITHOUT = "without"
    MAY_ADD = "may_add"
    CONFIRM = "confirm"


class ClauseCategory(str, enum.Enum):
    """Categories for clause library"""
    SHIPMENT = "shipment"
    DOCUMENTS = "documents"
    PAYMENT = "payment"
    SPECIAL = "special"
    AMENDMENTS = "amendments"
    RED_GREEN = "red_green"


class RiskLevel(str, enum.Enum):
    """Risk level indicator"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BiasIndicator(str, enum.Enum):
    """Who benefits from the clause"""
    BENEFICIARY = "beneficiary"
    APPLICANT = "applicant"
    NEUTRAL = "neutral"


class LCApplication(Base):
    """LC Application - the main entity"""
    __tablename__ = "lc_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Basic Info
    reference_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=True)  # User-friendly name
    lc_type = Column(SQLEnum(LCType), default=LCType.DOCUMENTARY)
    status = Column(SQLEnum(LCStatus), default=LCStatus.DRAFT)
    
    # Amount
    currency = Column(String(3), default="USD")
    amount = Column(Float, nullable=False)
    tolerance_plus = Column(Float, default=0)  # e.g., 5 for +5%
    tolerance_minus = Column(Float, default=0)  # e.g., 5 for -5%
    
    # Parties - Applicant
    applicant_name = Column(String(200), nullable=False)
    applicant_address = Column(Text)
    applicant_country = Column(String(100))
    applicant_contact = Column(String(200))
    
    # Parties - Beneficiary
    beneficiary_name = Column(String(200), nullable=False)
    beneficiary_address = Column(Text)
    beneficiary_country = Column(String(100))
    beneficiary_contact = Column(String(200))
    
    # Parties - Banks
    issuing_bank_name = Column(String(200))
    issuing_bank_swift = Column(String(11))
    advising_bank_name = Column(String(200))
    advising_bank_swift = Column(String(11))
    confirming_bank_name = Column(String(200))
    confirming_bank_swift = Column(String(11))
    
    # Shipment
    port_of_loading = Column(String(200))
    port_of_discharge = Column(String(200))
    place_of_delivery = Column(String(200))
    latest_shipment_date = Column(DateTime)
    incoterms = Column(String(10))  # FOB, CIF, etc.
    incoterms_place = Column(String(200))
    partial_shipments = Column(Boolean, default=True)
    transhipment = Column(Boolean, default=True)
    
    # Goods
    goods_description = Column(Text, nullable=False)
    hs_code = Column(String(20))
    quantity = Column(String(100))
    unit_price = Column(String(100))
    
    # Payment
    payment_terms = Column(SQLEnum(PaymentTerms), default=PaymentTerms.SIGHT)
    usance_days = Column(Integer)  # For usance LCs
    usance_from = Column(String(50))  # bl_date, invoice_date, presentation
    
    # Validity
    expiry_date = Column(DateTime, nullable=False)
    expiry_place = Column(String(200))
    presentation_period = Column(Integer, default=21)  # Days after shipment
    confirmation_instructions = Column(
        SQLEnum(ConfirmationInstructions), 
        default=ConfirmationInstructions.WITHOUT
    )
    
    # Documents (stored as JSON array of document requirements)
    documents_required = Column(JSON, default=list)
    
    # Additional conditions
    additional_conditions = Column(JSON, default=list)
    
    # Selected clauses (references to clause library)
    selected_clause_ids = Column(JSON, default=list)
    
    # Validation & Risk
    validation_issues = Column(JSON, default=list)
    risk_score = Column(Float)  # 0-100
    risk_details = Column(JSON)  # Detailed risk breakdown
    
    # Template reference
    template_id = Column(UUID(as_uuid=True), ForeignKey("lc_templates.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime)
    
    # Relationships
    documents = relationship("LCDocumentRequirement", back_populates="lc_application")
    versions = relationship("LCApplicationVersion", back_populates="lc_application")


class LCDocumentRequirement(Base):
    """Document requirements for an LC"""
    __tablename__ = "lc_document_requirements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_application_id = Column(UUID(as_uuid=True), ForeignKey("lc_applications.id"), nullable=False)
    
    document_type = Column(String(100), nullable=False)  # commercial_invoice, b/l, etc.
    description = Column(Text)
    copies_original = Column(Integer, default=1)
    copies_copy = Column(Integer, default=0)
    specific_requirements = Column(Text)  # Any special requirements
    is_required = Column(Boolean, default=True)
    
    # Relationship
    lc_application = relationship("LCApplication", back_populates="documents")


class LCApplicationVersion(Base):
    """Version history for LC applications"""
    __tablename__ = "lc_application_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_application_id = Column(UUID(as_uuid=True), ForeignKey("lc_applications.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # Full snapshot of application state
    change_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))
    
    # Relationship
    lc_application = relationship("LCApplication", back_populates="versions")


class LCClause(Base):
    """Clause library - pre-approved clauses"""
    __tablename__ = "lc_clauses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identification
    code = Column(String(20), unique=True, nullable=False)  # e.g., SHIP-001
    category = Column(SQLEnum(ClauseCategory), nullable=False)
    subcategory = Column(String(100))
    
    # Content
    title = Column(String(200), nullable=False)
    clause_text = Column(Text, nullable=False)
    plain_english = Column(Text)  # Plain English explanation
    
    # Risk indicators
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.MEDIUM)
    bias = Column(SQLEnum(BiasIndicator), default=BiasIndicator.NEUTRAL)
    risk_notes = Column(Text)  # Explanation of risk
    
    # Usage
    bank_acceptance = Column(Float, default=0.95)  # 0-1, how often banks accept this
    usage_count = Column(Integer, default=0)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    tags = Column(JSON, default=list)  # For search
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LCTemplate(Base):
    """Trade route templates"""
    __tablename__ = "lc_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Null = system template
    
    # Identification
    name = Column(String(200), nullable=False)
    description = Column(Text)
    trade_route = Column(String(100))  # e.g., "Bangladesh → USA"
    industry = Column(String(100))  # e.g., "RMG", "Electronics"
    
    # Template data (partial LC application data)
    template_data = Column(JSON, nullable=False)
    
    # Default clauses for this template
    default_clause_ids = Column(JSON, default=list)
    
    # Default documents
    default_documents = Column(JSON, default=list)
    
    # Metadata
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)  # System-provided template
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApplicantProfile(Base):
    """Saved applicant profiles for quick reuse"""
    __tablename__ = "lc_applicant_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    address = Column(Text)
    country = Column(String(100))
    contact_name = Column(String(200))
    contact_email = Column(String(200))
    contact_phone = Column(String(50))
    bank_name = Column(String(200))
    bank_swift = Column(String(11))
    bank_account = Column(String(50))
    
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BeneficiaryProfile(Base):
    """Saved beneficiary profiles for quick reuse"""
    __tablename__ = "lc_beneficiary_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    address = Column(Text)
    country = Column(String(100))
    contact_name = Column(String(200))
    contact_email = Column(String(200))
    contact_phone = Column(String(50))
    bank_name = Column(String(200))
    bank_swift = Column(String(11))
    bank_account = Column(String(50))
    
    # For risk assessment
    trade_history_count = Column(Integer, default=0)
    first_trade_date = Column(DateTime)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

