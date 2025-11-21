from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class RuleRecord(Base):
    """
    Normalized rule definition stored in the `rules` governance table.

    This is the primary source of truth for rules. The legacy `Rule` / `rules_registry`
    table has been deprecated and is no longer used.
    """

    __tablename__ = "rules"

    rule_id = Column(String, primary_key=True)
    rule_version = Column(String(50), nullable=True)
    article = Column(String(50), nullable=True)
    version = Column(String(50), nullable=True)

    domain = Column(String(50), nullable=False)
    jurisdiction = Column(String(50), nullable=False, server_default="global")
    document_type = Column(String(50), nullable=False)
    rule_type = Column(String(50), nullable=False, server_default="deterministic")

    severity = Column(String(20), nullable=False, server_default="fail")
    deterministic = Column(Boolean, nullable=False, server_default=text("true"))
    requires_llm = Column(Boolean, nullable=False, server_default=text("false"))

    title = Column(String(255), nullable=False)
    reference = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    conditions = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    expected_outcome = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    tags = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    rule_metadata = Column(JSONB, name="metadata", nullable=True, server_default=text("'{}'::jsonb"))

    checksum = Column(String(32), nullable=False)

    ruleset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rulesets.id", ondelete="SET NULL"),
        nullable=True,
    )
    ruleset_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    archived_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


Index("ix_rules_rule_id", RuleRecord.rule_id, unique=True)
Index("ix_rules_ruleset_id", RuleRecord.ruleset_id)
Index(
    "ix_rules_domain_document_type",
    RuleRecord.domain,
    RuleRecord.document_type,
)

