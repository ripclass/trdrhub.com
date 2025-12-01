"""
Audit Log SQLAlchemy Models

Models for compliance-grade audit logging of Price Verification actions.
Every verification is logged with full context for regulatory compliance.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.sql import func

from app.database import Base


class PriceVerifyAuditLog(Base):
    """
    Immutable audit log entry for Price Verification actions.
    
    Designed for compliance with financial regulations requiring
    complete audit trails of price verification activities.
    """
    __tablename__ = "price_verify_audit_logs"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Action type
    action = Column(String(50), nullable=False)  # price_verify_single, price_verify_batch, etc.
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    
    # Who
    user_id = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    company_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # What
    resource_type = Column(String(50), nullable=False)  # verification, extraction, report
    resource_id = Column(String(255), nullable=True)
    
    # Input/Output (JSONB for flexibility)
    request_data = Column(JSONB, nullable=True)
    response_summary = Column(JSONB, nullable=True)
    
    # Results
    verdict = Column(String(20), nullable=True)  # pass, warning, fail
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical
    
    # Source Attribution
    data_sources = Column(JSONB, nullable=True)  # Array of sources used
    
    # Context
    session_id = Column(String(255), nullable=True)
    request_id = Column(String(255), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Indexes defined in Alembic migration

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, severity={self.severity}, timestamp={self.timestamp})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "severity": self.severity,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "company_id": self.company_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "verdict": self.verdict,
            "risk_level": self.risk_level,
            "duration_ms": self.duration_ms,
            "request_id": self.request_id,
        }

