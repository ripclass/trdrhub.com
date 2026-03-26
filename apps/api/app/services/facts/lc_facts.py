from __future__ import annotations

import re
from datetime import datetime
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
_MT_FIELD_PATTERNS: Tuple[str, ...] = (
    r"(?ims)^\s*:\s*{tag}\s*:\s*(.*?)(?=^\s*:\s*\d{{2,3}}[A-Z]?\s*:|\Z)",
    r"(?ims)^\s*Field\s*{tag}\s*:\s*(.*?)(?=^\s*(?:Field\s*\d{{2,3}}[A-Z]?|:\s*\d{{2,3}}[A-Z]?\s*:)|\Z)",
)
_DATE_TOKEN_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{8}\b"),
    re.compile(r"\b\d{6}\b"),
)
_INCOTERM_RE = re.compile(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b", re.IGNORECASE)
_CURRENCY_AMOUNT_RE = re.compile(r"\b([A-Z]{3})\s*([0-9][0-9,\.]*)\b")
_AMOUNT_CURRENCY_RE = re.compile(r"\b([0-9][0-9,\.]*)\s*([A-Z]{3})\b")


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


def _raw_text_source(payload: Dict[str, Any]) -> Optional[str]:
    extraction_artifacts = (
        payload.get("extraction_artifacts_v1")
        if isinstance(payload.get("extraction_artifacts_v1"), dict)
        else {}
    )
    mt700 = payload.get("mt700") if isinstance(payload.get("mt700"), dict) else {}

    for value in (
        payload.get("raw_text"),
        payload.get("text"),
        payload.get("content"),
        payload.get("narrative"),
        extraction_artifacts.get("raw_text"),
        mt700.get("raw_text"),
        payload.get("raw_text_preview"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_mt_field_block(raw_text: str, tag: str) -> Optional[str]:
    text = str(raw_text or "")
    if not text.strip():
        return None
    for pattern in _MT_FIELD_PATTERNS:
        match = re.search(pattern.format(tag=re.escape(tag)), text)
        if not match:
            continue
        block = str(match.group(1) or "").strip()
        if block:
            return block
    return None


def _strip_leading_labels(text: str, labels: Iterable[str]) -> str:
    cleaned = str(text or "").strip()
    for label in labels:
        cleaned = re.sub(
            rf"(?im)^\s*(?:{re.escape(label)})\s*[:\-]?\s*",
            "",
            cleaned,
        ).strip()
    return cleaned


def _first_line(text: str) -> Optional[str]:
    for line in str(text or "").splitlines():
        cleaned = line.strip(" -\t")
        if cleaned:
            return cleaned
    return None


def _normalize_date_token(token: str) -> Optional[str]:
    normalized = normalize_date(token)
    if normalized and normalized != token:
        return normalized

    compact = re.sub(r"[^0-9]", "", str(token or ""))
    if len(compact) == 6:
        try:
            return datetime.strptime(compact, "%y%m%d").date().isoformat()
        except ValueError:
            return normalized
    return normalized


def _extract_date_from_block(block: str) -> Optional[str]:
    text = str(block or "")
    for pattern in _DATE_TOKEN_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        normalized = _normalize_date_token(match.group(0))
        if normalized:
            return normalized
    return None


def _recovery_detail(value: Any, snippet: str, *, confidence: float = 0.93) -> Dict[str, Any]:
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


def _raw_text_recoveries(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    raw_text = _raw_text_source(payload)
    if not raw_text:
        return {}, {}

    recovered_fields: Dict[str, Any] = {}
    recovered_details: Dict[str, Dict[str, Any]] = {}

    def _set(field_name: str, value: Any, snippet: Optional[str], *, confidence: float = 0.93) -> None:
        if not _is_populated(value) or field_name in recovered_fields:
            return
        recovered_fields[field_name] = value
        recovered_details[field_name] = _recovery_detail(value, snippet or str(value), confidence=confidence)

    lc_number_block = _extract_mt_field_block(raw_text, "20")
    if lc_number_block:
        lc_number_text = _strip_leading_labels(lc_number_block, ("Documentary Credit Number", "LC Number", "Credit Number"))
        lc_number_line = _first_line(lc_number_text) or lc_number_text
        lc_number_match = re.search(r"\b([A-Z0-9][A-Z0-9/\-]{4,})\b", lc_number_line or "", re.IGNORECASE)
        _set("lc_number", lc_number_match.group(1).strip() if lc_number_match else lc_number_line, lc_number_line, confidence=0.96)

    issue_block = _extract_mt_field_block(raw_text, "31C")
    if issue_block:
        _set("issue_date", _extract_date_from_block(issue_block), _first_line(issue_block) or issue_block, confidence=0.95)

    expiry_block = _extract_mt_field_block(raw_text, "31D")
    if expiry_block:
        _set("expiry_date", _extract_date_from_block(expiry_block), _first_line(expiry_block) or expiry_block, confidence=0.94)

    shipment_block = _extract_mt_field_block(raw_text, "44C")
    if shipment_block:
        _set(
            "latest_shipment_date",
            _extract_date_from_block(shipment_block),
            _first_line(shipment_block) or shipment_block,
            confidence=0.94,
        )

    applicant_block = _extract_mt_field_block(raw_text, "50")
    if applicant_block:
        applicant_text = _strip_leading_labels(applicant_block, ("Applicant",))
        _set("applicant", _first_line(applicant_text), _first_line(applicant_block) or applicant_block, confidence=0.92)

    beneficiary_block = _extract_mt_field_block(raw_text, "59")
    if beneficiary_block:
        beneficiary_text = _strip_leading_labels(beneficiary_block, ("Beneficiary",))
        _set("beneficiary", _first_line(beneficiary_text), _first_line(beneficiary_block) or beneficiary_block, confidence=0.92)

    amount_block = _extract_mt_field_block(raw_text, "32B")
    if amount_block:
        amount_text = _strip_leading_labels(amount_block, ("Currency Code, Amount", "Amount"))
        snippet = _first_line(amount_block) or amount_block
        match = _CURRENCY_AMOUNT_RE.search(amount_text)
        if not match:
            match = _AMOUNT_CURRENCY_RE.search(amount_text)
            if match:
                _set("amount", match.group(1).strip(), snippet, confidence=0.94)
                _set("currency", match.group(2).strip(), snippet, confidence=0.94)
        else:
            _set("currency", match.group(1).strip(), snippet, confidence=0.94)
            _set("amount", match.group(2).strip(), snippet, confidence=0.94)

    port_loading_block = _extract_mt_field_block(raw_text, "44E")
    if port_loading_block:
        loading_text = _strip_leading_labels(port_loading_block, ("Port of Loading", "Airport of Departure"))
        _set("port_of_loading", _first_line(loading_text), _first_line(port_loading_block) or port_loading_block, confidence=0.9)

    port_discharge_block = _extract_mt_field_block(raw_text, "44F")
    if port_discharge_block:
        discharge_text = _strip_leading_labels(port_discharge_block, ("Port of Discharge", "Airport of Destination"))
        _set("port_of_discharge", _first_line(discharge_text), _first_line(port_discharge_block) or port_discharge_block, confidence=0.9)

    ucp_block = _extract_mt_field_block(raw_text, "40E")
    if ucp_block:
        ucp_text = _strip_leading_labels(ucp_block, ("Applicable Rules",))
        _set("ucp_reference", _first_line(ucp_text), _first_line(ucp_block) or ucp_block, confidence=0.9)

    goods_block = _extract_mt_field_block(raw_text, "45A")
    if goods_block:
        goods_text = _strip_leading_labels(goods_block, ("Description of Goods",))
        _set("goods_description", goods_text.strip(), _first_line(goods_block) or goods_block, confidence=0.88)
        incoterm_match = _INCOTERM_RE.search(goods_text)
        if incoterm_match:
            _set("incoterm", incoterm_match.group(1).upper(), incoterm_match.group(0), confidence=0.88)

    issuing_bank_block = _extract_mt_field_block(raw_text, "52A") or _extract_mt_field_block(raw_text, "52D")
    if issuing_bank_block:
        _set("issuing_bank", _first_line(issuing_bank_block), _first_line(issuing_bank_block) or issuing_bank_block, confidence=0.88)

    advising_bank_block = _extract_mt_field_block(raw_text, "57A") or _extract_mt_field_block(raw_text, "57D")
    if advising_bank_block:
        _set("advising_bank", _first_line(advising_bank_block), _first_line(advising_bank_block) or advising_bank_block, confidence=0.88)

    return recovered_fields, recovered_details


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
    recovered_fields, recovered_details = _raw_text_recoveries(payload)
    for key, value in recovered_fields.items():
        if not _is_populated(fields.get(key)):
            fields[key] = value
    for key, detail in recovered_details.items():
        if not isinstance(details.get(key), dict):
            details[key] = detail
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
