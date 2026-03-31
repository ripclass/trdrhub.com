from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Tuple

from .models import DocumentFact, DocumentFactSet
from .normalization import normalize_amount, normalize_currency, normalize_date, normalize_party_name, normalize_reference


_INSURANCE_FACT_FIELDS: Dict[str, Tuple[str, ...]] = {
    "policy_number": ("policy_number", "policy_no", "insurance_policy_number", "certificate_number", "certificate_no"),
    "certificate_number": ("certificate_number", "certificate_no", "policy_number", "policy_no"),
    "insured_amount": ("insured_amount", "coverage_amount", "sum_insured", "amount"),
    "currency": ("currency", "currency_code", "insured_currency"),
    "coverage_type": ("coverage_type", "coverage", "risk_coverage", "risks_covered"),
    "issuer_name": ("issuer_name", "insurer", "issuing_authority", "issuer", "beneficiary"),
    "issue_date": ("issue_date", "date", "document_date", "doc_date", "date_of_issue"),
    "lc_reference": ("lc_reference", "lc_number", "credit_number"),
    "originals_presented": ("originals_presented", "number_of_originals", "original_count"),
}
_RAW_TEXT_INTEGER_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "originals_presented": (
        "Presented Originals",
        "Originals Presented",
        "Number of Originals",
    ),
}


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _coerce_confidence(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def _detail_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    details = payload.get("field_details")
    if isinstance(details, dict):
        return {str(key): value for key, value in details.items() if isinstance(value, dict)}
    return {}


def _source_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    fields = payload.get("extracted_fields")
    if isinstance(fields, dict):
        return fields
    return {}


def _raw_text_source(payload: Dict[str, Any]) -> Optional[str]:
    extraction_artifacts = payload.get("extraction_artifacts_v1")
    if not isinstance(extraction_artifacts, dict):
        extraction_artifacts = {}
    for value in (
        payload.get("raw_text"),
        payload.get("text"),
        payload.get("content"),
        extraction_artifacts.get("raw_text"),
        payload.get("raw_text_preview"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_detail(details: Dict[str, Dict[str, Any]], aliases: Iterable[str]) -> Tuple[Optional[str], Dict[str, Any]]:
    for alias in aliases:
        detail = details.get(alias)
        if isinstance(detail, dict):
            return alias, detail
    return None, {}


def _first_value(
    payload: Dict[str, Any],
    fields: Dict[str, Any],
    details: Dict[str, Dict[str, Any]],
    aliases: Iterable[str],
) -> Tuple[Optional[Any], Optional[str], Dict[str, Any]]:
    for alias in aliases:
        if _is_populated(fields.get(alias)):
            return fields.get(alias), alias, details.get(alias) if isinstance(details.get(alias), dict) else {}

    for alias in aliases:
        detail = details.get(alias)
        if not isinstance(detail, dict):
            continue
        if _is_populated(detail.get("value")):
            return detail.get("value"), alias, detail
        if _is_populated(detail.get("rejected_value")):
            return detail.get("rejected_value"), alias, detail
        if _is_populated(detail.get("raw_value")):
            return detail.get("raw_value"), alias, detail

    for alias in aliases:
        if _is_populated(payload.get(alias)):
            return payload.get(alias), alias, details.get(alias) if isinstance(details.get(alias), dict) else {}

    detail_alias, detail = _first_detail(details, aliases)
    if detail_alias:
        return None, detail_alias, detail

    return None, None, {}


def _normalize_fact_value(field_name: str, value: Any) -> Optional[Any]:
    if field_name == "insured_amount":
        return normalize_amount(value)
    if field_name == "currency":
        return normalize_currency(value)
    if field_name == "issue_date":
        return normalize_date(value)
    if field_name == "issuer_name":
        return normalize_party_name(value)
    if field_name == "originals_presented":
        if value in (None, ""):
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return normalize_reference(value)
    return normalize_reference(value)


def _recovery_detail(value: Any, snippet: str, *, confidence: float = 0.9) -> Dict[str, Any]:
    return {
        "value": value,
        "confidence": confidence,
        "verification": "text_supported",
        "source": "artifact_raw_text",
        "evidence": {
            "snippet": snippet,
            "source": "artifact_raw_text",
        },
    }


def _extract_labeled_integer(raw_text: str, labels: Iterable[str]) -> Tuple[Optional[int], Optional[str]]:
    text = str(raw_text or "")
    if not text.strip():
        return None, None
    for label in labels:
        pattern = re.compile(rf"(?im)^\s*{re.escape(label)}\s*[:\-]\s*(\d+)\s*$")
        match = pattern.search(text)
        if not match:
            continue
        value = int(match.group(1))
        return value, f"{label}: {value}"
    return None, None


def _can_use_raw_text_recovery(detail: Dict[str, Any]) -> bool:
    verification = str(detail.get("verification") or "").strip().lower()
    if verification in {"operator_confirmed", "operator_rejected"}:
        return False
    if verification in {"confirmed", "text_supported"} and detail.get("evidence"):
        return False
    evidence = detail.get("evidence")
    if isinstance(evidence, dict) and evidence:
        return False
    return True


def _raw_text_recoveries(
    payload: Dict[str, Any],
    details: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    raw_text = _raw_text_source(payload)
    if not raw_text:
        return {}, {}

    recovered_fields: Dict[str, Any] = {}
    recovered_details: Dict[str, Dict[str, Any]] = {}

    for field_name, labels in _RAW_TEXT_INTEGER_PATTERNS.items():
        detail = details.get(field_name) if isinstance(details.get(field_name), dict) else {}
        if not _can_use_raw_text_recovery(detail):
            continue
        recovered_value, snippet = _extract_labeled_integer(raw_text, labels)
        if recovered_value is None:
            continue
        recovered_fields[field_name] = recovered_value
        recovered_details[field_name] = _recovery_detail(recovered_value, snippet or str(recovered_value))

    return recovered_fields, recovered_details


def _verification_state(value: Any, detail: Dict[str, Any]) -> str:
    verification = str(detail.get("verification") or "").strip().lower()
    if verification == "operator_confirmed":
        return "operator_confirmed"
    if verification == "operator_rejected":
        return "operator_rejected"
    if verification in {"confirmed", "text_supported"}:
        return "confirmed"
    if verification == "model_suggested":
        return "candidate"
    if verification == "not_found":
        if str(detail.get("reason_code") or "").strip().lower() == "source_absent":
            return "absent_in_source"
        return "unconfirmed"
    if not _is_populated(value):
        return "unconfirmed"
    if detail.get("evidence"):
        return "confirmed"
    return "candidate"


def _origin(payload: Dict[str, Any], detail: Dict[str, Any]) -> str:
    verification = str(detail.get("verification") or "").strip().lower()
    if verification in {"operator_confirmed", "operator_rejected"}:
        return "operator_override"

    source = str(detail.get("source") or "").strip()
    if source:
        return source

    lane = str(payload.get("extraction_lane") or payload.get("extractionLane") or "").strip().lower()
    if lane == "document_ai":
        return "document_ai"
    if lane in {"structured_mt", "structured_iso"}:
        return lane
    if lane == "support_only":
        return "support_text"

    method = str(payload.get("extraction_method") or "").strip().lower()
    if "ai" in method or "multimodal" in method:
        return "document_ai"
    if "support" in method or "text" in method:
        return "support_text"
    return "unknown"


def _evidence(detail: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    evidence = detail.get("evidence")
    if not isinstance(evidence, dict):
        return None, None, None
    page = evidence.get("page")
    if not isinstance(page, int):
        try:
            page = int(page) if page not in (None, "") else None
        except (TypeError, ValueError):
            page = None
    return (
        str(evidence.get("snippet") or "").strip() or None,
        str(evidence.get("source") or "").strip() or None,
        page,
    )


def build_insurance_fact_set(document_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = document_payload or {}
    fields = dict(_source_fields(payload))
    details = _detail_map(payload)
    recovered_fields, recovered_details = _raw_text_recoveries(payload, details)
    fields.update(recovered_fields)
    details.update(recovered_details)
    facts = []

    for field_name, aliases in _INSURANCE_FACT_FIELDS.items():
        value, source_field_name, detail = _first_value(payload, fields, details, aliases)
        confidence = _coerce_confidence(detail.get("confidence"))
        evidence_snippet, evidence_source, page = _evidence(detail)
        facts.append(
            DocumentFact(
                field_name=field_name,
                value=value,
                normalized_value=_normalize_fact_value(field_name, value),
                confidence=confidence,
                verification_state=_verification_state(value, detail),
                origin=_origin(payload, detail),
                source_field_name=source_field_name,
                evidence_snippet=evidence_snippet,
                evidence_source=evidence_source,
                page=page,
            )
        )

    document_type = str(payload.get("document_type") or "insurance_certificate").strip() or "insurance_certificate"
    document_subtype = str(payload.get("insurance_subtype") or document_type).strip() or None
    return DocumentFactSet(
        version="fact_graph_v1",
        document_type=document_type,
        document_subtype=document_subtype,
        facts=facts,
    ).to_dict()
