"""
Validation Gate - Phase 4: Hard stop when LC extraction fails.

This module implements the validation gate that checks if LC extraction
was successful enough to proceed with cross-document validation.

Gate Logic:
1. LC document must be detected
2. Critical fields (number, amount, parties) must be extracted
3. Minimum completeness threshold must be met
4. OCR quality must be acceptable

If gate fails:
- Validation is BLOCKED
- Clear error response returned
- Missing field issues generated
- Compliance score = 0%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from app.services.extraction.lc_baseline import (
    LCBaseline,
    FieldPriority,
    ExtractionStatus,
)
from app.services.extraction.lc_extractor_v2 import (
    extract_lc_with_baseline,
    LCExtractionResult,
)


logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    """Validation gate status."""
    PASSED = "passed"           # Proceed with validation
    BLOCKED = "blocked"         # Validation blocked, return error
    WARNING = "warning"         # Proceed with warnings


@dataclass
class GateResult:
    """Result of validation gate check."""
    status: GateStatus
    can_proceed: bool
    block_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # LC Baseline (if extraction succeeded)
    baseline: Optional[LCBaseline] = None
    
    # Extraction metrics
    completeness: float = 0.0
    critical_completeness: float = 0.0
    
    # Missing fields
    missing_critical: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    
    # Generated issues for missing fields
    blocking_issues: List[Dict[str, Any]] = field(default_factory=list)
    warning_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "can_proceed": self.can_proceed,
            "block_reason": self.block_reason,
            "warnings": self.warnings,
            "completeness": round(self.completeness * 100, 1),
            "critical_completeness": round(self.critical_completeness * 100, 1),
            "missing_critical": self.missing_critical,
            "missing_required": self.missing_required,
            "blocking_issue_count": len(self.blocking_issues),
            "warning_issue_count": len(self.warning_issues),
        }
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all issues (blocking + warning)."""
        return self.blocking_issues + self.warning_issues


