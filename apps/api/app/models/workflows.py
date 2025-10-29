"""
Workflow Models
Custom per-bank workflows, rule overrides, and policy versioning
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.database import Base


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RuleComparator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"


class EscalationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class BankWorkflow(Base):
    """Bank-specific workflow configuration"""

    __tablename__ = "bank_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default=WorkflowStatus.DRAFT)

    # Workflow configuration
    workflow_type = Column(String(32), nullable=False)  # lc_validation, doc_review, risk_assessment
    base_config = Column(JSONB, nullable=False, default=dict)

    # Policy versioning
    current_policy_version = Column(String(32), nullable=False, default="1.0")
    default_policy_version = Column(String(32), nullable=False, default="1.0")

    # Feature flags
    enable_auto_corrections = Column(Boolean, default=False)
    enable_ai_suggestions = Column(Boolean, default=True)
    enable_bulk_processing = Column(Boolean, default=True)
    enable_real_time_validation = Column(Boolean, default=True)

    # SLA configuration
    sla_response_hours = Column(Integer, default=24)
    sla_resolution_hours = Column(Integer, default=72)
    sla_escalation_hours = Column(Integer, default=48)

    # Usage tracking
    jobs_processed = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    rule_overrides = relationship("RuleOverride", back_populates="workflow", cascade="all, delete-orphan")
    escalation_rules = relationship("EscalationRule", back_populates="workflow", cascade="all, delete-orphan")
    policy_versions = relationship("PolicyVersion", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_bank_workflows_bank_status', 'bank_id', 'status'),
        Index('ix_bank_workflows_type', 'workflow_type'),
        Index('ix_bank_workflows_usage', 'last_used_at'),
    )


class RuleOverride(Base):
    """Bank-specific rule overrides for validation logic"""

    __tablename__ = "rule_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("bank_workflows.id", ondelete="CASCADE"), nullable=False)

    # Rule identification
    rule_key = Column(String(128), nullable=False)  # e.g., "UCP600.Art14.date_format"
    rule_category = Column(String(64), nullable=False)  # validation, format, business, compliance
    rule_description = Column(Text, nullable=True)

    # Override logic
    comparator = Column(String(32), nullable=False)
    value_data = Column(JSONB, nullable=False)  # The override value(s)
    condition_expr = Column(Text, nullable=True)  # Optional condition when to apply

    # Severity adjustment
    original_severity = Column(String(16), nullable=True)
    override_severity = Column(String(16), nullable=True)  # error, warning, info, disabled

    # Effective period
    effective_from = Column(DateTime(timezone=True), nullable=False, default=func.now())
    effective_to = Column(DateTime(timezone=True), nullable=True)

    # Approval workflow
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    applied_count = Column(Integer, default=0)
    last_applied_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workflow = relationship("BankWorkflow", back_populates="rule_overrides")

    __table_args__ = (
        Index('ix_rule_overrides_workflow_key', 'workflow_id', 'rule_key'),
        Index('ix_rule_overrides_effective', 'effective_from', 'effective_to'),
        Index('ix_rule_overrides_category', 'rule_category'),
    )


class PolicyVersion(Base):
    """Versioned policy configurations for workflows"""

    __tablename__ = "policy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("bank_workflows.id", ondelete="CASCADE"), nullable=False)

    version = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Policy configuration
    policy_config = Column(JSONB, nullable=False)
    schema_version = Column(String(16), nullable=False, default="1.0")

    # Status
    is_active = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # Validation
    config_hash = Column(String(64), nullable=False)  # SHA256 of policy_config
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(JSONB, nullable=True)

    # Usage tracking
    jobs_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)
    published_by = Column(UUID(as_uuid=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Change tracking
    changelog = Column(JSONB, nullable=True)
    parent_version = Column(String(32), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workflow = relationship("BankWorkflow", back_populates="policy_versions")

    __table_args__ = (
        Index('ix_policy_versions_workflow_version', 'workflow_id', 'version', unique=True),
        Index('ix_policy_versions_active', 'workflow_id', 'is_active'),
        Index('ix_policy_versions_hash', 'config_hash'),
    )


class EscalationRule(Base):
    """Escalation rules for workflow issues"""

    __tablename__ = "escalation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("bank_workflows.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Trigger conditions
    condition_expr = Column(Text, nullable=False)  # JSON Logic or SQL-like expression
    trigger_events = Column(JSONB, nullable=False)  # Which events can trigger this rule

    # Timing
    delay_minutes = Column(Integer, default=0)  # Delay before escalation
    max_escalations = Column(Integer, default=3)  # Maximum number of escalations

    # Target configuration
    target_team = Column(String(64), nullable=False)
    target_users = Column(JSONB, nullable=True)  # Specific user IDs
    target_roles = Column(JSONB, nullable=True)  # Role names

    # Notification configuration
    notification_channels = Column(JSONB, nullable=False)  # email, slack, sms, webhook
    notification_template = Column(String(64), nullable=True)
    priority = Column(String(16), nullable=False, default=EscalationPriority.NORMAL)

    # Status
    is_active = Column(Boolean, default=True)
    activation_count = Column(Integer, default=0)
    last_activated_at = Column(DateTime(timezone=True), nullable=True)

    # Management
    created_by = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workflow = relationship("BankWorkflow", back_populates="escalation_rules")

    __table_args__ = (
        Index('ix_escalation_rules_workflow_active', 'workflow_id', 'is_active'),
        Index('ix_escalation_rules_priority', 'priority'),
        Index('ix_escalation_rules_team', 'target_team'),
    )


class WorkflowExecution(Base):
    """Track individual workflow executions"""

    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("bank_workflows.id"), nullable=False)

    # Execution context
    job_id = Column(UUID(as_uuid=True), nullable=True)  # Link to LC job
    trigger_event = Column(String(64), nullable=False)
    execution_context = Column(JSONB, nullable=False)

    # Results
    status = Column(String(16), nullable=False)  # started, completed, failed, cancelled
    steps_completed = Column(Integer, default=0)
    steps_total = Column(Integer, default=0)

    # Overrides applied
    overrides_applied = Column(JSONB, nullable=True)
    policy_version_used = Column(String(32), nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Results
    output_data = Column(JSONB, nullable=True)
    error_details = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_workflow_executions_workflow', 'workflow_id'),
        Index('ix_workflow_executions_job', 'job_id'),
        Index('ix_workflow_executions_started', 'started_at'),
    )