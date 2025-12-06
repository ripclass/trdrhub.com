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


# ============================================================================
# Phase 3: USMCA and RCEP Rules of Origin
# ============================================================================

class ProductSpecificRule(Base):
    """
    Product-Specific Rules (PSR) for FTAs like USMCA and RCEP.
    These are the detailed rules that determine origin eligibility.
    """
    __tablename__ = "product_specific_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fta_id = Column(UUID(as_uuid=True), ForeignKey("fta_agreements.id"), nullable=False)
    
    # HS Code targeting (can be at various levels of specificity)
    hs_code_from = Column(String(10), nullable=False, index=True)  # Range start
    hs_code_to = Column(String(10))  # Range end (null if single code)
    chapter = Column(String(2))  # Chapter number
    
    # Rule type (USMCA uses multiple rule types)
    rule_type = Column(String(20), nullable=False)  # CTC, RVC, SP, WO, combination
    
    # Change in Tariff Classification (CTC) rules
    ctc_type = Column(String(10))  # CC (chapter), CTH (heading), CTSH (subheading)
    ctc_exceptions = Column(Text)  # "except from headings 52.04 through 52.12"
    
    # Regional Value Content (RVC) requirements
    rvc_required = Column(Boolean, default=False)
    rvc_threshold = Column(Float)  # e.g., 75 for USMCA autos
    rvc_method = Column(String(30))  # transaction_value, net_cost, build_down, build_up
    rvc_alternative_threshold = Column(Float)  # Some rules allow alternative RVC
    
    # Labor Value Content (LVC) - USMCA specific for autos
    lvc_required = Column(Boolean, default=False)
    lvc_threshold = Column(Float)  # e.g., 40 for USMCA autos
    
    # Steel/Aluminum requirements (USMCA specific)
    steel_aluminum_required = Column(Boolean, default=False)
    steel_requirement = Column(Float)  # % from North America
    
    # Specific Process rules
    process_requirements = Column(Text)  # e.g., "cut and sewn in territory"
    
    # Full rule text (official language)
    rule_text = Column(Text, nullable=False)
    rule_notes = Column(Text)  # Additional clarifications
    
    # Annex/Chapter reference
    annex_reference = Column(String(50))  # e.g., "Annex 4-B", "Chapter 62 Rule"
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    fta = relationship("FTAAgreement", backref="product_specific_rules")
    
    __table_args__ = (
        Index('ix_psr_fta_hs', 'fta_id', 'hs_code_from'),
    )


class RVCCalculation(Base):
    """
    Saved Regional Value Content calculations for origin determination.
    Users can save and track their RVC calculations.
    """
    __tablename__ = "rvc_calculations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product details
    product_description = Column(Text, nullable=False)
    hs_code = Column(String(15), nullable=False)
    fta_code = Column(String(20), nullable=False)  # USMCA, RCEP, etc.
    
    # Value breakdown
    transaction_value = Column(Float)  # FOB price
    adjusted_value = Column(Float)  # After adjustments
    
    # Non-originating materials
    vom_value = Column(Float)  # Value of non-originating materials
    vom_breakdown = Column(JSON)  # Detailed breakdown by component
    
    # Originating materials
    vdm_value = Column(Float)  # Value of originating materials
    vdm_breakdown = Column(JSON)  # Detailed breakdown
    
    # Cost elements
    direct_labor_cost = Column(Float)
    direct_overhead = Column(Float)
    profit = Column(Float)
    other_costs = Column(Float)
    
    # Net cost method components (for USMCA)
    net_cost = Column(Float)
    excluded_costs = Column(JSON)  # Royalties, shipping, packing, etc.
    
    # Calculation results
    rvc_percent = Column(Float)  # Calculated RVC
    method_used = Column(String(30))  # transaction_value, net_cost
    threshold_required = Column(Float)  # Required RVC threshold
    meets_requirement = Column(Boolean)
    
    # For autos (USMCA)
    lvc_percent = Column(Float)
    lvc_meets_requirement = Column(Boolean)
    
    # Notes and documentation
    notes = Column(Text)
    supporting_docs = Column(JSON)  # List of uploaded document references
    
    # Project organization
    project_name = Column(String(200))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_rvc_calc_user', 'user_id', 'created_at'),
    )


