"""
Admin Console Pydantic Schemas

This module contains Pydantic models for request/response validation
and serialization for the Admin Console API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import uuid

from app.models.admin import (
    ApprovalStatus, JobStatus, AdjustmentType, AdjustmentStatus,
    CreditType, DisputeType, DisputeStatus, PartnerType, EnvironmentType,
    PartnerStatus, ConnectorStatus, DeliveryStatus, ServiceAccountType,
    DataRegion, LegalHoldStatus, PromptLanguage, BudgetPeriod,
    FlagType, ReleaseType
)


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


# Admin Core Schemas
class AdminRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class AdminRoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class AdminRole(BaseSchema, TimestampMixin):
    id: uuid.UUID
    name: str
    description: Optional[str]
    permissions: List[str]


class AdminUserCreate(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    expires_at: Optional[datetime] = None


class AdminUser(BaseSchema, TimestampMixin):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    granted_by: Optional[uuid.UUID]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    role: Optional[AdminRole] = None


# Audit Schemas
class AuditEventFilter(BaseModel):
    actor_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    ip_address: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class AuditEvent(BaseSchema):
    id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID]
    actor_type: str
    resource_type: str
    resource_id: Optional[str]
    organization_id: Optional[uuid.UUID]
    action: str
    changes: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    created_at: datetime


class AuditExportRequest(BaseModel):
    filters: AuditEventFilter
    format: str = Field("csv", pattern="^(csv|json|pdf)$")
    include_pii: bool = False
    legal_hold_id: Optional[str] = None


# Approval Schemas
class ApprovalRequest(BaseModel):
    request_type: str = Field(..., min_length=1, max_length=100)
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: str = Field(..., min_length=1, max_length=255)
    requested_changes: Dict[str, Any]
    justification: str = Field(..., min_length=1)
    urgency: str = Field("normal", pattern="^(low|normal|high|urgent)$")


class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str = Field(..., min_length=1)
    conditions: Optional[Dict[str, Any]] = None


class Approval(BaseSchema, TimestampMixin):
    id: uuid.UUID
    request_type: str
    resource_type: str
    resource_id: str
    requester_id: uuid.UUID
    approver_id: Optional[uuid.UUID]
    status: ApprovalStatus
    requested_changes: Dict[str, Any]
    approval_reason: Optional[str]
    rejection_reason: Optional[str]
    auto_expires_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]


# Break Glass Schemas
class BreakGlassRequest(BaseModel):
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: str = Field(..., min_length=1, max_length=255)
    permissions: List[str] = Field(..., min_items=1)
    reason: str = Field(..., min_length=10)
    duration_hours: int = Field(4, ge=1, le=24)
    emergency_contact: str = Field(..., min_length=1)


class BreakGlassRevocation(BaseModel):
    reason: str = Field(..., min_length=1)
    immediate: bool = False


class BreakGlassEvent(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    reason: str
    resource_type: str
    resource_id: str
    granted_permissions: List[str]
    approved_by: Optional[uuid.UUID]
    expires_at: datetime
    revoked_at: Optional[datetime]
    revoked_by: Optional[uuid.UUID]
    created_at: datetime


# Job Management Schemas
class JobFilter(BaseModel):
    status: Optional[JobStatus] = None
    job_type: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    created_after: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class JobQueue(BaseSchema, TimestampMixin):
    id: uuid.UUID
    job_type: str
    job_data: Dict[str, Any]
    priority: int
    status: JobStatus
    attempts: int
    max_attempts: int
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    error_message: Optional[str]
    worker_id: Optional[str]
    organization_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    lc_id: Optional[str]


class BulkJobAction(BaseModel):
    job_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., pattern="^(retry|cancel|requeue)$")
    reason: str = Field(..., min_length=1)


class DLQReplayRequest(BaseModel):
    retry_count: int = Field(1, ge=1, le=5)
    delay_seconds: int = Field(0, ge=0, le=3600)
    modify_payload: Optional[Dict[str, Any]] = None


class BulkDLQReplay(BaseModel):
    dlq_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100)
    strategy: str = Field(..., pattern="^(immediate|scheduled|throttled)$")
    throttle_rate: Optional[int] = Field(None, ge=1, le=1000)


class JobDLQ(BaseSchema):
    id: uuid.UUID
    original_job_id: uuid.UUID
    job_type: str
    job_data: Dict[str, Any]
    failure_reason: str
    failure_count: int
    last_error: Optional[str]
    quarantine_reason: Optional[str]
    can_retry: bool
    retry_after: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[uuid.UUID]
    created_at: datetime


# KPI and Metrics Schemas
class KPIResponse(BaseModel):
    uptime_percentage: float = Field(..., ge=0, le=100)
    avg_response_time_ms: int = Field(..., ge=0)
    error_rate_percentage: float = Field(..., ge=0, le=100)
    active_users_24h: int = Field(..., ge=0)
    jobs_processed_24h: int = Field(..., ge=0)
    revenue_24h_usd: float = Field(..., ge=0)
    p95_latency_ms: int = Field(..., ge=0)
    p99_latency_ms: int = Field(..., ge=0)
    alerts_active: int = Field(..., ge=0)


class MetricsQuery(BaseModel):
    metric_names: List[str] = Field(..., min_items=1)
    time_range: str = Field("24h", pattern="^(1h|6h|24h|7d|30d)$")
    granularity: str = Field("1h", pattern="^(1m|5m|1h|1d)$")
    filters: Dict[str, Any] = Field(default_factory=dict)


class LogQuery(BaseModel):
    level: Optional[str] = Field(None, pattern="^(debug|info|warning|error|critical)$")
    service: Optional[str] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    query: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)


class LogExportRequest(BaseModel):
    query: LogQuery
    format: str = Field("json", pattern="^(json|csv|syslog)$")
    redact_pii: bool = True


class AlertRule(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    metric: str = Field(..., min_length=1)
    threshold: float
    operator: str = Field(..., pattern="^(gt|lt|eq|gte|lte)$")
    duration: str = Field("5m", pattern="^\\d+[smhd]$")
    severity: str = Field(..., pattern="^(critical|warning|info)$")
    channels: List[str] = Field(..., min_items=1)


class SilenceRequest(BaseModel):
    duration: str = Field(..., pattern="^\\d+[smhd]$")
    reason: str = Field(..., min_length=1)


# Billing Schemas
class BillingPlan(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str
    price_usd: float = Field(..., ge=0)
    billing_period: str = Field(..., pattern="^(monthly|annual)$")
    features: Dict[str, Any]
    quotas: Dict[str, int]
    is_active: bool = True


class PlanChangeRequest(BaseModel):
    new_plan_id: uuid.UUID
    effective_date: datetime
    proration_method: str = Field("immediate", pattern="^(immediate|next_cycle|custom)$")
    reason: str = Field(..., min_length=1)


class CreditCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, pattern="^[A-Z0-9_]+$")
    type: CreditType
    value_usd: Optional[float] = Field(None, ge=0)
    percentage: Optional[int] = Field(None, ge=1, le=100)
    max_uses: Optional[int] = Field(None, ge=1)
    valid_until: Optional[datetime] = None
    applicable_plans: List[str] = Field(default_factory=list)

    @validator('value_usd', 'percentage')
    def validate_credit_value(cls, v, values):
        credit_type = values.get('type')
        if credit_type == CreditType.FIXED_AMOUNT and not v:
            raise ValueError('value_usd required for fixed_amount credits')
        if credit_type == CreditType.PERCENTAGE and not values.get('percentage'):
            raise ValueError('percentage required for percentage credits')
        return v


class BillingAdjustmentCreate(BaseModel):
    organization_id: uuid.UUID
    type: AdjustmentType
    amount_usd: float = Field(..., ge=0)
    reason: str = Field(..., min_length=1)
    requires_approval: bool = True
    reference_invoice_id: Optional[uuid.UUID] = None


class BillingAdjustment(BaseSchema, TimestampMixin):
    id: uuid.UUID
    organization_id: uuid.UUID
    type: AdjustmentType
    amount_usd: float
    reason: str
    reference_invoice_id: Optional[uuid.UUID]
    applied_by: uuid.UUID
    approved_by: Optional[uuid.UUID]
    status: AdjustmentStatus
    metadata: Dict[str, Any]
    approved_at: Optional[datetime]


class DisputeAssignment(BaseModel):
    assigned_to: uuid.UUID
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    notes: str = Field(..., min_length=1)


class DisputeResolution(BaseModel):
    resolution: str = Field(..., pattern="^(resolved|escalated|invalid)$")
    amount_refunded: Optional[float] = Field(None, ge=0)
    notes: str = Field(..., min_length=1)
    evidence_url: Optional[str] = None


class Dispute(BaseSchema, TimestampMixin):
    id: uuid.UUID
    invoice_id: uuid.UUID
    organization_id: uuid.UUID
    type: DisputeType
    amount_usd: float
    reason: str
    evidence_url: Optional[str]
    status: DisputeStatus
    assigned_to: Optional[uuid.UUID]
    resolved_by: Optional[uuid.UUID]
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]


# Partner Schemas
class PartnerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: PartnerType
    environment: EnvironmentType = EnvironmentType.SANDBOX
    api_endpoint: str = Field(..., min_length=1)
    auth_config: Dict[str, Any]
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    contact_email: str = Field(..., pattern="^[^@]+@[^@]+\\.[^@]+$")
    contact_phone: Optional[str] = None
    technical_contact: Optional[Dict[str, Any]] = None
    business_contact: Optional[Dict[str, Any]] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[PartnerStatus] = None
    api_endpoint: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, int]] = None
    contact_email: Optional[str] = Field(None, pattern="^[^@]+@[^@]+\\.[^@]+$")
    contact_phone: Optional[str] = None


class Partner(BaseSchema, TimestampMixin):
    id: uuid.UUID
    name: str
    type: PartnerType
    environment: EnvironmentType
    status: PartnerStatus
    api_endpoint: Optional[str]
    auth_config: Dict[str, Any]
    rate_limits: Dict[str, int]
    sla_config: Dict[str, Any]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    technical_contact: Optional[Dict[str, Any]]
    business_contact: Optional[Dict[str, Any]]
    onboarded_at: Optional[datetime]
    last_health_check: Optional[datetime]
    health_status: str
    metadata: Dict[str, Any]


class PartnerMetrics(BaseModel):
    uptime_24h: float = Field(..., ge=0, le=100)
    avg_response_time: int = Field(..., ge=0)
    error_rate: float = Field(..., ge=0, le=100)
    total_requests: int = Field(..., ge=0)


class WebhookFilter(BaseModel):
    partner_id: Optional[uuid.UUID] = None
    status: Optional[DeliveryStatus] = None
    event_type: Optional[str] = None
    failed_only: bool = False
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class WebhookReplay(BaseModel):
    dlq_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100)
    modify_headers: Optional[Dict[str, str]] = None
    test_mode: bool = False


class WebhookDelivery(BaseSchema):
    id: uuid.UUID
    partner_id: uuid.UUID
    webhook_url: str
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    http_status: Optional[int]
    response_body: Optional[str]
    delivery_time_ms: Optional[int]
    attempts: int
    max_attempts: int
    status: DeliveryStatus
    next_retry_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_at: datetime


# Security Schemas
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    organization_id: uuid.UUID
    scopes: List[str] = Field(..., min_items=1)
    rate_limit: int = Field(1000, ge=1, le=10000)
    expires_at: Optional[datetime] = None
    ip_allowlist: List[str] = Field(default_factory=list)

    @validator('ip_allowlist')
    def validate_ip_ranges(cls, v):
        # TODO: Add CIDR validation
        return v


class APIKeyRotation(BaseModel):
    new_scopes: Optional[List[str]] = None
    new_rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    transition_period_hours: int = Field(24, ge=1, le=168)


class APIKey(BaseSchema, TimestampMixin):
    id: uuid.UUID
    name: str
    key_prefix: str
    organization_id: uuid.UUID
    created_by: uuid.UUID
    scopes: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    last_used_ip: Optional[str]
    is_active: bool
    usage_count: int


class SessionFilter(BaseModel):
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    active_only: bool = True
    suspicious_only: bool = False
    limit: int = Field(100, ge=1, le=500)


class BulkSessionRevocation(BaseModel):
    user_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100)
    reason: str = Field(..., min_length=1)
    force_reauth: bool = True


class UserSession(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    device_info: Dict[str, Any]
    ip_address: str
    user_agent: Optional[str]
    location: Optional[Dict[str, Any]]
    is_active: bool
    last_activity_at: datetime
    expires_at: datetime
    created_at: datetime


# Feature Flag Schemas
class FeatureFlagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, pattern="^[a-zA-Z0-9_-]+$")
    description: str = Field(..., min_length=1)
    type: FlagType = FlagType.BOOLEAN
    default_value: Union[bool, str, int, Dict[str, Any]] = False
    rollout_percentage: int = Field(0, ge=0, le=100)
    targeting_rules: Dict[str, Any] = Field(default_factory=dict)


class FeatureFlagUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    targeting_rules: Optional[Dict[str, Any]] = None


class FeatureFlag(BaseSchema, TimestampMixin):
    id: uuid.UUID
    name: str
    description: Optional[str]
    type: FlagType
    default_value: Union[bool, str, int, Dict[str, Any]]
    is_active: bool
    rollout_percentage: int
    targeting_rules: Dict[str, Any]
    created_by: uuid.UUID
    metadata: Dict[str, Any]


class FlagEvaluation(BaseSchema):
    id: uuid.UUID
    flag_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    organization_id: Optional[uuid.UUID]
    evaluation_context: Dict[str, Any]
    result_value: Union[bool, str, int, Dict[str, Any]]
    evaluation_reason: Optional[str]
    created_at: datetime


# LLM Ops Schemas
class LLMPromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=20)
    prompt_type: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = Field(..., min_length=1)
    user_template: str = Field(..., min_length=1)
    language: PromptLanguage = PromptLanguage.EN
    model_constraints: Dict[str, Any] = Field(default_factory=dict)
    safety_filters: Dict[str, Any] = Field(default_factory=dict)


class LLMPrompt(BaseSchema):
    id: uuid.UUID
    name: str
    version: str
    prompt_type: str
    system_prompt: str
    user_template: str
    language: PromptLanguage
    model_constraints: Dict[str, Any]
    safety_filters: Dict[str, Any]
    is_active: bool
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID]
    test_results: Optional[Dict[str, Any]]
    performance_metrics: Optional[Dict[str, Any]]
    created_at: datetime


class LLMBudgetCreate(BaseModel):
    organization_id: uuid.UUID
    model_name: str = Field(..., min_length=1, max_length=100)
    budget_period: BudgetPeriod = BudgetPeriod.MONTHLY
    budget_usd: float = Field(..., ge=0)
    token_budget: Optional[int] = Field(None, ge=0)
    alert_threshold_percent: int = Field(80, ge=1, le=100)
    hard_limit_enabled: bool = False
    period_start: date
    period_end: date


class LLMBudget(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    model_name: str
    budget_period: BudgetPeriod
    budget_usd: float
    used_usd: float
    token_budget: Optional[int]
    tokens_used: int
    alert_threshold_percent: int
    hard_limit_enabled: bool
    period_start: date
    period_end: date
    is_active: bool
    created_by: uuid.UUID
    metadata: Dict[str, Any]
    created_at: datetime


# Release Management Schemas
class ReleaseNoteCreate(BaseModel):
    version: str = Field(..., min_length=1, max_length=50, pattern="^\\d+\\.\\d+\\.\\d+")
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    release_type: ReleaseType = ReleaseType.MINOR
    features: List[Dict[str, str]] = Field(default_factory=list)
    bug_fixes: List[Dict[str, str]] = Field(default_factory=list)
    breaking_changes: List[Dict[str, str]] = Field(default_factory=list)
    migration_notes: Optional[str] = None
    rollout_strategy: Dict[str, Any] = Field(default_factory=dict)


class ReleaseNote(BaseSchema):
    id: uuid.UUID
    version: str
    title: str
    description: Optional[str]
    release_type: ReleaseType
    features: List[Dict[str, str]]
    bug_fixes: List[Dict[str, str]]
    breaking_changes: List[Dict[str, str]]
    migration_notes: Optional[str]
    rollout_strategy: Dict[str, Any]
    published_by: uuid.UUID
    published_at: Optional[datetime]
    is_published: bool
    metadata: Dict[str, Any]
    created_at: datetime


# Response schemas for pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        arbitrary_types_allowed = True


# Health check schema
class HealthCheck(BaseModel):
    status: str
    service: str
    version: str
    features: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)