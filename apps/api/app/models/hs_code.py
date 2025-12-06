"""
HS Code Finder Models

Database models for HS code classification, duty rates, and FTA eligibility.
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ClassificationSource(str, enum.Enum):
    """Source of HS code classification"""
    AI = "ai"
    MANUAL = "manual"
    VERIFIED = "verified"
    CUSTOMS = "customs"


class HSCodeTariff(Base):
    """
    HS Code tariff reference table for HS Code Finder tool.
    Stores the hierarchical tariff codes and their descriptions.
    Note: Named HSCodeTariff to avoid conflict with HSCode in commodities.py
    """
    __tablename__ = "hs_code_tariffs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Code hierarchy (6-digit international + country-specific extensions)
    code = Column(String(15), nullable=False, index=True)  # e.g., "6109.10.00.10"
    code_2 = Column(String(2), nullable=True)   # Chapter: 61
    code_4 = Column(String(4), nullable=True)   # Heading: 6109
    code_6 = Column(String(6), nullable=True)   # Subheading: 6109.10
    code_8 = Column(String(8), nullable=True)   # National: 6109.10.00
    code_10 = Column(String(10), nullable=True) # Statistical: 6109.10.00.10
    
    # Description at each level
    description = Column(Text, nullable=False)
    chapter_description = Column(Text)
    heading_description = Column(Text)
    subheading_description = Column(Text)
    
    # Country-specific
    country_code = Column(String(2), nullable=False, default="US", index=True)  # ISO 2-letter
    schedule_type = Column(String(20), default="HTS")  # HTS, TARIC, UK Tariff, etc.
    
    # Classification metadata
    unit_of_quantity = Column(String(50))  # kg, pieces, etc.
    unit_of_quantity_2 = Column(String(50))
    
    # Notes and restrictions
    general_notes = Column(Text)
    special_notes = Column(Text)
    requires_license = Column(Boolean, default=False)
    quota_applicable = Column(Boolean, default=False)
    
    # For AI training
    keywords = Column(JSON, default=list)  # Keywords for better AI matching
    related_codes = Column(JSON, default=list)  # Similar/related codes
    
    # Metadata
    effective_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_hs_code_tariffs_code_country', 'code', 'country_code'),
        Index('ix_hs_code_tariffs_code_6', 'code_6'),
    )


class DutyRate(Base):
    """
    Duty rates for HS codes by country.
    Includes MFN, preferential, and special rates.
    """
    __tablename__ = "duty_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hs_code_id = Column(UUID(as_uuid=True), ForeignKey("hs_code_tariffs.id"), nullable=False, index=True)
    
    # Rate type
    rate_type = Column(String(20), nullable=False)  # mfn, preferential, special
    rate_code = Column(String(20))  # e.g., "MFN", "GSP", "FTA-RCEP"
    
    # Origin country (for preferential rates)
    origin_country = Column(String(2))  # ISO 2-letter, NULL for MFN
    
    # Rate values
    ad_valorem_rate = Column(Float)  # Percentage (e.g., 12.5 for 12.5%)
    specific_rate = Column(Float)  # Per unit (e.g., $0.50/kg)
    specific_rate_unit = Column(String(20))  # kg, piece, liter
    compound_rate = Column(String(100))  # For complex rates like "10% + $0.50/kg"
    
    # Additional charges
    additional_duty = Column(Float, default=0)  # Anti-dumping, countervailing
    additional_duty_type = Column(String(50))  # AD, CVD, Safeguard
    
    # Quotas
    in_quota_rate = Column(Float)
    out_quota_rate = Column(Float)
    quota_quantity = Column(Float)
    quota_unit = Column(String(20))
    
    # Validity
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    hs_code = relationship("HSCodeTariff", backref="duty_rates")


class FTAAgreement(Base):
    """
    Free Trade Agreement reference.
    """
    __tablename__ = "fta_agreements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    code = Column(String(20), unique=True, nullable=False)  # e.g., "RCEP", "CPTPP", "USMCA"
    name = Column(String(200), nullable=False)
    full_name = Column(Text)
    
    # Member countries (JSON array of ISO codes)
    member_countries = Column(JSON, default=list)
    
    # Certificate types
    certificate_types = Column(JSON, default=list)  # ["Form A", "Form D", "EUR.1"]
    
    # Rules
    cumulation_type = Column(String(50))  # bilateral, diagonal, full
    de_minimis_threshold = Column(Float)  # e.g., 10 for 10%
    
    # Validity
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FTARule(Base):
    """
    Product-specific rules of origin for FTA eligibility.
    """
    __tablename__ = "fta_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fta_id = Column(UUID(as_uuid=True), ForeignKey("fta_agreements.id"), nullable=False)
    
    # HS code (can be 2, 4, or 6 digit)
    hs_code_prefix = Column(String(6), nullable=False, index=True)
    
    # Rule description
    rule_type = Column(String(50))  # CTC, RVC, SP (specific process)
    rule_text = Column(Text)
    
    # Change in Tariff Classification
    ctc_requirement = Column(String(50))  # CC, CTH, CTSH
    
    # Regional Value Content
    rvc_threshold = Column(Float)  # e.g., 40 for 40%
    rvc_method = Column(String(50))  # build-down, build-up, net cost
    
    # Preferential rate
    preferential_rate = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    fta = relationship("FTAAgreement", backref="rules")


class HSClassification(Base):
    """
    User's HS code classification history.
    """
    __tablename__ = "hs_classifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product info
    product_description = Column(Text, nullable=False)
    product_name = Column(String(200))
    
    # Classification result
    hs_code = Column(String(15), nullable=False, index=True)
    hs_code_description = Column(Text)
    
    # Countries
    import_country = Column(String(2), nullable=False)  # Destination
    export_country = Column(String(2))  # Origin
    
    # AI classification details
    source = Column(SQLEnum(ClassificationSource), default=ClassificationSource.AI)
    confidence_score = Column(Float)  # 0-1
    alternative_codes = Column(JSON, default=list)  # Other possible codes
    ai_reasoning = Column(Text)  # Why AI chose this code
    
    # Duty information (snapshot at time of classification)
    mfn_rate = Column(Float)
    preferential_rate = Column(Float)
    fta_applied = Column(String(50))
    estimated_duty = Column(Float)
    currency = Column(String(3), default="USD")
    
    # Value for duty calculation
    product_value = Column(Float)
    quantity = Column(Float)
    quantity_unit = Column(String(20))
    
    # Restrictions found
    restrictions = Column(JSON, default=list)  # Any import restrictions
    licenses_required = Column(JSON, default=list)
    
    # Status
    is_verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True))
    verified_at = Column(DateTime)
    
    # For organizing
    project_name = Column(String(200))
    tags = Column(JSON, default=list)
    notes = Column(Text)
    
    # Sharing
    is_shared = Column(Boolean, default=False)
    shared_with = Column(JSON, default=list)  # User IDs
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_hs_classifications_user_created', 'user_id', 'created_at'),
    )


class HSCodeSearch(Base):
    """
    Search analytics - track what people search for.
    """
    __tablename__ = "hs_code_searches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Search details
    search_query = Column(Text, nullable=False)
    search_type = Column(String(20), default="description")  # description, code, keyword
    
    # User (optional for anonymous)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Results
    results_count = Column(Integer, default=0)
    top_result_code = Column(String(15))
    selected_code = Column(String(15))  # What user actually chose
    
    # Context
    import_country = Column(String(2))
    export_country = Column(String(2))
    
    # Timing
    response_time_ms = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BindingRuling(Base):
    """
    CBP Binding Rulings (CROSS database) for classification precedent.
    Used as training context for AI classification.
    """
    __tablename__ = "binding_rulings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Ruling identification
    ruling_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "N123456"
    ruling_type = Column(String(20))  # NY (New York), HQ (Headquarters)
    
    # Product classification
    product_description = Column(Text, nullable=False)
    hs_code = Column(String(15), nullable=False, index=True)
    
    # Context
    country = Column(String(2), default="US")  # Issuing authority country
    legal_reference = Column(Text)  # GRI citations, chapter notes
    reasoning = Column(Text)  # Why this classification
    
    # Keywords extracted for AI matching
    keywords = Column(JSON, default=list)
    
    # Dates
    ruling_date = Column(DateTime)
    effective_date = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_binding_rulings_hs_code', 'hs_code'),
    )


class ChapterNote(Base):
    """
    HS Chapter and Section Notes for classification context.
    Critical for accurate AI classification per GRI rules.
    """
    __tablename__ = "chapter_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Note identification
    chapter = Column(String(2), nullable=False, index=True)  # "01" to "99"
    note_type = Column(String(20), nullable=False)  # section_note, chapter_note, subheading_note
    note_number = Column(Integer)  # Note 1, Note 2, etc.
    
    # Content
    note_text = Column(Text, nullable=False)
    
    # Country-specific (some notes differ)
    country_code = Column(String(2), default="US")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_chapter_notes_chapter', 'chapter', 'country_code'),
    )


class Section301Rate(Base):
    """
    US Section 301 additional tariffs (e.g., on China).
    Tracked separately due to frequent changes.
    """
    __tablename__ = "section_301_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    hs_code = Column(String(15), nullable=False, index=True)
    
    # Origin country subject to 301
    origin_country = Column(String(2), nullable=False, default="CN")  # China primarily
    
    # List identification
    list_number = Column(String(10))  # List 1, List 2, List 3, List 4A, List 4B
    
    # Rate
    additional_rate = Column(Float, nullable=False)  # 7.5%, 25%, etc.
    
    # Exclusions
    is_excluded = Column(Boolean, default=False)
    exclusion_number = Column(String(50))
    exclusion_expiry = Column(DateTime)
    
    # Validity
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_section_301_hs_origin', 'hs_code', 'origin_country'),
    )


class RateAlert(Base):
    """
    User subscriptions to rate change notifications.
    """
    __tablename__ = "rate_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Code to monitor
    hs_code = Column(String(15), nullable=False, index=True)
    import_country = Column(String(2), nullable=False, default="US")
    export_country = Column(String(2))
    
    # Alert configuration
    alert_type = Column(String(20), default="any")  # any, increase, decrease
    threshold_percent = Column(Float)  # Alert only if change exceeds this
    
    # Baseline rate at subscription time
    baseline_rate = Column(Float)
    baseline_date = Column(DateTime, default=datetime.utcnow)
    
    # Notification preferences
    email_notification = Column(Boolean, default=True)
    in_app_notification = Column(Boolean, default=True)
    
    # Tracking
    last_notified = Column(DateTime)
    notification_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_rate_alerts_user', 'user_id', 'is_active'),
    )