class OriginDetermination(Base):
    """
    Complete origin determination record for FTA claims.
    Links classification + PSR + RVC calculation + certificate.
    """
    __tablename__ = "origin_determinations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product
    product_description = Column(Text, nullable=False)
    product_name = Column(String(200))
    hs_code = Column(String(15), nullable=False)
    
    # FTA being claimed
    fta_code = Column(String(20), nullable=False)
    export_country = Column(String(2), nullable=False)
    import_country = Column(String(2), nullable=False)
    
    # Rule applied
    rule_applied = Column(String(50))  # CTC, RVC, combination
    psr_id = Column(UUID(as_uuid=True), ForeignKey("product_specific_rules.id"))
    rvc_calculation_id = Column(UUID(as_uuid=True), ForeignKey("rvc_calculations.id"))
    
    # Determination result
    is_originating = Column(Boolean)
    determination_reason = Column(Text)
    
    # Certificate details
    certificate_type = Column(String(50))  # USMCA Certificate, Form D, etc.
    certificate_number = Column(String(100))
    certificate_date = Column(DateTime)
    blanket_period_from = Column(DateTime)
    blanket_period_to = Column(DateTime)
    
    # Producer/Exporter info
    producer_name = Column(String(200))
    producer_address = Column(Text)
    exporter_name = Column(String(200))
    exporter_address = Column(Text)
    
    # Status
    status = Column(String(20), default="draft")  # draft, verified, certified, expired
    verified_by = Column(UUID(as_uuid=True))
    verified_at = Column(DateTime)
    
    # Documentation
    supporting_documents = Column(JSON)  # List of document references
    notes = Column(Text)
    
    # Sharing
    is_shared = Column(Boolean, default=False)
    shared_with = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    psr = relationship("ProductSpecificRule", backref="determinations")
    rvc_calculation = relationship("RVCCalculation", backref="determination")
    
    __table_args__ = (
        Index('ix_origin_det_user', 'user_id', 'fta_code'),
    )


# ============================================================================
# Phase 3: Team Collaboration
# ============================================================================

class HSCodeTeam(Base):
    """
    Teams for collaborative HS code management.
    """
    __tablename__ = "hs_code_teams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Owner
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Team settings
    default_import_country = Column(String(2), default="US")
    default_ftas = Column(JSON, default=list)  # Preferred FTAs
    
    # Subscription/billing
    plan = Column(String(20), default="free")  # free, pro, enterprise
    max_members = Column(Integer, default=3)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HSCodeTeamMember(Base):
    """
    Team membership with role-based permissions.
    """
    __tablename__ = "hs_code_team_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    team_id = Column(UUID(as_uuid=True), ForeignKey("hs_code_teams.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Role determines permissions
    role = Column(String(20), nullable=False, default="viewer")  # owner, admin, editor, viewer
    
    # Permissions (can override role defaults)
    can_classify = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    can_export = Column(Boolean, default=True)
    can_invite = Column(Boolean, default=False)
    
    # Status
    status = Column(String(20), default="active")  # active, invited, suspended
    invited_by = Column(UUID(as_uuid=True))
    invited_at = Column(DateTime)
    joined_at = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    team = relationship("HSCodeTeam", backref="members")
    
    __table_args__ = (
        Index('ix_team_members_team', 'team_id', 'user_id'),
    )


class HSCodeProject(Base):
    """
    Projects for organizing classifications within a team.
    """
    __tablename__ = "hs_code_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    team_id = Column(UUID(as_uuid=True), ForeignKey("hs_code_teams.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Project settings
    default_import_country = Column(String(2))
    default_export_country = Column(String(2))
    target_fta = Column(String(20))  # Primary FTA for this project
    
    # Status
    status = Column(String(20), default="active")  # active, completed, archived
    
    # Metadata
    classification_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    team = relationship("HSCodeTeam", backref="projects")
    
    __table_args__ = (
        Index('ix_projects_team', 'team_id'),
    )


