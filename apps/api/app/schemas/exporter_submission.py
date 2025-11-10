"""
Pydantic schemas for exporter submissions and customs packs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.exporter_submission import SubmissionStatus, SubmissionEventType


class CustomsPackManifest(BaseModel):
    """Manifest structure for customs pack."""
    lc_number: str
    validation_session_id: str
    generated_at: str
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    generator_version: str = "1.0"


class CustomsPackGenerateRequest(BaseModel):
    """Request to generate customs pack."""
    validation_session_id: UUID
    lc_number: Optional[str] = None


class CustomsPackGenerateResponse(BaseModel):
    """Response for customs pack generation."""
    download_url: str
    file_name: str
    manifest: CustomsPackManifest
    sha256: str
    generated_at: datetime

    class Config:
        from_attributes = True


class BankSubmissionCreate(BaseModel):
    """Request to create bank submission."""
    validation_session_id: UUID
    lc_number: str
    bank_id: Optional[UUID] = None
    bank_name: Optional[str] = None
    note: Optional[str] = None
    idempotency_key: Optional[str] = None


class BankSubmissionRead(BaseModel):
    """Response for bank submission."""
    id: UUID
    company_id: UUID
    user_id: UUID
    validation_session_id: UUID
    lc_number: str
    bank_id: Optional[UUID] = None
    bank_name: Optional[str] = None
    status: SubmissionStatus
    manifest_hash: Optional[str] = None
    note: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    result_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankSubmissionListResponse(BaseModel):
    """Response for listing bank submissions."""
    items: List[BankSubmissionRead]
    total: int


class SubmissionEventRead(BaseModel):
    """Response for submission event."""
    id: UUID
    submission_id: UUID
    event_type: SubmissionEventType
    payload: Optional[Dict[str, Any]] = None
    actor_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionEventListResponse(BaseModel):
    """Response for listing submission events."""
    items: List[SubmissionEventRead]
    total: int


class GuardrailCheckRequest(BaseModel):
    """Request to check guardrails before submission."""
    validation_session_id: UUID
    lc_number: Optional[str] = None


class GuardrailCheckResponse(BaseModel):
    """Response for guardrail check."""
    can_submit: bool
    blocking_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    required_docs_present: bool
    high_severity_discrepancies: int
    policy_checks_passed: bool

