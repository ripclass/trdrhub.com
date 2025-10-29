"""
Schema definitions for integration APIs with typed DTOs.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.integrations import IntegrationType, IntegrationStatus, BillingEventType


# Base DTOs
class IntegrationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    type: IntegrationType
    description: Optional[str] = None
    logo_url: Optional[str] = None
    base_url: str = Field(..., regex=r'^https?://')
    sandbox_url: Optional[str] = Field(None, regex=r'^https?://')
    documentation_url: Optional[str] = Field(None, regex=r'^https?://')
    supported_countries: Optional[List[str]] = None
    supported_currencies: Optional[List[str]] = None
    api_version: str = Field(default='v1', max_length=50)
    requires_mtls: bool = False
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)

    @validator('supported_currencies')
    def validate_currencies(cls, v):
        if v:
            valid_currencies = ['USD', 'EUR', 'GBP', 'BDT', 'AED', 'SAR', 'INR']
            for currency in v:
                if currency not in valid_currencies:
                    raise ValueError(f'Unsupported currency: {currency}')
        return v


class IntegrationCreate(IntegrationBase):
    config_schema: Optional[Dict[str, Any]] = None
    webhook_url: Optional[str] = Field(None, regex=r'^https?://')
    webhook_secret: Optional[str] = None


class IntegrationUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[IntegrationStatus] = None
    logo_url: Optional[str] = None
    documentation_url: Optional[str] = Field(None, regex=r'^https?://')
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)


class IntegrationResponse(IntegrationBase):
    id: UUID
    status: IntegrationStatus
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID

    class Config:
        from_attributes = True


# Company Integration DTOs
class CompanyIntegrationBase(BaseModel):
    is_enabled: bool = True
    billing_tier: str = Field(default='standard', max_length=50)
    price_per_check: Optional[Decimal] = Field(None, ge=0)
    monthly_quota: Optional[int] = Field(None, ge=0)


class CompanyIntegrationCreate(CompanyIntegrationBase):
    integration_id: UUID
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None


class CompanyIntegrationUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None
    billing_tier: Optional[str] = Field(None, max_length=50)
    price_per_check: Optional[Decimal] = Field(None, ge=0)
    monthly_quota: Optional[int] = Field(None, ge=0)


class CompanyIntegrationResponse(CompanyIntegrationBase):
    id: UUID
    company_id: UUID
    integration_id: UUID
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Related data
    integration: IntegrationResponse

    class Config:
        from_attributes = True


# Submission DTOs
class SubmissionBase(BaseModel):
    submission_type: str = Field(..., min_length=1, max_length=50)
    request_payload: Dict[str, Any]
    idempotency_key: str = Field(..., min_length=1, max_length=255)


class BankSubmissionRequest(SubmissionBase):
    """Bank-specific submission for LC validation/recheck."""
    lc_number: str = Field(..., min_length=1, max_length=100)
    swift_format: str = Field(default='MT700', regex=r'^MT(700|707|720|750)$')
    priority: str = Field(default='normal', regex=r'^(low|normal|high|urgent)$')
    callback_url: Optional[str] = Field(None, regex=r'^https?://')


class CustomsSubmissionRequest(SubmissionBase):
    """Customs-specific submission for trade document validation."""
    country_code: str = Field(..., regex=r'^[A-Z]{2}$')
    customs_office: Optional[str] = None
    declaration_type: str = Field(..., regex=r'^(import|export|transit)$')
    commodity_codes: List[str] = Field(..., min_items=1)


class LogisticsSubmissionRequest(SubmissionBase):
    """Logistics-specific submission for shipping/tracking."""
    service_type: str = Field(..., regex=r'^(tracking|pickup|delivery|quote)$')
    tracking_number: Optional[str] = None
    origin_country: str = Field(..., regex=r'^[A-Z]{2}$')
    destination_country: str = Field(..., regex=r'^[A-Z]{2}$')
    shipment_value: Optional[Decimal] = Field(None, ge=0)


class SubmissionResponse(BaseModel):
    id: UUID
    session_id: UUID
    integration_id: UUID
    submission_type: str
    external_reference_id: Optional[str]
    idempotency_key: str
    status_code: Optional[int]
    error_message: Optional[str]
    retry_count: int
    billing_recorded: bool
    submitted_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Billing DTOs
class BillingEventResponse(BaseModel):
    id: UUID
    submission_id: UUID
    company_id: UUID
    integration_id: UUID
    user_id: UUID
    event_type: BillingEventType
    charged_amount: Decimal
    currency: str
    billing_tier: str
    metadata: Optional[Dict[str, Any]]
    recorded_at: datetime

    class Config:
        from_attributes = True


# Health Check DTOs
class HealthCheckResponse(BaseModel):
    integration_id: UUID
    endpoint: str
    status_code: Optional[int]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    is_healthy: bool
    checked_at: datetime

    class Config:
        from_attributes = True


# Authentication DTOs
class ApiKeyAuth(BaseModel):
    api_key: str = Field(..., min_length=1)


class OAuth2Auth(BaseModel):
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    scope: Optional[str] = None
    token_url: str = Field(..., regex=r'^https?://')


class MTLSAuth(BaseModel):
    client_cert_path: str
    client_key_path: str
    ca_cert_path: Optional[str] = None


# ISO20022/SWIFT Message DTOs
class SwiftMT700(BaseModel):
    """SWIFT MT700 Letter of Credit message format."""
    sender_bic: str = Field(..., regex=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    receiver_bic: str = Field(..., regex=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    lc_number: str = Field(..., max_length=16)
    issue_date: datetime
    expiry_date: datetime
    applicant: Dict[str, str]  # name, address, country
    beneficiary: Dict[str, str]  # name, address, country
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., regex=r'^[A-Z]{3}$')
    description_of_goods: str = Field(..., max_length=65000)
    documents_required: List[str]
    latest_shipment_date: Optional[datetime] = None
    partial_shipments: bool = False
    transhipment: bool = False


class SwiftMT707(BaseModel):
    """SWIFT MT707 Amendment to Documentary Credit."""
    sender_bic: str = Field(..., regex=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    receiver_bic: str = Field(..., regex=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    lc_number: str = Field(..., max_length=16)
    amendment_number: str = Field(..., max_length=3)
    amendment_date: datetime
    amendments: List[Dict[str, Any]]


class ISO20022PaymentMessage(BaseModel):
    """ISO20022 payment message structure."""
    message_id: str = Field(..., max_length=35)
    creation_date_time: datetime
    number_of_transactions: int = Field(..., ge=1)
    control_sum: Optional[Decimal] = None
    initiating_party: Dict[str, str]
    payment_information: List[Dict[str, Any]]


# Webhook DTOs
class WebhookEvent(BaseModel):
    event_type: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1)
    timestamp: datetime
    data: Dict[str, Any]
    signature: Optional[str] = None


class WebhookResponse(BaseModel):
    received: bool = True
    processed: bool = True
    error_message: Optional[str] = None


# Integration Registry DTOs
class IntegrationRegistryEntry(BaseModel):
    integration: IntegrationResponse
    company_config: Optional[CompanyIntegrationResponse] = None
    health_status: Optional[HealthCheckResponse] = None
    billing_summary: Optional[Dict[str, Any]] = None


class IntegrationMarketplace(BaseModel):
    """Marketplace view of available integrations."""
    banks: List[IntegrationRegistryEntry]
    customs: List[IntegrationRegistryEntry]
    logistics: List[IntegrationRegistryEntry]
    fx_providers: List[IntegrationRegistryEntry]
    insurance: List[IntegrationRegistryEntry]


# Error DTOs
class IntegrationError(BaseModel):
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # seconds
    support_reference: Optional[str] = None


class ValidationError(BaseModel):
    field: str
    message: str
    invalid_value: Optional[str] = None


# Batch Operation DTOs
class BatchSubmissionRequest(BaseModel):
    submissions: List[SubmissionBase] = Field(..., min_items=1, max_items=100)
    batch_id: str = Field(..., min_length=1, max_length=255)


class BatchSubmissionResponse(BaseModel):
    batch_id: str
    total_count: int
    successful_count: int
    failed_count: int
    submissions: List[SubmissionResponse]
    processing_time_ms: int