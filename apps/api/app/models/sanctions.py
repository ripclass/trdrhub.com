"""
Sanctions Screening Database Models

Stores sanctions lists, entities, and screening history for compliance auditing.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Float, Integer, DateTime, 
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class SanctionsListType(enum.Enum):
    """Types of sanctions lists."""
    SDN = "sdn"  # Specially Designated Nationals
    CONSOLIDATED = "consolidated"  # Consolidated lists
    SECTORAL = "sectoral"  # Sectoral sanctions (SSI)
    ENTITY = "entity"  # Entity lists (BIS)
    COUNTRY = "country"  # Country-based sanctions


class EntityType(enum.Enum):
    """Types of sanctioned entities."""
    INDIVIDUAL = "individual"
    ENTITY = "entity"
    VESSEL = "vessel"
    AIRCRAFT = "aircraft"


class ScreeningStatus(enum.Enum):
    """Screening result status."""
    CLEAR = "clear"
    POTENTIAL_MATCH = "potential_match"
    MATCH = "match"


# ============================================================================
# Sanctions Lists
# ============================================================================

class SanctionsList(Base):
    """
    Metadata for sanctions lists we track.
    """
    __tablename__ = "sanctions_lists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # List identification
    code = Column(String(50), unique=True, nullable=False, index=True)  # OFAC_SDN, EU_CONS
    name = Column(String(200), nullable=False)
    source = Column(String(100))  # US Treasury, European Commission
    jurisdiction = Column(String(10))  # US, EU, UN, UK
    
    # List type
    list_type = Column(String(20), default="consolidated")
    
    # Data source
    source_url = Column(Text)
    format = Column(String(20))  # XML, CSV, JSON
    
    # Update tracking
    last_synced = Column(DateTime)
    last_modified = Column(DateTime)  # Source file modification date
    version = Column(String(50))
    entry_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entities = relationship("SanctionedEntity", back_populates="sanctions_list")


class SanctionedEntity(Base):
    """
    Individual sanctioned entities from various lists.
    Cached locally for fast screening.
    """
    __tablename__ = "sanctioned_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source list
    list_id = Column(UUID(as_uuid=True), ForeignKey("sanctions_lists.id"), nullable=False)
    list_code = Column(String(50), index=True)  # Denormalized for performance
    
    # Entity identification
    source_id = Column(String(100), index=True)  # ID from source (e.g., OFAC SDN ID)
    entity_type = Column(String(20))  # individual, entity, vessel, aircraft
    
    # Primary name
    primary_name = Column(Text, nullable=False)
    name_normalized = Column(Text, index=True)  # For matching
    
    # Aliases (stored as JSON array)
    aliases = Column(JSON, default=list)
    aliases_normalized = Column(JSON, default=list)
    
    # Additional identifiers
    identifiers = Column(JSON, default=dict)  # passport, tax_id, imo, etc.
    
    # Program/reason
    programs = Column(JSON, default=list)  # IRAN, SDGT, etc.
    sanctions_programs = Column(Text)  # Comma-separated for display
    
    # Dates
    listed_date = Column(DateTime)
    delisted_date = Column(DateTime)
    
    # Additional data
    nationality = Column(String(100))
    country = Column(String(2))  # ISO code
    address = Column(Text)
    remarks = Column(Text)
    
    # Vessel-specific (if entity_type = vessel)
    vessel_type = Column(String(50))
    vessel_flag = Column(String(50))
    vessel_imo = Column(String(20))
    vessel_mmsi = Column(String(20))
    vessel_tonnage = Column(String(50))
    vessel_owner = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sanctions_list = relationship("SanctionsList", back_populates="entities")
    
    __table_args__ = (
        Index('ix_sanctioned_entities_list_name', 'list_code', 'name_normalized'),
        Index('ix_sanctioned_entities_type', 'entity_type'),
    )


# ============================================================================
# Screening Results
# ============================================================================

class ScreeningSession(Base):
    """
    A screening session groups multiple entity screenings together.
    """
    __tablename__ = "screening_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)
    
    # Session info
    session_type = Column(String(20))  # single, batch
    source = Column(String(50))  # web, api, lcopilot
    
    # Counts
    total_screenings = Column(Integer, default=0)
    clear_count = Column(Integer, default=0)
    match_count = Column(Integer, default=0)
    potential_match_count = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="complete")  # pending, processing, complete
    
    # For batch uploads
    batch_file_name = Column(String(200))
    batch_file_size = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    screenings = relationship("ScreeningResult", back_populates="session")
    
    __table_args__ = (
        Index('ix_screening_sessions_user', 'user_id', 'created_at'),
    )


class ScreeningResult(Base):
    """
    Individual screening result for a party, vessel, or goods.
    """
    __tablename__ = "screening_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session (optional for single screenings)
    session_id = Column(UUID(as_uuid=True), ForeignKey("screening_sessions.id"))
    user_id = Column(UUID(as_uuid=True), index=True)
    
    # What was screened
    screening_type = Column(String(20), nullable=False)  # party, vessel, goods, port
    query_value = Column(Text, nullable=False)  # The name/IMO/HS code screened
    query_normalized = Column(Text)
    
    # Additional context
    country = Column(String(2))  # Country of entity if provided
    additional_data = Column(JSON)  # Any extra context (IMO, HS code, etc.)
    
    # Lists screened against
    lists_screened = Column(JSON, default=list)
    
    # Overall result
    status = Column(String(20), nullable=False)  # clear, potential_match, match
    risk_level = Column(String(20))  # low, medium, high, critical
    
    # Match details
    total_matches = Column(Integer, default=0)
    highest_match_score = Column(Float)
    matches = Column(JSON, default=list)  # Array of match details
    
    # Certificate
    certificate_id = Column(String(50), unique=True, index=True)
    certificate_generated = Column(Boolean, default=False)
    
    # Recommendations
    recommendation = Column(Text)
    flags = Column(JSON, default=list)
    
    # Processing
    processing_time_ms = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ScreeningSession", back_populates="screenings")
    
    __table_args__ = (
        Index('ix_screening_results_user', 'user_id', 'created_at'),
        Index('ix_screening_results_status', 'status'),
        Index('ix_screening_results_cert', 'certificate_id'),
    )


class ScreeningMatch(Base):
    """
    Individual match detail from a screening.
    Stored separately for detailed audit trail.
    """
    __tablename__ = "screening_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    result_id = Column(UUID(as_uuid=True), ForeignKey("screening_results.id"), nullable=False)
    
    # What matched
    entity_id = Column(UUID(as_uuid=True), ForeignKey("sanctioned_entities.id"))
    list_code = Column(String(50), nullable=False)
    list_name = Column(String(200))
    
    # Matched entity details
    matched_name = Column(Text, nullable=False)
    matched_type = Column(String(20))
    matched_programs = Column(Text)
    matched_country = Column(String(100))
    
    # Match quality
    match_type = Column(String(20))  # exact, alias, fuzzy
    match_score = Column(Float, nullable=False)
    match_method = Column(String(50))  # jaro_winkler, token_set, exact
    
    # Source entry details
    source_id = Column(String(100))  # Original ID from sanctions list
    remarks = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_screening_matches_result', 'result_id'),
    )


# ============================================================================
# Watchlist Monitoring
# ============================================================================

class WatchlistEntry(Base):
    """
    Parties/vessels on continuous monitoring.
    Alert when list updates affect them.
    """
    __tablename__ = "watchlist_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # What to monitor
    entry_type = Column(String(20), nullable=False)  # party, vessel
    name = Column(Text, nullable=False)
    name_normalized = Column(Text, index=True)
    
    # Additional identifiers
    country = Column(String(2))
    identifiers = Column(JSON)  # IMO, tax ID, etc.
    
    # Monitoring config
    lists_to_monitor = Column(JSON, default=list)  # Empty = all lists
    alert_email = Column(Boolean, default=True)
    alert_in_app = Column(Boolean, default=True)
    
    # Current status (from last screening)
    last_screened = Column(DateTime)
    last_status = Column(String(20))  # clear, potential_match, match
    last_result_id = Column(UUID(as_uuid=True))
    
    # Notes
    notes = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_watchlist_user', 'user_id', 'is_active'),
    )


class WatchlistAlert(Base):
    """
    Alerts generated when watchlist entries have status changes.
    """
    __tablename__ = "watchlist_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    watchlist_entry_id = Column(UUID(as_uuid=True), ForeignKey("watchlist_entries.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # What changed
    alert_type = Column(String(50), nullable=False)  # new_match, status_change, list_update
    previous_status = Column(String(20))
    new_status = Column(String(20))
    
    # Match details if applicable
    match_list = Column(String(50))
    match_entity = Column(Text)
    match_score = Column(Float)
    
    # Alert delivery
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_watchlist_alerts_user', 'user_id', 'is_read'),
    )

