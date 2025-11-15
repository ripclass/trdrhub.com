"""
Public validation job status and results endpoints for exporter/importer flows.
"""

from __future__ import annotations

from uuid import UUID
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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


def _status_to_progress(status_value: str) -> int:
    mapping = {
        SessionStatus.CREATED.value: 10,
        SessionStatus.UPLOADING.value: 25,
        SessionStatus.PROCESSING.value: 70,
        SessionStatus.COMPLETED.value: 100,
        SessionStatus.FAILED.value: 100,
        SessionStatus.ERROR.value: 100,
    }
    return mapping.get(status_value, 0)


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
    discrepancy_map: Dict[str, List[Dict[str, Any]]] = {}
    for entry in discrepancies:
        doc_ids = entry.get("document_ids") or entry.get("document_id")
        if isinstance(doc_ids, list):
            for doc_id in doc_ids:
                discrepancy_map.setdefault(str(doc_id), []).append(entry)
        elif doc_ids:
            discrepancy_map.setdefault(str(doc_ids), []).append(entry)

    documents_payload: List[Dict[str, Any]] = []
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

    return documents_payload


@router.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ValidationSession)
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
        "documentCount": len(session.documents),
        "discrepancyCount": len(session.discrepancies),
    }


@router.get("/api/results/{job_id}")
def get_job_results(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ValidationSession)
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

    summary = {
        "totalChecks": len(raw_results),
        "passed": sum(1 for item in raw_results if item.get("passed")),
        "failed": sum(1 for item in raw_results if not item.get("passed")),
    }

    documents = _serialize_documents(session, raw_discrepancies)

    return {
        "jobId": str(session.id),
        "lcNumber": _extract_lc_number(session),
        "status": session.status,
        "completedAt": session.processing_completed_at,
        "results": raw_results,
        "discrepancies": raw_discrepancies,
        "summary": summary,
        "documents": documents,
        "aiEnrichment": results_payload.get("ai_enrichment"),
    }