class ClassificationShare(Base):
    """
    Sharing individual classifications with team members or external users.
    """
    __tablename__ = "classification_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    classification_id = Column(UUID(as_uuid=True), ForeignKey("hs_classifications.id"), nullable=False)
    shared_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Share target (one of these will be set)
    shared_with_user = Column(UUID(as_uuid=True))  # Specific user
    shared_with_team = Column(UUID(as_uuid=True))  # Entire team
    shared_with_email = Column(String(200))  # External email
    
    # Permissions
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_comment = Column(Boolean, default=True)
    
    # Access control
    share_link = Column(String(100), unique=True)  # For link sharing
    requires_auth = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    
    # Tracking
    view_count = Column(Integer, default=0)
    last_viewed = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    classification = relationship("HSClassification", backref="shares")
    
    __table_args__ = (
        Index('ix_shares_classification', 'classification_id'),
    )


# ============================================================================
# Phase 4: Compliance Suite
# ============================================================================

class ExportControlItem(Base):
    """
    Export Control Classification Numbers (ECCN) from EAR Commerce Control List.
    Maps HS codes to export control requirements.
    """
    __tablename__ = "export_control_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ECCN identification
    eccn = Column(String(20), nullable=False, index=True)  # e.g., "3A001", "5A002"
    category = Column(String(5))  # 0-9 (Nuclear, Materials, Electronics, etc.)
    product_group = Column(String(5))  # A-E (Equipment, Test equipment, Materials, etc.)
    
    # Description
    description = Column(Text, nullable=False)
    technical_description = Column(Text)
    
    # Control reasons
    control_reasons = Column(JSON, default=list)  # NS, MT, NP, CB, CC, RS, AT, UN
    license_requirements = Column(JSON)  # By country group
    license_exceptions = Column(JSON)  # Available exceptions
    
    # HS code mapping (many ECCNs can map to multiple HS codes)
    hs_codes = Column(JSON, default=list)  # List of related HS codes
    
    # Classification notes
    notes = Column(Text)
    related_definitions = Column(Text)
    
    # ITAR crosswalk (some items are ITAR controlled)
    itar_category = Column(String(50))  # USML Category if applicable
    is_itar = Column(Boolean, default=False)
    
    # Status
    effective_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_eccn_category', 'category', 'product_group'),
    )


class ITARItem(Base):
    """
    ITAR (International Traffic in Arms Regulations) controlled items.
    US Munitions List categories.
    """
    __tablename__ = "itar_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # USML Category
    usml_category = Column(String(10), nullable=False, index=True)  # I-XXI
    subcategory = Column(String(20))  # e.g., "(a)", "(b)(1)"
    
    # Description
    description = Column(Text, nullable=False)
    technical_notes = Column(Text)
    
    # Control details
    significant_military_equipment = Column(Boolean, default=False)  # SME
    missile_technology = Column(Boolean, default=False)  # MTCR
    
    # Related HS codes (for screening)
    hs_codes = Column(JSON, default=list)
    
    # License requirements
    license_required = Column(Boolean, default=True)
    exemptions = Column(JSON, default=list)  # ITAR exemptions
    
    # Keywords for matching
    keywords = Column(JSON, default=list)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_usml_category', 'usml_category'),
    )


class Section301Exclusion(Base):
    """
    Section 301 tariff exclusions granted by USTR.
    Separate from Section301Rate as these are specific product exclusions.
    """
    __tablename__ = "section_301_exclusions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Exclusion identification
    exclusion_number = Column(String(50), nullable=False, unique=True, index=True)
    list_number = Column(String(10), nullable=False)  # List 1, 2, 3, 4A, 4B
    
    # Product details
    hs_code = Column(String(15), nullable=False, index=True)
    product_description = Column(Text, nullable=False)
    product_scope = Column(Text)  # Detailed scope of exclusion
    
    # Status
    status = Column(String(20), default="active")  # active, expired, extended
    
    # Dates
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=False)
    original_expiry = Column(DateTime)  # Before any extensions
    
    # Extension history
    extensions = Column(JSON, default=list)  # List of extension dates
    
    # Federal Register citation
    fr_citation = Column(String(100))  # e.g., "85 FR 12345"
    fr_date = Column(DateTime)
    
    # Requestor info (public)
    requestor_type = Column(String(50))  # Company, trade association, etc.
    
    notes = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_301_excl_hs_list', 'hs_code', 'list_number'),
    )


