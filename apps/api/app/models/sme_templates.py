"""
SME Templates Models
LC and document templates with pre-fill capabilities
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class TemplateType(str, Enum):
    """Types of templates."""
    LC = "lc"
    DOCUMENT = "document"


class DocumentType(str, Enum):
    """Types of document templates."""
    COMMERCIAL_INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"
    PACKING_LIST = "packing_list"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    INSPECTION_CERTIFICATE = "inspection_certificate"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    OTHER = "other"


class SMETemplate(Base):
    """LC and document templates for SME users."""

    __tablename__ = "sme_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Template identification
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(TemplateType), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=True)  # For document templates
    description = Column(Text, nullable=True)

    # Template fields (JSONB for flexible field structure)
    fields = Column(JSONB, nullable=False, default=dict)

    # Flags
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company", backref="templates")
    user = relationship("User", backref="templates")

