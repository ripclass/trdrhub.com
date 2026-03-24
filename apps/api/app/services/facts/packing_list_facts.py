from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

from .models import DocumentFact, DocumentFactSet
from .normalization import normalize_date, normalize_reference


_PACKING_LIST_FACT_FIELDS: Dict[str, Tuple[str, ...]] = {
    "packing_list_number": ("packing_list_number", "packing_no", "packing_reference"),
    "document_date": ("document_date", "date", "issue_date"),
    "total_packages": ("total_packages", "package_count", "number_of_packages", "cartons", "total_cartons"),
    "gross_weight": ("gross_weight", "gross_wt", "total_gross_weight"),
    "net_weight": ("net_weight", "net_wt", "total_net_weight"),
    "marks_and_numbers": ("marks_and_numbers", "shipping_marks", "marks"),
    "packing_size_breakdown": ("packing_size_breakdown", "size_breakdown", "carton_size", "dimensions"),
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
    if field_name == "document_date":
        return normalize_date(value)
    return normalize_reference(value)


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


def build_packing_list_fact_set(document_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = document_payload or {}
    fields = _source_fields(payload)
    details = _detail_map(payload)
    facts = []

    for field_name, aliases in _PACKING_LIST_FACT_FIELDS.items():
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

    return DocumentFactSet(
        version="fact_graph_v1",
        document_type="packing_list",
        document_subtype=str(payload.get("document_type") or "").strip() or None,
        facts=facts,
    ).to_dict()
