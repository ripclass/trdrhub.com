"""
Pydantic schemas for duplicate detection
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class LCFingerprintBase(BaseModel):
    """Base fingerprint schema"""
    lc_number: str
    client_name: Optional[str] = None
    content_hash: str
    fingerprint_data: Dict[str, Any]


class LCFingerprintCreate(LCFingerprintBase):
    """Schema for creating a fingerprint"""
    validation_session_id: UUID
    company_id: Optional[UUID] = None


class LCFingerprintRead(LCFingerprintBase):
    """Schema for reading a fingerprint"""
    id: UUID
    validation_session_id: UUID
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LCSimilarityBase(BaseModel):
    """Base similarity schema"""
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    content_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    field_matches: Optional[Dict[str, Any]] = None
    detection_method: str = "fingerprint"


class LCSimilarityCreate(LCSimilarityBase):
    """Schema for creating a similarity record"""
    fingerprint_id_1: UUID
    fingerprint_id_2: UUID
    session_id_1: UUID
    session_id_2: UUID
    detected_by: Optional[UUID] = None


class LCSimilarityRead(LCSimilarityBase):
    """Schema for reading a similarity record"""
    id: UUID
    fingerprint_id_1: UUID
    fingerprint_id_2: UUID
    session_id_1: UUID
    session_id_2: UUID
    detected_at: datetime
    detected_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class LCMergeHistoryBase(BaseModel):
    """Base merge history schema"""
    merge_type: str
    merge_reason: Optional[str] = None
    fields_merged: Optional[Dict[str, Any]] = None
    preserved_data: Optional[Dict[str, Any]] = None


class LCMergeHistoryCreate(LCMergeHistoryBase):
    """Schema for creating a merge history record"""
    source_session_id: UUID
    target_session_id: UUID
    merged_by: UUID


class LCMergeHistoryRead(LCMergeHistoryBase):
    """Schema for reading a merge history record"""
    id: UUID
    source_session_id: UUID
    target_session_id: UUID
    merged_by: UUID
    merged_at: datetime

    class Config:
        from_attributes = True


# Response schemas for API endpoints
class DuplicateCandidate(BaseModel):
    """A duplicate candidate with similarity details"""
    session_id: UUID
    lc_number: str
    client_name: Optional[str]
    similarity_score: float
    content_similarity: Optional[float]
    metadata_similarity: Optional[float]
    field_matches: Optional[Dict[str, Any]]
    detected_at: datetime
    completed_at: Optional[datetime]


class DuplicateCandidatesResponse(BaseModel):
    """Response for duplicate candidates endpoint"""
    session_id: UUID
    candidates: List[DuplicateCandidate]
    total_count: int


class MergeRequest(BaseModel):
    """Request to merge two sessions"""
    source_session_id: UUID
    target_session_id: UUID
    merge_type: str = "duplicate"
    merge_reason: Optional[str] = None
    fields_to_merge: Optional[List[str]] = None  # If None, merge all


class MergeResponse(BaseModel):
    """Response after merging sessions"""
    merge_id: UUID
    source_session_id: UUID
    target_session_id: UUID
    merge_type: str
    merged_at: datetime
    fields_merged: Optional[Dict[str, Any]] = None


class MergeHistoryResponse(BaseModel):
    """Response for merge history endpoint"""
    merges: List[LCMergeHistoryRead]
    total_count: int

