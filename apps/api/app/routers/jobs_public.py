"""
Public validation job status and results endpoints for exporter/importer flows.
"""

from __future__ import annotations

from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc
import logging

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
    documents: List[Dict[str, Any]] = []
    if isinstance(results_payload, dict):
        if results_payload.get("version") == "structured_result_v1":
            documents = results_payload.get("documents_structured") or []
        elif isinstance(results_payload.get("structured_result"), dict) and results_payload["structured_result"].get("version") == "structured_result_v1":
            documents = results_payload["structured_result"].get("documents_structured") or []
        else:
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


def _extract_option_e_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        if payload.get("version") == "structured_result_v1":
            return payload
        nested = payload.get("structured_result")
        if isinstance(nested, dict) and nested.get("version") == "structured_result_v1":
            return nested
    return None


def _count_option_e_documents(payload: Any) -> int:
    option_e = _extract_option_e_payload(payload)
    if option_e:
        return len(option_e.get("documents_structured") or [])
    if isinstance(payload, dict):
        return len(payload.get("documents") or [])
    return 0


def _extract_top_issue(results_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    option_e_source: Optional[Dict[str, Any]] = None
    if isinstance(results_payload, dict):
        if results_payload.get("version") == "structured_result_v1":
            option_e_source = results_payload
        elif isinstance(results_payload.get("structured_result"), dict) and results_payload["structured_result"].get("version") == "structured_result_v1":
            option_e_source = results_payload["structured_result"]

    if option_e_source:
        issues = option_e_source.get("issues") or []
        if issues:
            first = issues[0]
            docs = first.get("documents") or []
            return {
                "title": first.get("title"),
                "severity": first.get("severity"),
                "documentName": docs[0] if docs else None,
                "rule": first.get("rule"),
            }

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

    # Self-heal stuck jobs: if results are present but status never flipped, mark as completed
    if (
        session.validation_results
        and session.status not in [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]
    ):
        session.status = SessionStatus.COMPLETED.value
        session.processing_completed_at = session.processing_completed_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    return {
        "jobId": str(session.id),
        "status": session.status,
        "progress": _status_to_progress(session.status),
        "lcNumber": _extract_lc_number(session),
        "createdAt": session.created_at,
        "completedAt": session.processing_completed_at,
        "updatedAt": session.updated_at,
        "documentCount": len(session.documents) or _count_option_e_documents(session.validation_results or {}),
        "discrepancyCount": len(session.discrepancies) or len((session.validation_results or {}).get("discrepancies") or []),
    }


@router.get("/api/results/{job_id}")
def get_job_results(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger = logging.getLogger(__name__)
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

    # If the pipeline persisted results but left the status non-terminal, close it out here
    if (
        session.validation_results
        and session.status not in [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]
    ):
        session.status = SessionStatus.COMPLETED.value
        session.processing_completed_at = session.processing_completed_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    if session.status not in [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not completed yet (status={session.status})",
        )

    stored_payload = session.validation_results or {}
    structured_result = _extract_option_e_payload(stored_payload)
    if not structured_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "no_structured_result", "message": "Results not available yet"}
        )

    logger.info(
        "UnifiedStructuredResultServed",
        extra={"job_id": str(session.id), "version": structured_result.get("version")},
    )

    return {
        "job_id": str(session.id),
        "jobId": str(session.id),
        "structured_result": structured_result,
        "telemetry": {"UnifiedStructuredResultServed": True},
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
                "documentCount": len(session.documents) if session.documents else _count_option_e_documents(session.validation_results or {}),
                "discrepancyCount": len(session.discrepancies) if session.discrepancies else len((session.validation_results or {}).get("discrepancies") or []),
                **_summarize_job_overview(session),
            }
            for session in sessions
        ],
        "total": len(sessions),
    }

