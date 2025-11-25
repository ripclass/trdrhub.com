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
]

