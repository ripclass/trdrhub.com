"""
Admin Console Database Models

This module contains SQLAlchemy models for the Admin Console functionality,
including RBAC, audit trails, job management, billing, partners, and compliance.
"""

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, Date, Numeric,
    ForeignKey, UniqueConstraint, Enum as SQLEnum, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum
import uuid
from datetime import datetime, timedelta

from app.database import Base


# Enum definitions
class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class AdjustmentType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    WRITE_OFF = "write_off"
    PROMOTIONAL = "promotional"


class AdjustmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class CreditType(str, enum.Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    FREE_TIER_UPGRADE = "free_tier_upgrade"


class DisputeType(str, enum.Enum):
    CHARGEBACK = "chargeback"
    INQUIRY = "inquiry"
    QUALITY_DISPUTE = "quality_dispute"
    BILLING_ERROR = "billing_error"


class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class PartnerType(str, enum.Enum):
    BANK = "bank"
    CUSTOMS = "customs"
    LOGISTICS = "logistics"
    PAYMENT = "payment"
    DATA_PROVIDER = "data_provider"


class EnvironmentType(str, enum.Enum):
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"


class PartnerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class ConnectorStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    ABANDONED = "abandoned"


class ServiceAccountType(str, enum.Enum):
    INTERNAL = "internal"
    PARTNER = "partner"
    WEBHOOK = "webhook"
    BACKUP = "backup"


class DataRegion(str, enum.Enum):
    BD = "BD"
    EU = "EU"
    SG = "SG"
    US = "US"
    GLOBAL = "GLOBAL"


class LegalHoldStatus(str, enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


class PromptLanguage(str, enum.Enum):
    EN = "en"
    BN = "bn"
    AR = "ar"
    ZH = "zh"


class BudgetPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class FlagType(str, enum.Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class ReleaseType(str, enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    HOTFIX = "hotfix"


# Admin Core Models
class AdminRole(Base):
    """Admin roles with fine-grained permissions"""
    __tablename__ = "admin_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    permissions = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    admin_users = relationship("AdminUser", back_populates="role")


class AdminUser(Base):
    """Admin user assignments to roles"""
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("admin_roles.id"), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    role = relationship("AdminRole", back_populates="admin_users")


class AuditEvent(Base):
    """Global audit log for compliance and debugging"""
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_type = Column(String(50), nullable=False, default="user")
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    action = Column(String(100), nullable=False)
    changes = Column(JSONB)
    event_metadata = Column(JSONB, default=dict)
    ip_address = Column(INET)
    user_agent = Column(Text)
    session_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=func.now())


class Approval(Base):
    """4-eyes approval system for sensitive operations"""
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    requested_changes = Column(JSONB, nullable=False)
    approval_reason = Column(Text)
    rejection_reason = Column(Text)
    auto_expires_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class BreakGlassEvent(Base):
    """Emergency access events with auto-expiry"""
    __tablename__ = "break_glass_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    granted_permissions = Column(JSONB, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())


# Job Management Models
class JobQueue(Base):
    """Job queue with priority and retry logic"""
    __tablename__ = "jobs_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False)
    job_data = Column(JSONB, nullable=False)
    priority = Column(Integer, default=5)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    scheduled_at = Column(DateTime(timezone=True), default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    error_stack = Column(Text)
    worker_id = Column(String(255))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    lc_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class JobDLQ(Base):
    """Dead letter queue for failed jobs"""
    __tablename__ = "jobs_dlq"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_job_id = Column(UUID(as_uuid=True), nullable=False)
    job_type = Column(String(100), nullable=False)
    job_data = Column(JSONB, nullable=False)
    failure_reason = Column(Text, nullable=False)
    failure_count = Column(Integer, nullable=False)
    last_error = Column(Text)
    quarantine_reason = Column(Text)
    can_retry = Column(Boolean, default=True)
    retry_after = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())


class JobHistory(Base):
    """Job execution history for analytics"""
    __tablename__ = "jobs_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False)
    duration_ms = Column(Integer)
    memory_mb = Column(Integer)
    cpu_percent = Column(Numeric(5, 2))
    step_name = Column(String(100))
    step_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())


class SystemAlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SystemAlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


class SystemAlert(Base):
    """Operational/system alert surfaced in admin dashboard."""
    __tablename__ = "system_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=False, default="system")
    category = Column(String(50), nullable=True)
    severity = Column(SQLEnum(SystemAlertSeverity), nullable=False, default=SystemAlertSeverity.MEDIUM)
    status = Column(SQLEnum(SystemAlertStatus), nullable=False, default=SystemAlertStatus.ACTIVE)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)
    auto_generated = Column(Boolean, nullable=False, default=False)
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    acknowledged_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_user = relationship("User", foreign_keys=[resolved_by])


# Billing & Finance Models
class BillingAdjustment(Base):
    """Billing adjustments, credits, and write-offs"""
    __tablename__ = "billing_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    type = Column(SQLEnum(AdjustmentType), nullable=False)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=False)
    reference_invoice_id = Column(UUID(as_uuid=True))
    applied_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(SQLEnum(AdjustmentStatus), default=AdjustmentStatus.PENDING)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    approved_at = Column(DateTime(timezone=True))


class Credit(Base):
    """Credits and promotional codes"""
    __tablename__ = "credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    type = Column(SQLEnum(CreditType), nullable=False)
    value_usd = Column(Numeric(12, 2))
    percentage = Column(Integer)
    min_spend_usd = Column(Numeric(12, 2))
    max_uses = Column(Integer)
    uses_count = Column(Integer, default=0)
    valid_from = Column(DateTime(timezone=True), default=func.now())
    valid_until = Column(DateTime(timezone=True))
    applicable_plans = Column(ARRAY(Text))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())


