"""
Response Contract Validator - Output-First Validation Layer

This module validates that the backend response contains all required fields
before returning to the frontend. This catches extraction issues early and
provides clear warnings to users about what data may be missing.

Contract validation runs AFTER all processing is complete but BEFORE the
response is returned, ensuring data completeness without blocking the flow.

Key Principle: Missing data should be visible, not silent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContractSeverity(str, Enum):
    """Severity level for contract warnings."""
    ERROR = "error"      # Critical field missing - may cause downstream failures
    WARNING = "warning"  # Recommended field missing - functionality degraded
    INFO = "info"        # Optional field missing - noted for completeness


@dataclass
class ContractWarning:
    """A single contract validation warning."""
    field: str
    message: str
    severity: ContractSeverity
    source: str  # Which section of the response (lc_data, processing_summary, etc.)
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "suggestion": self.suggestion,
        }


@dataclass
class ContractValidationResult:
    """Result of contract validation."""
    valid: bool  # True if no errors (warnings are OK)
    warnings: List[ContractWarning] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "warnings": [w.to_dict() for w in self.warnings],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
        }


# =============================================================================
# FIELD DEFINITIONS
# =============================================================================

# Critical LC fields - should always be present for valid LC processing
REQUIRED_LC_FIELDS = {
    "number": "LC number is required for document identification",
    "amount": "LC amount is required for value matching",
    "currency": "Currency code is required for amount validation",
}

# Important LC fields - should be present for full validation coverage
RECOMMENDED_LC_FIELDS = {
    "expiry_date": "Expiry date helps validate shipment timelines",
    "issuing_bank": "Issuing bank is needed for bank-specific rules",
    "applicant": "Applicant details needed for party matching",
    "beneficiary": "Beneficiary details needed for party matching",
    "additional_conditions": "47A Additional Conditions may contain PO/BIN/TIN requirements",
    "goods_description": "Goods description needed for invoice matching",
}

# Optional LC fields - nice to have
OPTIONAL_LC_FIELDS = {
    "latest_shipment_date": "Latest shipment date for B/L validation",
    "port_of_loading": "Port of loading for B/L matching",
    "port_of_discharge": "Port of discharge for B/L matching",
    "incoterm": "Incoterm for insurance coverage validation",
    "partial_shipment": "Partial shipment terms",
    "transhipment": "Transhipment permissions",
}

# Required processing summary fields
REQUIRED_SUMMARY_FIELDS = {
    "documents": "Document count is required",
}

# Required analytics fields
REQUIRED_ANALYTICS_FIELDS = {
    "compliance_score": "Compliance score should be calculated",
}


def _get_nested_value(data: Dict[str, Any], key: str) -> Any:
    """Get a value from nested dict, supporting dot notation."""
    if not data:
        return None
    
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _is_empty(value: Any) -> bool:
    """Check if a value is effectively empty."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def validate_response_contract(
    structured_result: Dict[str, Any],
    strict: bool = False,
) -> ContractValidationResult:
    """
    Validate that the response has all required and recommended fields.
    
    Args:
        structured_result: The full validation response payload
        strict: If True, recommended fields also trigger warnings
        
    Returns:
        ContractValidationResult with any warnings found
    """
    warnings: List[ContractWarning] = []
    
    # ==========================================================================
    # LC DATA VALIDATION
    # ==========================================================================
    lc_data = structured_result.get("lc_data") or {}
    
    # Also check alternative locations for LC data
    if not lc_data:
        lc_data = structured_result.get("extracted_context", {}).get("lc", {})
    if not lc_data:
        lc_data = structured_result.get("mt700", {})
    
    # Required LC fields
    for field_key, reason in REQUIRED_LC_FIELDS.items():
        # Map field names to various possible locations
        possible_keys = [field_key]
        if field_key == "number":
            possible_keys.extend(["lc_number", "20"])
        elif field_key == "amount":
            possible_keys.extend(["lc_amount", "32B_amount", "total_amount"])
        elif field_key == "currency":
            possible_keys.extend(["32B_currency", "currency_code"])
        
        found = False
        for key in possible_keys:
            if not _is_empty(lc_data.get(key)):
                found = True
                break
        
        if not found:
            warnings.append(ContractWarning(
                field=field_key,
                message=f"LC {field_key} missing from extraction - {reason}",
                severity=ContractSeverity.ERROR,
                source="lc_data",
                suggestion=f"Ensure the LC document contains the {field_key} field clearly visible",
            ))
    
    # Recommended LC fields
    for field_key, reason in RECOMMENDED_LC_FIELDS.items():
        possible_keys = [field_key]
        if field_key == "additional_conditions":
            possible_keys.extend(["47A", "conditions", "47a_conditions"])
        elif field_key == "expiry_date":
            possible_keys.extend(["31D", "expiry", "31D_date"])
        elif field_key == "issuing_bank":
            possible_keys.extend(["51a", "issuing_bank_name", "51A"])
        elif field_key == "applicant":
            possible_keys.extend(["50", "applicant_name"])
        elif field_key == "beneficiary":
            possible_keys.extend(["59", "beneficiary_name"])
        elif field_key == "goods_description":
            possible_keys.extend(["45A", "goods", "description_of_goods"])
        
        found = False
        for key in possible_keys:
            value = lc_data.get(key)
            if not _is_empty(value):
                found = True
                break
        
        if not found:
            # Special handling for 47A - always warn as it's critical for validation
            severity = ContractSeverity.WARNING
            if field_key == "additional_conditions":
                # 47A is particularly important - may contain PO/BIN/TIN requirements
                warnings.append(ContractWarning(
                    field="47A_additional_conditions",
                    message="47A Additional Conditions not extracted - may miss PO/BIN/TIN validation requirements",
                    severity=ContractSeverity.WARNING,
                    source="lc_data",
                    suggestion="Check if the LC contains Field 47A with additional documentary requirements",
                ))
            elif strict:
                warnings.append(ContractWarning(
                    field=field_key,
                    message=f"{field_key.replace('_', ' ').title()} not extracted - {reason}",
                    severity=severity,
                    source="lc_data",
                    suggestion=None,
                ))
    
    # ==========================================================================
    # PROCESSING SUMMARY VALIDATION
    # ==========================================================================
    processing_summary = structured_result.get("processing_summary") or {}
    
    for field_key, reason in REQUIRED_SUMMARY_FIELDS.items():
        value = processing_summary.get(field_key)
        if value is None:
            warnings.append(ContractWarning(
                field=field_key,
                message=f"Processing summary missing {field_key} - {reason}",
                severity=ContractSeverity.WARNING,
                source="processing_summary",
                suggestion=None,
            ))
    
    # Check for zero documents (likely an issue)
    doc_count = processing_summary.get("documents", 0)
    if doc_count == 0:
        warnings.append(ContractWarning(
            field="documents",
            message="No documents in processing summary - validation may be incomplete",
            severity=ContractSeverity.WARNING,
            source="processing_summary",
            suggestion="Ensure documents were uploaded and processed successfully",
        ))

    # Authoritative verdict contract for evaluation mode
    if not structured_result.get("authoritative_verdict") and not structured_result.get("verdict_signature"):
        warnings.append(ContractWarning(
            field="authoritative_verdict",
            message="Authoritative verdict contract field absent; evaluator uses fallback signal mapping",
            severity=ContractSeverity.INFO,
            source="structured_result",
            suggestion="Add authoritative_verdict.label + source + rationale before client consumption",
        ))

    # ==========================================================================
    # ANALYTICS VALIDATION
    # ==========================================================================
    analytics = structured_result.get("analytics") or {}
    
    compliance_score = analytics.get("compliance_score") or analytics.get("lc_compliance_score")
    if compliance_score is None:
        warnings.append(ContractWarning(
            field="compliance_score",
            message="Compliance score not calculated",
            severity=ContractSeverity.INFO,
            source="analytics",
            suggestion=None,
        ))
    
    # ==========================================================================
    # ISSUES VALIDATION
    # ==========================================================================
    issues = structured_result.get("issues") or []
    
    # Check for issues with missing required fields
    for i, issue in enumerate(issues):
        if not issue.get("title"):
            warnings.append(ContractWarning(
                field=f"issues[{i}].title",
                message=f"Issue #{i+1} missing title",
                severity=ContractSeverity.INFO,
                source="issues",
                suggestion=None,
            ))
        if not issue.get("severity"):
            warnings.append(ContractWarning(
                field=f"issues[{i}].severity",
                message=f"Issue #{i+1} missing severity - defaulting to 'minor'",
                severity=ContractSeverity.INFO,
                source="issues",
                suggestion=None,
            ))
    
    # ==========================================================================
    # BUILD RESULT
    # ==========================================================================
    error_count = sum(1 for w in warnings if w.severity == ContractSeverity.ERROR)
    warning_count = sum(1 for w in warnings if w.severity == ContractSeverity.WARNING)
    info_count = sum(1 for w in warnings if w.severity == ContractSeverity.INFO)
    
    # Valid if no errors (warnings are OK - they're informational)
    valid = error_count == 0
    
    if warnings:
        logger.warning(
            "Contract validation found %d issue(s): %d errors, %d warnings, %d info",
            len(warnings), error_count, warning_count, info_count
        )
        for w in warnings:
            if w.severity == ContractSeverity.ERROR:
                logger.error("  [%s] %s: %s", w.severity.value.upper(), w.field, w.message)
            elif w.severity == ContractSeverity.WARNING:
                logger.warning("  [%s] %s: %s", w.severity.value.upper(), w.field, w.message)
            else:
                logger.info("  [%s] %s: %s", w.severity.value.upper(), w.field, w.message)
    else:
        logger.info("Contract validation passed - all required fields present")
    
    return ContractValidationResult(
        valid=valid,
        warnings=warnings,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
    )


def add_contract_warnings_to_response(
    structured_result: Dict[str, Any],
    validation_result: ContractValidationResult,
) -> Dict[str, Any]:
    """
    Add contract warnings to the response payload.
    
    This modifies the structured_result in place and returns it.
    """
    if validation_result.warnings:
        structured_result["_contract_warnings"] = [
            w.to_dict() for w in validation_result.warnings
        ]
        structured_result["_contract_validation"] = {
            "valid": validation_result.valid,
            "error_count": validation_result.error_count,
            "warning_count": validation_result.warning_count,
            "info_count": validation_result.info_count,
        }
    
    return structured_result


# Convenience function for single-call usage
def validate_and_annotate_response(
    structured_result: Dict[str, Any],
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Validate response contract and add warnings to the payload.
    
    This is the main entry point for contract validation.
    
    Args:
        structured_result: The full validation response payload
        strict: If True, recommended fields also trigger warnings
        
    Returns:
        The structured_result with _contract_warnings added if any found
    """
    result = validate_response_contract(structured_result, strict=strict)
    return add_contract_warnings_to_response(structured_result, result)

