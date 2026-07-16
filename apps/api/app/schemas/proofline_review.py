"""Typed analyst requests for Proofline."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import ProoflineDecisionValue, ProoflineFindingStatus


class AnalystClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force: bool = False


class AnalystNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(min_length=1, max_length=10000)


class AnalystFindingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Optional[str] = Field(default=None, pattern="^(critical|high|medium|low|info)$")
    status: Optional[ProoflineFindingStatus] = None
    visibility: Optional[str] = Field(default=None, pattern="^(customer|internal)$")
    reviewer_decision: Optional[str] = Field(default=None, max_length=64)
    explanation: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    suggested_correction: Optional[str] = Field(default=None, min_length=1, max_length=10000)


class AnalystFindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=2, max_length=96)
    severity: str = Field(pattern="^(critical|high|medium|low|info)$")
    title: str = Field(min_length=2, max_length=255)
    explanation: str = Field(min_length=2, max_length=10000)
    expected: str = Field(min_length=1, max_length=10000)
    observed: str = Field(min_length=1, max_length=10000)
    suggested_correction: str = Field(min_length=1, max_length=10000)
    visibility: str = Field(default="customer", pattern="^(customer|internal)$")


class AnalystCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    requested_action: str = Field(min_length=2, max_length=10000)
    responsible_party: Optional[str] = Field(default=None, max_length=128)
    requested_document_type: Optional[str] = Field(default=None, max_length=64)
    due_at: Optional[datetime] = None


class AnalystDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: ProoflineDecisionValue
    summary: str = Field(min_length=2, max_length=10000)
    reason: str = Field(min_length=2, max_length=10000)
    override_reason: Optional[str] = Field(default=None, max_length=10000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class BuyerRequirementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_id: UUID
    buyer_reference: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=2, max_length=10000)
    applicable_party_type: Optional[str] = Field(default=None, max_length=64)
    product_scope: dict[str, Any] = Field(default_factory=dict)
    jurisdiction: Optional[str] = Field(default=None, max_length=64)
    required_document_type: Optional[str] = Field(default=None, max_length=64)
    required_credential_type: Optional[str] = Field(default=None, max_length=128)
    approved_issuer_type: Optional[str] = Field(default=None, max_length=128)
    validity_period_days: Optional[int] = Field(default=None, gt=0)
    severity: str = Field(default="medium", pattern="^(critical|high|medium|low|info)$")
    effective_date: date
    version: int = Field(default=1, gt=0)
    is_active: bool = True
    rulhub_mapping: Optional[dict[str, Any]] = None


class BuyerRequirementActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class BuyerRequirementResponse(BuyerRequirementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "AnalystClaimRequest",
    "AnalystCorrectionRequest",
    "AnalystDecisionRequest",
    "AnalystFindingCreate",
    "AnalystFindingUpdate",
    "AnalystNoteRequest",
    "BuyerRequirementActivationRequest",
    "BuyerRequirementCreate",
    "BuyerRequirementResponse",
]