class ADCVDOrder(Base):
    """
    Antidumping (AD) and Countervailing Duty (CVD) orders.
    Active trade remedy orders on specific products/countries.
    """
    __tablename__ = "ad_cvd_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Order identification
    case_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "A-570-848"
    order_type = Column(String(10), nullable=False)  # AD, CVD, AD/CVD
    
    # Product and country
    product_name = Column(String(200), nullable=False)
    product_description = Column(Text)
    country = Column(String(2), nullable=False, index=True)  # ISO 2-letter
    country_name = Column(String(100))
    
    # HS codes covered
    hs_codes = Column(JSON, nullable=False, default=list)  # List of covered codes
    scope_description = Column(Text)  # Official scope language
    
    # Duty rates
    all_others_rate = Column(Float)  # Rate for non-examined companies
    company_rates = Column(JSON, default=list)  # Individual company rates
    
    # Cash deposit rate (current)
    current_deposit_rate = Column(Float)
    deposit_effective_date = Column(DateTime)
    
    # Order status
    status = Column(String(20), default="active")  # active, revoked, suspended
    order_date = Column(DateTime)
    revocation_date = Column(DateTime)
    
    # Review information
    last_review_period = Column(String(50))  # e.g., "01/01/2023 - 12/31/2023"
    next_review_due = Column(DateTime)
    sunset_review_due = Column(DateTime)
    
    # Federal Register citations
    order_fr_citation = Column(String(100))
    latest_rate_fr = Column(String(100))
    
    notes = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_adcvd_country_type', 'country', 'order_type'),
    )


class TariffQuota(Base):
    """
    Tariff Rate Quotas (TRQ) status and fill rates.
    Track quota availability for preferential duty rates.
    """
    __tablename__ = "tariff_quotas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Quota identification
    quota_number = Column(String(50), nullable=False, index=True)
    quota_name = Column(String(200), nullable=False)
    
    # Product coverage
    hs_codes = Column(JSON, nullable=False, default=list)
    product_description = Column(Text)
    
    # Country/FTA
    applicable_countries = Column(JSON, default=list)  # ISO codes or "all"
    fta_code = Column(String(20))  # Associated FTA if any
    
    # Quota quantities
    quota_quantity = Column(Float, nullable=False)
    quota_unit = Column(String(20))  # kg, pieces, metric tons
    quota_period = Column(String(20))  # annual, quarterly
    
    # Current period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Fill status
    quantity_used = Column(Float, default=0)
    fill_rate_percent = Column(Float, default=0)  # Calculated
    last_updated = Column(DateTime)
    
    # Rates
    in_quota_rate = Column(Float)  # Preferential rate
    over_quota_rate = Column(Float)  # MFN or higher rate
    
    # Status
    status = Column(String(20), default="open")  # open, near_full, full, closed
    
    # Alert thresholds
    alert_threshold_percent = Column(Float, default=80)  # Alert when fill rate hits this
    
    notes = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_quota_hs', 'quota_number'),
    )


class ComplianceScreening(Base):
    """
    User's compliance screening history.
    Tracks what products have been screened and results.
    """
    __tablename__ = "compliance_screenings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product being screened
    product_description = Column(Text, nullable=False)
    hs_code = Column(String(15))
    
    # Screening parameters
    export_country = Column(String(2))
    import_country = Column(String(2))
    end_use = Column(String(200))
    end_user = Column(String(200))
    
    # Screening results
    export_control_result = Column(JSON)  # ECCN match, license requirements
    itar_result = Column(JSON)  # USML category if applicable
    sanctions_result = Column(JSON)  # Country sanctions
    ad_cvd_result = Column(JSON)  # AD/CVD orders
    section_301_result = Column(JSON)  # 301 rates and exclusions
    quota_result = Column(JSON)  # Applicable quotas
    
    # Overall assessment
    overall_risk = Column(String(20))  # low, medium, high, prohibited
    flags = Column(JSON, default=list)  # List of compliance flags
    recommendations = Column(JSON, default=list)
    
    # Status
    status = Column(String(20), default="complete")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_screening_user', 'user_id', 'created_at'),
    )

