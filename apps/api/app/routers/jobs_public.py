"""
Public validation job status and results endpoints for exporter/importer flows.
"""

from __future__ import annotations

from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc

from app.database import get_db
from app.models import User, ValidationSession, SessionStatus
from app.core.security import get_current_user
from app.core.rbac import RBACPolicyEngine, Permission


router = APIRouter(tags=["validation-jobs"])


def _ensure_access(session: ValidationSession, user: User) -> None:
    if not RBACPolicyEngine.can_access_resource(
        user_role=user.role,
        resource_owner_id=str(session.user_id),
        user_id=str(user.id),
        permission=Permission.VIEW_OWN_JOBS,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this validation job",
        )


def _status_to_progress(status_value: str | None) -> int:
    """
    Map ValidationSession.status to an approximate progress percentage.

    The database may contain legacy statuses (e.g. "error") that are not part of
    the Enum defined in the current code version. We therefore normalize to a
    lowercase string and fall back gracefully instead of raising AttributeError.
    """
    if not status_value:
        return 0

    normalized = status_value.lower()
    mapping = {
        SessionStatus.CREATED.value: 10,
        SessionStatus.UPLOADING.value: 25,
        SessionStatus.PROCESSING.value: 70,
        SessionStatus.COMPLETED.value: 100,
        SessionStatus.FAILED.value: 100,
        "error": 100,  # Legacy / extended status emitted by validation pipeline
        "queued": 5,
    }
    return mapping.get(normalized, 0)


def _extract_lc_number(session: ValidationSession) -> str | None:
    extracted = session.extracted_data or {}
    if "lc_number" in extracted:
        return extracted.get("lc_number")
    if "lcNumber" in extracted:
        return extracted.get("lcNumber")
    bank_meta = extracted.get("bank_metadata") or {}
    return (
        bank_meta.get("lc_number")
        or bank_meta.get("lcNumber")
        or (session.validation_results or {}).get("lc_number")
    )


