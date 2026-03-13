"""
Validation Utilities Module

Pure utility functions with no external dependencies.
Handles string manipulation, type coercion, and formatting.
"""

import json
import re
from typing import Any, Dict, Optional

from app.services.crossdoc import DEFAULT_LABELS


# =============================================================================
# SEVERITY UTILITIES
# =============================================================================

def severity_rank(severity: Optional[str]) -> int:
    """Get numeric rank for severity comparison."""
    order = {
        "critical": 3,
        "error": 3,
        "major": 2,
        "warning": 2,
        "warn": 2,
        "minor": 1,
    }
    if not severity:
        return 0
    return order.get(severity.lower(), 1)


def severity_to_status(severity: Optional[str]) -> str:
    """Convert severity to UI status (success/warning/error)."""
    if not severity:
        return "success"
    normalized = severity.lower()
    if normalized in {"critical", "error"}:
        return "error"
    if normalized in {"major", "warning", "warn", "minor"}:
        return "warning"
    return "success"


def normalize_issue_severity(value: Optional[str]) -> str:
    """Normalize issue severity to standard values: critical, major, minor."""
    if not value:
        return "minor"
    normalized = value.lower()
    if normalized in {"critical", "high"}:
        return "critical"
    if normalized in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def priority_to_severity(priority: Optional[str], fallback: Optional[str]) -> str:
    """Convert priority to severity."""
    if priority:
        normalized = priority.lower()
        if normalized in {"high", "critical"}:
            return "critical"
        if normalized in {"medium", "major"}:
            return "major"
        return "minor"
    return fallback or "minor"


# =============================================================================
# DOCUMENT TYPE UTILITIES
# =============================================================================

def label_to_doc_type(label: Optional[str]) -> Optional[str]:
    """Convert human label to canonical document type."""
    if not label:
        return None
    normalized = str(label).strip().lower()
    for canonical, friendly in DEFAULT_LABELS.items():
        if normalized == friendly.lower():
            return canonical
        if normalized.replace(" ", "_") == canonical:
            return canonical
    return None


def normalize_doc_type_key(value: Optional[str]) -> Optional[str]:
    """Normalize document type to canonical form (snake_case)."""
    if not value:
        return None
    normalized = str(value).strip().lower()
    normalized_snake = normalized.replace(" ", "_")
    if normalized_snake in DEFAULT_LABELS:
        return normalized_snake
    if normalized in DEFAULT_LABELS:
        return normalized
    return normalized_snake


def humanize_doc_type(doc_type: Optional[str]) -> str:
    """Convert canonical document type to human-readable label."""
    if not doc_type:
        return "Supporting Document"
    return DEFAULT_LABELS.get(doc_type, doc_type.replace("_", " ").title())


_SUPPORTING_SUBTYPE_TO_CANONICAL = {
    "bill_of_lading": "bill_of_lading",
    "waybill": "air_waybill",
    "awb": "air_waybill",
    "packing_list": "packing_list",
    "weight_list": "weight_list",
    "weight_certificate": "weight_certificate",
    "invoice": "commercial_invoice",
    "commercial_invoice": "commercial_invoice",
    "certificate": "supporting_document",
    "certificate_of_origin": "certificate_of_origin",
    "origin": "certificate_of_origin",
    "insurance": "insurance_certificate",
    "insurance_certificate": "insurance_certificate",
    "insurance_policy": "insurance_policy",
    "inspection": "inspection_certificate",
    "inspection_certificate": "inspection_certificate",
    "analysis": "analysis_certificate",
    "analysis_certificate": "analysis_certificate",
    "test_report": "lab_test_report",
    "quality": "quality_certificate",
    "quality_certificate": "quality_certificate",
    "beneficiary_certificate": "beneficiary_certificate",
    "beneficiary_statement": "beneficiary_certificate",
    "manufacturer_certificate": "manufacturer_certificate",
    "conformity": "conformity_certificate",
    "conformity_certificate": "conformity_certificate",
    "phytosanitary": "phytosanitary_certificate",
    "fumigation": "fumigation_certificate",
    "health_certificate": "health_certificate",
    "halal": "halal_certificate",
    "kosher": "kosher_certificate",
    "organic": "organic_certificate",
}

_SUPPORTING_FAMILY_TO_CANONICAL = {
    "transport_document": "bill_of_lading",
    "inspection_testing_quality": "inspection_certificate",
    "origin_customs_regulatory": "certificate_of_origin",
    "insurance_compliance_special_certificates": "insurance_certificate",
    "commercial_payment_instruments": "commercial_invoice",
    "lc_financial_undertakings": "letter_of_credit",
}


