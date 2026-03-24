from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

from .models import DocumentFact, DocumentFactSet
from .normalization import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_party_name,
    normalize_reference,
)


_LC_FACT_FIELDS: Dict[str, Tuple[str, ...]] = {
    "lc_number": ("lc_number", "number", "reference"),
    "issue_date": ("issue_date",),
    "expiry_date": ("expiry_date",),
    "latest_shipment_date": ("latest_shipment_date", "latest_shipment"),
    "applicant": ("applicant", "applicant_name"),
    "beneficiary": ("beneficiary", "beneficiary_name"),
    "issuing_bank": ("issuing_bank", "issuing_bank_name"),
    "advising_bank": ("advising_bank", "advising_bank_name"),
    "amount": ("amount", "lc_amount"),
    "currency": ("currency",),
    "port_of_loading": ("port_of_loading",),
    "port_of_discharge": ("port_of_discharge",),
    "incoterm": ("incoterm",),
    "goods_description": ("goods_description",),
    "documents_required": ("documents_required",),
    "ucp_reference": ("ucp_reference",),
}

_LC_SYSTEM_AUTHORITY_FIELDS = {
    "incoterm",
    "goods_description",
    "documents_required",
    "ucp_reference",
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


def _payload_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}

    fields = payload.get("extracted_fields")
    if isinstance(fields, dict):
        flattened.update(fields)

    dates = payload.get("dates")
    if isinstance(dates, dict):
        flattened.setdefault("issue_date", dates.get("issue") or dates.get("issue_date"))
        flattened.setdefault("expiry_date", dates.get("expiry") or dates.get("expiry_date"))
        flattened.setdefault(
            "latest_shipment_date",
            dates.get("latest_shipment") or dates.get("latest_shipment_date"),
        )

    ports = payload.get("ports")
    if isinstance(ports, dict):
        flattened.setdefault(
            "port_of_loading",
            ports.get("loading") or ports.get("port_of_loading"),
        )
        flattened.setdefault(
            "port_of_discharge",
            ports.get("discharge") or ports.get("port_of_discharge"),
        )

    amount = payload.get("amount")
    if isinstance(amount, dict):
        flattened.setdefault("amount", amount.get("value") or amount.get("amount"))
        flattened.setdefault("currency", amount.get("currency"))

    for key in ("applicant", "beneficiary", "issuing_bank", "advising_bank"):
        value = payload.get(key)
        if isinstance(value, dict):
            flattened.setdefault(key, value.get("name") or value.get("value"))

    flattened.setdefault(
        "lc_number",
        payload.get("lc_number") or payload.get("number") or payload.get("reference"),
    )
    flattened.setdefault("issue_date", payload.get("issue_date"))
    flattened.setdefault("expiry_date", payload.get("expiry_date"))
    flattened.setdefault(
        "latest_shipment_date",
        payload.get("latest_shipment_date") or payload.get("latest_shipment"),
    )
    flattened.setdefault("amount", payload.get("amount"))
    flattened.setdefault("currency", payload.get("currency"))
    flattened.setdefault("port_of_loading", payload.get("port_of_loading"))
    flattened.setdefault("port_of_discharge", payload.get("port_of_discharge"))
    flattened.setdefault("incoterm", payload.get("incoterm"))
    flattened.setdefault("goods_description", payload.get("goods_description"))
    flattened.setdefault("documents_required", payload.get("documents_required"))
    flattened.setdefault("ucp_reference", payload.get("ucp_reference"))

    return flattened


def _first_detail(
    details: Dict[str, Dict[str, Any]],
    aliases: Iterable[str],
) -> Tuple[Optional[str], Dict[str, Any]]:
    for alias in aliases:
        detail = details.get(alias)
        if isinstance(detail, dict):
            return alias, detail
    return None, {}


def _first_value(
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

    detail_alias, detail = _first_detail(details, aliases)
    if detail_alias:
        return None, detail_alias, detail

    return None, None, {}


def _normalize_fact_value(field_name: str, value: Any) -> Optional[Any]:
    if field_name in {"issue_date", "expiry_date", "latest_shipment_date"}:
        return normalize_date(value)
    if field_name == "amount":
        return normalize_amount(value)
    if field_name == "currency":
        return normalize_currency(value)
    if field_name in {"applicant", "beneficiary", "issuing_bank", "advising_bank"}:
        return normalize_party_name(value)
    if field_name == "documents_required":
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return normalize_reference(value)
    return normalize_reference(value)


def _verification_state(field_name: str, value: Any, detail: Dict[str, Any]) -> str:
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
    if field_name in _LC_SYSTEM_AUTHORITY_FIELDS and _is_populated(value):
        return "confirmed"
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


def build_lc_fact_set(document_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = document_payload or {}
    fields = _payload_fields(payload)
    details = _detail_map(payload)
    facts = []

    for field_name, aliases in _LC_FACT_FIELDS.items():
        value, source_field_name, detail = _first_value(fields, details, aliases)
        confidence = _coerce_confidence(detail.get("confidence"))
        evidence_snippet, evidence_source, page = _evidence(detail)
        facts.append(
            DocumentFact(
                field_name=field_name,
                value=value,
                normalized_value=_normalize_fact_value(field_name, value),
                confidence=confidence,
                verification_state=_verification_state(field_name, value, detail),
                origin=_origin(payload, detail),
                source_field_name=source_field_name,
                evidence_snippet=evidence_snippet,
                evidence_source=evidence_source,
                page=page,
            )
        )

    document_type = str(payload.get("document_type") or "letter_of_credit").strip() or "letter_of_credit"
    return DocumentFactSet(
        version="fact_graph_v1",
        document_type=document_type,
        document_subtype=str(payload.get("lc_subtype") or document_type).strip() or None,
        facts=facts,
    ).to_dict()
