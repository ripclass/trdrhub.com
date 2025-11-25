"""
LC Extractor V2 - Phase 2: Enhanced LC Extraction with Baseline Tracking

This module provides the new extraction entry point that:
1. Uses existing parsers (MT700, regex, 46A, 47A)
2. Wraps results in LCBaseline for field tracking
3. Calculates extraction completeness
4. Generates missing field issues

Usage:
    from app.services.extraction.lc_extractor_v2 import extract_lc_with_baseline
    
    result = extract_lc_with_baseline(raw_text)
    if not result.baseline.is_valid_for_validation:
        # Block validation
        issues = result.baseline.generate_missing_field_issues()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from .lc_extractor import extract_lc_structured
from .lc_baseline import (
    LCBaseline,
    create_lc_baseline_from_extraction,
    FieldPriority,
    ExtractionStatus,
)


logger = logging.getLogger(__name__)


@dataclass
class LCExtractionResult:
    """
    Complete result of LC extraction with baseline tracking.
    
    This is the new return type for LC extraction that provides
    everything needed for validation gating and issue generation.
    """
    # The structured baseline with field tracking
    baseline: LCBaseline
    
    # Raw extraction output (for backward compatibility)
    raw_extraction: Dict[str, Any]
    
    # Extraction metadata
    extraction_time_ms: int
    source_parsers: List[str]
    raw_text_length: int
    
    # Validation readiness
    is_valid: bool
    validation_blocked: bool
    block_reason: Optional[str]
    
    # Pre-generated issues for missing fields
    missing_field_issues: List[Dict[str, Any]]
    
    # Completeness scores
    completeness: float  # 0.0 to 1.0
    critical_completeness: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "baseline": self.baseline.to_dict(),
            "extraction_time_ms": self.extraction_time_ms,
            "source_parsers": self.source_parsers,
            "is_valid": self.is_valid,
            "validation_blocked": self.validation_blocked,
            "block_reason": self.block_reason,
            "completeness": round(self.completeness * 100, 1),
            "critical_completeness": round(self.critical_completeness * 100, 1),
            "missing_field_count": len(self.missing_field_issues),
            "missing_critical_count": len(self.baseline.get_missing_critical()),
            # Include raw for backward compatibility
            "structured": self.raw_extraction,
        }
    
    def get_validation_gate_result(self) -> Dict[str, Any]:
        """
        Get the result for validation gating (Phase 4).
        
        Returns a dict that can be used to decide whether to proceed with validation.
        """
        return {
            "can_proceed": not self.validation_blocked,
            "is_valid": self.is_valid,
            "block_reason": self.block_reason,
            "completeness": self.completeness,
            "critical_completeness": self.critical_completeness,
            "missing_critical": [f.field_name for f in self.baseline.get_missing_critical()],
            "missing_required": [f.field_name for f in self.baseline.get_missing_required()],
            "issue_count": len(self.missing_field_issues),
            "critical_issue_count": sum(
                1 for issue in self.missing_field_issues
                if issue.get("severity") == "critical"
            ),
        }


def extract_lc_with_baseline(
    raw_text: str,
    min_completeness: float = 0.3,
    require_lc_number: bool = True,
    require_amount: bool = True,
) -> LCExtractionResult:
    """
    Extract LC data with full baseline tracking.
    
    This is the new primary entry point for LC extraction that:
    1. Runs existing extraction logic
    2. Wraps results in LCBaseline
    3. Calculates completeness
    4. Determines if validation should proceed
    5. Generates issues for missing fields
    
    Args:
        raw_text: OCR text from LC document
        min_completeness: Minimum completeness to allow validation (default 0.3)
        require_lc_number: Block if LC number not found (default True)
        require_amount: Block if amount not found (default True)
    
    Returns:
        LCExtractionResult with baseline, completeness, and issues
    """
    start_time = time.perf_counter()
    
    # Run existing extraction
    try:
        extraction_result = extract_lc_structured(raw_text)
    except Exception as e:
        logger.error("LC extraction failed: %s", e)
        extraction_result = {}
    
    extraction_time_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Determine source parsers from extraction result
    source_parsers = extraction_result.get("source", {}).get("parsers", ["unknown"])
    
    # Create baseline from extraction
    baseline = create_lc_baseline_from_extraction(
        extraction_result,
        raw_text=raw_text,
        source_parsers=source_parsers,
    )
    baseline._extraction_time_ms = extraction_time_ms
    
    # Calculate completeness
    completeness = baseline.extraction_completeness
    critical_completeness = baseline.critical_completeness
    
    # Determine if validation should be blocked
    validation_blocked = False
    block_reason = None
    
    # Check 1: Minimum completeness
    if completeness < min_completeness:
        validation_blocked = True
        block_reason = f"Extraction completeness ({completeness*100:.1f}%) below minimum threshold ({min_completeness*100:.1f}%)"
    
    # Check 2: LC number required
    if require_lc_number and not baseline.lc_number.is_present:
        validation_blocked = True
        block_reason = "LC number could not be extracted - cannot identify the Letter of Credit"
    
    # Check 3: Amount required
    if require_amount and not baseline.amount.is_present:
        validation_blocked = True
        block_reason = "LC amount could not be extracted - cannot validate document amounts"
    
    # Check 4: Critical fields
    missing_critical = baseline.get_missing_critical()
    if len(missing_critical) >= 3:  # More than half of critical fields missing
        validation_blocked = True
        block_reason = f"Too many critical fields missing: {[f.field_name for f in missing_critical]}"
    
    # Generate issues for missing fields
    missing_field_issues = baseline.generate_missing_field_issues()
    
    # Determine overall validity
    is_valid = baseline.is_valid_for_validation and completeness >= min_completeness
    
    logger.info(
        "LC extraction complete: valid=%s, blocked=%s, completeness=%.1f%%, critical=%.1f%%, issues=%d, time=%dms",
        is_valid, validation_blocked, completeness * 100, critical_completeness * 100,
        len(missing_field_issues), extraction_time_ms
    )
    
    return LCExtractionResult(
        baseline=baseline,
        raw_extraction=extraction_result,
        extraction_time_ms=extraction_time_ms,
        source_parsers=source_parsers,
        raw_text_length=len(raw_text) if raw_text else 0,
        is_valid=is_valid,
        validation_blocked=validation_blocked,
        block_reason=block_reason,
        missing_field_issues=missing_field_issues,
        completeness=completeness,
        critical_completeness=critical_completeness,
    )


def extract_lc_structured_v2(raw_text: str) -> Dict[str, Any]:
    """
    Drop-in replacement for extract_lc_structured that includes baseline metadata.
    
    This provides backward compatibility while adding the new extraction tracking.
    The return format is compatible with existing code but includes additional
    extraction_summary and field_status keys.
    """
    result = extract_lc_with_baseline(raw_text)
    
    # Merge baseline data into raw extraction for compatibility
    output = dict(result.raw_extraction)
    
    # Add new tracking data
    output["extraction_summary"] = result.baseline.get_extraction_summary()
    output["field_status"] = {
        f.field_name: {
            "status": f.status.value,
            "priority": f.priority.value,
            "confidence": f.confidence,
        }
        for f in result.baseline.get_all_fields()
    }
    output["validation_gate"] = result.get_validation_gate_result()
    output["extraction_time_ms"] = result.extraction_time_ms
    
    return output


# ---------------------------------------------------------------------------
# Utility functions for validation integration
# ---------------------------------------------------------------------------

def check_lc_extraction_gate(
    extraction_result: LCExtractionResult,
) -> Dict[str, Any]:
    """
    Check if LC extraction passes the gate for validation.
    
    Returns a dict with:
    - passed: bool - Whether validation can proceed
    - issues: List - Issues to add if gate failed
    - reason: str - Human-readable reason for failure
    """
    if not extraction_result.validation_blocked:
        return {
            "passed": True,
            "issues": [],
            "reason": None,
        }
    
    # Create a blocking issue
    blocking_issue = {
        "rule": "LC-EXTRACTION-GATE",
        "title": "LC Extraction Failed - Validation Blocked",
        "passed": False,
        "severity": "critical",
        "message": extraction_result.block_reason or "LC extraction did not meet minimum requirements",
        "expected": "LC document with extractable key fields (number, amount, parties)",
        "actual": f"Extraction completeness: {extraction_result.completeness*100:.1f}%",
        "suggestion": (
            "Please ensure the uploaded document is a valid Letter of Credit. "
            "Check that the document is clear, well-scanned, and contains standard LC fields."
        ),
        "documents": ["Letter of Credit"],
        "document_names": ["Letter of Credit"],
        "display_card": True,
        "ruleset_domain": "icc.lcopilot.extraction",
        "auto_generated": True,
        "blocks_validation": True,
    }
    
    # Combine with missing field issues
    all_issues = [blocking_issue] + extraction_result.missing_field_issues
    
    return {
        "passed": False,
        "issues": all_issues,
        "reason": extraction_result.block_reason,
        "completeness": extraction_result.completeness,
        "missing_critical": [f.field_name for f in extraction_result.baseline.get_missing_critical()],
    }


def get_lc_baseline_for_validation(
    raw_text: str,
) -> tuple[Optional[LCBaseline], List[Dict[str, Any]], bool]:
    """
    Convenience function to get LC baseline for validation.
    
    Returns:
        (baseline, issues, can_proceed)
        
    If can_proceed is False, issues contains blocking issues.
    """
    result = extract_lc_with_baseline(raw_text)
    
    if result.validation_blocked:
        all_issues = [
            {
                "rule": "LC-EXTRACTION-BLOCKED",
                "title": "LC Extraction Blocked",
                "passed": False,
                "severity": "critical",
                "message": result.block_reason,
                "expected": "Valid LC extraction",
                "actual": f"Completeness: {result.completeness*100:.1f}%",
                "display_card": True,
                "blocks_validation": True,
            }
        ] + result.missing_field_issues
        
        return result.baseline, all_issues, False
    
    return result.baseline, result.missing_field_issues, True