class Dispute(Base):
    """Chargebacks and billing disputes"""
    __tablename__ = "disputes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    type = Column(SQLEnum(DisputeType), nullable=False)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=False)
    evidence_url = Column(Text)
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.OPEN)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    resolved_at = Column(DateTime(timezone=True))


# Partner & Integration Models
class PartnerRegistry(Base):
    """Partner API registry with health monitoring"""
    __tablename__ = "partner_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    type = Column(SQLEnum(PartnerType), nullable=False)
    environment = Column(SQLEnum(EnvironmentType), default=EnvironmentType.SANDBOX)
    status = Column(SQLEnum(PartnerStatus), default=PartnerStatus.ACTIVE)
    api_endpoint = Column(Text)
    auth_config = Column(JSONB, nullable=False, default=dict)
    rate_limits = Column(JSONB, default=dict)
    sla_config = Column(JSONB, default=dict)
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    technical_contact = Column(JSONB)
    business_contact = Column(JSONB)
    onboarded_at = Column(DateTime(timezone=True))
    last_health_check = Column(DateTime(timezone=True))
    health_status = Column(String(20), default="unknown")
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    connectors = relationship("PartnerConnector", back_populates="partner")
    webhook_deliveries = relationship("PartnerWebhookDelivery", back_populates="partner")


class PartnerConnector(Base):
    """Partner connector health and versioning"""
    __tablename__ = "partner_connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_registry.id"), nullable=False)
    connector_type = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    health_endpoint = Column(Text)
    last_success_at = Column(DateTime(timezone=True))
    last_failure_at = Column(DateTime(timezone=True))
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    avg_response_time_ms = Column(Integer)
    uptime_percentage = Column(Numeric(5, 2))
    status = Column(SQLEnum(ConnectorStatus), default=ConnectorStatus.UNKNOWN)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    partner = relationship("PartnerRegistry", back_populates="connectors")


class PartnerWebhookDelivery(Base):
    """Partner webhook delivery tracking with retry logic"""
    __tablename__ = "partner_webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_registry.id"), nullable=False)
    webhook_url = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB, default=dict)
    http_status = Column(Integer)
    response_body = Column(Text)
    delivery_time_ms = Column(Integer)
    attempts = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING)
    next_retry_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    partner = relationship("PartnerRegistry", back_populates="webhook_deliveries")


class WebhookDLQ(Base):
    """Webhook dead letter queue"""
    __tablename__ = "webhook_dlq"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_delivery_id = Column(UUID(as_uuid=True), ForeignKey("partner_webhook_deliveries.id"), nullable=False)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_registry.id"), nullable=False)
    webhook_url = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    failure_reason = Column(Text, nullable=False)
    failure_count = Column(Integer, nullable=False)
    can_replay = Column(Boolean, default=True)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())


