from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Tuple

from .models import DocumentFact, DocumentFactSet
from .normalization import normalize_date, normalize_party_name, normalize_reference


_BL_FACT_FIELDS: Dict[str, Tuple[str, ...]] = {
    "bl_number": (
        "bl_number",
        "bill_of_lading_number",
        "transport_document_reference",
        "transport_reference_number",
    ),
    "consignment_reference": (
        "consignment_reference",
        "transport_document_reference",
        "transport_reference_number",
        "bl_number",
        "receipt_number",
        "courier_receipt_number",
    ),
    "airway_bill_number": ("airway_bill_number", "awb_number", "bl_number"),
    "shipper": ("shipper", "shipper_name", "exporter"),
    "consignee": ("consignee", "consignee_name", "importer", "applicant"),
    "port_of_loading": ("port_of_loading", "pol", "load_port", "loading_port"),
    "port_of_discharge": ("port_of_discharge", "pod", "discharge_port", "destination_port"),
    "airport_of_departure": ("airport_of_departure", "port_of_loading"),
    "airport_of_destination": ("airport_of_destination", "port_of_discharge"),
    "transport_mode_chain": ("transport_mode_chain",),
    "carriage_vessel_name": ("carriage_vessel_name", "vessel_name"),
    "carriage_voyage_number": ("carriage_voyage_number", "voyage_number"),
    "on_board_date": (
        "on_board_date",
        "shipped_on_board_date",
        "shipment_date",
        "date_of_shipment",
        "date",
    ),
}
_RAW_TEXT_FIELD_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "port_of_loading": ("Port of Loading", "POL", "Load Port", "Loading Port"),
    "port_of_discharge": ("Port of Discharge", "POD", "Discharge Port", "Destination Port"),
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
    if field_name == "on_board_date":
        return normalize_date(value)
    if field_name in {"shipper", "consignee"}:
        return normalize_party_name(value)
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


def _extract_labeled_line(raw_text: str, labels: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    text = str(raw_text or "")
    if not text.strip():
        return None, None
    for label in labels:
        pattern = re.compile(
            rf"(?im)^\s*{re.escape(label)}\s*[:\-]\s*(.+?)\s*$",
        )
        match = pattern.search(text)
        if not match:
            continue
        value = str(match.group(1) or "").strip()
        if value:
            snippet = f"{label}: {value}"
            return value, snippet
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

    for field_name, labels in _RAW_TEXT_FIELD_PATTERNS.items():
        detail = details.get(field_name) if isinstance(details.get(field_name), dict) else {}
        if not _can_use_raw_text_recovery(detail):
            continue
        recovered_value, snippet = _extract_labeled_line(raw_text, labels)
        if not _is_populated(recovered_value):
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


def build_bl_fact_set(document_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = document_payload or {}
    fields = _source_fields(payload)
    details = _detail_map(payload)
    recovered_fields, recovered_details = _raw_text_recoveries(payload, details)
    fields = {**fields, **recovered_fields}
    details = {**details, **recovered_details}
    facts = []

    for field_name, aliases in _BL_FACT_FIELDS.items():
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

    document_type = str(payload.get("document_type") or "bill_of_lading").strip() or "bill_of_lading"
    return DocumentFactSet(
        version="fact_graph_v1",
        document_type=document_type,
        document_subtype=str(payload.get("transport_subtype") or document_type).strip() or None,
        facts=facts,
    ).to_dict()