class ValidationGate:
    """
    Validation gate that determines if validation can proceed.
    
    This is the critical safeguard that prevents the "100% compliance
    with N/A fields" bug by blocking validation when LC extraction fails.
    """
    
    # Configurable thresholds
    DEFAULT_MIN_COMPLETENESS = 0.3          # Minimum overall completeness
    DEFAULT_MIN_CRITICAL_COMPLETENESS = 0.5  # Minimum critical field completeness
    
    def __init__(
        self,
        min_completeness: float = DEFAULT_MIN_COMPLETENESS,
        min_critical_completeness: float = DEFAULT_MIN_CRITICAL_COMPLETENESS,
        require_lc_number: bool = True,
        require_amount: bool = True,
        require_party: bool = True,
    ):
        self.min_completeness = min_completeness
        self.min_critical_completeness = min_critical_completeness
        self.require_lc_number = require_lc_number
        self.require_amount = require_amount
        self.require_party = require_party
    
    def check_from_text(
        self,
        lc_text: str,
    ) -> GateResult:
        """
        Check validation gate from raw LC text.
        
        This extracts the LCBaseline and checks if validation can proceed.
        """
        # Extract LC with baseline
        extraction_result = extract_lc_with_baseline(lc_text)
        
        return self.check_from_extraction(extraction_result)
    
    def check_from_extraction(
        self,
        extraction_result: LCExtractionResult,
    ) -> GateResult:
        """
        Check validation gate from extraction result.
        """
        baseline = extraction_result.baseline
        
        return self.check_from_baseline(
            baseline,
            extraction_result.completeness,
            extraction_result.critical_completeness,
        )
    
    def check_from_baseline(
        self,
        baseline: LCBaseline,
        completeness: Optional[float] = None,
        critical_completeness: Optional[float] = None,
    ) -> GateResult:
        """
        Check validation gate from LCBaseline.
        """
        # Calculate completeness if not provided
        if completeness is None:
            completeness = baseline.extraction_completeness
        if critical_completeness is None:
            critical_completeness = baseline.critical_completeness
        
        # Collect blocking reasons and warnings
        block_reasons: List[str] = []
        warnings: List[str] = []
        blocking_issues: List[Dict[str, Any]] = []
        warning_issues: List[Dict[str, Any]] = []
        
        # Check 1: LC Number
        if self.require_lc_number and not baseline.lc_number.is_present:
            block_reasons.append("LC number could not be extracted")
            blocking_issues.append(self._create_blocking_issue(
                "LC-GATE-NUMBER",
                "LC Number Not Found",
                "The Letter of Credit reference number could not be extracted. "
                "This is required to identify the credit and proceed with validation.",
                "LC reference number (tag :20: or equivalent)",
                "Not found",
                "Ensure the document is a valid LC with a visible reference number.",
            ))
        
        # Check 2: Amount
        if self.require_amount and not baseline.amount.is_present:
            block_reasons.append("LC amount could not be extracted")
            blocking_issues.append(self._create_blocking_issue(
                "LC-GATE-AMOUNT",
                "LC Amount Not Found",
                "The credit amount could not be extracted from the LC. "
                "This is required to validate invoice amounts and tolerances.",
                "Credit amount with currency (tag :32B: or equivalent)",
                "Not found",
                "Check that the LC document contains a clearly visible amount field.",
            ))
        
        # Check 3: At least one party
        if self.require_party:
            has_applicant = baseline.applicant.is_present
            has_beneficiary = baseline.beneficiary.is_present
            
            if not has_applicant and not has_beneficiary:
                block_reasons.append("Neither applicant nor beneficiary could be extracted")
                blocking_issues.append(self._create_blocking_issue(
                    "LC-GATE-PARTIES",
                    "LC Parties Not Found",
                    "Neither the applicant nor beneficiary could be extracted. "
                    "At least one party is required to proceed with validation.",
                    "Applicant (tag :50:) and/or Beneficiary (tag :59:)",
                    "Neither found",
                    "Verify the LC contains party information and is properly scanned.",
                ))
            elif not has_applicant:
                warnings.append("Applicant not extracted (beneficiary found)")
                warning_issues.append(self._create_warning_issue(
                    "LC-GATE-APPLICANT",
                    "Applicant Not Found",
                    "The applicant name could not be extracted, but beneficiary was found.",
                    "Applicant name and address (tag :50:)",
                    "Not found",
                ))
            elif not has_beneficiary:
                warnings.append("Beneficiary not extracted (applicant found)")
                warning_issues.append(self._create_warning_issue(
                    "LC-GATE-BENEFICIARY",
                    "Beneficiary Not Found",
                    "The beneficiary name could not be extracted, but applicant was found.",
                    "Beneficiary name and address (tag :59:)",
                    "Not found",
                ))
        
        # Check 4: Critical completeness
        if critical_completeness < self.min_critical_completeness:
            block_reasons.append(
                f"Critical field completeness ({critical_completeness*100:.1f}%) "
                f"below minimum ({self.min_critical_completeness*100:.1f}%)"
            )
            blocking_issues.append(self._create_blocking_issue(
                "LC-GATE-CRITICAL",
                "Insufficient Critical Field Extraction",
                f"Only {critical_completeness*100:.1f}% of critical LC fields were extracted. "
                f"Minimum {self.min_critical_completeness*100:.1f}% required.",
                f">= {self.min_critical_completeness*100:.0f}% critical fields extracted",
                f"{critical_completeness*100:.1f}% extracted",
                "Re-scan the LC with better quality or verify document format.",
            ))
        
        # Check 5: Overall completeness
        if completeness < self.min_completeness:
            block_reasons.append(
                f"Overall extraction completeness ({completeness*100:.1f}%) "
                f"below minimum ({self.min_completeness*100:.1f}%)"
            )
            blocking_issues.append(self._create_blocking_issue(
                "LC-GATE-COMPLETENESS",
                "Insufficient Field Extraction",
                f"Only {completeness*100:.1f}% of LC fields were successfully extracted. "
                f"Minimum {self.min_completeness*100:.1f}% required for reliable validation.",
                f">= {self.min_completeness*100:.0f}% fields extracted",
                f"{completeness*100:.1f}% extracted",
                "Check document quality or verify it is a valid Letter of Credit.",
            ))
        
        # Add issues for other missing fields (as warnings, not blockers)
        for field_result in baseline.get_missing_required():
            if field_result.priority == FieldPriority.REQUIRED:
                warning_issues.append(self._create_warning_issue(
                    f"LC-MISSING-{field_result.field_name.upper()}",
                    f"Missing {field_result.field_name.replace('_', ' ').title()}",
                    f"The {field_result.field_name.replace('_', ' ')} field could not be extracted.",
                    f"{field_result.field_name.replace('_', ' ').title()} value",
                    "Not found",
                ))
        
        # Determine gate status
        if block_reasons:
            status = GateStatus.BLOCKED
            can_proceed = False
            block_reason = "; ".join(block_reasons)
        elif warnings:
            status = GateStatus.WARNING
            can_proceed = True
            block_reason = None
        else:
            status = GateStatus.PASSED
            can_proceed = True
            block_reason = None
        
        logger.info(
            "Validation gate check: status=%s, can_proceed=%s, completeness=%.1f%%, critical=%.1f%%",
            status.value, can_proceed, completeness * 100, critical_completeness * 100
        )
        
        return GateResult(
            status=status,
            can_proceed=can_proceed,
            block_reason=block_reason,
            warnings=warnings,
            baseline=baseline,
            completeness=completeness,
            critical_completeness=critical_completeness,
            missing_critical=[f.field_name for f in baseline.get_missing_critical()],
            missing_required=[f.field_name for f in baseline.get_missing_required()],
            blocking_issues=blocking_issues,
            warning_issues=warning_issues,
        )
    
    def check_lc_presence(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Quick check if LC document is present in payload.
        
        Returns:
            (is_present, error_message)
        """
        lc_context = payload.get("lc") or {}
        documents = payload.get("documents") or []
        documents_presence = payload.get("documents_presence") or {}
        
        # Check if LC is in documents
        has_lc_doc = any(
            doc.get("document_type") == "letter_of_credit" or 
            doc.get("type") == "letter_of_credit"
            for doc in documents
        )
        
        # Check documents_presence
        lc_presence = documents_presence.get("letter_of_credit", {})
        lc_present = lc_presence.get("present", False)
        
        # Check if LC context has any meaningful data
        has_lc_data = bool(lc_context) and any(
            lc_context.get(key) for key in ["number", "amount", "applicant", "beneficiary"]
        )
        
        if not has_lc_doc and not lc_present and not has_lc_data:
            return False, "No Letter of Credit document detected in upload"
        
        return True, None
    
    def _create_blocking_issue(
        self,
        rule_id: str,
        title: str,
        message: str,
        expected: str,
        actual: str,
        suggestion: str,
    ) -> Dict[str, Any]:
        """Create a blocking issue."""
        return {
            "rule": rule_id,
            "title": title,
            "passed": False,
            "severity": "critical",
            "message": message,
            "expected": expected,
            "actual": actual,
            "suggestion": suggestion,
            "documents": ["Letter of Credit"],
            "document_names": ["Letter of Credit"],
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.gate",
            "blocks_validation": True,
            "auto_generated": True,
        }
    
    def _create_warning_issue(
        self,
        rule_id: str,
        title: str,
        message: str,
        expected: str,
        actual: str,
    ) -> Dict[str, Any]:
        """Create a warning issue."""
        return {
            "rule": rule_id,
            "title": title,
            "passed": False,
            "severity": "major",
            "message": message,
            "expected": expected,
            "actual": actual,
            "suggestion": "Review the LC document and verify field visibility.",
            "documents": ["Letter of Credit"],
            "document_names": ["Letter of Credit"],
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.gate",
            "blocks_validation": False,
            "auto_generated": True,
        }


def create_blocked_response(
    gate_result: GateResult,
    processing_time_seconds: float = 0.0,
) -> Dict[str, Any]:
    """
    Create a blocked validation response.
    
    This is returned when validation gate fails, providing clear
    information about why validation could not proceed.
    """
    return {
        "validation_blocked": True,
        "validation_status": "blocked",
        "block_reason": gate_result.block_reason,
        
        # Processing summary showing blocked state
        "processing_summary": {
            "documents": 0,
            "verified": 0,
            "warnings": len(gate_result.warning_issues),
            "errors": len(gate_result.blocking_issues),
            "compliance_rate": 0,  # 0% when blocked
            "processing_time_seconds": round(processing_time_seconds, 2),
            "extraction_quality": round(gate_result.completeness * 100),
            "discrepancies": len(gate_result.get_all_issues()),
            "status_counts": {
                "error": len(gate_result.blocking_issues),
                "warning": len(gate_result.warning_issues),
                "success": 0,
            },
        },
        
        # Issues explaining why blocked
        "issues": gate_result.get_all_issues(),
        "issue_cards": gate_result.get_all_issues(),
        
        # Gate details
        "gate_result": gate_result.to_dict(),
        
        # Empty document status
        "document_status": {
            "success": 0,
            "warning": 0,
            "error": 1,  # LC has error
        },
        
        # Extraction summary
        "extraction_summary": {
            "completeness": round(gate_result.completeness * 100, 1),
            "critical_completeness": round(gate_result.critical_completeness * 100, 1),
            "missing_critical": gate_result.missing_critical,
            "missing_required": gate_result.missing_required,
        },
        
        # Analytics showing failure
        "analytics": {
            "extraction_accuracy": round(gate_result.completeness * 100),
            "lc_compliance_score": 0,
            "customs_ready_score": 0,
            "documents_processed": 0,
            "document_status_distribution": {
                "success": 0,
                "warning": 0,
                "error": 1,
            },
        },
    }


# Module-level instance
_validation_gate: Optional[ValidationGate] = None


def get_validation_gate() -> ValidationGate:
    """Get the global validation gate instance."""
    global _validation_gate
    if _validation_gate is None:
        _validation_gate = ValidationGate()
    return _validation_gate


def check_validation_gate(
    lc_text: Optional[str] = None,
    baseline: Optional[LCBaseline] = None,
    extraction_result: Optional[LCExtractionResult] = None,
) -> GateResult:
    """
    Convenience function to check the validation gate.
    
    Provide one of:
    - lc_text: Raw LC text to extract and check
    - baseline: LCBaseline to check
    - extraction_result: LCExtractionResult to check
    """
    gate = get_validation_gate()
    
    if extraction_result is not None:
        return gate.check_from_extraction(extraction_result)
    elif baseline is not None:
        return gate.check_from_baseline(baseline)
    elif lc_text is not None:
        return gate.check_from_text(lc_text)
    else:
        # No input - return blocked
        return GateResult(
            status=GateStatus.BLOCKED,
            can_proceed=False,
            block_reason="No LC data provided",
            blocking_issues=[{
                "rule": "LC-GATE-NO-INPUT",
                "title": "No LC Document",
                "passed": False,
                "severity": "critical",
                "message": "No Letter of Credit document was provided for validation.",
                "expected": "LC document upload",
                "actual": "No LC found",
                "suggestion": "Upload a Letter of Credit document to proceed.",
                "documents": ["Letter of Credit"],
                "display_card": True,
                "ruleset_domain": "icc.lcopilot.gate",
                "blocks_validation": True,
            }],
        )

