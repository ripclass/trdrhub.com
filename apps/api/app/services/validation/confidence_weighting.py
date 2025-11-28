"""
Confidence Weighting for OCR Noise

When OCR extraction has low confidence, validation results should be adjusted:
- Low OCR confidence → potential false negative (field might exist but wasn't extracted)
- High OCR confidence → trust the extraction result

This module provides:
1. Severity escalation based on OCR confidence
2. Audit trail showing confidence factors
3. Recommendations for manual verification
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""
    HIGH = "high"           # >= 0.85 - Trust extraction
    MEDIUM = "medium"       # 0.6-0.85 - Likely correct
    LOW = "low"             # 0.3-0.6 - Uncertain
    VERY_LOW = "very_low"   # < 0.3 - Unreliable


@dataclass
class ConfidenceAdjustment:
    """Result of confidence-based adjustment."""
    original_severity: str
    adjusted_severity: str
    ocr_confidence: float
    confidence_level: ConfidenceLevel
    ambiguity_factor: float
    adjustment_applied: bool
    reason: str
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_severity": self.original_severity,
            "adjusted_severity": self.adjusted_severity,
            "ocr_confidence": round(self.ocr_confidence, 3),
            "confidence_level": self.confidence_level.value,
            "ambiguity_factor": round(self.ambiguity_factor, 3),
            "adjustment_applied": self.adjustment_applied,
            "reason": self.reason,
            "recommendation": self.recommendation,
        }


def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """Categorize confidence score into levels."""
    if confidence >= 0.85:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.6:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


def calculate_ambiguity_factor(ocr_confidence: float) -> float:
    """
    Calculate ambiguity factor from OCR confidence.
    
    Ambiguity = 1 - confidence
    Used to potentially escalate severity.
    """
    return max(0.0, min(1.0, 1.0 - ocr_confidence))


def adjust_severity_for_confidence(
    base_severity: str,
    ocr_confidence: float,
    field_is_critical: bool = False,
) -> ConfidenceAdjustment:
    """
    Adjust issue severity based on OCR confidence.
    
    Rules:
    - High confidence (>=0.85): Keep original severity
    - Medium confidence (0.6-0.85): Keep or escalate by 1 level
    - Low confidence (0.3-0.6): Escalate by 1 level, add manual review note
    - Very low confidence (<0.3): Escalate + flag for manual verification
    
    Args:
        base_severity: Original severity from validator ("critical", "major", "minor")
        ocr_confidence: OCR extraction confidence (0.0-1.0)
        field_is_critical: Whether the field being checked is critical for LC compliance
        
    Returns:
        ConfidenceAdjustment with adjusted severity and audit info
    """
    confidence_level = get_confidence_level(ocr_confidence)
    ambiguity = calculate_ambiguity_factor(ocr_confidence)
    
    # Severity hierarchy for escalation
    severity_order = ["minor", "major", "critical"]
    
    # Normalize input
    base_lower = base_severity.lower()
    if base_lower not in severity_order:
        base_lower = "minor"
    
    base_index = severity_order.index(base_lower)
    adjusted_index = base_index
    adjustment_applied = False
    reason = ""
    recommendation = ""
    
    if confidence_level == ConfidenceLevel.HIGH:
        # Trust the extraction
        reason = "High OCR confidence - extraction trusted"
        recommendation = ""
        
    elif confidence_level == ConfidenceLevel.MEDIUM:
        # Generally trust, but note the confidence
        reason = "Medium OCR confidence - result likely correct"
        recommendation = "Consider spot-checking extracted values"
        
    elif confidence_level == ConfidenceLevel.LOW:
        # Escalate severity by 1 level
        if base_index < len(severity_order) - 1:
            adjusted_index = base_index + 1
            adjustment_applied = True
        reason = f"Low OCR confidence ({ocr_confidence:.2f}) - severity escalated"
        recommendation = "Manual verification recommended - OCR extraction uncertain"
        
    else:  # VERY_LOW
        # Escalate to at least major, flag heavily
        if base_index < len(severity_order) - 1:
            adjusted_index = min(base_index + 1, len(severity_order) - 1)
            adjustment_applied = True
        if field_is_critical:
            adjusted_index = len(severity_order) - 1  # Make critical
            adjustment_applied = True
        reason = f"Very low OCR confidence ({ocr_confidence:.2f}) - extraction unreliable"
        recommendation = "MANUAL VERIFICATION REQUIRED - OCR extraction may be incorrect"
    
    adjusted_severity = severity_order[adjusted_index]
    
    return ConfidenceAdjustment(
        original_severity=base_severity,
        adjusted_severity=adjusted_severity,
        ocr_confidence=ocr_confidence,
        confidence_level=confidence_level,
        ambiguity_factor=ambiguity,
        adjustment_applied=adjustment_applied,
        reason=reason,
        recommendation=recommendation,
    )


def get_field_confidence(
    extracted_data: Dict[str, Any],
    field_name: str,
) -> float:
    """
    Get confidence score for a specific field from extraction data.
    
    Looks for confidence in:
    - _field_details.{field_name}.confidence
    - _extraction_confidence (document-level)
    - Default to 0.5 if not found
    """
    # Try field-specific confidence
    field_details = extracted_data.get("_field_details", {})
    if isinstance(field_details, dict):
        field_info = field_details.get(field_name, {})
        if isinstance(field_info, dict) and "confidence" in field_info:
            return float(field_info["confidence"])
    
    # Try document-level confidence
    doc_confidence = extracted_data.get("_extraction_confidence")
    if doc_confidence is not None:
        return float(doc_confidence)
    
    # Check for two-stage validation confidence
    two_stage = extracted_data.get("_two_stage_validation", {})
    if isinstance(two_stage, dict):
        ai_conf = two_stage.get("ai_confidence", 0.5)
        return float(ai_conf)
    
    # Default
    return 0.5


def batch_adjust_issues(
    issues: List[Dict[str, Any]],
    extraction_data: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Adjust severity for a batch of issues based on OCR confidence.
    
    Args:
        issues: List of validation issues
        extraction_data: Dict of document_type -> extracted_data
        
    Returns:
        Issues with adjusted severities and confidence audit info
    """
    adjusted_issues = []
    
    for issue in issues:
        issue_copy = issue.copy()
        
        # Get relevant document's extraction data
        documents = issue.get("documents", []) or issue.get("document_names", [])
        doc_type = documents[0] if documents else "unknown"
        
        # Normalize document type
        doc_type_key = doc_type.lower().replace(" ", "_")
        doc_data = extraction_data.get(doc_type_key, {})
        
        # Get field being checked
        source_field = issue.get("source_field", "")
        
        # Get confidence for this field
        confidence = get_field_confidence(doc_data, source_field)
        
        # Determine if field is critical
        critical_fields = {"amount", "lc_number", "beneficiary", "expiry_date", "latest_shipment"}
        field_is_critical = source_field.lower() in critical_fields
        
        # Adjust severity
        base_severity = issue.get("severity", "minor")
        adjustment = adjust_severity_for_confidence(
            base_severity=base_severity,
            ocr_confidence=confidence,
            field_is_critical=field_is_critical,
        )
        
        # Apply adjustment
        issue_copy["severity"] = adjustment.adjusted_severity
        issue_copy["confidence_adjustment"] = adjustment.to_dict()
        
        # Add recommendation to suggestion if needed
        if adjustment.recommendation:
            existing_suggestion = issue_copy.get("suggestion", "")
            if existing_suggestion:
                issue_copy["suggestion"] = f"{existing_suggestion}\n\n⚠️ {adjustment.recommendation}"
            else:
                issue_copy["suggestion"] = adjustment.recommendation
        
        adjusted_issues.append(issue_copy)
        
        if adjustment.adjustment_applied:
            logger.info(
                f"Issue severity adjusted: {base_severity} → {adjustment.adjusted_severity} "
                f"(OCR confidence: {confidence:.2f}, field: {source_field})"
            )
    
    return adjusted_issues


