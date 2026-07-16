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


class TradeCaseDetailResponse(TradeCaseSummaryResponse):
    customer_user_id: Optional[UUID] = None
    owner_user_id: Optional[UUID] = None
    payment_terms: Optional[str] = None
    shipment_date: Optional[date] = None
    expected_payment_date: Optional[date] = None
    transaction_details: dict[str, Any] = Field(default_factory=dict)
    source_lcopilot_session_id: Optional[UUID] = None
    final_report_id: Optional[UUID] = None


class TradeCaseListResponse(BaseModel):
    items: list[TradeCaseSummaryResponse]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0, le=100)


__all__ = [
    "TradeCaseCreate",
    "TradeCaseDetailResponse",
    "TradeCaseListResponse",
    "TradeCaseSummaryResponse",
    "TradeCaseUpdate",
]

