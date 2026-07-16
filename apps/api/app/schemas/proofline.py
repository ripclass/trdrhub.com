"""Customer-safe Proofline request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.proofline import PaymentArrangement, ProoflineDecisionValue, TradeCaseStatus


class TradeCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    payment_arrangement: PaymentArrangement
    service_package_id: Optional[str] = Field(default=None, max_length=64)
    origin_country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    destination_country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    shipment_date: Optional[date] = None
    expected_payment_date: Optional[date] = None
    payment_terms: Optional[str] = Field(default=None, max_length=5000)
    transaction_details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("origin_country", "destination_country", "currency")
    @classmethod
    def uppercase_codes(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class TradeCaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    payment_arrangement: Optional[PaymentArrangement] = None
    service_package_id: Optional[str] = Field(default=None, max_length=64)
    origin_country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    destination_country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    shipment_date: Optional[date] = None
    expected_payment_date: Optional[date] = None
    payment_terms: Optional[str] = Field(default=None, max_length=5000)
    transaction_details: Optional[dict[str, Any]] = None

    @field_validator("origin_country", "destination_country", "currency")
    @classmethod
    def uppercase_codes(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class TradeCaseSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_reference: str
    company_id: UUID
    title: str
    status: TradeCaseStatus
    payment_arrangement: PaymentArrangement
    service_package_id: Optional[str] = None
    recommended_decision: Optional[ProoflineDecisionValue] = None
    final_decision: Optional[ProoflineDecisionValue] = None
    currency: Optional[str] = None
    amount: Optional[Decimal] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    document_count: int = 0
    finding_counts: dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TradeCasePartyResponse(BaseModel):
    id: UUID
    role: str
    name: str
    country_code: Optional[str] = None
    identifiers: dict[str, Any] = Field(default_factory=dict)


class TradeCasePartyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    identifiers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class ProoflineCheckResponse(BaseModel):
    id: UUID
    module: str
    state: str
    applicable: bool
    applicability_reason: str
    source_record_type: Optional[str] = None
    source_record_id: Optional[str] = None
    summary: Optional[str] = None
    completed_at: Optional[datetime] = None


class ProoflineFindingResponse(BaseModel):
    id: UUID
    source_module: str
    source_finding_id: Optional[str] = None
    category: str
    severity: str
    title: str
    explanation: str
    affected_entity: Optional[str] = None
    affected_document_id: Optional[UUID] = None
    affected_field: Optional[str] = None
    expected: str
    observed: str
    suggested_correction: str
    automated: bool
    visibility: str
    status: str
    reviewer_decision: Optional[str] = None
    rule_reference: Optional[dict[str, Any]] = None
    evidence_references: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProoflineRemediationResponse(BaseModel):
    id: UUID
    finding_id: UUID
    requested_action: str
    responsible_party: Optional[str] = None
    requested_document_type: Optional[str] = None
    due_at: Optional[datetime] = None
    customer_response: Optional[str] = None
    correction_document_id: Optional[UUID] = None
    status: str
    correction_round: int = Field(gt=0)


class ProoflineDecisionResponse(BaseModel):
    id: UUID
    version: int = Field(gt=0)
    decision: ProoflineDecisionValue
    decision_type: str
    summary: str
    reason: str
    reviewer_id: Optional[UUID] = None
    decided_at: datetime
    report_version: Optional[int] = None


class TradeCaseDetailResponse(TradeCaseSummaryResponse):
    customer_user_id: Optional[UUID] = None
    owner_user_id: Optional[UUID] = None
    payment_terms: Optional[str] = None
    shipment_date: Optional[date] = None
    expected_payment_date: Optional[date] = None
    transaction_details: dict[str, Any] = Field(default_factory=dict)
    source_lcopilot_session_id: Optional[UUID] = None
    final_report_id: Optional[UUID] = None
    parties: list[TradeCasePartyResponse] = Field(default_factory=list)
    documents: list["TradeCaseDocumentResponse"] = Field(default_factory=list)
    checks: list[ProoflineCheckResponse] = Field(default_factory=list)
    findings: list[ProoflineFindingResponse] = Field(default_factory=list)
    actions: list[ProoflineRemediationResponse] = Field(default_factory=list)
    decision_history: list[ProoflineDecisionResponse] = Field(default_factory=list)


class TradeCaseListResponse(BaseModel):
    items: list[TradeCaseSummaryResponse]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0, le=100)


class TradeCaseDocumentAssociate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    logical_key: str = Field(min_length=1, max_length=128)
    document_type: str = Field(min_length=1, max_length=64)
    content_hash: Optional[str] = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    supersedes_id: Optional[UUID] = None
    correction_round: int = Field(default=0, ge=0)


class TradeCaseDocumentResponse(BaseModel):
    id: UUID
    document_id: UUID
    logical_key: str
    document_type: str
    filename: str
    version: int = Field(gt=0)
    supersedes_id: Optional[UUID] = None
    correction_round: int = Field(ge=0)
    is_current: bool
    extraction_status: Optional[str] = None
    created_at: datetime


class RemediationResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: Optional[str] = Field(default=None, max_length=10000)
    correction_document_id: Optional[UUID] = None


__all__ = [
    "TradeCaseCreate",
    "TradeCaseDetailResponse",
    "TradeCaseDocumentAssociate",
    "TradeCaseDocumentResponse",
    "TradeCaseListResponse",
    "TradeCasePartyCreate",
    "TradeCasePartyResponse",
    "RemediationResponseRequest",
    "TradeCaseSummaryResponse",
    "TradeCaseUpdate",
]
