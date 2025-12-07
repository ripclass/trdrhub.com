"""
Issue Resolver Module

Functions for resolving, collecting, and formatting validation issues.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .utilities import (
    severity_rank,
    normalize_issue_severity,
    label_to_doc_type,
    normalize_doc_type_key,
    coerce_issue_value,
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
    Resolve issue statistics for a document by ID, filename, or type.
    
    Returns:
        Dict with 'count' and 'max_severity' if found, else None
    """
    if detail_id and detail_id in issue_by_id:
        return issue_by_id[detail_id]

    if filename:
        name_key = filename.strip().lower()
        if name_key in issue_by_name:
            return issue_by_name[name_key]
        inferred_type = label_to_doc_type(name_key)
        if inferred_type and inferred_type in issue_by_type:
            return issue_by_type[inferred_type]

    if doc_type and doc_type in issue_by_type:
        return issue_by_type[doc_type]

    return None


def collect_document_issue_stats(
    results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Collect issue statistics grouped by document name, type, and ID.
    
    Args:
        results: List of validation results/issues
        
    Returns:
        Tuple of (issue_by_name, issue_by_type, issue_by_id)
    """
    issue_by_name: Dict[str, Dict[str, Any]] = {}
    issue_by_type: Dict[str, Dict[str, Any]] = {}
    issue_by_id: Dict[str, Dict[str, Any]] = {}

    for result in results:
        if result.get("passed", False) or result.get("not_applicable", False):
            continue

        severity = (result.get("severity") or "minor").lower()
        doc_names = extract_document_names(result)
        doc_types = extract_document_types(result)
        doc_ids = extract_document_ids(result)

        for doc_id in doc_ids:
            bump_issue_entry(issue_by_id, doc_id, severity)

        for name in doc_names:
            name_key = name.strip().lower()
            bump_issue_entry(issue_by_name, name_key, severity)
            inferred_type = label_to_doc_type(name)
            if inferred_type:
                bump_issue_entry(issue_by_type, inferred_type, severity)

        for doc_type in doc_types:
            canonical = normalize_doc_type_key(doc_type)
            if canonical:
                bump_issue_entry(issue_by_type, canonical, severity)

    return issue_by_name, issue_by_type, issue_by_id


def extract_document_names(discrepancy: Dict[str, Any]) -> List[str]:
    """Extract document names from a discrepancy/issue dict."""
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
    """Extract document types from a discrepancy/issue dict."""
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
    """Extract document IDs from a discrepancy/issue dict."""
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
    """Increment issue count and update max severity for a bucket key."""
    if not key:
        return {}
    entry = bucket.setdefault(key, {"count": 0, "max_severity": "minor"})
    entry["count"] += 1
    if severity_rank(severity) > severity_rank(entry["max_severity"]):
        entry["max_severity"] = severity
    return entry


def count_issue_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count issues by severity level."""
    counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = normalize_issue_severity(issue.get("severity"))
        if severity in counts:
            counts[severity] += 1
        else:
            counts["minor"] += 1
    return counts


def format_deterministic_issue(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format a deterministic rule result as a standardized issue dict."""
    issue_id = str(result.get("rule") or result.get("rule_id") or uuid4())
    severity = normalize_issue_severity(result.get("severity"))
    priority = result.get("priority") or severity
    documents = extract_document_names(result)
    expected = result.get("expected") or result.get("expected_value")
    found = result.get("found") or result.get("actual_value")
    suggestion = result.get("suggestion")
    expected_outcome = result.get("expected_outcome") or {}
    if not suggestion:
        suggestion = expected_outcome.get("invalid") or expected_outcome.get("message")

    return {
        "id": issue_id,
        "title": result.get("title") or result.get("rule") or "Rule Breach",
        "severity": severity,
        "priority": priority,
        "documents": documents,
        "description": result.get("message") or "",
        "expected": coerce_issue_value(expected),
        "found": coerce_issue_value(found),
        "suggested_fix": coerce_issue_value(suggestion),
        "ucp_reference": coerce_issue_value(result.get("rule")),
    }