def resolve_structured_document_type(detail: Optional[Dict[str, Any]], *, filename: Optional[str] = None, index: int = 0) -> str:
    """Resolve the best canonical document type from a detail payload.

    This is the single response-shaping truth function. It prefers explicit canonical
    types, then content-classification promotions, then supporting subtype/family hints,
    then weak field-signature inference, and only finally falls back to filename/index.
    """
    payload = detail or {}
    raw_candidates = [
        payload.get("document_type"),
        payload.get("documentType"),
        payload.get("type"),
        payload.get("content_classification", {}).get("document_type") if isinstance(payload.get("content_classification"), dict) else None,
        payload.get("extracted_fields", {}).get("document_type") if isinstance(payload.get("extracted_fields"), dict) else None,
        payload.get("extracted_fields", {}).get("source_type") if isinstance(payload.get("extracted_fields"), dict) else None,
    ]
    for candidate in raw_candidates:
        normalized = normalize_doc_type_key(candidate)
        if normalized and normalized != "supporting_document":
            return normalized

    extracted_fields = payload.get("extracted_fields") if isinstance(payload.get("extracted_fields"), dict) else {}
    subtype_candidates = [
        payload.get("supporting_subtype_guess"),
        payload.get("supportingSubtypeGuess"),
        extracted_fields.get("supporting_subtype_guess"),
        extracted_fields.get("supportingSubtypeGuess"),
        extracted_fields.get("document_type"),
    ]
    for subtype in subtype_candidates:
        normalized_subtype = normalize_doc_type_key(subtype)
        if normalized_subtype in _SUPPORTING_SUBTYPE_TO_CANONICAL:
            canonical = _SUPPORTING_SUBTYPE_TO_CANONICAL[normalized_subtype]
            if canonical != "supporting_document":
                return canonical

    family_candidates = [
        payload.get("supporting_family_guess"),
        payload.get("supportingFamilyGuess"),
        extracted_fields.get("supporting_family_guess"),
        extracted_fields.get("supportingFamilyGuess"),
    ]
    for family in family_candidates:
        family_key = str(family or "").strip().lower()
        if family_key in _SUPPORTING_FAMILY_TO_CANONICAL:
            return _SUPPORTING_FAMILY_TO_CANONICAL[family_key]

    field_keys = {str(key).strip().lower() for key in extracted_fields.keys()}
    if {"gross_weight", "net_weight"} & field_keys:
        return "weight_list"
    if {"packing_list_number", "total_packages", "package_count", "marks_and_numbers"} & field_keys:
        return "packing_list"
    if {"beneficiary_statement", "certificate_text", "certification_text"} & field_keys:
        return "beneficiary_certificate"
    if {"policy_number", "insured_amount", "coverage_amount"} & field_keys:
        return "insurance_certificate"

    return infer_document_type_from_name(filename, index)


def infer_document_type_from_name(filename: Optional[str], index: int) -> str:
    """Infer the document type using filename patterns."""
    if filename:
        name = filename.lower()
        if any(token in name for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in name for token in ("bill", "b_l", "bl", "b/l", "lading")):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "pack_list", "packlist")):
            return "packing_list"
        if any(token in name for token in ("cert", "origin", "coo", "c_o")):
            return "certificate_of_origin"
        if any(token in name for token in ("insurance", "insur")):
            return "insurance_certificate"
        if any(token in name for token in ("inspection", "insp")):
            return "inspection_certificate"
        if any(token in name for token in ("lc", "letter", "credit", "mt700")):
            return "letter_of_credit"
    return fallback_doc_type(index)


def fallback_doc_type(index: int) -> str:
    """Fallback document type based on position."""
    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
    }
    return mapping.get(index, "letter_of_credit")


# =============================================================================
# STRING UTILITIES
# =============================================================================

def normalize_doc_match_key(value: Optional[str]) -> Optional[str]:
    """Normalize a string for document matching (lowercase, alphanumeric only)."""
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return normalized or None


def strip_extension(value: Optional[str]) -> Optional[str]:
    """Remove file extension from filename."""
    if not value:
        return None
    if "." not in value:
        return value
    return value.rsplit(".", 1)[0]


def coerce_issue_value(value: Any) -> str:
    """Coerce any value to string for issue display."""
    if not value:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value)


def format_duration(duration_seconds: float) -> str:
    """Format duration in human-readable form."""
    if not duration_seconds:
        return "0s"
    minutes = duration_seconds / 60
    if minutes >= 1:
        return f"{minutes:.1f} minutes"
    return f"{duration_seconds:.1f} seconds"


# =============================================================================
# FIELD FILTERING
# =============================================================================

# Fields to exclude from user display (internal metadata)
INTERNAL_FIELDS = {
    "_extraction_method", "_extraction_confidence", "_ai_provider",
    "_status", "_field_details", "_status_counts", "_document_type",
    "_two_stage_validation", "_validation_details", "_raw_ai_response",
    "_fallback_used", "_failure_reason", "raw_text",
}


def filter_user_facing_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter extracted fields to only include user-facing data.
    
    Removes internal metadata fields that start with underscore (_).
    These are useful for debugging but shouldn't clutter the user interface.
    """
    if not extracted:
        return {}
    
    filtered = {}
    for key, value in extracted.items():
        # Skip underscore-prefixed fields
        if key.startswith("_"):
            continue
        # Skip known internal fields
        if key in INTERNAL_FIELDS:
            continue
        # Skip None values
        if value is None:
            continue
        # Skip empty strings
        if isinstance(value, str) and not value.strip():
            continue
        # Keep this field
        filtered[key] = value
    
    return filtered

