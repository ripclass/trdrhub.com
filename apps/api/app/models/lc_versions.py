"""
SQLAlchemy models for LC version control.
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class LCVersionStatus(str, Enum):
    """LC version status."""
    DRAFT = "draft"
    VALIDATED = "validated"
    PACKAGED = "packaged"


class LCVersion(Base):
    """LC version tracking model for amendments and revisions."""
    __tablename__ = "lc_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_number = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), nullable=False, default=LCVersionStatus.DRAFT.value)

    # File metadata as JSONB for flexibility
    file_metadata = Column(JSONB, nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('lc_number', 'version', name='_lc_number_version_uc'),
        Index('idx_lc_versions_lc_number', 'lc_number'),
        Index('idx_lc_versions_created_at', 'created_at'),
        Index('idx_lc_versions_status', 'status'),
    )

    # Relationships
    validation_session = relationship("ValidationSession", back_populates="lc_version")
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<LCVersion(lc_number='{self.lc_number}', version={self.version}, status='{self.status}')>"