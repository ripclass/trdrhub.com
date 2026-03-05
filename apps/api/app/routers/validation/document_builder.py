"""
Document Builder Module

Functions for building document summaries, lookups, and sections.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .utilities import (
    severity_to_status,
    normalize_doc_type_key,
    humanize_doc_type,
    infer_document_type_from_name,
    normalize_doc_match_key,
    strip_extension,
    filter_user_facing_fields,
)
from .issue_resolver import (
    resolve_issue_stats,
    collect_document_issue_stats,
)

logger = logging.getLogger(__name__)


def build_document_summaries(
    files_list: List[Any],
    results: List[Dict[str, Any]],
    document_details: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Create lightweight document summaries for downstream consumers.
    
    Args:
        files_list: List of file objects (UploadFile or similar)
        results: List of validation results/issues
        document_details: Optional list of document detail dicts
        
    Returns:
        List of document summary dicts with id, name, type, status, etc.
    """
    details = document_details or []
    issue_by_name, issue_by_type, issue_by_id = collect_document_issue_stats(results)

    def _build_summary_from_detail(detail: Dict[str, Any], index: int) -> Dict[str, Any]:
        filename = detail.get("filename") or detail.get("name")
        doc_type = detail.get("document_type") or infer_document_type_from_name(filename, index)
        # Normalize doc_type to canonical form (e.g., "Bill of Lading" -> "bill_of_lading")
        normalized_type = normalize_doc_type_key(doc_type) or doc_type or "supporting_document"
        detail_id = detail.get("id") or str(uuid4())
        stats = resolve_issue_stats(
            detail_id,
            filename,
            normalized_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        status = severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0

        return {
            "id": detail_id,
            "name": filename or f"Document {index + 1}",
            "type": humanize_doc_type(normalized_type),
            "documentType": normalized_type,
            "status": status,
            "discrepancyCount": discrepancy_count,
            "extractedFields": filter_user_facing_fields(detail.get("extracted_fields") or {}),
            "ocrConfidence": detail.get("ocr_confidence"),
            "extractionStatus": detail.get("extraction_status"),
        }

    if details:
        logger.info(
            "Building document summaries from details: %d documents found",
            len(details),
        )
        return [_build_summary_from_detail(detail, index) for index, detail in enumerate(details)]

    if not files_list:
        # GUARANTEE: Never return empty - create a placeholder document if nothing available
        logger.warning("No document details or files_list available - creating placeholder document")
        return [
            {
                "id": str(uuid4()),
                "name": "No documents uploaded",
                "type": "Supporting Document",
                "documentType": "supporting_document",
                "status": "warning",
                "discrepancyCount": 0,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
            }
        ]

    summaries: List[Dict[str, Any]] = []
    for index, file_obj in enumerate(files_list):
        filename = getattr(file_obj, "filename", None)
        inferred_type = infer_document_type_from_name(filename, index)
        stats = resolve_issue_stats(
            None,
            filename,
            inferred_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        doc_status = severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0
        summaries.append(
            {
                "id": str(uuid4()),
                "name": filename or f"Document {index + 1}",
                "type": humanize_doc_type(inferred_type),
                "documentType": inferred_type,
                "status": doc_status,
                "discrepancyCount": discrepancy_count,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
            }
        )

    # GUARANTEE: Never return empty list
    if not summaries:
        logger.warning("Document summaries still empty after processing - adding placeholder")
        summaries.append({
            "id": str(uuid4()),
            "name": "Document",
            "type": "Supporting Document",
            "documentType": "supporting_document",
            "status": "warning",
            "discrepancyCount": 0,
            "extractedFields": {},
            "ocrConfidence": None,
            "extractionStatus": "unknown",
        })

    return summaries


def build_document_lookup(
    documents: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    """
    Build lookup tables for document matching.
    
    Returns:
        Tuple of (doc_meta by ID, key_map for matching)
    """
    meta: Dict[str, Dict[str, Any]] = {}
    key_map: Dict[str, List[str]] = {}

    for doc in documents:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        display_name = doc.get("name") or doc.get("type") or doc.get("documentType") or doc_id
        meta[doc_id] = {
            "document_id": doc_id,
            "name": doc.get("name"),
            "display": display_name,
            "type": doc.get("documentType") or doc.get("type"),
        }
        candidate_keys = {
            normalize_doc_match_key(display_name),
            normalize_doc_match_key(doc.get("name")),
            normalize_doc_match_key(strip_extension(doc.get("name"))),
            normalize_doc_match_key(doc.get("documentType")),
            normalize_doc_match_key(doc.get("type")),
        }
        for key in filter(None, candidate_keys):
            key_map.setdefault(key, []).append(doc_id)

    return meta, key_map


def match_issue_documents(
    issue: Dict[str, Any],
    doc_meta: Dict[str, Dict[str, Any]],
    key_map: Dict[str, List[str]],
) -> Tuple[List[str], List[str]]:
    """
    Match issue documents to actual document records.
    
    Returns:
        Tuple of (matched display names, matched IDs)
    """
    matched: List[str] = []
    matched_ids: List[str] = []

    requested = issue.get("documents") or []
    if isinstance(requested, str):
        requested = [requested]

    for raw in requested:
        key = normalize_doc_match_key(raw)
        if not key:
            continue
        for doc_id in key_map.get(key, []):
            if doc_id in matched_ids:
                continue
            meta = doc_meta.get(doc_id)
            if not meta:
                continue
            matched.append(meta.get("name") or meta.get("display") or meta.get("type") or doc_id)
            matched_ids.append(doc_id)

    return matched, matched_ids


def build_documents_section(
    documents: List[Dict[str, Any]],
    issue_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Build the documents section for structured output."""
    section: List[Dict[str, Any]] = []
    for doc in documents:
        doc_id = doc.get("id") or str(uuid4())
        extraction_status = (
            doc.get("extractionStatus")
            or doc.get("extraction_status")
            or doc.get("status")
            or "unknown"
        )
        section.append(
            {
                "document_id": doc_id,
                "document_type": humanize_doc_type(doc.get("documentType") or doc.get("type")),
                "filename": doc.get("name"),
                "extraction_status": extraction_status,
                "extracted_fields": filter_user_facing_fields(doc.get("extractedFields") or doc.get("extracted_fields") or {}),
                "issues_count": issue_counts.get(doc_id, 0),
            }
        )
    return section

