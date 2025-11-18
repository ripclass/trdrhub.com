"""
Integration models for partner API management.
"""

import uuid
import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship

from .base import Base


class IntegrationType(str, enum.Enum):
    BANK = "bank"
    CUSTOMS = "customs"
    LOGISTICS = "logistics"
    FX_PROVIDER = "fx_provider"
    INSURANCE = "insurance"


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class BillingEventType(str, enum.Enum):
    SME_VALIDATION = "sme_validation"
    BANK_RECHECK = "bank_recheck"
    CUSTOMS_SUBMISSION = "customs_submission"
    LOGISTICS_TRACKING = "logistics_tracking"
    FX_QUOTE = "fx_quote"
    INSURANCE_QUOTE = "insurance_quote"


class Integration(Base):
    """
    Master registry of available integrations.
    """
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    type = Column(ENUM(IntegrationType), nullable=False, index=True)
    status = Column(ENUM(IntegrationStatus), nullable=False, default=IntegrationStatus.ACTIVE, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)

    # API Configuration
    base_url = Column(String(500), nullable=False)
    sandbox_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    api_version = Column(String(50), nullable=False, default='v1')

    # Technical Configuration
    requires_mtls = Column(Boolean, nullable=False, default=False)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    retry_attempts = Column(Integer, nullable=False, default=3)

    # Capability Configuration
    supported_countries = Column(JSONB, nullable=True)  # ['BD', 'IN', 'AE']
    supported_currencies = Column(JSONB, nullable=True)  # ['USD', 'BDT', 'AED']
    config_schema = Column(JSONB, nullable=True)  # JSON schema for company config

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Relationships
    created_by = relationship("User")
    company_integrations = relationship("CompanyIntegration", back_populates="integration")
    submissions = relationship("IntegrationSubmission", back_populates="integration")
    health_checks = relationship("IntegrationHealthCheck", back_populates="integration")

    def __repr__(self):
        return f"<Integration(name='{self.name}', type={self.type}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if integration is active and available."""
        return self.status == IntegrationStatus.ACTIVE

    @property
    def supports_sandbox(self) -> bool:
        """Check if integration has sandbox environment."""
        return self.sandbox_url is not None

    def get_api_url(self, use_sandbox: bool = False) -> str:
        """Get appropriate API URL based on environment."""
        if use_sandbox and self.sandbox_url:
            return self.sandbox_url
        return self.base_url


class CompanyIntegration(Base):
    """
    Company-specific integration configurations and credentials.
    """
    __tablename__ = "company_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id'), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Authentication Configuration
    api_key = Column(String(500), nullable=True)  # Encrypted
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(500), nullable=True)  # Encrypted
    oauth_token = Column(Text, nullable=True)  # Encrypted
    oauth_refresh_token = Column(Text, nullable=True)  # Encrypted
    oauth_expires_at = Column(DateTime, nullable=True)
    custom_config = Column(JSONB, nullable=True)  # Integration-specific config

    # Billing Configuration
    billing_tier = Column(String(50), nullable=False, default='standard')
    price_per_check = Column(Numeric(10, 4), nullable=True)
    monthly_quota = Column(Integer, nullable=True)

    # Usage Tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company")
    integration = relationship("Integration", back_populates="company_integrations")
    submissions = relationship("IntegrationSubmission", back_populates="company_integration")

    # Indexes
    __table_args__ = (
        Index('ix_company_integrations_company', 'company_id'),
        Index('ix_company_integrations_integration', 'integration_id'),
    )

    def __repr__(self):
        return f"<CompanyIntegration(company_id={self.company_id}, integration={self.integration.name})>"

    @property
    def is_oauth_expired(self) -> bool:
        """Check if OAuth token is expired."""
        if not self.oauth_expires_at:
            return False
        return datetime.utcnow() >= self.oauth_expires_at


