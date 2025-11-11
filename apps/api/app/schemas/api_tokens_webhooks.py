"""
Pydantic schemas for API tokens and webhooks
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class APITokenBase(BaseModel):
    """Base API token schema"""
    name: str
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1)


class APITokenCreate(APITokenBase):
    """Schema for creating an API token"""
    pass


class APITokenRead(APITokenBase):
    """Schema for reading an API token (masked)"""
    id: UUID
    company_id: UUID
    created_by: UUID
    token_prefix: str  # Only show prefix, never full token
    is_active: bool
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    usage_count: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    revoke_reason: Optional[str] = None

    class Config:
        from_attributes = True


class APITokenCreateResponse(BaseModel):
    """Response when creating a token (includes full token once)"""
    token: str  # Full token - only shown once!
    token_id: UUID
    token_prefix: str
    expires_at: Optional[datetime] = None
    warning: str = "Store this token securely. You won't be able to see it again."


class APITokenUpdate(BaseModel):
    """Schema for updating an API token"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None


class APITokenRevokeRequest(BaseModel):
    """Request to revoke an API token"""
    reason: Optional[str] = None


class APITokenListResponse(BaseModel):
    """Response for listing API tokens"""
    tokens: List[APITokenRead]
    total: int


# Webhook Schemas
class WebhookSubscriptionBase(BaseModel):
    """Base webhook subscription schema"""
    name: str
    description: Optional[str] = None
    url: str  # HttpUrl validation
    events: List[str] = Field(default_factory=list)
    timeout_seconds: int = Field(30, ge=1, le=300)
    retry_count: int = Field(3, ge=0, le=10)
    retry_backoff_multiplier: float = Field(2.0, ge=1.0, le=10.0)
    headers: Optional[Dict[str, str]] = None


class WebhookSubscriptionCreate(WebhookSubscriptionBase):
    """Schema for creating a webhook subscription"""
    pass


class WebhookSubscriptionRead(WebhookSubscriptionBase):
    """Schema for reading a webhook subscription"""
    id: UUID
    company_id: UUID
    created_by: UUID
    is_active: bool
    success_count: int
    failure_count: int
    last_delivery_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Note: secret is never returned in read operations

    class Config:
        from_attributes = True


class WebhookSubscriptionCreateResponse(BaseModel):
    """Response when creating a webhook subscription"""
    subscription: WebhookSubscriptionRead
    secret: str  # Secret shown once for signing
    warning: str = "Store this secret securely. You won't be able to see it again."


class WebhookSubscriptionUpdate(BaseModel):
    """Schema for updating a webhook subscription"""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    headers: Optional[Dict[str, str]] = None


class WebhookSubscriptionListResponse(BaseModel):
    """Response for listing webhook subscriptions"""
    subscriptions: List[WebhookSubscriptionRead]
    total: int


class WebhookDeliveryRead(BaseModel):
    """Schema for reading a webhook delivery"""
    id: UUID
    subscription_id: UUID
    company_id: UUID
    event_type: str
    event_id: Optional[str] = None
    status: str
    attempt_number: int
    max_attempts: int
    http_status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    next_retry_at: Optional[datetime] = None
    retry_reason: Optional[str] = None

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    """Response for listing webhook deliveries"""
    deliveries: List[WebhookDeliveryRead]
    total: int


class WebhookTestRequest(BaseModel):
    """Request to test a webhook"""
    payload: Optional[Dict[str, Any]] = None  # Custom test payload, or use default


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook"""
    delivery_id: UUID
    status: str
    http_status_code: Optional[int] = None
    response_body: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class WebhookReplayRequest(BaseModel):
    """Request to replay a failed webhook delivery"""
    delivery_id: UUID


class WebhookReplayResponse(BaseModel):
    """Response from replaying a webhook"""
    new_delivery_id: UUID
    status: str

