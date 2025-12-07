"""
Validation Router Modules

Split from the monolithic validate.py for maintainability.
Each module has a single responsibility.
"""

from .utilities import (
    # Severity utilities
    severity_rank,
    severity_to_status,
    normalize_issue_severity,
    priority_to_severity,
    # Document type utilities
    label_to_doc_type,
    normalize_doc_type_key,
    humanize_doc_type,
    infer_document_type_from_name,
    fallback_doc_type,
    # String utilities
    normalize_doc_match_key,
    strip_extension,
    coerce_issue_value,
    format_duration,
    # Field filtering
    filter_user_facing_fields,
)

from .issue_resolver import (
    resolve_issue_stats,
    collect_document_issue_stats,
    extract_document_names,
    extract_document_types,
    extract_document_ids,
    bump_issue_entry,
    count_issue_severity,
    format_deterministic_issue,
)

from .document_builder import (
    build_document_summaries,
    build_document_lookup,
    match_issue_documents,
    build_documents_section,
)

from .response_builder import (
    compose_processing_summary,
    build_analytics_section,
    build_timeline_entries,
    build_document_processing_analytics,
    summarize_document_statuses,
)

__all__ = [
    # Utilities
    "severity_rank",
    "severity_to_status",
    "normalize_issue_severity",
    "priority_to_severity",
    "label_to_doc_type",
    "normalize_doc_type_key",
    "humanize_doc_type",
    "infer_document_type_from_name",
    "fallback_doc_type",
    "normalize_doc_match_key",
    "strip_extension",
    "coerce_issue_value",
    "format_duration",
    "filter_user_facing_fields",
    # Issue resolver
    "resolve_issue_stats",
    "collect_document_issue_stats",
    "extract_document_names",
    "extract_document_types",
    "extract_document_ids",
    "bump_issue_entry",
    "count_issue_severity",
    "format_deterministic_issue",
    # Document builder
    "build_document_summaries",
    "build_document_lookup",
    "match_issue_documents",
    "build_documents_section",
    # Response builder
    "compose_processing_summary",
    "build_analytics_section",
    "build_timeline_entries",
    "build_document_processing_analytics",
    "summarize_document_statuses",
]

