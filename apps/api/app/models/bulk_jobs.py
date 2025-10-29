"""
Bulk Processing Models
Batch LC processing with async job tracking and failure management
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.database import Base


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ItemStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"
    SKIPPED = "skipped"


class JobEventType(str, Enum):
    CREATED = "created"
    STARTED = "started"
    PROGRESS = "progress"
    ITEM_COMPLETED = "item_completed"
    ITEM_FAILED = "item_failed"
    RETRY_REQUESTED = "retry_requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkJob(Base):
    """Bulk processing job for LC batches"""

    __tablename__ = "bulk_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    bank_alias = Column(String(32), nullable=True, index=True)

    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # Job configuration
    job_type = Column(String(32), nullable=False)  # lc_validation, doc_verification, risk_analysis
    config = Column(JSONB, nullable=False, default=dict)

    # User context
    created_by = Column(UUID(as_uuid=True), nullable=False)
    priority = Column(Integer, default=0)  # Higher number = higher priority

    # Status tracking
    status = Column(String(16), nullable=False, default=JobStatus.PENDING)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    succeeded_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    skipped_items = Column(Integer, default=0)

    # Progress tracking
    progress_percent = Column(DECIMAL(5, 2), default=0.00)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Resume capability
    resume_token = Column(String(128), nullable=True)
    checkpoint_data = Column(JSONB, nullable=True)

    # File references
    s3_manifest_bucket = Column(String(128), nullable=True)
    s3_manifest_key = Column(String(512), nullable=True)
    s3_results_bucket = Column(String(128), nullable=True)
    s3_results_key = Column(String(512), nullable=True)

    # Error summary
    last_error = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)

    # Metrics
    throughput_items_per_sec = Column(DECIMAL(10, 2), nullable=True)
    peak_memory_mb = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    items = relationship("BulkItem", back_populates="job", cascade="all, delete-orphan")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_bulk_jobs_tenant_status', 'tenant_id', 'status'),
        Index('ix_bulk_jobs_created_at', 'created_at'),
        Index('ix_bulk_jobs_priority', 'priority', 'created_at'),
    )


class BulkItem(Base):
    """Individual item in a bulk job"""

    __tablename__ = "bulk_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("bulk_jobs.id", ondelete="CASCADE"), nullable=False)

    # Item identification
    lc_identifier = Column(String(128), nullable=False)  # LC number or document ID
    source_ref = Column(String(256), nullable=True)  # Reference in manifest
    item_data = Column(JSONB, nullable=False)  # LC data or file references

    # Processing
    status = Column(String(16), nullable=False, default=ItemStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Results
    result_data = Column(JSONB, nullable=True)  # Validation results, extracted data
    output_files = Column(JSONB, nullable=True)  # Generated reports, corrected docs

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_category = Column(String(32), nullable=True)  # validation, processing, system
    retriable = Column(Boolean, default=True)

    # Idempotency
    idempotency_key = Column(String(128), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job = relationship("BulkJob", back_populates="items")
    failures = relationship("BulkFailure", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_bulk_items_job_status', 'job_id', 'status'),
        Index('ix_bulk_items_identifier', 'job_id', 'lc_identifier'),
        Index('ix_bulk_items_idempotency', 'idempotency_key'),
    )


class BulkFailure(Base):
    """Detailed failure information for bulk items"""

    __tablename__ = "bulk_failures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("bulk_items.id", ondelete="CASCADE"), nullable=False)

    attempt_number = Column(Integer, nullable=False)
    error_code = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=False)
    error_details = Column(JSONB, nullable=True)

    # Classification
    error_category = Column(String(32), nullable=False)  # validation, processing, system, network
    error_severity = Column(String(16), nullable=False)  # low, medium, high, critical
    retriable = Column(Boolean, nullable=False)

    # Context
    worker_id = Column(String(64), nullable=True)
    execution_context = Column(JSONB, nullable=True)

    # Timing
    failed_at = Column(DateTime(timezone=True), server_default=func.now())
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("BulkItem", back_populates="failures")

    __table_args__ = (
        Index('ix_bulk_failures_item', 'item_id'),
        Index('ix_bulk_failures_code', 'error_code'),
        Index('ix_bulk_failures_category', 'error_category'),
    )


class JobEvent(Base):
    """Event log for bulk job lifecycle"""

    __tablename__ = "job_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("bulk_jobs.id", ondelete="CASCADE"), nullable=False)

    event_type = Column(String(32), nullable=False)
    event_data = Column(JSONB, nullable=False, default=dict)

    # Context
    user_id = Column(UUID(as_uuid=True), nullable=True)
    worker_id = Column(String(64), nullable=True)
    correlation_id = Column(String(128), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("BulkJob", back_populates="events")

    __table_args__ = (
        Index('ix_job_events_job_type', 'job_id', 'event_type'),
        Index('ix_job_events_created', 'created_at'),
    )


class BulkTemplate(Base):
    """Reusable templates for bulk job configurations"""

    __tablename__ = "bulk_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    job_type = Column(String(32), nullable=False)

    # Template configuration
    config_template = Column(JSONB, nullable=False)
    manifest_schema = Column(JSONB, nullable=True)
    validation_rules = Column(JSONB, nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Access control
    created_by = Column(UUID(as_uuid=True), nullable=False)
    is_public = Column(Boolean, default=False)
    allowed_roles = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_bulk_templates_tenant_type', 'tenant_id', 'job_type'),
        Index('ix_bulk_templates_usage', 'usage_count', 'last_used_at'),
    )