def _serialize_documents(session: ValidationSession, discrepancies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    import logging
    logger = logging.getLogger(__name__)
    
    discrepancy_map: Dict[str, List[Dict[str, Any]]] = {}
    for entry in discrepancies:
        doc_ids = entry.get("document_ids") or entry.get("document_id")
        if isinstance(doc_ids, list):
            for doc_id in doc_ids:
                discrepancy_map.setdefault(str(doc_id), []).append(entry)
        elif doc_ids:
            discrepancy_map.setdefault(str(doc_ids), []).append(entry)

    documents_payload: List[Dict[str, Any]] = []
    if session.documents:
        logger.info("Using DB-backed documents: %d found", len(session.documents))
        for document in session.documents:
            doc_id = str(document.id)
            doc_discrepancies = discrepancy_map.get(doc_id, [])
            status_hint = "success"
            if any(d.get("severity") in {"critical", "major"} for d in doc_discrepancies):
                status_hint = "error"
            elif doc_discrepancies:
                status_hint = "warning"

            documents_payload.append(
                {
                    "id": doc_id,
                    "name": document.original_filename,
                    "type": document.document_type,
                    "status": status_hint,
                    "discrepancyCount": len(doc_discrepancies),
                    "discrepancies": doc_discrepancies,
                    "extractedFields": document.extracted_fields or {},
                    "ocrConfidence": document.ocr_confidence,
                }
            )

    if documents_payload:
        logger.info("Returning %d documents from DB-backed sources", len(documents_payload))
        return documents_payload

    # Fallback to summaries stored in validation_results when no DB-backed docs
    validation_results = session.validation_results or {}
    fallback_docs = validation_results.get("documents") or []
    logger.info(
        "No DB-backed documents, checking validation_results: has_results=%s documents_count=%d",
        bool(validation_results),
        len(fallback_docs),
    )
    
    if not fallback_docs:
        logger.warning(
            "No documents found in validation_results! Keys: %s",
            list(validation_results.keys()) if validation_results else "None"
        )
    
    for doc in fallback_docs:
        doc_id = str(doc.get("id") or uuid4())
        status_hint = doc.get("status") or "warning"
        documents_payload.append(
            {
                "id": doc_id,
                "name": doc.get("name") or doc.get("original_filename") or "Uploaded Document",
                "type": doc.get("type") or "supporting_document",
                "status": status_hint,
                "discrepancyCount": doc.get("discrepancyCount", 0),
                "discrepancies": doc.get("discrepancies") or [],
                "extractedFields": doc.get("extractedFields") or {},
                "ocrConfidence": doc.get("ocrConfidence"),
            }
        )

    return documents_payload


def _normalize_party(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, dict):
        for key in ("name", "company", "full_name", "legal_name", "value"):
            if value.get(key):
                return str(value[key]).strip()
        return None
    return str(value).strip()


def _extract_supplier(extracted_data: Dict[str, Any]) -> Optional[str]:
    invoice = extracted_data.get("invoice") or {}
    bl = extracted_data.get("bill_of_lading") or {}
    lc = extracted_data.get("lc") or {}
    return (
        _normalize_party(invoice.get("consignee"))
        or _normalize_party(invoice.get("buyer"))
        or _normalize_party(bl.get("consignee"))
        or _normalize_party(lc.get("beneficiary"))
        or _normalize_party(lc.get("applicant"))
    )


def _extract_invoice_amount(extracted_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    invoice = extracted_data.get("invoice") or {}
    amount_field = invoice.get("invoice_amount") or invoice.get("amount")
    currency = invoice.get("currency") or invoice.get("invoice_currency")

    if isinstance(amount_field, dict):
        currency = currency or amount_field.get("currency")
        amount = amount_field.get("value")
    else:
        amount = amount_field

    if amount is None:
        return None, currency
    return str(amount), currency


def _summarize_documents(results_payload: Dict[str, Any]) -> Optional[Dict[str, int]]:
    documents = results_payload.get("documents") or []
    if not documents:
        return None

    summary = {"success": 0, "warning": 0, "error": 0}
    for doc in documents:
        status = (doc.get("status") or "success").lower()
        if status not in summary:
            status = "warning"
        summary[status] += 1
    return summary


def _extract_top_issue(results_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    issue_cards = results_payload.get("issue_cards") or []
    if issue_cards:
        top_card = issue_cards[0]
        return {
            "title": top_card.get("title"),
            "severity": top_card.get("severity"),
            "documentName": top_card.get("documentName"),
            "rule": top_card.get("rule"),
        }

    discrepancies = results_payload.get("discrepancies") or []
    if discrepancies:
        first = discrepancies[0]
        return {
            "title": first.get("title") or first.get("rule"),
            "severity": first.get("severity"),
            "documentName": (first.get("documents") or [None])[0],
            "rule": first.get("rule"),
        }

    return None


def _summarize_job_overview(session: ValidationSession) -> Dict[str, Any]:
    results_payload = session.validation_results or {}
    extracted_data = (
        results_payload.get("extracted_data")
        or session.extracted_data
        or {}
    )

    supplier_name = _extract_supplier(extracted_data)
    invoice_amount, invoice_currency = _extract_invoice_amount(extracted_data)
    document_status = _summarize_documents(results_payload)
    top_issue = _extract_top_issue(results_payload)

    return {
        "supplierName": supplier_name,
        "invoiceAmount": invoice_amount,
        "invoiceCurrency": invoice_currency,
        "documentStatus": document_status,
        "topIssue": top_issue,
    }


@router.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ValidationSession)
        .options(
            selectinload(ValidationSession.documents),
            selectinload(ValidationSession.discrepancies),
        )
        .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
        .first()
    )

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _ensure_access(session, current_user)

    return {
        "jobId": str(session.id),
        "status": session.status,
        "progress": _status_to_progress(session.status),
        "lcNumber": _extract_lc_number(session),
        "createdAt": session.created_at,
        "completedAt": session.processing_completed_at,
        "updatedAt": session.updated_at,
        "documentCount": len(session.documents) or len((session.validation_results or {}).get("documents") or []),
        "discrepancyCount": len(session.discrepancies) or len((session.validation_results or {}).get("discrepancies") or []),
    }


@router.get("/api/results/{job_id}")
def get_job_results(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ValidationSession)
        .options(
            selectinload(ValidationSession.documents),
            selectinload(ValidationSession.discrepancies),
        )
        .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
        .first()
    )

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _ensure_access(session, current_user)

    if session.status not in [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not completed yet (status={session.status})",
        )

    results_payload = session.validation_results or {}
    raw_results = results_payload.get("results") or []
    raw_discrepancies = results_payload.get("discrepancies") or []
    
    # Filter out not_applicable rules from discrepancies (they shouldn't appear in Issues tab)
    filtered_discrepancies = [
        d for d in raw_discrepancies
        if not d.get("not_applicable", False)
    ]

    summary = {
        "totalChecks": len(raw_results),
        "passed": sum(1 for item in raw_results if item.get("passed")),
        "failed": sum(1 for item in raw_results if not item.get("passed") and not item.get("not_applicable", False)),
    }

    documents = _serialize_documents(session, filtered_discrepancies)
    
    # Extract extracted_data from validation_results or session.extracted_data
    extracted_data = {}
    if "extracted_data" in results_payload:
        extracted_data = results_payload["extracted_data"]
    elif session.extracted_data:
        # Try to reconstruct from session.extracted_data if available
        extracted_data = session.extracted_data
    
    extraction_status = results_payload.get("extraction_status") or "unknown"
    
    # Include issue_cards and reference_issues for better UI display
    issue_cards = results_payload.get("issue_cards") or []
    reference_issues = results_payload.get("reference_issues") or []
    ai_enrichment = results_payload.get("ai_enrichment") or results_payload.get("aiEnrichment")

    return {
        "jobId": str(session.id),
        "lcNumber": _extract_lc_number(session),
        "status": session.status,
        "completedAt": session.processing_completed_at,
        "results": raw_results,
        "discrepancies": filtered_discrepancies,  # Only failed, non-not_applicable rules
        "summary": summary,
        "documents": documents,
        "extracted_data": extracted_data,  # Include extracted LC fields for frontend
        "extraction_status": extraction_status,  # success, partial, empty, error
        "issue_cards": issue_cards,  # User-facing actionable issues
        "reference_issues": reference_issues,  # Technical rule references
        "aiEnrichment": ai_enrichment,
        "ai_enrichment": ai_enrichment,  # Support both naming conventions
        "lc_type": results_payload.get("lc_type"),
        "lc_type_reason": results_payload.get("lc_type_reason"),
        "lc_type_confidence": results_payload.get("lc_type_confidence"),
        "lc_type_source": results_payload.get("lc_type_source"),
        "structured_result": results_payload.get("structured_result"),
    }


@router.get("/api/jobs")
def list_user_jobs(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of jobs to return"),
    status_filter: Optional[str] = Query(default=None, description="Filter by status (completed, processing, failed)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List recent validation sessions for the current user.
    
    Returns a paginated list of validation jobs with basic metadata.
    """
    query = (
        db.query(ValidationSession)
        .filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None)
        )
    )
    
    # Filter by status if provided
    if status_filter:
        query = query.filter(ValidationSession.status == status_filter)
    
    # Order by most recent first
    query = query.order_by(desc(ValidationSession.created_at))
    
    # Limit results
    sessions = query.limit(limit).all()
    
    return {
        "jobs": [
            {
                "jobId": str(session.id),
                "status": session.status,
                "progress": _status_to_progress(session.status),
                "lcNumber": _extract_lc_number(session),
                "createdAt": session.created_at.isoformat() if session.created_at else None,
                "completedAt": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
                "documentCount": len(session.documents) if session.documents else len((session.validation_results or {}).get("documents") or []),
                "discrepancyCount": len(session.discrepancies) if session.discrepancies else len((session.validation_results or {}).get("discrepancies") or []),
                **_summarize_job_overview(session),
            }
            for session in sessions
        ],
        "total": len(sessions),
    }