def calculate_overall_extraction_confidence(
    extraction_data: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculate overall extraction confidence across all documents.
    
    Returns summary with:
    - Average confidence
    - Lowest confidence document
    - Recommendations
    """
    confidences = []
    lowest_doc = None
    lowest_conf = 1.0
    
    for doc_type, data in extraction_data.items():
        if doc_type.startswith("_"):
            continue
        
        conf = data.get("_extraction_confidence", 0.5)
        confidences.append(conf)
        
        if conf < lowest_conf:
            lowest_conf = conf
            lowest_doc = doc_type
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    recommendations = []
    if avg_confidence < 0.6:
        recommendations.append("Overall extraction quality is low - consider re-uploading clearer documents")
    if lowest_conf < 0.4 and lowest_doc:
        recommendations.append(f"Document '{lowest_doc}' has very low extraction quality - manual verification required")
    
    return {
        "average_confidence": round(avg_confidence, 3),
        "documents_analyzed": len(confidences),
        "lowest_confidence_document": lowest_doc,
        "lowest_confidence_value": round(lowest_conf, 3),
        "overall_level": get_confidence_level(avg_confidence).value,
        "recommendations": recommendations,
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ConfidenceLevel",
    "ConfidenceAdjustment",
    "get_confidence_level",
    "calculate_ambiguity_factor",
    "adjust_severity_for_confidence",
    "get_field_confidence",
    "batch_adjust_issues",
    "calculate_overall_extraction_confidence",
]

