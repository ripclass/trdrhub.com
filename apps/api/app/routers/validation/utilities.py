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

