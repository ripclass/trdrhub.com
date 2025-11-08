"""
Ruleset models for managing trade rules (ICC, country regulations, etc.)
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class RulesetStatus(str, Enum):
    """Ruleset status types."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SCHEDULED = "scheduled"


class RulesetAuditAction(str, Enum):
    """Ruleset audit action types."""
    UPLOAD = "upload"
    VALIDATE = "validate"
    PUBLISH = "publish"
    ROLLBACK = "rollback"
    ARCHIVE = "archive"


class Ruleset(Base):
    """Ruleset model for storing rule metadata and file references."""
    __tablename__ = "rulesets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(50), nullable=False, index=True)  # icc, incoterms, vat, sanctions, aml, customs, shipping
    jurisdiction = Column(String(50), nullable=False, server_default="global", index=True)  # global, eu, us, bd, in, etc.
    ruleset_version = Column(String(50), nullable=False)  # Semantic version like "1.0.0"
    rulebook_version = Column(String(50), nullable=False)  # e.g., "UCP600:2007"
    file_path = Column(String(500), nullable=False)  # Path in Supabase Storage
    status = Column(
        String(20),
        nullable=False,
        server_default=RulesetStatus.DRAFT.value,
        index=True
    )
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    checksum_md5 = Column(String(32), nullable=False)  # MD5 hash of normalized JSON
    rule_count = Column(Integer, nullable=False, server_default="0")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    publisher = relationship("User", foreign_keys=[published_by])
    audit_logs = relationship("RulesetAudit", back_populates="ruleset", cascade="all, delete-orphan")

    __table_args__ = (
        # Partial unique index: one active per (domain, jurisdiction)
        # This is enforced at the database level via migration
        CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'scheduled')",
            name="ck_rulesets_status"
        ),
    )


class RulesetAudit(Base):
    """Audit log for ruleset operations."""
    __tablename__ = "ruleset_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruleset_id = Column(UUID(as_uuid=True), ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(
        String(20),
        nullable=False,
        index=True
    )
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    detail = Column(JSONB, nullable=True)  # Additional context (validation errors, diff, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    ruleset = relationship("Ruleset", back_populates="audit_logs")
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        CheckConstraint(
            "action IN ('upload', 'validate', 'publish', 'rollback', 'archive')",
            name="ck_ruleset_audit_action"
        ),
    )

