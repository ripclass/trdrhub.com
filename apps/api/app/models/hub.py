"""
Hub Multi-Tool Models

SQLAlchemy models for the multi-tool SaaS architecture:
- HubPlan: Pricing tiers (payg, starter, growth, pro, enterprise)
- HubSubscription: Company subscription to a plan
- HubUsage: Monthly aggregated usage per company
- HubUsageLog: Detailed audit trail of all operations
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, Date, Boolean, ForeignKey, Text, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PAUSED = "paused"


class ToolOperation(str, Enum):
    """Operations that can be tracked for usage."""
    LC_VALIDATION = "lc_validation"
    PRICE_CHECK = "price_check"
    HS_LOOKUP = "hs_lookup"
    SANCTIONS_SCREEN = "sanctions_screen"
    CONTAINER_TRACK = "container_track"


class Tool(str, Enum):
    """Available tools in the hub."""
    LCOPILOT = "lcopilot"
    PRICE_VERIFY = "price_verify"
    HS_CODE = "hs_code"
    SANCTIONS = "sanctions"
    TRACKING = "tracking"


# Mapping from operation to the field name in HubUsage
OPERATION_TO_FIELD = {
    ToolOperation.LC_VALIDATION: "lc_validations",
    ToolOperation.PRICE_CHECK: "price_checks",
    ToolOperation.HS_LOOKUP: "hs_lookups",
    ToolOperation.SANCTIONS_SCREEN: "sanctions_screens",
    ToolOperation.CONTAINER_TRACK: "container_tracks",
}


class HubPlan(Base):
    """
    Pricing plan definition for TRDR Hub.
    
    Plans define:
    - Monthly/yearly price
    - Included usage limits per tool
    - Overage rates when limits exceeded
    - Feature flags (API access, support level, etc.)
    """
    __tablename__ = "hub_plans"
    
    id = Column(String(50), primary_key=True)  # payg, starter, growth, pro, enterprise
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    price_monthly = Column(Numeric(10, 2), nullable=True)
    price_yearly = Column(Numeric(10, 2), nullable=True)
    
    # Usage limits: {"lc_validations": 10, "price_checks": 30, ...}
    # -1 means unlimited, 0 means not included (pay as you go)
    limits = Column(JSONB, nullable=False)
    
    # Overage rates: {"lc_validations": 7.00, "price_checks": 0.80, ...}
    overage_rates = Column(JSONB, nullable=False)
    
    # Feature flags: {"api_access": false, "priority_support": false, ...}
    features = Column(JSONB, nullable=True)
    
    # User limits (-1 = unlimited)
    max_users = Column(Integer, default=1)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    subscriptions = relationship("HubSubscription", back_populates="plan")
    
    def __repr__(self):
        return f"<HubPlan(id='{self.id}', name='{self.name}', price=${self.price_monthly})>"
    
    def get_limit(self, operation: str) -> int:
        """Get the usage limit for an operation. -1 = unlimited, 0 = pay as you go."""
        return self.limits.get(operation, 0)
    
    def get_overage_rate(self, operation: str) -> Decimal:
        """Get the overage rate for an operation."""
        return Decimal(str(self.overage_rates.get(operation, 0)))
    
    def has_feature(self, feature: str) -> bool:
        """Check if plan includes a feature."""
        if not self.features:
            return False
        return self.features.get(feature, False)
    
    @property
    def is_unlimited(self) -> bool:
        """Check if plan has unlimited usage (enterprise)."""
        return all(v == -1 for v in self.limits.values())
    
    @property
    def is_pay_as_you_go(self) -> bool:
        """Check if plan is pay-as-you-go (no included usage)."""
        return self.id == "payg"


class HubSubscription(Base):
    """
    Company subscription to a plan.
    
    Tracks:
    - Current plan
    - Billing period
    - Subscription status
    - Stripe integration
    """
    __tablename__ = "hub_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(50), ForeignKey("hub_plans.id"), nullable=False)
    
    # Status
    status = Column(String(50), default=SubscriptionStatus.ACTIVE.value, nullable=False)
    
    # Billing period
    current_period_start = Column(Date, nullable=False)
    current_period_end = Column(Date, nullable=False)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Trial
    trial_end = Column(Date, nullable=True)
    
    # Stripe integration
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    plan = relationship("HubPlan", back_populates="subscriptions")
    company = relationship("Company", backref="hub_subscription")
    
    # Indexes
    __table_args__ = (
        Index("ix_hub_subscriptions_company", "company_id", unique=True),
        Index("ix_hub_subscriptions_status", "status"),
    )
    
    def __repr__(self):
        return f"<HubSubscription(company_id={self.company_id}, plan='{self.plan_id}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == SubscriptionStatus.ACTIVE.value
    
    @property
    def is_trialing(self) -> bool:
        """Check if subscription is in trial."""
        return self.status == SubscriptionStatus.TRIALING.value
    
    @property
    def days_remaining(self) -> int:
        """Days remaining in current billing period."""
        if not self.current_period_end:
            return 0
        delta = self.current_period_end - date.today()
        return max(0, delta.days)


class HubUsage(Base):
    """
    Monthly aggregated usage per company.
    
    Tracks:
    - Usage counts per tool
    - Overage counts
    - Total overage charges
    """
    __tablename__ = "hub_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    period = Column(String(7), nullable=False)  # YYYY-MM format
    
    # Usage counts per tool
    lc_validations_used = Column(Integer, default=0, nullable=False)
    price_checks_used = Column(Integer, default=0, nullable=False)
    hs_lookups_used = Column(Integer, default=0, nullable=False)
    sanctions_screens_used = Column(Integer, default=0, nullable=False)
    container_tracks_used = Column(Integer, default=0, nullable=False)
    
    # Overage counts (how many were over the limit)
    lc_validations_overage = Column(Integer, default=0, nullable=False)
    price_checks_overage = Column(Integer, default=0, nullable=False)
    hs_lookups_overage = Column(Integer, default=0, nullable=False)
    sanctions_screens_overage = Column(Integer, default=0, nullable=False)
    container_tracks_overage = Column(Integer, default=0, nullable=False)
    
    # Total overage charges for the period
    overage_charges = Column(Numeric(10, 2), default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    company = relationship("Company", backref="hub_usage")
    
    # Indexes
    __table_args__ = (
        Index("ix_hub_usage_company_period", "company_id", "period", unique=True),
        Index("ix_hub_usage_period", "period"),
    )
    
    def __repr__(self):
        return f"<HubUsage(company_id={self.company_id}, period='{self.period}')>"
    
    def get_usage(self, operation: str) -> int:
        """Get usage count for an operation."""
        field = f"{operation}_used"
        return getattr(self, field, 0)
    
    def get_overage(self, operation: str) -> int:
        """Get overage count for an operation."""
        field = f"{operation}_overage"
        return getattr(self, field, 0)
    
    def increment_usage(self, operation: str, quantity: int = 1, is_overage: bool = False):
        """Increment usage for an operation."""
        field = f"{operation}_used"
        current = getattr(self, field, 0)
        setattr(self, field, current + quantity)
        
        if is_overage:
            overage_field = f"{operation}_overage"
            current_overage = getattr(self, overage_field, 0)
            setattr(self, overage_field, current_overage + quantity)
    
    def add_overage_charge(self, amount: Decimal):
        """Add to overage charges."""
        self.overage_charges = Decimal(str(self.overage_charges)) + amount
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "period": self.period,
            "lc_validations": {
                "used": self.lc_validations_used,
                "overage": self.lc_validations_overage
            },
            "price_checks": {
                "used": self.price_checks_used,
                "overage": self.price_checks_overage
            },
            "hs_lookups": {
                "used": self.hs_lookups_used,
                "overage": self.hs_lookups_overage
            },
            "sanctions_screens": {
                "used": self.sanctions_screens_used,
                "overage": self.sanctions_screens_overage
            },
            "container_tracks": {
                "used": self.container_tracks_used,
                "overage": self.container_tracks_overage
            },
            "overage_charges": float(self.overage_charges)
        }


class HubUsageLog(Base):
    """
    Detailed audit trail of all billable operations.
    
    Every usage event is logged with:
    - Who did it (user)
    - What they did (operation, tool)
    - Whether it was overage
    - Cost if applicable
    """
    __tablename__ = "hub_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Operation details
    operation = Column(String(50), nullable=False)  # lc_validation, price_check, etc.
    tool = Column(String(50), nullable=False)  # lcopilot, price_verify, etc.
    quantity = Column(Integer, default=1, nullable=False)
    
    # Cost tracking
    unit_cost = Column(Numeric(10, 2), nullable=True)
    is_overage = Column(Boolean, default=False, nullable=False)
    
    # Context
    log_data = Column(JSONB, nullable=True)  # {"job_id": "xxx", "document_count": 6, ...}
    description = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    company = relationship("Company", backref="hub_usage_logs")
    user = relationship("User", backref="hub_usage_logs")
    
    # Indexes
    __table_args__ = (
        Index("ix_hub_usage_logs_company", "company_id"),
        Index("ix_hub_usage_logs_user", "user_id"),
        Index("ix_hub_usage_logs_operation", "operation"),
        Index("ix_hub_usage_logs_tool", "tool"),
        Index("ix_hub_usage_logs_created", "created_at"),
        Index("ix_hub_usage_logs_company_created", "company_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<HubUsageLog(operation='{self.operation}', tool='{self.tool}', is_overage={self.is_overage})>"
    
    @classmethod
    def create(
        cls,
        company_id: uuid.UUID,
        operation: str,
        tool: str,
        user_id: Optional[uuid.UUID] = None,
        quantity: int = 1,
        unit_cost: Optional[Decimal] = None,
        is_overage: bool = False,
        metadata: Optional[Dict] = None,
        description: Optional[str] = None
    ) -> "HubUsageLog":
        """Factory method to create a usage log entry."""
        return cls(
            company_id=company_id,
            user_id=user_id,
            operation=operation,
            tool=tool,
            quantity=quantity,
            unit_cost=unit_cost,
            is_overage=is_overage,
            metadata=metadata,
            description=description
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "operation": self.operation,
            "tool": self.tool,
            "quantity": self.quantity,
            "unit_cost": float(self.unit_cost) if self.unit_cost else None,
            "is_overage": self.is_overage,
            "metadata": self.metadata,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

