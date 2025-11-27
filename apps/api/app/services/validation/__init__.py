"""
Validation Services - Core validation infrastructure for LCopilot.

This module provides:
- Validation Gating (Phase 4): Block validation when LC extraction fails
- Issue Engine (Phase 5): Auto-generate issues from missing fields
- Compliance Scoring (Phase 6): Calculate accurate compliance scores

Key Components:
- validation_gate.py: Check if validation can proceed
- issue_engine.py: Generate issues from missing fields and rules
- DIAGNOSTIC_AUDIT_PHASE1.md: Root cause analysis documentation
"""

from .validation_gate import (
    ValidationGate,
    GateResult,
    GateStatus,
    get_validation_gate,
    check_validation_gate,
    create_blocked_response,
)

from .issue_engine import (
    IssueEngine,
    Issue,
    IssueSeverity,
    IssueSource,
    IssueEngineResult,
    get_issue_engine,
    generate_issues_from_baseline,
    generate_all_issues,
)

from .compliance_scorer import (
    ComplianceScorer,
    ComplianceScore,
    ComplianceLevel,
    get_compliance_scorer,
    calculate_compliance_score,
    calculate_compliance_rate,
)

from .crossdoc_validator import (
    CrossDocValidator,
    CrossDocIssue,
    CrossDocResult,
    DocumentType,
    get_crossdoc_validator,
    validate_cross_documents,
)

from .audit_logger import (
    ValidationAuditLogger,
    AuditEvent,
    AuditTrail,
    AuditEventType,
    AuditSeverity,
    create_audit_logger,
    get_current_audit_logger,
    set_current_audit_logger,
)

from .pipeline import (
    ValidationPipeline,
    ValidationInput,
    ValidationOutput,
    run_validation_pipeline,
)

from .response_schema import (
    ValidationResponseSchema,
    GateResultSchema,
    ExtractionSummarySchema,
    LCBaselineSchema,
    IssueSchema,
    AnalyticsSchema,
    ProcessingSummarySchema,
    build_v2_structured_result,
)

from .ai_validator import (
    run_ai_validation,
    parse_lc_requirements,
    check_document_completeness,
    semantic_goods_match,
    validate_document_fields,
    generate_discrepancy_explanation,
    AIValidationIssue,
    RequiredDocument,
    IssueSeverity as AIIssueSeverity,
)

__all__ = [
    # Validation Gate
    "ValidationGate",
    "GateResult",
    "GateStatus",
    "get_validation_gate",
    "check_validation_gate",
    "create_blocked_response",
    # Issue Engine
    "IssueEngine",
    "Issue",
    "IssueSeverity",
    "IssueSource",
    "IssueEngineResult",
    "get_issue_engine",
    "generate_issues_from_baseline",
    "generate_all_issues",
    # Compliance Scorer
    "ComplianceScorer",
    "ComplianceScore",
    "ComplianceLevel",
    "get_compliance_scorer",
    "calculate_compliance_score",
    "calculate_compliance_rate",
    # Cross-Document Validator
    "CrossDocValidator",
    "CrossDocIssue",
    "CrossDocResult",
    "DocumentType",
    "get_crossdoc_validator",
    "validate_cross_documents",
    # Audit Logger
    "ValidationAuditLogger",
    "AuditEvent",
    "AuditTrail",
    "AuditEventType",
    "AuditSeverity",
    "create_audit_logger",
    "get_current_audit_logger",
    "set_current_audit_logger",
    # Pipeline
    "ValidationPipeline",
    "ValidationInput",
    "ValidationOutput",
    "run_validation_pipeline",
    # Response Schema
    "ValidationResponseSchema",
    "GateResultSchema",
    "ExtractionSummarySchema",
    "LCBaselineSchema",
    "IssueSchema",
    "AnalyticsSchema",
    "ProcessingSummarySchema",
    "build_v2_structured_result",
    # AI Validator
    "run_ai_validation",
    "parse_lc_requirements",
    "check_document_completeness",
    "semantic_goods_match",
    "validate_document_fields",
    "generate_discrepancy_explanation",
    "AIValidationIssue",
    "RequiredDocument",
    "AIIssueSeverity",
]

