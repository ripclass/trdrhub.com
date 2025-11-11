"""
Saved Views models for bank dashboard filters and views.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SavedView(Base):
    """Saved filter/view configuration for bank dashboard resources."""
    __tablename__ = "saved_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    resource = Column(String(50), nullable=False, index=True)  # 'results', 'jobs', 'evidence'
    query_params = Column(JSONB, nullable=False)  # Filter parameters as JSON
    columns = Column(JSONB, nullable=True)  # Visible columns configuration
    is_org_default = Column(Boolean, nullable=False, default=False)
    shared = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    owner = relationship("User", foreign_keys=[owner_id])

    # Indexes
    __table_args__ = (
        Index('ix_saved_views_company_resource', 'company_id', 'resource'),
        Index('ix_saved_views_org_default', 'company_id', 'resource', 'is_org_default'),
    )

