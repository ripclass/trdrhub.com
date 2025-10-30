"""
Pydantic schemas for billing API endpoints.

These schemas define the request/response models for billing operations
including invoices, usage records, payments, and company billing settings.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator, condecimal

from app.models.invoice import InvoiceStatus
from app.models.company import PlanType
from app.core.pricing import PricingConstants

Money = condecimal(max_digits=18, decimal_places=2)


# Base schemas
class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


# Company billing schemas
class CompanyBillingInfo(BaseModel):
    """Company billing information."""
    id: UUID
    name: str
    plan: PlanType
    quota_limit: Optional[int] = None
    quota_used: int = 0
    quota_remaining: Optional[int] = None
    billing_email: Optional[str] = None
    payment_customer_id: Optional[str] = None

    class Config:
        orm_mode = True


class CompanyBillingUpdate(BaseModel):
    """Update company billing settings."""
    plan: Optional[PlanType] = None
    quota_limit: Optional[int] = None
    billing_email: Optional[str] = None


class UsageStats(BaseModel):
    """Company usage statistics."""
    company_id: UUID
    current_month: int = 0
    current_week: int = 0
    today: int = 0
    total_usage: int = 0
    total_cost: Money = Field(default=Decimal("0"))
    quota_limit: Optional[int] = None
    quota_used: int = 0
    quota_remaining: Optional[int] = None


# Usage record schemas
class UsageRecordBase(BaseModel):
    """Base usage record schema."""
    action: str
    cost: Money
    session_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class UsageRecordCreate(UsageRecordBase):
    """Create usage record request."""
    pass


class UsageRecord(UsageRecordBase, TimestampMixin):
    """Usage record response."""
    id: UUID
    company_id: UUID
    user_id: Optional[UUID] = None

    class Config:
        orm_mode = True


class UsageRecordList(BaseModel):
    """Paginated list of usage records."""
    records: List[UsageRecord]
    total: int
    page: int
    per_page: int
    pages: int


# Invoice schemas
class InvoiceLineItemBase(BaseModel):
    """Base invoice line item schema."""
    description: str
    quantity: int = 1
    unit_price: Money
    amount: Money


class InvoiceLineItem(InvoiceLineItemBase):
    """Invoice line item response."""
    id: UUID

    class Config:
        orm_mode = True


class InvoiceBase(BaseModel):
    """Base invoice schema."""
    amount: Money
    currency: str = "BDT"
    due_date: date
    description: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Create invoice request."""
    line_items: List[InvoiceLineItemBase] = []

    @validator('line_items')
    def validate_line_items(cls, v):
        if not v:
            raise ValueError("Invoice must have at least one line item")
        return v


class Invoice(InvoiceBase, TimestampMixin):
    """Invoice response."""
    id: UUID
    company_id: UUID
    invoice_number: str
    status: InvoiceStatus
    issued_date: date
    paid_date: Optional[date] = None
    payment_intent_id: Optional[str] = None
    payment_method: Optional[str] = None
    line_items: List[InvoiceLineItem] = []

    class Config:
        orm_mode = True


class InvoiceList(BaseModel):
    """Paginated list of invoices."""
    invoices: List[Invoice]
    total: int
    page: int
    per_page: int
    pages: int


class InvoiceUpdate(BaseModel):
    """Update invoice request."""
    status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


# Payment schemas
class PaymentIntentCreate(BaseModel):
    """Create payment intent request."""
    invoice_id: Optional[UUID] = None
    amount: Optional[Money] = None
    currency: str = "BDT"
    payment_method_types: Optional[List[str]] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None

    @validator('currency')
    def validate_currency(cls, v):
        supported = ["BDT", "USD"]
        if v.upper() not in supported:
            raise ValueError(f"Currency must be one of: {', '.join(supported)}")
        return v.upper()


class PaymentIntent(BaseModel):
    """Payment intent response."""
    id: str
    amount: Money
    currency: str
    status: str
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None
    payment_method_types: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


class PaymentResult(BaseModel):
    """Payment result response."""
    success: bool
    payment_id: str
    transaction_id: Optional[str] = None
    status: str
    amount: Money
    currency: str
    payment_method: Optional[str] = None
    error_message: Optional[str] = None


class RefundCreate(BaseModel):
    """Create refund request."""
    amount: Optional[Money] = None
    reason: Optional[str] = None


class RefundResult(BaseModel):
    """Refund result response."""
    success: bool
    refund_id: str
    original_payment_id: str
    amount: Money
    status: str
    error_message: Optional[str] = None


# Webhook schemas
class WebhookEvent(BaseModel):
    """Webhook event response."""
    event_id: str
    event_type: str
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Money] = None
    currency: Optional[str] = None
    timestamp: datetime
    is_verified: bool = False


# Pricing and quota schemas
class PricingInfo(BaseModel):
    """Current pricing information."""
    per_check: Decimal = PricingConstants.PER_CHECK
    import_draft: Decimal = PricingConstants.IMPORT_DRAFT
    import_bundle: Decimal = PricingConstants.IMPORT_BUNDLE
    currency: str = "BDT"

    class Config:
        use_enum_values = True


class QuotaCheck(BaseModel):
    """Quota check request."""
    action: str
    quantity: int = 1


class QuotaCheckResult(BaseModel):
    """Quota check result."""
    allowed: bool
    remaining: Optional[int] = None
    limit: Optional[int] = None
    message: Optional[str] = None


# Admin schemas (for admin endpoints)
class AdminCompanyStats(BaseModel):
    """Admin view of company statistics."""
    company_id: UUID
    company_name: str
    plan: PlanType
    total_usage: int
    total_cost: Money
    quota_limit: Optional[int] = None
    quota_used: int = 0
    last_activity: Optional[datetime] = None
    status: str  # active, suspended, etc.


class AdminUsageReport(BaseModel):
    """Admin usage report."""
    period_start: date
    period_end: date
    total_companies: int
    total_usage: int
    total_revenue: Money
    companies: List[AdminCompanyStats]


# Error schemas
class ErrorDetail(BaseModel):
    """Error detail schema."""
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationError(BaseModel):
    """Validation error schema."""
    field: str
    message: str
    value: Any


class HTTPError(BaseModel):
    """HTTP error response schema."""
    detail: str
    errors: Optional[List[ValidationError]] = None
