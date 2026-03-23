"""
Public validation job status and results endpoints for exporter/importer flows.
"""

from __future__ import annotations

import copy
from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc
import logging

from app.database import get_db
from app.models import User, ValidationSession, SessionStatus
from app.core.security import get_current_user
from app.core.rbac import RBACPolicyEngine, Permission
from app.config import settings
from app.middleware.audit_middleware import create_audit_context
from app.models.audit_log import AuditResult
from app.services.audit_service import AuditService


router = APIRouter(tags=["validation-jobs"])


class FieldOverrideRequestBody(BaseModel):
    document_id: str
    field_name: str
    override_value: Any
    note: Optional[str] = Field(default=None, max_length=1000)


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


def _looks_like_structured_result(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    hallmark_keys = {
        "documents",
        "documents_structured",
        "issues",
        "processing_summary",
        "processing_summary_v2",
        "validation_status",
        "submission_eligibility",
        "bank_verdict",
        "analytics",
        "lc_structured",
        "lc_data",
    }
    return any(key in payload for key in hallmark_keys)


def _normalize_structured_result_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("version", "structured_result_v1")
    documents = normalized.get("documents") or normalized.get("documents_structured") or []
    if isinstance(documents, list):
        normalized.setdefault("documents", documents)
        normalized.setdefault("documents_structured", documents)
    return normalized


def _extract_option_e_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        if payload.get("version") == "structured_result_v1":
            return _normalize_structured_result_shape(payload)
        nested = payload.get("structured_result")
        if isinstance(nested, dict):
            if nested.get("version") == "structured_result_v1" or _looks_like_structured_result(nested):
                return _normalize_structured_result_shape(nested)
        if _looks_like_structured_result(payload):
            return _normalize_structured_result_shape(payload)
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


def _normalize_job_id(job_id_str: str) -> UUID:
    """Strip 'job_' prefix if present and parse as UUID."""
    if job_id_str.startswith("job_"):
        job_id_str = job_id_str[4:]
    return UUID(job_id_str)


def _debug_trace_for_response(extracted_data: Any) -> Optional[List[Dict[str, Any]]]:
    if not settings.DEBUG_EXTRACTION_TRACE:
        return None
    if not isinstance(extracted_data, dict):
        return None
    trace = extracted_data.get("_debug_extraction_trace")
    if isinstance(trace, list):
        return trace
    return None


def _build_fallback_structured_result(session: ValidationSession) -> Optional[Dict[str, Any]]:
    extracted_data = session.extracted_data or {}
    documents_structured: List[Dict[str, Any]] = []
    for document in session.documents or []:
        extracted_fields = document.extracted_fields if isinstance(document.extracted_fields, dict) else {}
        documents_structured.append(
            {
                "document_type": document.document_type,
                "filename": document.original_filename,
                "status": "success",
                "extracted_fields": extracted_fields,
                "ocr_confidence": document.ocr_confidence,
            }
        )

    if not documents_structured and not extracted_data:
        return None

    issues = []
    for discrepancy in session.discrepancies or []:
        issues.append(
            {
                "title": discrepancy.rule_name or discrepancy.description or "Validation issue",
                "severity": discrepancy.severity or "warning",
                "rule": discrepancy.rule_name,
                "documents": [discrepancy.document_name] if getattr(discrepancy, "document_name", None) else [],
            }
        )

    status_counts = {"success": len(documents_structured), "warning": 0, "error": 0}
    lc_number = _extract_lc_number(session)
    validation_status = "pass" if not issues else "review"
    return {
        "version": "structured_result_v1",
        "documents": documents_structured,
        "documents_structured": documents_structured,
        "issues": issues,
        "validation_status": validation_status,
        "submission_eligibility": {
            "can_submit": len(issues) == 0,
            "status": "eligible" if len(issues) == 0 else "review_required",
            "reasons": [] if len(issues) == 0 else ["fallback_results_from_persisted_session"],
        },
        "bank_verdict": {
            "verdict": "ACCEPT" if len(issues) == 0 else "REVIEW",
            "can_submit": len(issues) == 0,
            "action_items": [],
        },
        "analytics": {
            "issue_counts": {
                "total": len(issues),
                "critical": len([i for i in issues if str(i.get("severity", "")).lower() == "critical"]),
            },
            "document_status_distribution": status_counts,
        },
        "processing_summary": {
            "total_documents": len(documents_structured),
            "documents_found": len(documents_structured),
            "verified": len(documents_structured),
            "warnings": 0,
            "errors": 0,
            "status_counts": status_counts,
            "document_status": status_counts,
            "discrepancies": len(issues),
        },
        "processing_summary_v2": {
            "total_documents": len(documents_structured),
            "documents_found": len(documents_structured),
            "successful_extractions": len(documents_structured),
            "failed_extractions": 0,
            "total_issues": len(issues),
            "status_counts": status_counts,
            "documents": documents_structured,
        },
        "lc_number": lc_number,
        "extracted_data": extracted_data,
    }


def _normalize_override_field_name(field_name: str) -> str:
    return str(field_name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _is_unresolved_field_state(value: Any) -> bool:
    return str(value or "").strip().lower() in {"missing", "failed", "parse_failed", "unconfirmed"}


def _remove_override_resolved_review_reasons(
    review_reasons: List[str],
    field_name: str,
    unresolved_fields_remaining: int,
) -> List[str]:
    normalized_field = _normalize_override_field_name(field_name)
    filtered: List[str] = []
    for reason in review_reasons:
        reason_value = str(reason or "").strip()
        normalized_reason = _normalize_override_field_name(reason_value)
        if normalized_reason in {
            f"missing:{normalized_field}",
            f"critical_{normalized_field}_missing",
        }:
            continue
        if normalized_reason == "field_not_found" and unresolved_fields_remaining == 0:
            continue
        filtered.append(reason_value)
    return filtered


def _apply_field_override_to_document(
    document: Dict[str, Any],
    *,
    field_name: str,
    override_value: Any,
    note: Optional[str],
    actor_email: str,
    applied_at_iso: str,
) -> Dict[str, Any]:
    normalized_field = _normalize_override_field_name(field_name)
    updated = copy.deepcopy(document or {})

    extracted_fields = (
        copy.deepcopy(updated.get("extracted_fields"))
        if isinstance(updated.get("extracted_fields"), dict)
        else copy.deepcopy(updated.get("extractedFields"))
        if isinstance(updated.get("extractedFields"), dict)
        else {}
    )
    extracted_fields[normalized_field] = override_value
    updated["extracted_fields"] = extracted_fields
    if "extractedFields" in updated:
        updated["extractedFields"] = copy.deepcopy(extracted_fields)

    field_details = (
        copy.deepcopy(updated.get("field_details"))
        if isinstance(updated.get("field_details"), dict)
        else copy.deepcopy(updated.get("fieldDetails"))
        if isinstance(updated.get("fieldDetails"), dict)
        else {}
    )
    existing_detail = field_details.get(normalized_field)
    if not isinstance(existing_detail, dict):
        existing_detail = {}
    field_details[normalized_field] = {
        **existing_detail,
        "value": override_value,
        "raw_value": override_value,
        "verification": "operator_confirmed",
        "status": "trusted",
        "source": "operator_override",
        "confidence": 1.0,
        "evidence": {
            "source": "operator_override",
            "snippet": str(note).strip() if note else f"{override_value}",
            "strategy": "manual_override",
        },
        "operator_note": str(note).strip() if note else None,
        "operator_confirmed_by": actor_email,
        "operator_confirmed_at": applied_at_iso,
    }
    updated["field_details"] = field_details
    if "fieldDetails" in updated:
        updated["fieldDetails"] = copy.deepcopy(field_details)

    missing_required_fields = [
        str(value)
        for value in (
            updated.get("missing_required_fields")
            if isinstance(updated.get("missing_required_fields"), list)
            else updated.get("missingRequiredFields")
            if isinstance(updated.get("missingRequiredFields"), list)
            else []
        )
        if _normalize_override_field_name(value) != normalized_field
    ]
    updated["missing_required_fields"] = missing_required_fields
    if "missingRequiredFields" in updated:
        updated["missingRequiredFields"] = list(missing_required_fields)

    critical_field_states = (
        copy.deepcopy(updated.get("critical_field_states"))
        if isinstance(updated.get("critical_field_states"), dict)
        else copy.deepcopy(updated.get("criticalFieldStates"))
        if isinstance(updated.get("criticalFieldStates"), dict)
        else {}
    )
    if normalized_field in critical_field_states:
        critical_field_states[normalized_field] = "found"
    updated["critical_field_states"] = critical_field_states
    if "criticalFieldStates" in updated:
        updated["criticalFieldStates"] = copy.deepcopy(critical_field_states)

    extraction_artifacts = (
        copy.deepcopy(updated.get("extraction_artifacts_v1"))
        if isinstance(updated.get("extraction_artifacts_v1"), dict)
        else {}
    )
    field_diagnostics = (
        copy.deepcopy(extraction_artifacts.get("field_diagnostics"))
        if isinstance(extraction_artifacts.get("field_diagnostics"), dict)
        else copy.deepcopy(updated.get("field_diagnostics"))
        if isinstance(updated.get("field_diagnostics"), dict)
        else {}
    )
    current_diag = field_diagnostics.get(normalized_field)
    if not isinstance(current_diag, dict):
        current_diag = {}
    field_diagnostics[normalized_field] = {
        **current_diag,
        "state": "operator_confirmed",
        "source": "operator_override",
        "override_value": override_value,
        "override_note": str(note).strip() if note else None,
        "confirmed_by": actor_email,
        "confirmed_at": applied_at_iso,
    }
    if extraction_artifacts:
        extraction_artifacts["field_diagnostics"] = field_diagnostics
        updated["extraction_artifacts_v1"] = extraction_artifacts
    else:
        updated["field_diagnostics"] = field_diagnostics

    unresolved_remaining = len(
        [
            key
            for key, value in critical_field_states.items()
            if _normalize_override_field_name(key) != normalized_field and _is_unresolved_field_state(value)
        ]
    ) + len(missing_required_fields)
    review_reasons = [
        str(value)
        for value in (
            updated.get("review_reasons")
            if isinstance(updated.get("review_reasons"), list)
            else updated.get("reviewReasons")
            if isinstance(updated.get("reviewReasons"), list)
            else []
        )
    ]
    review_reasons = _remove_override_resolved_review_reasons(review_reasons, normalized_field, unresolved_remaining)
    updated["review_reasons"] = review_reasons
    if "reviewReasons" in updated:
        updated["reviewReasons"] = list(review_reasons)
    updated["review_required"] = bool(review_reasons or unresolved_remaining > 0)
    if "reviewRequired" in updated:
        updated["reviewRequired"] = updated["review_required"]

    required_fields_found = updated.get("required_fields_found")
    required_fields_total = updated.get("required_fields_total")
    if isinstance(required_fields_found, int) and isinstance(required_fields_total, int):
        updated["required_fields_found"] = min(required_fields_total, required_fields_found + 1)
        if "requiredFieldsFound" in updated:
            updated["requiredFieldsFound"] = updated["required_fields_found"]

    return updated


def _apply_field_override_to_structured_result(
    structured_result: Dict[str, Any],
    *,
    document_id: str,
    field_name: str,
    override_value: Any,
    note: Optional[str],
    actor_email: str,
    applied_at_iso: str,
) -> Optional[Dict[str, Any]]:
    updated_document: Optional[Dict[str, Any]] = None
    for collection_name in ("documents", "documents_structured"):
        collection = structured_result.get(collection_name)
        if not isinstance(collection, list):
            continue
        next_collection: List[Dict[str, Any]] = []
        for entry in collection:
            if not isinstance(entry, dict):
                next_collection.append(entry)
                continue
            entry_id = str(entry.get("document_id") or entry.get("id") or "")
            if entry_id == document_id:
                patched = _apply_field_override_to_document(
                    entry,
                    field_name=field_name,
                    override_value=override_value,
                    note=note,
                    actor_email=actor_email,
                    applied_at_iso=applied_at_iso,
                )
                next_collection.append(patched)
                updated_document = patched
            else:
                next_collection.append(entry)
        structured_result[collection_name] = next_collection

    lc_structured = structured_result.get("lc_structured")
    if isinstance(lc_structured, dict) and isinstance(lc_structured.get("documents_structured"), list):
        next_collection = []
        for entry in lc_structured.get("documents_structured") or []:
            if not isinstance(entry, dict):
                next_collection.append(entry)
                continue
            entry_id = str(entry.get("document_id") or entry.get("id") or "")
            if entry_id == document_id:
                patched = _apply_field_override_to_document(
                    entry,
                    field_name=field_name,
                    override_value=override_value,
                    note=note,
                    actor_email=actor_email,
                    applied_at_iso=applied_at_iso,
                )
                next_collection.append(patched)
                updated_document = patched
            else:
                next_collection.append(entry)
        lc_structured["documents_structured"] = next_collection

    return updated_document


def _record_operator_field_override(
    extracted_data: Dict[str, Any],
    *,
    document_id: str,
    field_name: str,
    override_value: Any,
    note: Optional[str],
    actor_id: str,
    actor_email: str,
    applied_at_iso: str,
) -> Dict[str, Any]:
    updated = copy.deepcopy(extracted_data or {})
    overrides = updated.get("operator_field_overrides")
    if not isinstance(overrides, dict):
        overrides = {}
    doc_overrides = overrides.get(document_id)
    if not isinstance(doc_overrides, dict):
        doc_overrides = {}
    doc_overrides[_normalize_override_field_name(field_name)] = {
        "value": override_value,
        "note": str(note).strip() if note else None,
        "verification": "operator_confirmed",
        "confirmed_by": actor_email,
        "confirmed_by_user_id": actor_id,
        "confirmed_at": applied_at_iso,
    }
    overrides[document_id] = doc_overrides
    updated["operator_field_overrides"] = overrides
    return updated


@router.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: str,  # Accept string to handle 'job_' prefix
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        job_uuid = _normalize_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid job ID format: {job_id}")
    session = (
        db.query(ValidationSession)
        .options(
            selectinload(ValidationSession.documents),
            selectinload(ValidationSession.discrepancies),
        )
        .filter(ValidationSession.id == job_uuid, ValidationSession.deleted_at.is_(None))
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

    response_payload = {
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
    debug_trace = _debug_trace_for_response(session.extracted_data)
    if debug_trace is not None:
        response_payload["debug_extraction_trace"] = debug_trace

    return response_payload


@router.get("/api/results/{job_id}")
def get_job_results(
    job_id: str,  # Accept string to handle 'job_' prefix
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger = logging.getLogger(__name__)
    try:
        job_uuid = _normalize_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid job ID format: {job_id}")
    session = (
        db.query(ValidationSession)
        .options(
            selectinload(ValidationSession.documents),
            selectinload(ValidationSession.discrepancies),
        )
        .filter(ValidationSession.id == job_uuid, ValidationSession.deleted_at.is_(None))
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
    if structured_result and isinstance(stored_payload, dict):
        nested = stored_payload.get("structured_result") if isinstance(stored_payload.get("structured_result"), dict) else None
        if nested is not structured_result and nested != structured_result:
            session.validation_results = {**stored_payload, "structured_result": structured_result}
            db.commit()
            db.refresh(session)
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


@router.post("/api/results/{job_id}/field-overrides")
def save_job_field_override(
    job_id: str,
    payload: FieldOverrideRequestBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger = logging.getLogger(__name__)
    try:
        job_uuid = _normalize_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid job ID format: {job_id}")

    session = (
        db.query(ValidationSession)
        .options(
            selectinload(ValidationSession.documents),
            selectinload(ValidationSession.discrepancies),
        )
        .filter(ValidationSession.id == job_uuid, ValidationSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _ensure_access(session, current_user)

    stored_payload = copy.deepcopy(session.validation_results or {})
    structured_result = _extract_option_e_payload(stored_payload)
    if not structured_result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "no_structured_result", "message": "Results not available yet"},
        )

    field_name = _normalize_override_field_name(payload.field_name)
    document_id = str(payload.document_id)
    applied_at = datetime.now(timezone.utc)
    applied_at_iso = applied_at.isoformat()

    updated_document = _apply_field_override_to_structured_result(
        structured_result,
        document_id=document_id,
        field_name=field_name,
        override_value=payload.override_value,
        note=payload.note,
        actor_email=current_user.email,
        applied_at_iso=applied_at_iso,
    )
    if not updated_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "document_not_found", "message": "Document not found in structured results"},
        )

    if isinstance(stored_payload, dict) and stored_payload.get("version") == "structured_result_v1":
        session.validation_results = structured_result
    else:
        session.validation_results = {**stored_payload, "structured_result": structured_result}

    session.extracted_data = _record_operator_field_override(
        session.extracted_data if isinstance(session.extracted_data, dict) else {},
        document_id=document_id,
        field_name=field_name,
        override_value=payload.override_value,
        note=payload.note,
        actor_id=str(current_user.id),
        actor_email=current_user.email,
        applied_at_iso=applied_at_iso,
    )

    db.commit()
    db.refresh(session)

    try:
        audit_context = create_audit_context(request)
        request_data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        AuditService(db).log_action(
            action="field_override",
            user=current_user,
            correlation_id=audit_context.get("correlation_id"),
            session_id=audit_context.get("session_id"),
            resource_type="validation_session_field",
            resource_id=str(session.id),
            lc_number=_extract_lc_number(session),
            result=AuditResult.SUCCESS,
            ip_address=audit_context.get("ip_address"),
            user_agent=audit_context.get("user_agent"),
            endpoint=audit_context.get("endpoint"),
            http_method=audit_context.get("http_method"),
            status_code=status.HTTP_200_OK,
            request_data=request_data,
            response_data={
                "document_id": document_id,
                "field_name": field_name,
                "verification": "operator_confirmed",
            },
            audit_metadata={
                "override_scope": "session_structured_result",
                "applied_at": applied_at_iso,
            },
        )
    except Exception as audit_error:
        logger.warning("Field override saved but audit logging failed: %s", audit_error)

    return {
        "job_id": str(session.id),
        "jobId": str(session.id),
        "document_id": document_id,
        "field_name": field_name,
        "override_value": payload.override_value,
        "verification": "operator_confirmed",
        "applied_at": applied_at_iso,
        "updated_document": updated_document,
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

