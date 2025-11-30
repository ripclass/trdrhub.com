"""
Models for commodity prices and price verification.
"""

from sqlalchemy import Column, String, Text, Float, Integer, JSON, TIMESTAMP, Boolean, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid
import enum


class CommodityCategory(str, enum.Enum):
    """Categories of commodities."""
    AGRICULTURE = "agriculture"
    ENERGY = "energy"
    METALS = "metals"
    TEXTILES = "textiles"
    CHEMICALS = "chemicals"
    FOOD_BEVERAGE = "food_beverage"
    ELECTRONICS = "electronics"
    OTHER = "other"


class RiskLevel(str, enum.Enum):
    """Risk level for price verification."""
    LOW = "low"           # Variance < 10%
    MEDIUM = "medium"     # Variance 10-25%
    HIGH = "high"         # Variance 25-50%
    CRITICAL = "critical" # Variance > 50%


class Commodity(Base):
    """
    Master table of commodities that can be verified.
    """
    __tablename__ = "commodities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)  # e.g., "COTTON_RAW", "STEEL_HRC"
    name = Column(String(200), nullable=False)  # e.g., "Raw Cotton", "Hot Rolled Steel Coils"
    category = Column(String(50), nullable=False)  # agriculture, energy, metals, etc.
    
    # Unit information
    default_unit = Column(String(50), nullable=False)  # kg, mt, bbl, etc.
    alternate_units = Column(JSON)  # {"lb": 2.205, "ton": 0.001} conversion factors to default
    
    # Data source configuration
    data_sources = Column(JSON)  # ["world_bank", "fred", "custom"]
    source_codes = Column(JSON)  # {"world_bank": "COTTON_A_INDEX", "fred": "WPU0131"}
    
    # Price thresholds
    typical_min_price = Column(Float)  # Historical minimum (per default unit)
    typical_max_price = Column(Float)  # Historical maximum
    
    # Metadata
    description = Column(Text)
    hs_codes = Column(JSON)  # Related HS codes ["5201", "5201.00"]
    aliases = Column(JSON)  # ["cotton lint", "raw cotton fiber"]
    regions = Column(JSON)  # Regions where this commodity is commonly traded
    is_active = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class CommodityPrice(Base):
    """
    Historical and current commodity prices from various sources.
    """
    __tablename__ = "commodity_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_code = Column(String(50), nullable=False, index=True)
    
    # Price data
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")  # ISO currency code
    unit = Column(String(50), nullable=False)  # kg, mt, bbl
    
    # Source information
    source = Column(String(100), nullable=False)  # world_bank, fred, lme, custom
    source_reference = Column(String(200))  # Original source identifier
    
    # Timing
    price_date = Column(TIMESTAMP, nullable=False, index=True)  # Date the price is for
    fetched_at = Column(TIMESTAMP, server_default=func.now())  # When we fetched it
    
    # Quality indicators
    is_spot = Column(Boolean, default=True)  # Spot vs futures
    contract_month = Column(String(10))  # For futures: "2024-03"
    quality_grade = Column(String(50))  # e.g., "A Index", "Grade A"
    
    # Metadata
    metadata = Column(JSON)  # Additional source-specific data


class PriceVerification(Base):
    """
    Price verification requests and results.
    """
    __tablename__ = "price_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request details
    commodity_code = Column(String(50), nullable=False)
    commodity_name = Column(String(200))  # As extracted/entered
    
    # Document price (what user is verifying)
    document_price = Column(Float, nullable=False)
    document_currency = Column(String(3), default="USD")
    document_unit = Column(String(50), nullable=False)
    document_quantity = Column(Float)
    total_value = Column(Float)
    
    # Normalized price (converted to standard unit/currency for comparison)
    normalized_price = Column(Float)
    normalized_unit = Column(String(50))
    
    # Market comparison
    market_price = Column(Float)
    market_price_low = Column(Float)
    market_price_high = Column(Float)
    market_source = Column(String(100))
    market_date = Column(TIMESTAMP)
    
    # Variance calculation
    variance_percent = Column(Float)  # (doc_price - market_price) / market_price * 100
    variance_absolute = Column(Float)
    
    # Risk assessment
    risk_level = Column(String(20))  # low, medium, high, critical
    risk_flags = Column(JSON)  # ["over_invoicing", "unusual_quantity"]
    
    # Verdict
    verdict = Column(String(20))  # pass, warning, fail
    verdict_reason = Column(Text)
    
    # Context
    document_type = Column(String(50))  # invoice, lc, contract
    document_reference = Column(String(200))  # Invoice number, LC number
    origin_country = Column(String(3))  # ISO country code
    destination_country = Column(String(3))
    
    # Source
    source_type = Column(String(20), default="manual")  # manual, document, api
    extracted_data = Column(JSON)  # If from document, what was extracted
    
    # User/Session
    session_id = Column(String(100))
    user_id = Column(UUID(as_uuid=True))
    company_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Export
    exported_pdf = Column(Boolean, default=False)
    exported_at = Column(TIMESTAMP)