# Security & Access Models
class APIKey(Base):
    """API key management with scopes and rotation"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(20), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scopes = Column(ARRAY(Text), nullable=False, default=list)
    rate_limit = Column(Integer, default=1000)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    last_used_ip = Column(INET)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class ServiceAccount(Base):
    """Service accounts for system integrations"""
    __tablename__ = "service_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(SQLEnum(ServiceAccountType), default=ServiceAccountType.INTERNAL)
    permissions = Column(JSONB, nullable=False, default=list)
    ip_allowlist = Column(ARRAY(Text))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_rotation_at = Column(DateTime(timezone=True))
    next_rotation_due = Column(DateTime(timezone=True))
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())


class IPAllowlist(Base):
    """IP allowlists for enhanced security"""
    __tablename__ = "ip_allowlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    ip_ranges = Column(JSONB, nullable=False)  # Array of CIDR blocks
    is_global = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class UserSession(Base):
    """User session tracking for security"""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_token_hash = Column(String(255), nullable=False, unique=True)
    device_info = Column(JSONB, default=dict)
    ip_address = Column(INET, nullable=False)
    user_agent = Column(Text)
    location = Column(JSONB)  # Country, city from IP
    is_active = Column(Boolean, default=True)
    last_activity_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


# Compliance & Data Models
class DataResidencyPolicy(Base):
    """Data residency policies for compliance"""
    __tablename__ = "data_residency_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    region = Column(SQLEnum(DataRegion), nullable=False)
    data_types = Column(ARRAY(Text), nullable=False)
    storage_location = Column(String(100), nullable=False)
    encryption_key_id = Column(String(255))
    compliance_frameworks = Column(ARRAY(Text))
    policy_document_url = Column(Text)
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())


class RetentionPolicy(Base):
    """Data retention policies"""
    __tablename__ = "retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    data_type = Column(String(100), nullable=False)
    retention_period_days = Column(Integer, nullable=False)
    archive_after_days = Column(Integer)
    delete_after_days = Column(Integer)
    legal_basis = Column(Text)
    applies_to_regions = Column(ARRAY(SQLEnum(DataRegion)))
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())


class LegalHold(Base):
    """Legal holds for litigation support"""
    __tablename__ = "legal_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(100), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    data_types = Column(ARRAY(Text), nullable=False)
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    custodian_users = Column(ARRAY(UUID))
    search_terms = Column(ARRAY(Text))
    status = Column(SQLEnum(LegalHoldStatus), default=LegalHoldStatus.ACTIVE)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    legal_contact = Column(JSONB)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    closed_at = Column(DateTime(timezone=True))


# LLM Ops Models
class LLMPrompt(Base):
    """LLM prompt library with versioning"""
    __tablename__ = "llm_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    version = Column(String(20), nullable=False)
    prompt_type = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_template = Column(Text, nullable=False)
    language = Column(SQLEnum(PromptLanguage), default=PromptLanguage.EN)
    model_constraints = Column(JSONB, default=dict)
    safety_filters = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    test_results = Column(JSONB)
    performance_metrics = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (UniqueConstraint('name', 'version'),)


class LLMEvalRun(Base):
    """LLM evaluation runs for quality assurance"""
    __tablename__ = "llm_eval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("llm_prompts.id"), nullable=False)
    eval_set_name = Column(String(200), nullable=False)
    model_name = Column(String(100), nullable=False)
    test_cases_count = Column(Integer, nullable=False)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    avg_latency_ms = Column(Integer)
    avg_tokens_used = Column(Integer)
    cost_usd = Column(Numeric(10, 4))
    quality_score = Column(Numeric(3, 2))
    safety_score = Column(Numeric(3, 2))
    detailed_results = Column(JSONB)
    run_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


class LLMBudget(Base):
    """LLM usage budgets and cost control"""
    __tablename__ = "llm_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    model_name = Column(String(100), nullable=False)
    budget_period = Column(SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY)
    budget_usd = Column(Numeric(10, 2), nullable=False)
    used_usd = Column(Numeric(10, 2), default=0)
    token_budget = Column(Integer)
    tokens_used = Column(Integer, default=0)
    alert_threshold_percent = Column(Integer, default=80)
    hard_limit_enabled = Column(Boolean, default=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())


# Feature Flags & Release Models
class FeatureFlag(Base):
    """Feature flags for controlled rollouts"""
    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    type = Column(SQLEnum(FlagType), default=FlagType.BOOLEAN)
    default_value = Column(JSONB, default=False)
    is_active = Column(Boolean, default=True)
    rollout_percentage = Column(Integer, default=0)
    targeting_rules = Column(JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class FlagEvaluation(Base):
    """Feature flag evaluation logs for analytics"""
    __tablename__ = "flag_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flag_id = Column(UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    evaluation_context = Column(JSONB, default=dict)
    result_value = Column(JSONB, nullable=False)
    evaluation_reason = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now())


class ReleaseNote(Base):
    """Release notes and changelog management"""
    __tablename__ = "release_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    release_type = Column(SQLEnum(ReleaseType), default=ReleaseType.MINOR)
    features = Column(JSONB, default=list)
    bug_fixes = Column(JSONB, default=list)
    breaking_changes = Column(JSONB, default=list)
    migration_notes = Column(Text)
    rollout_strategy = Column(JSONB, default=dict)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    published_at = Column(DateTime(timezone=True))
    is_published = Column(Boolean, default=False)
    event_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=func.now())