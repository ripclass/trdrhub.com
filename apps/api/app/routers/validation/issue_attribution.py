"""
Issue Attribution Module

Helpers for attributing validation issues to documents.
Extracted from validate.py to keep behavior parity.
"""

from typing import Any, Dict, List, Optional, Tuple

from .utilities import severity_rank
from .doc_types import (
    label_to_doc_type,
    normalize_doc_type_key,
    doc_type_to_display_name,
)


def resolve_issue_stats(
    detail_id: Optional[str],
    filename: Optional[str],
    doc_type: Optional[str],
    issue_by_name: Dict[str, Dict[str, Any]],
    issue_by_type: Dict[str, Dict[str, Any]],
    issue_by_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Resolve issue stats for a specific document.

    Matches by document ID, filename, or document type.
    Uses fuzzy matching to connect issues to documents.

    NOTE: Cross-doc issues use 'affected_documents' field which contains
    document types (e.g., 'invoice', 'bill_of_lading'). This function
    matches these to actual filenames like "Invoice.pdf".
    """
    # Match by specific document ID
    if detail_id and detail_id in issue_by_id:
        return issue_by_id[detail_id]

    # Match by specific filename
    if filename:
        name_key = filename.strip().lower()
        if name_key in issue_by_name:
            return issue_by_name[name_key]

        # Try filename without extension (e.g., "Invoice.pdf" -> "invoice")
        name_no_ext = name_key.rsplit(".", 1)[0] if "." in name_key else name_key
        if name_no_ext in issue_by_name:
            return issue_by_name[name_no_ext]

        # Try matching display names (e.g., "invoice" matches "commercial invoice")
        for key in issue_by_name:
            if name_no_ext in key or key in name_no_ext:
                return issue_by_name[key]

        # Try underscore variants (e.g., "bill_of_lading" -> "bill of lading")
        name_spaced = name_no_ext.replace("_", " ")
        if name_spaced in issue_by_name:
            return issue_by_name[name_spaced]

        # Also check if filename (without extension) matches a type
        inferred_type = label_to_doc_type(name_key)
        if inferred_type and inferred_type in issue_by_type:
            return issue_by_type[inferred_type]

        # Try the name without extension for type matching
        inferred_type_no_ext = label_to_doc_type(name_no_ext)
        if inferred_type_no_ext and inferred_type_no_ext in issue_by_type:
            return issue_by_type[inferred_type_no_ext]

    # Match by document type
    if doc_type:
        doc_type_lower = doc_type.lower()
        if doc_type_lower in issue_by_type:
            return issue_by_type[doc_type_lower]
        # Try snake_case version
        doc_type_snake = doc_type_lower.replace(" ", "_")
        if doc_type_snake in issue_by_type:
            return issue_by_type[doc_type_snake]

    return None


def collect_document_issue_stats(
    results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Collect issue statistics by document.

    IMPORTANT: Uses 'affected_documents' field if present (from crossdoc issues)
    to correctly attribute issues ONLY to the document with the problem,
    not to all documents referenced in a cross-doc check.

    For example, "B/L Missing Voyage Number" should only count against B/L,
    not against both B/L and LC (even though the rule references both).
    """
    issue_by_name: Dict[str, Dict[str, Any]] = {}
    issue_by_type: Dict[str, Dict[str, Any]] = {}
    issue_by_id: Dict[str, Dict[str, Any]] = {}

    for result in results:
        if result.get("passed", False) or result.get("not_applicable", False):
            continue

        severity = (result.get("severity") or "minor").lower()

        # Use affected_documents if present (crossdoc issues), else fall back to documents
        # affected_documents contains ONLY the document with the actual issue
        affected_docs = result.get("affected_documents")
        if affected_docs is not None:
            # Crossdoc issue with explicit affected documents
            doc_names = affected_docs if isinstance(affected_docs, list) else [affected_docs]
        else:
            # Legacy issue format - use documents field
            doc_names = extract_document_names(result)

        doc_types = extract_document_types(result)
        doc_ids = extract_document_ids(result)

        for doc_id in doc_ids:
            bump_issue_entry(issue_by_id, doc_id, severity)

        for name in doc_names:
            name_key = name.strip().lower()
            bump_issue_entry(issue_by_name, name_key, severity)

            # Also add by display name variants for better matching
            # e.g., 'invoice' -> also add 'commercial invoice', 'commercial_invoice'
            display_name = doc_type_to_display_name(name_key)
            if display_name and display_name.lower() != name_key:
                bump_issue_entry(issue_by_name, display_name.lower(), severity)

            # Add snake_case and space variants
            name_snake = name_key.replace(" ", "_")
            if name_snake != name_key:
                bump_issue_entry(issue_by_name, name_snake, severity)
            name_spaced = name_key.replace("_", " ")
            if name_spaced != name_key:
                bump_issue_entry(issue_by_name, name_spaced, severity)

            inferred_type = label_to_doc_type(name)
            if inferred_type:
                bump_issue_entry(issue_by_type, inferred_type, severity)

        # Only add to issue_by_type if no affected_documents was specified
        # (affected_documents already handles type-based attribution correctly)
        if affected_docs is None:
            for doc_type in doc_types:
                canonical = normalize_doc_type_key(doc_type)
                if canonical:
                    bump_issue_entry(issue_by_type, canonical, severity)

    return issue_by_name, issue_by_type, issue_by_id


def extract_document_names(discrepancy: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for key in ("documents", "document_names"):
        value = discrepancy.get(key)
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            names.extend([str(item) for item in value if isinstance(item, str)])
    for key in ("document", "document_name"):
        if discrepancy.get(key):
            names.append(str(discrepancy[key]))
    return names


def extract_document_types(discrepancy: Dict[str, Any]) -> List[str]:
    types: List[str] = []
    value = discrepancy.get("document_types")
    if isinstance(value, str):
        types.append(value)
    elif isinstance(value, list):
        types.extend([str(item) for item in value if item])
    elif value:
        types.append(str(value))
    if discrepancy.get("document_type"):
        types.append(str(discrepancy["document_type"]))
    return types


def extract_document_ids(discrepancy: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    value = discrepancy.get("document_ids")
    if isinstance(value, str):
        ids.append(value)
    elif isinstance(value, list):
        ids.extend([str(item) for item in value if item])
    elif value:
        ids.append(str(value))
    if discrepancy.get("document_id"):
        ids.append(str(discrepancy["document_id"]))
    return ids


def bump_issue_entry(bucket: Dict[str, Dict[str, Any]], key: str, severity: str) -> Dict[str, Any]:
    if not key:
        return {}
    entry = bucket.setdefault(key, {"count": 0, "max_severity": "minor"})
    entry["count"] += 1
    if severity_rank(severity) > severity_rank(entry["max_severity"]):
        entry["max_severity"] = severity
    return entry
