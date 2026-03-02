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
    parse_lc_requirements_sync,
    check_document_completeness,
    validate_bl_fields,
    AIValidationIssue,
    IssueSeverity as AIIssueSeverity,
)

# New hybrid validation components
from .llm_requirement_parser import (
    RequirementGraph,
    DocumentRequirement,
    NestedObligation,
    ToleranceRule,
    ToleranceSource,
    Contradiction,
    BLRequirements,
    parse_lc_requirements_llm,
    parse_lc_requirements_sync_v2,
    get_cached_requirements,
    infer_document_type,
)

from .party_matcher import (
    parties_match,
    normalize_party_name,
    match_party_to_candidates,
    PartyMatchResult,
)

from .amendment_generator import (
    AmendmentDraft,
    generate_late_shipment_amendment,
    generate_amount_amendment,
    generate_expiry_amendment,
    generate_port_amendment,
    generate_amendment_for_discrepancy,
    generate_amendments_for_issues,
    calculate_total_amendment_cost,
)

from .bank_profiles import (
    BankProfile,
    BankStrictness,
    get_bank_profile,
    detect_bank_from_lc,
    apply_bank_strictness,
    BANK_PROFILES,
    DEFAULT_PROFILE,
)

from .confidence_weighting import (
    ConfidenceLevel,
    ConfidenceAdjustment,
    adjust_severity_for_confidence,
    get_field_confidence,
    batch_adjust_issues,
    calculate_overall_extraction_confidence,
)

from .arbitration import (
    compute_shadow_arbitration,
    normalize_verdict,
)

from .response_contract_validator import (
    ContractSeverity,
    ContractWarning,
    ContractValidationResult,
    validate_response_contract,
    add_contract_warnings_to_response,
    validate_and_annotate_response,
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
    "parse_lc_requirements_sync",
    "check_document_completeness",
    "validate_bl_fields",
    "AIValidationIssue",
    "AIIssueSeverity",
    # LLM Requirement Parser (Hybrid Pipeline)
    "RequirementGraph",
    "DocumentRequirement",
    "NestedObligation",
    "ToleranceRule",
    "ToleranceSource",
    "Contradiction",
    "BLRequirements",
    "parse_lc_requirements_llm",
    "parse_lc_requirements_sync_v2",
    "get_cached_requirements",
    "infer_document_type",
    # Party Matcher
    "parties_match",
    "normalize_party_name",
    "match_party_to_candidates",
    "PartyMatchResult",
    # Amendment Generator
    "AmendmentDraft",
    "generate_late_shipment_amendment",
    "generate_amount_amendment",
    "generate_expiry_amendment",
    "generate_port_amendment",
    "generate_amendment_for_discrepancy",
    "generate_amendments_for_issues",
    "calculate_total_amendment_cost",
    # Bank Profiles
    "BankProfile",
    "BankStrictness",
    "get_bank_profile",
    "detect_bank_from_lc",
    "apply_bank_strictness",
    "BANK_PROFILES",
    "DEFAULT_PROFILE",
    # Confidence Weighting
    "ConfidenceLevel",
    "ConfidenceAdjustment",
    "adjust_severity_for_confidence",
    "get_field_confidence",
    "batch_adjust_issues",
    "calculate_overall_extraction_confidence",
    # Arbitration
    "compute_shadow_arbitration",
    "normalize_verdict",
    # Response Contract Validator
    "ContractSeverity",
    "ContractWarning",
    "ContractValidationResult",
    "validate_response_contract",
    "add_contract_warnings_to_response",
    "validate_and_annotate_response",
]

