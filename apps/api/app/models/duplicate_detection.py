"""
Duplicate Detection Models
Stores fingerprints, similarity scores, and merge history for LC duplicate detection
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MergeType(str, Enum):
    """Types of LC merges"""
    DUPLICATE = "duplicate"
    AMENDMENT = "amendment"
    CORRECTION = "correction"
    MANUAL = "manual"


class DetectionMethod(str, Enum):
    """Methods used to detect duplicates"""
    FINGERPRINT = "fingerprint"
    MANUAL = "manual"
    RULE_BASED = "rule_based"


class LCFingerprint(Base):
    """Content fingerprint for LC duplicate detection"""
    __tablename__ = "lc_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="CASCADE"), nullable=False)
    lc_number = Column(String(100), nullable=False, index=True)
    client_name = Column(String(255), nullable=True, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Content fingerprint - hash of normalized LC data
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    fingerprint_data = Column(JSONB, nullable=False)  # Normalized LC data for comparison
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    validation_session = relationship("ValidationSession", foreign_keys=[validation_session_id])
    company = relationship("Company", foreign_keys=[company_id])
    
    # Similarities where this fingerprint is involved
    similarities_as_1 = relationship(
        "LCSimilarity",
        foreign_keys="LCSimilarity.fingerprint_id_1",
        back_populates="fingerprint_1"
    )
    similarities_as_2 = relationship(
        "LCSimilarity",
        foreign_keys="LCSimilarity.fingerprint_id_2",
        back_populates="fingerprint_2"
    )
    
    __table_args__ = (
        UniqueConstraint('validation_session_id', name='uq_lc_fingerprints_session'),
        Index('idx_lc_fingerprints_content_hash', 'content_hash'),
        Index('idx_lc_fingerprints_lc_client', 'lc_number', 'client_name'),
        Index('idx_lc_fingerprints_company_created', 'company_id', 'created_at'),
    )


class LCSimilarity(Base):
    """Similarity scores between LC pairs"""
    __tablename__ = "lc_similarities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint_id_1 = Column(UUID(as_uuid=True), ForeignKey("lc_fingerprints.id", ondelete="CASCADE"), nullable=False)
    fingerprint_id_2 = Column(UUID(as_uuid=True), ForeignKey("lc_fingerprints.id", ondelete="CASCADE"), nullable=False)
    session_id_1 = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="CASCADE"), nullable=False)
    session_id_2 = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Similarity metrics (0.0 to 1.0)
    similarity_score = Column(Float, nullable=False)  # Overall similarity
    content_similarity = Column(Float, nullable=True)  # Text content similarity
    metadata_similarity = Column(Float, nullable=True)  # Metadata fields similarity
    field_matches = Column(JSONB, nullable=True)  # Which fields matched and their scores
    
    # Detection metadata
    detection_method = Column(String(50), nullable=False, default=DetectionMethod.FINGERPRINT.value)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detected_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    fingerprint_1 = relationship("LCFingerprint", foreign_keys=[fingerprint_id_1], back_populates="similarities_as_1")
    fingerprint_2 = relationship("LCFingerprint", foreign_keys=[fingerprint_id_2], back_populates="similarities_as_2")
    session_1 = relationship("ValidationSession", foreign_keys=[session_id_1])
    session_2 = relationship("ValidationSession", foreign_keys=[session_id_2])
    detected_by_user = relationship("User", foreign_keys=[detected_by])
    
    __table_args__ = (
        CheckConstraint('fingerprint_id_1 < fingerprint_id_2', name='chk_similarity_order'),
        UniqueConstraint('fingerprint_id_1', 'fingerprint_id_2', name='uq_lc_similarities_pair'),
        Index('idx_lc_similarities_score', 'similarity_score'),
        Index('idx_lc_similarities_session_1', 'session_id_1'),
        Index('idx_lc_similarities_session_2', 'session_id_2'),
        Index('idx_lc_similarities_detected', 'detected_at'),
    )


class LCMergeHistory(Base):
    """History of LC merges"""
    __tablename__ = "lc_merge_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="CASCADE"), nullable=False)
    target_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Merge metadata
    merge_type = Column(String(50), nullable=False)  # MergeType enum value
    merge_reason = Column(Text(), nullable=True)
    merged_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    merged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Merge details
    fields_merged = Column(JSONB, nullable=True)  # Which fields were merged
    preserved_data = Column(JSONB, nullable=True)  # Data preserved from source session
    
    # Relationships
    source_session = relationship("ValidationSession", foreign_keys=[source_session_id])
    target_session = relationship("ValidationSession", foreign_keys=[target_session_id])
    merged_by_user = relationship("User", foreign_keys=[merged_by])
    
    __table_args__ = (
        Index('idx_lc_merge_source', 'source_session_id'),
        Index('idx_lc_merge_target', 'target_session_id'),
        Index('idx_lc_merge_merged_at', 'merged_at'),
        Index('idx_lc_merge_type', 'merge_type'),
    )

