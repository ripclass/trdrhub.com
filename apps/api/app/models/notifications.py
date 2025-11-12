"""
Notification Models
Multi-channel notifications, templates, subscriptions, and delivery tracking
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.database import Base


class ChannelType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PUSH = "push"
    IN_APP = "in_app"


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    REJECTED = "rejected"


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class DigestFrequency(str, Enum):
    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class NotificationChannel(Base):
    """Notification delivery channels (email, Slack, SMS, webhooks)"""

    __tablename__ = "notification_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    channel_type = Column(String(16), nullable=False)

    # Channel configuration (encrypted in production)
    config = Column(JSONB, nullable=False)  # SMTP settings, webhook URLs, API keys
    auth_config = Column(JSONB, nullable=True)  # OAuth tokens, API keys

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(128), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Rate limiting
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)

    # Health monitoring
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    health_status = Column(String(16), default="unknown")  # healthy, degraded, failed

    # Usage tracking
    messages_sent = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="channel")
    deliveries = relationship("NotificationDelivery", back_populates="channel")

    __table_args__ = (
        Index('ix_channels_tenant_type', 'tenant_id', 'channel_type'),
        Index('ix_channels_active', 'is_active'),
        Index('ix_channels_health', 'health_status'),
    )


class NotificationTemplate(Base):
    """Message templates for notifications"""

    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Template identification
    template_key = Column(String(128), nullable=False)  # e.g., "collab.comment.created"
    version = Column(String(16), nullable=False, default="1.0")
    locale = Column(String(8), nullable=False, default="en")

    # Content
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    subject_template = Column(String(512), nullable=True)  # For email/SMS
    body_markdown = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)  # Pre-rendered HTML

    # Channel-specific variants
    email_template = Column(JSONB, nullable=True)
    sms_template = Column(JSONB, nullable=True)
    slack_template = Column(JSONB, nullable=True)
    webhook_template = Column(JSONB, nullable=True)

    # Template variables schema
    variables_schema = Column(JSONB, nullable=True)
    sample_data = Column(JSONB, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_templates_key_locale', 'template_key', 'locale', 'version', unique=True),
        Index('ix_templates_tenant_key', 'tenant_id', 'template_key'),
        Index('ix_templates_active', 'is_active'),
    )


class Subscription(Base):
    """User/team subscriptions to notification events"""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Subscriber
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Individual user
    team_id = Column(String(64), nullable=True)  # Team/role subscription
    subscription_name = Column(String(128), nullable=True)

    # Event configuration
    event_key = Column(String(128), nullable=False)  # e.g., "collab.comment.created"
    event_filters = Column(JSONB, nullable=True)  # Filtering conditions

    # Delivery configuration
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id"), nullable=False)
    template_key = Column(String(128), nullable=True)  # Override default template
    priority = Column(String(16), default=EventPriority.NORMAL)

    # Digest settings
    digest_frequency = Column(String(16), default=DigestFrequency.IMMEDIATE)
    digest_window_start = Column(String(8), nullable=True)  # HH:MM format
    digest_timezone = Column(String(32), default="UTC")

    # Preferences
    include_attachments = Column(Boolean, default=False)
    max_frequency_per_hour = Column(Integer, nullable=True)  # Rate limiting
    quiet_hours_start = Column(String(8), nullable=True)  # HH:MM
    quiet_hours_end = Column(String(8), nullable=True)  # HH:MM

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    events_received = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    channel = relationship("NotificationChannel", back_populates="subscriptions")

    __table_args__ = (
        Index('ix_subscriptions_user_event', 'user_id', 'event_key'),
        Index('ix_subscriptions_team_event', 'team_id', 'event_key'),
        Index('ix_subscriptions_channel', 'channel_id'),
        Index('ix_subscriptions_active', 'is_active'),
    )


class NotificationEvent(Base):
    """Notification events to be processed"""

    __tablename__ = "notification_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    # Event identification
    event_key = Column(String(128), nullable=False)
    correlation_id = Column(String(128), nullable=True, index=True)
    source_id = Column(String(128), nullable=True)  # ID of the triggering entity

    # Event data
    event_data = Column(JSONB, nullable=False)
    context_data = Column(JSONB, nullable=True)  # Additional context

    # Priority and routing
    priority = Column(String(16), default=EventPriority.NORMAL)
    routing_key = Column(String(128), nullable=True)

    # Processing status
    status = Column(String(16), default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    delivery_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Timing
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    deliveries = relationship("NotificationDelivery", back_populates="event")

    __table_args__ = (
        Index('ix_events_tenant_key', 'tenant_id', 'event_key'),
        Index('ix_events_status', 'status'),
        Index('ix_events_created', 'created_at'),
        Index('ix_events_correlation', 'correlation_id'),
    )


class NotificationDelivery(Base):
    """Individual notification delivery attempts"""

    __tablename__ = "notification_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("notification_events.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id"), nullable=False)

    # Recipient
    recipient_id = Column(UUID(as_uuid=True), nullable=True)  # User ID
    recipient_address = Column(String(256), nullable=False)  # Email, phone, webhook URL

    # Message
    subject = Column(String(512), nullable=True)
    body = Column(Text, nullable=False)
    template_used = Column(String(128), nullable=True)

    # Delivery tracking
    status = Column(String(16), default=DeliveryStatus.QUEUED)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    # External tracking
    external_id = Column(String(128), nullable=True)  # Provider message ID
    external_status = Column(String(64), nullable=True)
    webhook_signature = Column(String(256), nullable=True)

    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    retry_after = Column(DateTime(timezone=True), nullable=True)

    # Response tracking
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    event = relationship("NotificationEvent", back_populates="deliveries")
    channel = relationship("NotificationChannel", back_populates="deliveries")

    __table_args__ = (
        Index('ix_deliveries_event', 'event_id'),
        Index('ix_deliveries_channel_status', 'channel_id', 'status'),
        Index('ix_deliveries_recipient', 'recipient_id'),
        Index('ix_deliveries_scheduled', 'scheduled_at'),
        Index('ix_deliveries_external', 'external_id'),
    )


class DigestEntry(Base):
    """Entries for digest notifications"""

    __tablename__ = "digest_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)

    # Digest grouping
    digest_key = Column(String(128), nullable=False)  # e.g., "daily_2024-01-15"
    event_id = Column(UUID(as_uuid=True), ForeignKey("notification_events.id"), nullable=False)

    # Entry data
    entry_data = Column(JSONB, nullable=False)
    summary_text = Column(Text, nullable=True)

    # Status
    included_in_digest = Column(Boolean, default=False)
    digest_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_digest_entries_key', 'digest_key'),
        Index('ix_digest_entries_subscription', 'subscription_id'),
        Index('ix_digest_entries_status', 'included_in_digest'),
    )


# Aliases for backward compatibility
NotificationSubscription = Subscription
NotificationDigest = DigestEntry