# Lightweight audit/billing data classes used by tests and event pipeline.
# The production implementation stores richer records in dedicated tables,
# but the tests only need structured containers.
@dataclass
class AIAuditEvent:
    session_id: str
    user_id: str
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BillingEvent:
    company_id: str
    event_type: BillingEventType
    amount_usd: Decimal
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_quota_remaining(self) -> bool:
        """Check if company has quota remaining for this integration."""
        if not self.monthly_quota:
            return True  # Unlimited
        return self.usage_count < self.monthly_quota

    def increment_usage(self) -> None:
        """Increment usage counter and update last used timestamp."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()


class IntegrationSubmission(Base):
    """
    Record of submissions to partner APIs with billing tracking.
    """
    __tablename__ = "integration_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('validation_sessions.id'), nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Submission Details
    submission_type = Column(String(50), nullable=False)  # 'validation', 'recheck', 'submission'
    external_reference_id = Column(String(255), nullable=True)  # Partner's reference
    idempotency_key = Column(String(255), nullable=False, unique=True)

    # Request/Response Data
    request_payload = Column(JSONB, nullable=False)
    response_payload = Column(JSONB, nullable=True)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Retry Logic
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True)

    # Billing Protection
    billing_recorded = Column(Boolean, nullable=False, default=False)

    # Timestamps
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("ValidationSession")
    integration = relationship("Integration", back_populates="submissions")
    company = relationship("Company")
    user = relationship("User")
    billing_events = relationship("IntegrationBillingEvent", back_populates="submission")

    # Indexes
    __table_args__ = (
        Index('ix_integration_submissions_session', 'session_id'),
        Index('ix_integration_submissions_integration', 'integration_id'),
        Index('ix_integration_submissions_company', 'company_id'),
        Index('ix_integration_submissions_status', 'status_code'),
        Index('ix_integration_submissions_retry', 'next_retry_at'),
    )

    def __repr__(self):
        return f"<IntegrationSubmission(id={self.id}, type={self.submission_type}, status={self.status_code})>"

    @property
    def is_successful(self) -> bool:
        """Check if submission was successful."""
        return self.status_code and 200 <= self.status_code < 300

    @property
    def is_failed(self) -> bool:
        """Check if submission failed and should not be retried."""
        return self.status_code and self.status_code >= 400

    @property
    def should_retry(self) -> bool:
        """Check if submission should be retried."""
        if self.is_successful or not self.next_retry_at:
            return False
        return datetime.utcnow() >= self.next_retry_at

    def mark_completed(self, status_code: int, response_payload: Optional[Dict[str, Any]] = None,
                      error_message: Optional[str] = None) -> None:
        """Mark submission as completed."""
        self.status_code = status_code
        self.response_payload = response_payload
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def schedule_retry(self, retry_delay_seconds: int = 60) -> None:
        """Schedule next retry attempt."""
        self.retry_count += 1
        self.next_retry_at = datetime.utcnow().replace(
            second=0, microsecond=0
        ) + datetime.timedelta(seconds=retry_delay_seconds * (2 ** self.retry_count))


class IntegrationBillingEvent(Base):
    """
    Immutable billing events for partner API usage.
    Critical for business model protection.
    """
    __tablename__ = "integration_billing_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey('integration_submissions.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Billing Details
    event_type = Column(ENUM(BillingEventType), nullable=False, index=True)
    charged_amount = Column(Numeric(10, 4), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    billing_tier = Column(String(50), nullable=False)
    event_metadata = Column(JSONB, nullable=True)

    # Invoice Linking
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoices.id'), nullable=True)

    # Timestamp (immutable)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    submission = relationship("IntegrationSubmission", back_populates="billing_events")
    company = relationship("Company")
    integration = relationship("Integration")
    user = relationship("User")
    invoice = relationship("Invoice")

    # Indexes
    __table_args__ = (
        Index('ix_integration_billing_company', 'company_id'),
        Index('ix_integration_billing_integration', 'integration_id'),
        Index('ix_integration_billing_event_type', 'event_type'),
        Index('ix_integration_billing_recorded_at', 'recorded_at'),
    )

    def __repr__(self):
        return f"<IntegrationBillingEvent(type={self.event_type}, amount={self.charged_amount})>"

    @property
    def is_sme_event(self) -> bool:
        """Check if this is an SME billing event."""
        return self.event_type == BillingEventType.SME_VALIDATION

    @property
    def is_bank_event(self) -> bool:
        """Check if this is a bank billing event."""
        return self.event_type == BillingEventType.BANK_RECHECK


class IntegrationHealthCheck(Base):
    """
    Health check monitoring for partner integrations.
    """
    __tablename__ = "integration_health_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey('integrations.id'), nullable=False)
    endpoint = Column(String(255), nullable=False)

    # Health Check Results
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    is_healthy = Column(Boolean, nullable=False, default=True)

    # Timestamp
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    integration = relationship("Integration", back_populates="health_checks")

    # Indexes
    __table_args__ = (
        Index('ix_integration_health_integration', 'integration_id'),
        Index('ix_integration_health_checked_at', 'checked_at'),
    )

    def __repr__(self):
        return f"<IntegrationHealthCheck(integration={self.integration.name}, healthy={self.is_healthy})>"

    @property
    def is_timeout(self) -> bool:
        """Check if health check timed out."""
        return self.response_time_ms and self.response_time_ms > 30000

    @property
    def is_slow(self) -> bool:
        """Check if response is slow (>5 seconds)."""
        return self.response_time_ms and self.response_time_ms > 5000