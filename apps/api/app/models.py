"""
SQLAlchemy models for LCopilot database schema.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Date, Boolean, ForeignKey, Text, JSON, Float, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

# Import version models
from .models.lc_versions import LCVersion, LCVersionStatus

# Import audit models
from .models.audit_log import AuditLog, AuditAction, AuditResult

# Import billing models
from .models.company import Company, PlanType, CompanyStatus
from .models.invoice import Invoice, InvoiceStatus, Currency
from .models.usage_record import UsageRecord, UsageAction


class UserRole(str, Enum):
    """User role types for access control."""

    EXPORTER = "exporter"
    IMPORTER = "importer"
    TENANT_ADMIN = "tenant_admin"
    BANK_OFFICER = "bank_officer"
    BANK_ADMIN = "bank_admin"
    SYSTEM_ADMIN = "system_admin"

    # Backwards compatibility aliases
    BANK = "bank_officer"
    ADMIN = "system_admin"


class SessionStatus(str, Enum):
    """Validation session status."""
    CREATED = "created"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document types for LC validation."""
    LETTER_OF_CREDIT = "letter_of_credit"
    COMMERCIAL_INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"


class DiscrepancyType(str, Enum):
    """Types of discrepancies in Fatal Four validation."""
    DATE_MISMATCH = "date_mismatch"
    AMOUNT_MISMATCH = "amount_mismatch"
    PARTY_MISMATCH = "party_mismatch"
    PORT_MISMATCH = "port_mismatch"
    MISSING_FIELD = "missing_field"
    INVALID_FORMAT = "invalid_format"


class DiscrepancySeverity(str, Enum):
    """Severity levels for discrepancies."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class User(Base):
    """User account model with role-based access control."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.EXPORTER, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Billing relationship
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Onboarding fields
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_data = Column(JSONB, nullable=True, default=dict)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('exporter','importer','tenant_admin','bank_officer','bank_admin','system_admin','bank','admin')",
            name="ck_users_role",
        ),
    )

    # Relationships
    validation_sessions = relationship("ValidationSession", back_populates="user")
    company = relationship("Company", back_populates="users")

    def is_system_admin(self) -> bool:
        """Check if the user is a system administrator."""
        return self.role in {UserRole.SYSTEM_ADMIN, UserRole.ADMIN}

    def is_bank_officer(self) -> bool:
        """Check if the user is a bank officer-level user."""
        return self.role in {UserRole.BANK_OFFICER, UserRole.BANK}

    def is_bank_admin(self) -> bool:
        """Check if the user is a bank administrator."""
        return self.role == UserRole.BANK_ADMIN

    def is_tenant_admin(self) -> bool:
        """Check if the user is a tenant administrator."""
        return self.role == UserRole.TENANT_ADMIN

    def can_access_all_resources(self) -> bool:
        """Check if user can access all system resources."""
        return self.is_system_admin() or self.is_bank_admin()

    def can_manage_roles(self) -> bool:
        """Check if user can manage other users' roles."""
        return self.is_system_admin()

    # Relationships
    roles = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")


class UserRoleAssignment(Base):
    """Optional mapping table for multi-role assignments."""

    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="roles")


class BankTenant(Base):
    """Mapping between a bank (company) and its managed SME tenants."""

    __tablename__ = "bank_tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    bank = relationship("Company", foreign_keys=[bank_id])
    tenant = relationship("Company", foreign_keys=[tenant_id])


class BankReport(Base):
    """Aggregated bank portfolio metrics by reporting period."""

    __tablename__ = "bank_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(Date, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bank = relationship("Company", foreign_keys=[bank_id])


class BankAuditLog(Base):
    """Bank-scoped audit events with tenant scoping."""

    __tablename__ = "bank_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    lc_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    event = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bank = relationship("Company", foreign_keys=[bank_id])
    tenant = relationship("Company", foreign_keys=[tenant_id])
    validation_session = relationship("ValidationSession", foreign_keys=[lc_id])


class ValidationSession(Base):
    """Central container for a single validation job."""
    __tablename__ = "validation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default=SessionStatus.CREATED.value)
    
    # Processing metadata
    ocr_provider = Column(String(50), nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extracted data (JSON fields)
    extracted_data = Column(JSON, nullable=True)
    validation_results = Column(JSON, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="validation_sessions")
    company = relationship("Company", back_populates="validation_sessions")
    documents = relationship("Document", back_populates="validation_session")
    discrepancies = relationship("Discrepancy", back_populates="validation_session")
    reports = relationship("Report", back_populates="validation_session")
    lc_version = relationship("LCVersion", back_populates="validation_session", uselist=False)
    usage_records = relationship("UsageRecord", back_populates="session")


class Document(Base):
    """Represents a single user-uploaded file and its metadata."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False)
    document_type = Column(String(50), nullable=False)
    
    # File metadata
    original_filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extracted structured data
    extracted_fields = Column(JSON, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    validation_session = relationship("ValidationSession", back_populates="documents")


class Discrepancy(Base):
    """Represents a single issue flagged by the validation engine."""
    __tablename__ = "discrepancies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False)
    
    # Discrepancy details
    discrepancy_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default=DiscrepancySeverity.MAJOR.value)
    rule_name = Column(String(100), nullable=False)
    
    # Context
    field_name = Column(String(100), nullable=True)
    expected_value = Column(String(500), nullable=True)
    actual_value = Column(String(500), nullable=True)
    description = Column(Text, nullable=False)
    
    # References to source documents
    source_document_types = Column(JSON, nullable=True)  # Array of document types involved
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    validation_session = relationship("ValidationSession", back_populates="discrepancies")


class Report(Base):
    """Represents the final, versioned PDF output of a session."""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=False)
    
    # Report metadata
    report_version = Column(Integer, nullable=False, default=1)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Summary data (for quick access)
    total_discrepancies = Column(Integer, nullable=False, default=0)
    critical_discrepancies = Column(Integer, nullable=False, default=0)
    major_discrepancies = Column(Integer, nullable=False, default=0)
    minor_discrepancies = Column(Integer, nullable=False, default=0)
    
    # Generation metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    validation_session = relationship("ValidationSession", back_populates="reports")
