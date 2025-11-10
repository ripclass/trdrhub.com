"""
Bank policy overlay models for per-bank stricter checks and exceptions.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class BankPolicyOverlay(Base):
    """Per-bank policy overlay with stricter validation rules."""
    __tablename__ = "bank_policy_overlays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Versioning
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=False, index=True)
    
    # Policy configuration (JSONB)
    # Example structure:
    # {
    #   "stricter_checks": {
    #     "max_date_slippage_days": 0,  # Stricter than default
    #     "mandatory_documents": ["commercial_invoice", "bill_of_lading"],
    #     "require_expiry_date": true,
    #     "min_amount_threshold": 1000
    #   },
    #   "thresholds": {
    #     "discrepancy_severity_override": "critical",  # Treat minor as critical
    #     "auto_reject_on": ["amount_mismatch", "date_mismatch"]
    #   }
    # }
    config = Column(JSONB, nullable=False, default=dict)
    
    # Metadata
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    published_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bank = relationship("Company", foreign_keys=[bank_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    published_by = relationship("User", foreign_keys=[published_by_id])
    exceptions = relationship("BankPolicyException", back_populates="overlay", cascade="all, delete-orphan")
    application_events = relationship("BankPolicyApplicationEvent", back_populates="overlay", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_bank_policy_overlays_bank_active', 'bank_id', 'active'),
    )


class BankPolicyException(Base):
    """Exceptions to policy rules for specific scopes (client/branch/product)."""
    __tablename__ = "bank_policy_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    overlay_id = Column(UUID(as_uuid=True), ForeignKey("bank_policy_overlays.id", ondelete="CASCADE"), nullable=True)
    
    # Exception details
    rule_code = Column(String(100), nullable=False, index=True)  # e.g., "UCP600_ARTICLE_14_B"
    scope = Column(JSONB, nullable=False, default=dict)  # {"client": "ABC Corp", "branch": "NYC", "product": "LC"}
    reason = Column(Text, nullable=False)  # Justification for exception
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Auto-expire after date
    
    # Effect: what happens when this exception applies
    # "waive" - rule failure is waived
    # "downgrade" - severity reduced (e.g., critical -> minor)
    # "override" - rule result is overridden
    effect = Column(String(20), nullable=False, default="waive")  # waive, downgrade, override
    
    # Metadata
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bank = relationship("Company", foreign_keys=[bank_id])
    overlay = relationship("BankPolicyOverlay", back_populates="exceptions")
    created_by = relationship("User", foreign_keys=[created_by_id])
    application_events = relationship("BankPolicyApplicationEvent", back_populates="exception", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_bank_policy_exceptions_bank_rule', 'bank_id', 'rule_code'),
        Index('ix_bank_policy_exceptions_expires', 'bank_id', 'expires_at'),
    )


class BankPolicyApplicationEvent(Base):
    """
    Immutable audit log for policy overlay and exception applications during validation.
    
    Tracks when policies are applied, their impact, and effectiveness metrics.
    """
    __tablename__ = "bank_policy_application_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session and context
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False, index=True)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Policy references
    overlay_id = Column(UUID(as_uuid=True), ForeignKey("bank_policy_overlays.id", ondelete="SET NULL"), nullable=True, index=True)
    overlay_version = Column(Integer, nullable=True)
    exception_id = Column(UUID(as_uuid=True), ForeignKey("bank_policy_exceptions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Application details
    application_type = Column(String(20), nullable=False)  # "overlay", "exception", "both"
    rule_code = Column(String(100), nullable=True, index=True)  # Rule affected (for exceptions)
    exception_effect = Column(String(20), nullable=True)  # "waive", "downgrade", "override"
    
    # Impact metrics (before/after policy application)
    discrepancies_before = Column(Integer, nullable=False, default=0)  # Count before policy
    discrepancies_after = Column(Integer, nullable=False, default=0)  # Count after policy
    severity_changes = Column(JSONB, nullable=True)  # {"critical": -2, "major": +1, "minor": -1}
    
    # Result details
    result_summary = Column(JSONB, nullable=True)  # Summary of changes made
    # Example: {
    #   "rules_affected": ["UCP600_ARTICLE_14_B", "UCP600_ARTICLE_20"],
    #   "severity_upgrades": 2,
    #   "severity_downgrades": 1,
    #   "waived_rules": 1,
    #   "overridden_rules": 0
    # }
    
    # Metadata
    document_type = Column(String(50), nullable=True)
    processing_time_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    validation_session = relationship("ValidationSession")
    bank = relationship("Company", foreign_keys=[bank_id])
    user = relationship("User")
    overlay = relationship("BankPolicyOverlay", back_populates="application_events")
    exception = relationship("BankPolicyException", back_populates="application_events")
    
    __table_args__ = (
        Index('ix_policy_app_bank_created', 'bank_id', 'created_at'),
        Index('ix_policy_app_overlay_created', 'overlay_id', 'created_at'),
        Index('ix_policy_app_exception_created', 'exception_id', 'created_at'),
        Index('ix_policy_app_session', 'validation_session_id'),
    )
