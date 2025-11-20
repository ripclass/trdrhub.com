from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class RuleAudit(Base):
    """Audit records for normalized rule mutations."""

    __tablename__ = "rules_audit"

    id = Column(UUID(as_uuid=True), primary_key=True)
    rule_id = Column(String(255), nullable=True, index=True)
    ruleset_id = Column(UUID(as_uuid=True), ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    detail = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

