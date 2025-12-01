"""
Commodity database models for sustainable commodity management.

These models replace the hardcoded COMMODITIES_DATABASE with a flexible,
database-driven system that can grow organically from user needs.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Commodity(Base):
    """
    Database-driven commodity with aliases, HS codes, and price ranges.
    
    Replaces the hardcoded COMMODITIES_DATABASE dictionary.
    """
    __tablename__ = "commodities"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "DRY_FISH"
    name = Column(String(200), nullable=False)  # e.g., "Dry Fish"
    category = Column(String(50), nullable=False, index=True)  # e.g., "seafood"
    unit = Column(String(20), nullable=False)  # e.g., "kg"
    
    # Searchable fields
    aliases = Column(JSONB, default=list)  # ["dried fish", "stockfish", "bacalao"]
    hs_codes = Column(JSONB, default=list)  # ["0305.59", "0305.69"]
    
    # Price information
    price_low = Column(Numeric(12, 4), nullable=True)  # Typical range low
    price_high = Column(Numeric(12, 4), nullable=True)  # Typical range high
    current_estimate = Column(Numeric(12, 4), nullable=True)  # Curated current estimate
    
    # Data source configuration
    data_sources = Column(JSONB, default=dict)  # {"world_bank": "FISH_DRIED", "fred": "..."}
    source_codes = Column(JSONB, default=dict)
    
    # Status and audit
    verified = Column(Boolean, default=False)  # Admin approved?
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)  # user_id, "system", "ai"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    requests = relationship("CommodityRequest", back_populates="resolved_commodity")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "aliases": self.aliases or [],
            "hs_codes": self.hs_codes or [],
            "price_low": float(self.price_low) if self.price_low else None,
            "price_high": float(self.price_high) if self.price_high else None,
            "current_estimate": float(self.current_estimate) if self.current_estimate else None,
            "data_sources": self.data_sources or {},
            "verified": self.verified,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HSCode(Base):
    """
    Harmonized System (HS) codes for global commodity classification.
    
    HS codes are standardized globally and used by all customs authorities.
    This table helps map unknown commodities to categories via their HS codes.
    """
    __tablename__ = "hs_codes"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(12), unique=True, nullable=False, index=True)  # e.g., "0305.59"
    description = Column(String(500), nullable=False)  # e.g., "Fish, dried, other than cod"
    chapter = Column(String(2), nullable=False, index=True)  # e.g., "03"
    heading = Column(String(4), nullable=True)  # e.g., "0305"
    
    # Category mapping for price estimation
    category = Column(String(50), nullable=True)  # e.g., "seafood"
    typical_unit = Column(String(20), nullable=True)  # e.g., "kg"
    price_range_low = Column(Numeric(12, 4), nullable=True)
    price_range_high = Column(Numeric(12, 4), nullable=True)
    
    # Keywords for fuzzy matching
    keywords = Column(JSONB, default=list)  # ["dried fish", "dry fish", "stockfish"]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "code": self.code,
            "description": self.description,
            "chapter": self.chapter,
            "heading": self.heading,
            "category": self.category,
            "typical_unit": self.typical_unit,
            "price_range_low": float(self.price_range_low) if self.price_range_low else None,
            "price_range_high": float(self.price_range_high) if self.price_range_high else None,
            "keywords": self.keywords or [],
        }


class CommodityRequest(Base):
    """
    User-submitted requests for new commodities.
    
    When a user encounters an unknown commodity, they can submit a request
    which goes to admin review. This helps the database grow organically.
    """
    __tablename__ = "commodity_requests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Request details
    requested_name = Column(String(200), nullable=False)
    requested_by = Column(String(100), nullable=True)  # user_id
    company_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # User suggestions
    suggested_category = Column(String(50), nullable=True)
    suggested_unit = Column(String(20), nullable=True)
    suggested_hs_code = Column(String(12), nullable=True)
    suggested_price_low = Column(Numeric(12, 4), nullable=True)
    suggested_price_high = Column(Numeric(12, 4), nullable=True)
    
    # Context
    document_reference = Column(String(200), nullable=True)  # Which document it came from
    
    # Status
    status = Column(String(20), default='pending', index=True)  # pending, approved, rejected
    resolved_commodity_id = Column(PGUUID(as_uuid=True), ForeignKey('commodities.id'), nullable=True)
    
    # Admin review
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    resolved_commodity = relationship("Commodity", back_populates="requests")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "requested_name": self.requested_name,
            "requested_by": self.requested_by,
            "description": self.description,
            "suggested_category": self.suggested_category,
            "suggested_unit": self.suggested_unit,
            "suggested_hs_code": self.suggested_hs_code,
            "suggested_price_low": float(self.suggested_price_low) if self.suggested_price_low else None,
            "suggested_price_high": float(self.suggested_price_high) if self.suggested_price_high else None,
            "status": self.status,
            "resolved_commodity_id": str(self.resolved_commodity_id) if self.resolved_commodity_id else None,
            "admin_notes": self.admin_notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

