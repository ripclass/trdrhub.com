"""
Validation Services - Core validation infrastructure for LCopilot.

This module provides:
- Validation Gating (Phase 4): Block validation when LC extraction fails
- Issue Engine (Phase 5): Auto-generate issues from missing fields
- Compliance Scoring (Phase 6): Calculate accurate compliance scores

Key Components:
- validation_gate.py: Check if validation can proceed
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

__all__ = [
    "ValidationGate",
    "GateResult",
    "GateStatus",
    "get_validation_gate",
    "check_validation_gate",
    "create_blocked_response",
]

