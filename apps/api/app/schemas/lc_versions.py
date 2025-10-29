"""
Pydantic schemas for LC version control.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.lc_versions import LCVersionStatus


class LCVersionBase(BaseModel):
    """Base LC version schema."""
    lc_number: str = Field(..., min_length=1, max_length=100)
    status: LCVersionStatus = LCVersionStatus.DRAFT
    file_metadata: Optional[Dict[str, Any]] = None


class LCVersionCreate(LCVersionBase):
    """Schema for creating a new LC version."""
    validation_session_id: UUID
    uploaded_by: UUID

    class Config:
        json_encoders = {
            UUID: str
        }


class LCVersionRead(LCVersionBase):
    """Schema for reading LC version data."""
    id: UUID
    version: int
    validation_session_id: UUID
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class LCVersionUpdate(BaseModel):
    """Schema for updating LC version."""
    status: Optional[LCVersionStatus] = None
    file_metadata: Optional[Dict[str, Any]] = None


class LCVersionSummary(BaseModel):
    """Summary schema for LC version listing."""
    id: UUID
    lc_number: str
    version: int
    status: LCVersionStatus
    uploaded_by: UUID
    created_at: datetime
    total_files: int
    total_size: int

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class LCVersionsList(BaseModel):
    """Schema for listing all versions of an LC."""
    lc_number: str
    versions: List[LCVersionRead]
    total_versions: int
    latest_version: int


class DiscrepancyChange(BaseModel):
    """Schema for discrepancy changes in version comparison."""
    id: Optional[str] = None
    title: str
    description: str
    severity: str
    rule_name: Optional[str] = None
    field_name: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None


class VersionChanges(BaseModel):
    """Schema for changes between versions."""
    added_discrepancies: List[DiscrepancyChange] = []
    removed_discrepancies: List[DiscrepancyChange] = []
    modified_discrepancies: List[DiscrepancyChange] = []
    status_change: Optional[Dict[str, str]] = None


class ComparisonSummary(BaseModel):
    """Schema for version comparison summary."""
    total_changes: int
    improvement_score: float = Field(..., ge=-1.0, le=1.0)


class LCVersionComparison(BaseModel):
    """Schema for comparing two LC versions."""
    lc_number: str
    from_version: str
    to_version: str
    changes: VersionChanges
    summary: ComparisonSummary


class AmendedLCInfo(BaseModel):
    """Schema for amended LC information."""
    lc_number: str
    versions: int
    latest_version: str
    last_updated: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class LCExistsResponse(BaseModel):
    """Schema for LC existence check response."""
    exists: bool
    next_version: str
    current_versions: int
    latest_version_id: Optional[UUID] = None

    class Config:
        json_encoders = {
            UUID: str
        }