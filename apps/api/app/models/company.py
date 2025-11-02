from sqlalchemy import Column, String, Integer, Date, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from .base import Base


class PlanType(str, enum.Enum):
    FREE = "free"
    PAY_PER_CHECK = "pay_per_check"
    MONTHLY_BASIC = "monthly_basic"
    MONTHLY_PRO = "monthly_pro"
    ENTERPRISE = "enterprise"


class CompanyStatus(str, enum.Enum):
    ACTIVE = "active"
    DELINQUENT = "delinquent"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class LanguageType(str, enum.Enum):
    ENGLISH = "en"
    BANGLA = "bn"
    ARABIC = "ar"
    HINDI = "hi"
    URDU = "ur"
    MANDARIN = "zh"
    FRENCH = "fr"
    GERMAN = "de"
    MALAY = "ms"


class Company(Base):
    """
    Company model for multi-tenant billing and quota management.
    Each company has users, billing plan, and usage quotas.
    """
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    contact_email = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)
    registration_number = Column(String(128), nullable=True)
    regulator_id = Column(String(128), nullable=True)
    country = Column(String(128), nullable=True)

    # Billing configuration
    plan = Column(Enum(PlanType), nullable=False, default=PlanType.FREE)
    quota_limit = Column(Integer, nullable=True)  # null = unlimited for enterprise
    billing_cycle_start = Column(Date, nullable=True)

    # External payment provider reference
    payment_provider_id = Column(String(255), nullable=True, index=True)  # Stripe customer_id or SSLCommerz ref

    # Status and metadata
    status = Column(Enum(CompanyStatus), nullable=False, default=CompanyStatus.ACTIVE)
    preferred_language = Column(Enum(LanguageType), nullable=False, default=LanguageType.ENGLISH)
    event_metadata = Column(JSONB, nullable=True)  # Additional company settings, preferences

    # Business information for invoicing
    business_address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True)  # VAT/TIN number

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="company")
    validation_sessions = relationship("ValidationSession", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")
    usage_records = relationship("UsageRecord", back_populates="company")
    kyc_documents = relationship("KYCDocument", back_populates="company")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', plan={self.plan})>"

    @property
    def is_active(self) -> bool:
        """Check if company is in active billing status"""
        return self.status == CompanyStatus.ACTIVE

    @property
    def has_quota_limit(self) -> bool:
        """Check if company has a quota limit (not unlimited)"""
        return self.quota_limit is not None

    @property
    def is_subscription_plan(self) -> bool:
        """Check if company is on a subscription plan"""
        return self.plan in [PlanType.MONTHLY_BASIC, PlanType.MONTHLY_PRO, PlanType.ENTERPRISE]

    @property
    def is_pay_per_check(self) -> bool:
        """Check if company is on pay-per-check billing"""
        return self.plan == PlanType.PAY_PER_CHECK

    def get_display_name(self) -> str:
        """Get formatted display name for the company"""
        return self.name.title()

    def get_plan_display(self) -> str:
        """Get human-readable plan name"""
        plan_names = {
            PlanType.FREE: "Free",
            PlanType.PAY_PER_CHECK: "Pay Per Check",
            PlanType.MONTHLY_BASIC: "Monthly Basic",
            PlanType.MONTHLY_PRO: "Monthly Pro",
            PlanType.ENTERPRISE: "Enterprise"
        }
        return plan_names.get(self.plan, str(self.plan))