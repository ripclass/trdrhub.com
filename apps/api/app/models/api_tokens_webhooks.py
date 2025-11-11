"""
API Tokens and Webhooks Models
Stores API tokens, webhook subscriptions, and delivery logs for bank integrations
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class TokenStatus(str, Enum):
    """API token status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DeliveryStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class APIToken(Base):
    """API token for bank integrations"""
    __tablename__ = "api_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    # Token metadata
    name = Column(String(255), nullable=False)
    description = Column(Text(), nullable=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    token_prefix = Column(String(8), nullable=False)  # First 8 chars for display
    
    # Token lifecycle
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # IPv6 max length
    usage_count = Column(Integer, nullable=False, default=0)
    
    # Scopes/permissions
    scopes = Column(JSONB, nullable=False, default=list)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=True)
    rate_limit_per_hour = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoke_reason = Column(Text(), nullable=True)
    
    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    creator = relationship("User", foreign_keys=[created_by])
    revoker = relationship("User", foreign_keys=[revoked_by])
    
    __table_args__ = (
        Index('ix_api_tokens_company_id', 'company_id'),
        Index('ix_api_tokens_created_by', 'created_by'),
    )


class WebhookSubscription(Base):
    """Webhook subscription configuration"""
    __tablename__ = "webhook_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    # Webhook metadata
    name = Column(String(255), nullable=False)
    description = Column(Text(), nullable=True)
    url = Column(String(2048), nullable=False, index=True)
    secret = Column(String(64), nullable=False)  # Secret for signing payloads
    
    # Event subscriptions
    events = Column(JSONB, nullable=False, default=list)
    
    # Configuration
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    retry_count = Column(Integer, nullable=False, default=3)
    retry_backoff_multiplier = Column(Float, nullable=False, default=2.0)
    
    # Headers
    headers = Column(JSONB, nullable=True)
    
    # Statistics
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    creator = relationship("User", foreign_keys=[created_by])
    deliveries = relationship("WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_webhook_subscriptions_company_id', 'company_id'),
        Index('ix_webhook_subscriptions_created_by', 'created_by'),
    )


class WebhookDelivery(Base):
    """Webhook delivery attempt and log"""
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Delivery metadata
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=True)  # ID of the event that triggered this
    payload = Column(JSONB, nullable=False)
    signature = Column(String(128), nullable=True)  # HMAC signature
    
    # Delivery status
    status = Column(String(50), nullable=False, index=True)  # pending, success, failed, retrying
    attempt_number = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    # HTTP response
    http_status_code = Column(Integer, nullable=True)
    response_body = Column(Text(), nullable=True)
    response_headers = Column(JSONB, nullable=True)
    error_message = Column(Text(), nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Retry information
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    retry_reason = Column(Text(), nullable=True)
    
    # Relationships
    subscription = relationship("WebhookSubscription", back_populates="deliveries")
    company = relationship("Company", foreign_keys=[company_id])
    
    __table_args__ = (
        Index('ix_webhook_deliveries_subscription_id', 'subscription_id'),
        Index('ix_webhook_deliveries_company_id', 'company_id'),
    )

