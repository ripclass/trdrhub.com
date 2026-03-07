from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .contract import DocumentExtraction, EvidenceRef, ExtractionBundle, FieldExtraction
from .field_states import infer_field_state
from .gate import evaluate_review_gate
from .profiles import load_profile

EXTRACTION_CORE_V1_ENV = "LCCOPILOT_EXTRACTION_CORE_V1_ENABLED"
PREPARSER_HARDENING_ENV = "LCCOPILOT_PREPARSER_HARDENING_ENABLED"
FAILURE_TAXONOMY_V2_ENV = "LCCOPILOT_FAILURE_TAXONOMY_V2_ENABLED"
PASS_GATE_V2_ENV = "LCCOPILOT_PASS_GATE_V2_ENABLED"
TOP3_FIELD_BOOST_V1_ENV = "LCCOPILOT_TOP3_FIELD_BOOST_V1_ENABLED"

_OCR_DIGIT_MAP = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"})
_WEIGHT_UNIT_OCR_FIXUPS = {
    "K6": "KG",
    "K65": "KGS",
    "K9": "KG",
    "K95": "KGS",
    "L8": "LB",
    "L85": "LBS",
}
_CANONICAL_REASON_CODES = {
    "OCR_UNSUPPORTED_FORMAT",
    "OCR_TIMEOUT",
    "OCR_AUTH_ERROR",
    "OCR_EMPTY_RESULT",
    "FIELD_NOT_FOUND",
    "FORMAT_INVALID",
    "EVIDENCE_MISSING",
    "LOW_CONFIDENCE_CRITICAL",
    "CROSS_FIELD_CONFLICT",
}
_PARSE_FAILURE_MARKERS = ("parse", "invalid", "failed", "error", "format", "rejected", "retry")
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")
_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
_PREPARSER_FIELDS = (
    "lc_number",
    "issue_date",
    "amount",
    "currency",
    "bin_tin",
    "voyage",
    "gross_weight",
    "net_weight",
    "issuer",
)
_FIELD_PRIORITY = {name: index for index, name in enumerate(_PREPARSER_FIELDS)}
_TOP3_FIELD_NAMES = frozenset({"bin_tin", "gross_weight", "net_weight"})


@dataclass(frozen=True)
class _ParsedFieldCandidate:
    name: str
    value_raw: Optional[Any]
    value_normalized: Optional[Any]
    state: str
    confidence: float
    evidence_snippet: Optional[str]
    reason_codes: List[str]
    source: str
    anchor_hit: bool = False


def _env_enabled(name: str) -> bool:
    raw = str(os.getenv(name, "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def extraction_core_v1_enabled() -> bool:
    return _env_enabled(EXTRACTION_CORE_V1_ENV)


def _preparser_hardening_enabled() -> bool:
    return _env_enabled(PREPARSER_HARDENING_ENV)


def _failure_taxonomy_v2_enabled() -> bool:
    return _env_enabled(FAILURE_TAXONOMY_V2_ENV)


def _pass_gate_v2_enabled() -> bool:
    return _env_enabled(PASS_GATE_V2_ENV)


def _top3_field_boost_v1_enabled() -> bool:
    return _env_enabled(TOP3_FIELD_BOOST_V1_ENV)


_DEFAULT_FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "issue_date": ("issue_date", "date", "invoice_date", "bl_date", "date_of_issue", "doc_date"),
    "issuer": ("issuer", "issuer_name"),
    "gross_weight": ("gross_weight", "gross_wt", "weight_gross", "gross", "total_gross_weight"),
    "net_weight": ("net_weight", "net_wt", "weight_net", "net", "total_net_weight"),
    "voyage": ("voyage", "voyage_number", "bl_voyage_no"),
    "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
}

_DOC_FIELD_ALIASES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "letter_of_credit": {
        "issuer": ("issuer", "issuing_bank", "issuer_name", "issuing_bank_name"),
        "issue_date": ("issue_date", "date_of_issue", "doc_date"),
    },
    "commercial_invoice": {
        "issuer": ("issuer", "seller_name", "seller", "exporter_name", "shipper"),
        "issue_date": ("issue_date", "invoice_date", "date", "doc_date"),
        "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
    },
    "bill_of_lading": {
        "issuer": ("issuer", "carrier", "shipper"),
        "issue_date": ("issue_date", "bl_date", "date", "date_of_issue", "shipped_on_board_date"),
        "voyage": ("voyage", "voyage_number", "bl_voyage_no"),
        "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
    },
    "packing_list": {
        "issuer": ("issuer", "shipper", "seller_name", "exporter_name"),
        "issue_date": ("issue_date", "date", "packing_list_date", "doc_date"),
    },
}

_FIELD_LABEL_TOKENS: Dict[str, Tuple[str, ...]] = {
    "lc_number": ("lc no", "lc number", "credit number", "documentary credit", ":20:"),
    "issue_date": ("issue date", "date of issue", "invoice date", "bl date", "packing list date", ":31c:"),
    "amount": (":32b:", "credit amount", "invoice amount", "total amount", "amount"),
    "currency": (":32b:", "currency", "ccy", "credit amount", "invoice amount", "amount"),
    "bin_tin": ("bin", "tin", "tax id", "tax identification", "vat reg", "vat no", "etin"),
    "voyage": ("voyage", "voy no", "voy.", "vvd", "vessel/voy"),
    "gross_weight": ("gross/net", "gross weight", "gross wt", "gross wgt", "g.w.", "gw"),
    "net_weight": ("gross/net", "net weight", "net wt", "net wgt", "n.w.", "nw"),
    "issuer": ("issuing bank", "issuer", "seller", "shipper", "carrier", "exporter"),
}

_DOC_ISSUER_TOKENS: Dict[str, Tuple[str, ...]] = {
    "letter_of_credit": ("issuing bank", "issuer"),
    "commercial_invoice": ("seller", "shipper", "exporter", "issuer"),
    "bill_of_lading": ("carrier", "shipper", "issuer"),
    "packing_list": ("shipper", "seller", "exporter", "issuer"),
}

_WEIGHT_UNIT_ALIASES = {
    "KG": 1.0,
    "KGS": 1.0,
    "KILOGRAM": 1.0,
    "KILOGRAMS": 1.0,
    "MT": 1000.0,
    "TON": 1000.0,
    "TONNE": 1000.0,
    "LBS": 0.45359237,
    "LB": 0.45359237,
}


def _field_aliases(field_name: str, document_type: str) -> Tuple[str, ...]:
    aliases: List[str] = []
    aliases.extend((_DOC_FIELD_ALIASES.get(document_type) or {}).get(field_name, ()))
    aliases.extend(_DEFAULT_FIELD_ALIASES.get(field_name, (field_name,)))
    aliases.append(field_name)
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _extract_field_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("value", "normalized_value", "normalized", "text", "raw_value", "raw"):
            if key in value:
                return value.get(key)
    return value


def _coerce_confidence(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1:
        confidence = confidence / 100.0
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def _normalize_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return str(value).strip()


def _base_clean(value: Any) -> str:
    return unicodedata.normalize("NFKC", _normalize_text(value))


def _scan_lines(raw_text: str) -> List[str]:
    return [line.strip() for line in (raw_text or "").splitlines() if line and line.strip()]


def _normalize_numeric_context(raw_text: str) -> str:
    return _base_clean(raw_text).upper().translate(_OCR_DIGIT_MAP)


def _normalize_numeric_token(token: str) -> str:
    return _base_clean(token).upper().translate(_OCR_DIGIT_MAP)


def _format_decimal(value: float, decimals: int = 3) -> str:
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return round(value, 4)


def _field_tokens(field_name: str, document_type: str) -> Tuple[str, ...]:
    if field_name == "issuer":
        tokens = list(_DOC_ISSUER_TOKENS.get(document_type, ())) or list(_FIELD_LABEL_TOKENS["issuer"])
        return tuple(tokens)
    return _FIELD_LABEL_TOKENS.get(field_name, ())


def _label_seen(raw_text: str, field_name: str, document_type: str) -> bool:
    lowered = _normalize_text(raw_text).lower()
    return any(token in lowered for token in _field_tokens(field_name, document_type))


def _compute_candidate_confidence(
    *,
    source: str,
    state: str,
    explicit_confidence: Optional[float] = None,
    anchor_hit: bool = False,
    evidence_snippet: Optional[str] = None,
    normalized_value: Optional[Any] = None,
) -> float:
    if explicit_confidence is not None:
        return _clamp_confidence(explicit_confidence)
    if state == "missing":
        return 0.0
    if state == "parse_failed":
        score = 0.28
        if anchor_hit:
            score += 0.07
        return _clamp_confidence(score)

    score = 0.58
    if source == "existing":
        score += 0.08
    if anchor_hit:
        score += 0.14
    if evidence_snippet:
        score += 0.10
    if normalized_value not in (None, "", [], {}):
        score += 0.08
    if source == "preparser" and not anchor_hit:
        score -= 0.08
    return _clamp_confidence(score)


def _canonicalize_reason_codes(raw_codes: Iterable[Any]) -> List[str]:
    canonical: List[str] = []
    for raw_code in raw_codes:
        text = _normalize_text(raw_code)
        if not text:
            continue
        upper = text.upper()
        if upper in _CANONICAL_REASON_CODES:
            canonical.append(upper)
            continue

        lowered = text.lower()
        if any(token in lowered for token in ("unsupported", "invalid mime", "content type", "content-type")):
            canonical.append("OCR_UNSUPPORTED_FORMAT")
        elif "timeout" in lowered or "timed out" in lowered or "deadline" in lowered:
            canonical.append("OCR_TIMEOUT")
        elif any(token in lowered for token in ("unauthor", "forbidden", "credential", "access denied", "permission", "api key", "auth")):
            canonical.append("OCR_AUTH_ERROR")
        elif any(token in lowered for token in ("empty_all_stages", "parser_empty_output", "empty_output", "empty result", "empty_result", "no text", "no output", "provider_unavailable")):
            canonical.append("OCR_EMPTY_RESULT")
        elif any(token in lowered for token in ("evidence_missing", "evidence missing")):
            canonical.append("EVIDENCE_MISSING")
        elif any(token in lowered for token in ("low_confidence", "low confidence")):
            canonical.append("LOW_CONFIDENCE_CRITICAL")
        elif any(token in lowered for token in ("net_gt_gross", "amount_currency", "cross_field_conflict", "conflict")):
            canonical.append("CROSS_FIELD_CONFLICT")
        elif any(
            token in lowered
            for token in (
                "parse_failed",
                "format_invalid",
                "date_parse_invalid",
                "bin_length_invalid",
                "tin_length_invalid",
                "weight_unit_unknown",
                "weight_number_missing",
                "voyage_format_invalid",
                "issuer_empty",
                "invalid",
            )
        ):
            canonical.append("FORMAT_INVALID")
        elif any(token in lowered for token in ("field_not_found", "missing")):
            canonical.append("FIELD_NOT_FOUND")

    return sorted(dict.fromkeys(code for code in canonical if code))


def _field_reason_codes(state: str, base_codes: Iterable[Any]) -> List[str]:
    reason_codes = _canonicalize_reason_codes(base_codes)
    if state == "missing":
        reason_codes.append("FIELD_NOT_FOUND")
    elif state == "parse_failed":
        reason_codes.append("FORMAT_INVALID")
    return sorted(dict.fromkeys(reason_codes))


def _extract_value_and_details(
    document: Dict[str, Any],
    extracted_fields: Dict[str, Any],
    field_details: Dict[str, Dict[str, Any]],
    field_name: str,
    document_type: str,
) -> Tuple[str, Any, Dict[str, Any], List[Dict[str, Any]]]:
    aliases = _field_aliases(field_name, document_type)
    selected_key = aliases[0] if aliases else field_name
    selected_value: Any = None
    selected_details: Dict[str, Any] = {}
    detail_candidates: List[Dict[str, Any]] = []

    for key in aliases:
        details = field_details.get(key) if isinstance(field_details.get(key), dict) else {}
        if details:
            detail_candidates.append(details)
        raw_value = None
        if isinstance(extracted_fields, dict) and key in extracted_fields:
            raw_value = extracted_fields.get(key)
        elif key in document:
            raw_value = document.get(key)
        value = _extract_field_value(raw_value)

        if selected_value in (None, "", [], {}) and value not in (None, "", [], {}):
            selected_key = key
            selected_value = value
            selected_details = details
        elif not selected_details and details:
            selected_key = key
            selected_details = details

    return selected_key, selected_value, selected_details, detail_candidates


def _infer_parse_error(detail_candidates: Iterable[Dict[str, Any]]) -> bool:
    for details in detail_candidates:
        if not isinstance(details, dict):
            continue
        if details.get("parse_error") is True:
            return True
        markers = [
            details.get("status"),
            details.get("reason"),
            details.get("reason_code"),
            details.get("decision_status"),
        ]
        issues = details.get("issues")
        if isinstance(issues, list):
            markers.extend(issues)
        for marker in markers:
            text = _normalize_text(marker).lower()
            if text and any(flag in text for flag in _PARSE_FAILURE_MARKERS):
                return True
    return False


def _snippet_from_text(raw_text: str, value: Any) -> Optional[str]:
    needle = _normalize_text(value)
    haystack = _normalize_text(raw_text)
    if not needle or not haystack:
        return None
    lower_haystack = haystack.lower()
    lower_needle = needle.lower()
    index = lower_haystack.find(lower_needle)
    if index < 0:
        return None
    start = max(0, index - 40)
    end = min(len(haystack), index + len(needle) + 40)
    return haystack[start:end]


def _build_evidence_refs(details: Dict[str, Any], value: Any, raw_text: str) -> List[EvidenceRef]:
    evidence_refs: List[EvidenceRef] = []
    raw_candidates: List[Any] = []

    for key in ("evidence", "evidence_span", "evidence_spans", "spans"):
        if key in details:
            raw_candidates.append(details.get(key))

    if not raw_candidates:
        inline_text = None
        for key in ("evidence_snippet", "text_span", "raw_text", "snippet", "text"):
            candidate = _normalize_text(details.get(key))
            if candidate:
                inline_text = candidate
                break
        if not inline_text:
            inline_text = _snippet_from_text(raw_text, value)
        if inline_text:
            raw_candidates.append(
                {
                    "page": details.get("page") or details.get("page_number") or 1,
                    "text_span": inline_text,
                    "bbox": details.get("bbox"),
                    "source_layer": details.get("source") or details.get("source_layer"),
                    "confidence": details.get("confidence"),
                }
            )

    for candidate in raw_candidates:
        items = candidate if isinstance(candidate, list) else [candidate]
        for item in items:
            if isinstance(item, str):
                text_span = item.strip()
                page = 1
                bbox = None
                source_layer = None
                confidence = None
            elif isinstance(item, dict):
                text_span = _normalize_text(
                    item.get("text_span")
                    or item.get("text")
                    or item.get("snippet")
                    or item.get("raw")
                    or item.get("value")
                )
                page = int(item.get("page") or item.get("page_number") or 1)
                bbox = item.get("bbox")
                source_layer = item.get("source_layer") or item.get("source")
                confidence = item.get("confidence")
            else:
                continue
            if not text_span:
                continue
            evidence_refs.append(
                EvidenceRef(
                    page=page if page >= 1 else 1,
                    text_span=text_span,
                    bbox=bbox if isinstance(bbox, list) else None,
                    source_layer=_normalize_text(source_layer) or None,
                    confidence=_coerce_confidence(confidence),
                )
            )
    return evidence_refs


def _build_parser_evidence(snippet: Optional[str], confidence: float) -> List[EvidenceRef]:
    text_span = _normalize_text(snippet)
    if not text_span:
        return []
    return [EvidenceRef(page=1, text_span=text_span, source_layer="preparser", confidence=_coerce_confidence(confidence))]


def _field_confidence(document: Dict[str, Any], details: Dict[str, Any]) -> float:
    for candidate in (
        details.get("final_confidence"),
        details.get("confidence"),
        details.get("ai_confidence"),
        document.get("extraction_confidence"),
        document.get("ocr_confidence"),
        document.get("ocrConfidence"),
    ):
        confidence = _coerce_confidence(candidate)
        if confidence is not None:
            return confidence
    return 0.0


def _normalize_lc_number(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(r"^(?:LC\s*(?:NO\.?|NUMBER|#)|L/C\s*(?:NO\.?|NUMBER|#)|CREDIT\s*(?:NO\.?|NUMBER|#)|REF(?:ERENCE)?)\s*[:#-]*\s*", "", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^A-Z0-9/-]", "", text)
    if len(text) < 5 or not re.search(r"\d", text):
        return None, "FORMAT_INVALID"
    return text, None


def _normalize_issue_date(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value)
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(r"^(?:DATE(?:\s+OF)?\s+ISSUE|ISSUE\s+DATE|INVOICE\s+DATE|BL\s+DATE|DOC(?:UMENT)?\s+DATE|:31C:)\s*[:#-]*\s*", "", text, flags=re.IGNORECASE)
    compact = text.strip()
    if re.fullmatch(r"\d{6}", compact):
        year_prefix = 2000 if int(compact[:2]) <= 69 else 1900
        try:
            parsed = datetime(year=year_prefix + int(compact[:2]), month=int(compact[2:4]), day=int(compact[4:6]))
            return parsed.strftime("%Y-%m-%d"), None
        except ValueError:
            return None, "FORMAT_INVALID"
    for pattern in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(compact, pattern)
            return parsed.strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", compact)
    if match:
        month = _MONTHS.get(match.group(2)[:3].upper())
        if month is None:
            return None, "FORMAT_INVALID"
        try:
            parsed = datetime(year=int(match.group(3)), month=month, day=int(match.group(1)))
            return parsed.strftime("%Y-%m-%d"), None
        except ValueError:
            return None, "FORMAT_INVALID"
    return None, "FORMAT_INVALID"


def _normalize_amount(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(r"^(?:AMOUNT|CREDIT\s+AMOUNT|INVOICE\s+AMOUNT|TOTAL\s+AMOUNT|:32B:)\s*[:#-]*\s*", "", text)
    text = re.sub(r"^[A-Z]{3}\s*", "", text)
    digits = re.sub(r"[^0-9,.\-]", "", text)
    if not digits or digits in {".", ",", "-"}:
        return None, "FORMAT_INVALID"
    if digits.count(",") > 1 and "." not in digits:
        digits = digits.replace(",", "")
    elif "," in digits and "." not in digits:
        digits = digits.replace(",", ".")
    else:
        digits = digits.replace(",", "")
    try:
        value = float(digits)
    except ValueError:
        return None, "FORMAT_INVALID"
    if value <= 0:
        return None, "FORMAT_INVALID"
    return f"{value:.2f}", None


def _normalize_currency(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, "FIELD_NOT_FOUND"
    match = re.search(r"\b([A-Z]{3})\b", text)
    if not match:
        return None, "FORMAT_INVALID"
    return match.group(1), None


def _normalize_bin_tin(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _normalize_numeric_context(raw_value)
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(
        r"\b(?:EXPORTER|SELLER|SHIPPER|VAT\s*REG(?:ISTRATION)?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|BIN|TIN|TAX\s*ID|TAX\s*IDENTIFICATION|E-?TIN|ETIN)\b",
        " ",
        text,
    )
    digits = re.sub(r"\D", "", text)
    if len(digits) == 13:
        return digits, None
    if 10 <= len(digits) <= 12:
        return digits, None
    return None, "FORMAT_INVALID"


def _normalize_voyage(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(r"\b(?:VOYAGE|VOY\.?|VOY\s*NO\.?|VVD|VYG|NO\.?)\b", " ", text)
    text = re.sub(r"[\s/\\]+", "-", text)
    text = re.sub(r"[^A-Z0-9.-]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text or not re.search(r"[A-Z]", text) or not re.search(r"\d", text):
        return None, "FORMAT_INVALID"
    return text, None


def _normalize_weight(raw_value: Any) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, None, "FIELD_NOT_FOUND"
    text = re.sub(r"\bK[69]S?\b", lambda match: _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(0), match.group(0)), text)
    text = re.sub(r"\bL8S?\b", lambda match: _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(0), match.group(0)), text)
    match = re.search(r"([0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?)\s*([A-Z0-9]+)", text)
    if not match:
        return None, None, "FORMAT_INVALID"
    number_text = _normalize_numeric_token(match.group(1)).replace(",", "")
    unit = re.sub(r"[^A-Z]", "", _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(2).upper(), match.group(2).upper()))
    factor = _WEIGHT_UNIT_ALIASES.get(unit)
    if factor is None:
        return None, None, "FORMAT_INVALID"
    try:
        value = float(number_text)
    except ValueError:
        return None, None, "FORMAT_INVALID"
    kg_value = round(value * factor, 3)
    return f"{_format_decimal(kg_value)} KG", kg_value, None


def _normalize_issuer(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(r"^(?:ISSUING\s+BANK|ISSUER|SELLER|SHIPPER|CARRIER|EXPORTER)\s*[:#-]*\s*", "", text)
    text = re.sub(r"\bLIMITED\b", "LTD", text)
    text = re.sub(r"\bLTD\.?\b", "LTD", text)
    text = re.sub(r"\bPRIVATE\b", "PVT", text)
    text = re.sub(r"\bPVT\.?\b", "PVT", text)
    text = re.sub(r"[^A-Z0-9&/ -]", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    if len(text) < 3 or not re.search(r"[A-Z]", text):
        return None, "FORMAT_INVALID"
    return text, None


def _normalize_field_value(field_name: str, raw_value: Any) -> Tuple[Optional[Any], Optional[str], Optional[float]]:
    if field_name == "lc_number":
        normalized, error = _normalize_lc_number(raw_value)
        return normalized, error, None
    if field_name == "issue_date":
        normalized, error = _normalize_issue_date(raw_value)
        return normalized, error, None
    if field_name == "amount":
        normalized, error = _normalize_amount(raw_value)
        return normalized, error, None
    if field_name == "currency":
        normalized, error = _normalize_currency(raw_value)
        return normalized, error, None
    if field_name == "bin_tin":
        normalized, error = _normalize_bin_tin(raw_value)
        return normalized, error, None
    if field_name == "voyage":
        normalized, error = _normalize_voyage(raw_value)
        return normalized, error, None
    if field_name in {"gross_weight", "net_weight"}:
        normalized, numeric_kg, error = _normalize_weight(raw_value)
        return normalized, error, numeric_kg
    if field_name == "issuer":
        normalized, error = _normalize_issuer(raw_value)
        return normalized, error, None
    return raw_value, None, None


def _patterns_for_field(field_name: str, document_type: str) -> Sequence[re.Pattern[str]]:
    if field_name == "lc_number":
        return (
            re.compile(r":20:\s*([A-Z0-9][A-Z0-9/-]{4,30})", re.IGNORECASE),
            re.compile(r"(?:LC|L/C|CREDIT|DOCUMENTARY\s+CREDIT)\s*(?:NO\.?|NUMBER|#|REF(?:ERENCE)?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{4,30})", re.IGNORECASE),
        )
    if field_name == "issue_date":
        return (
            re.compile(r":31C:\s*([0-9]{6})", re.IGNORECASE),
            re.compile(r"(?:DATE\s+OF\s+ISSUE|ISSUE\s+DATE|INVOICE\s+DATE|BL\s+DATE|PACKING\s+LIST\s+DATE|DOC(?:UMENT)?\s+DATE)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 ./-]{5,24})", re.IGNORECASE),
        )
    if field_name == "bin_tin":
        return (
            re.compile(r"(?:BIN(?:\s*/\s*TIN)?|VAT\s*REG(?:ISTRATION)?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?)\s*(?:(?:NO\.?|NUMBER)\s*)?[:#-]?\s*([A-Z0-9OISBL-]{8,24})", re.IGNORECASE),
            re.compile(r"(?:TIN(?:\s*/\s*BIN)?|TAX\s*ID|TAX\s*IDENTIFICATION|E-?TIN|ETIN)\s*(?:(?:NO\.?|NUMBER)\s*)?[:#-]?\s*([A-Z0-9OISBL-]{8,24})", re.IGNORECASE),
        )
    if field_name == "voyage":
        return (
            re.compile(r"(?:VOYAGE(?:\s*NO\.?|\s*NUMBER|\s*#)?|VOY\.?|VVD(?:\s*(?:NO\.?|NUMBER|#))?)\s*[:#-]?\s*([A-Z0-9./-]{2,24})", re.IGNORECASE),
            re.compile(r"(?:VSL|VESSEL)\s*(?:/|&|AND)\s*VOY(?:AGE)?\s*[:#-]?\s*[A-Z0-9 .-]{2,80}[/ -]+([A-Z0-9./-]{2,24})", re.IGNORECASE),
        )
    if field_name == "gross_weight":
        return (
            re.compile(r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*([0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE)?)\s*/\s*[0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE)?", re.IGNORECASE),
            re.compile(r"(?:GROSS\s*(?:WEIGHT|WT|WGT)|G\.?\s*W\.?|GW)\s*[:#-]?\s*([0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE))", re.IGNORECASE),
        )
    if field_name == "net_weight":
        return (
            re.compile(r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*[0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE)?\s*/\s*([0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE)?)", re.IGNORECASE),
            re.compile(r"(?:NET\s*(?:WEIGHT|WT|WGT)|N\.?\s*W\.?|NW)\s*[:#-]?\s*([0-9OISBL.,]+\s*(?:KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE))", re.IGNORECASE),
        )
    if field_name == "issuer":
        tokens = "|".join(re.escape(token) for token in _field_tokens("issuer", document_type))
        return (re.compile(rf"(?:{tokens})\s*[:#-]?\s*([A-Z][A-Z0-9&.,/() -]{{2,90}})", re.IGNORECASE),)
    return ()


def _field_search_windows(lines: Sequence[str], field_name: str) -> List[str]:
    if not (_top3_field_boost_v1_enabled() and field_name in _TOP3_FIELD_NAMES):
        return [line for line in lines if line]

    windows: List[str] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        candidates = [line]
        if index + 1 < len(lines):
            candidates.append(f"{line} {lines[index + 1]}")
        if index > 0:
            candidates.append(f"{lines[index - 1]} {line}")
        if index > 0 and index + 1 < len(lines):
            candidates.append(f"{lines[index - 1]} {line} {lines[index + 1]}")
        for candidate in candidates:
            normalized = re.sub(r"\s+", " ", _normalize_text(candidate)).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                windows.append(normalized)
    return windows


def _find_weight_pair_match(field_name: str, raw_text: str) -> Tuple[Optional[str], Optional[str], bool]:
    if field_name not in {"gross_weight", "net_weight"}:
        return None, None, False

    pair_pattern = re.compile(
        r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*([0-9OISBL.,]+)\s*/\s*([0-9OISBL.,]+)\s*(KGS?|KG|KILOGRAMS?|LBS?|LB|MT|TON|TONNE)",
        re.IGNORECASE,
    )
    for window in _field_search_windows(_scan_lines(raw_text), field_name):
        match = pair_pattern.search(window)
        if not match:
            continue
        value = match.group(1) if field_name == "gross_weight" else match.group(2)
        return f"{value} {match.group(3)}", window, True
    return None, None, False


def _find_field_match(field_name: str, raw_text: str, document_type: str) -> Tuple[Optional[str], Optional[str], bool]:
    lines = _scan_lines(raw_text)
    label_present = _label_seen(raw_text, field_name, document_type)
    patterns = _patterns_for_field(field_name, document_type)
    for line in _field_search_windows(lines, field_name):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                value = match.group(match.lastindex or 1).strip()
                return value, line, True
    joined = " ".join(lines)
    for pattern in patterns:
        match = pattern.search(joined)
        if match:
            value = match.group(match.lastindex or 1).strip()
            return value, _snippet_from_text(joined, value), True
    return None, None, label_present


def _parse_amount_currency_fields(raw_text: str) -> Dict[str, _ParsedFieldCandidate]:
    missing_amount = _ParsedFieldCandidate("amount", None, None, "missing", 0.0, None, ["FIELD_NOT_FOUND"], "preparser")
    missing_currency = _ParsedFieldCandidate("currency", None, None, "missing", 0.0, None, ["FIELD_NOT_FOUND"], "preparser")
    if not raw_text:
        return {"amount": missing_amount, "currency": missing_currency}

    patterns = (
        re.compile(r":32B:\s*([A-Z]{3})\s*([0-9][0-9,\.]+)", re.IGNORECASE),
        re.compile(r"(?:CREDIT\s+AMOUNT|INVOICE\s+AMOUNT|TOTAL\s+AMOUNT|AMOUNT)\s*[:#-]?\s*([A-Z]{3})\s*([0-9][0-9,\.]+)", re.IGNORECASE),
        re.compile(r"(?:CREDIT\s+AMOUNT|INVOICE\s+AMOUNT|TOTAL\s+AMOUNT|AMOUNT)\s*[:#-]?\s*([0-9][0-9,\.]+)\s*([A-Z]{3})", re.IGNORECASE),
    )
    label_present = _label_seen(raw_text, "amount", "supporting_document")
    for line in _scan_lines(raw_text):
        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            groups = [group.strip() for group in match.groups() if group]
            if len(groups) != 2:
                continue
            if re.fullmatch(r"[A-Z]{3}", groups[0], re.IGNORECASE):
                currency_raw, amount_raw = groups[0], groups[1]
            else:
                amount_raw, currency_raw = groups[0], groups[1]
            amount_normalized, amount_error = _normalize_amount(amount_raw)
            currency_normalized, currency_error = _normalize_currency(currency_raw)
            amount_state = infer_field_state(amount_normalized, parse_error=amount_error is not None)
            currency_state = infer_field_state(currency_normalized, parse_error=currency_error is not None)
            return {
                "amount": _ParsedFieldCandidate(
                    "amount",
                    amount_raw,
                    amount_normalized,
                    amount_state,
                    _compute_candidate_confidence(source="preparser", state=amount_state, anchor_hit=True, evidence_snippet=line, normalized_value=amount_normalized),
                    line,
                    _field_reason_codes(amount_state, [amount_error]),
                    "preparser",
                    True,
                ),
                "currency": _ParsedFieldCandidate(
                    "currency",
                    currency_raw,
                    currency_normalized,
                    currency_state,
                    _compute_candidate_confidence(source="preparser", state=currency_state, anchor_hit=True, evidence_snippet=line, normalized_value=currency_normalized),
                    line,
                    _field_reason_codes(currency_state, [currency_error]),
                    "preparser",
                    True,
                ),
            }

    state = "parse_failed" if label_present else "missing"
    reason_codes = ["FORMAT_INVALID"] if label_present else ["FIELD_NOT_FOUND"]
    confidence = _compute_candidate_confidence(source="preparser", state=state, anchor_hit=label_present)
    return {
        "amount": _ParsedFieldCandidate("amount", None, None, state, confidence, None, reason_codes, "preparser", label_present),
        "currency": _ParsedFieldCandidate("currency", None, None, state, confidence, None, reason_codes, "preparser", label_present),
    }


def _parse_field_from_text(field_name: str, raw_text: str, document_type: str) -> _ParsedFieldCandidate:
    if field_name in {"amount", "currency"}:
        return _parse_amount_currency_fields(raw_text).get(field_name, _ParsedFieldCandidate(field_name, None, None, "missing", 0.0, None, ["FIELD_NOT_FOUND"], "preparser"))
    if _top3_field_boost_v1_enabled() and field_name in {"gross_weight", "net_weight"}:
        paired_value, paired_snippet, paired_anchor_hit = _find_weight_pair_match(field_name, raw_text)
        if paired_value is not None:
            normalized_value, error_code, _ = _normalize_field_value(field_name, paired_value)
            state = infer_field_state(normalized_value, parse_error=error_code is not None)
            return _ParsedFieldCandidate(
                field_name,
                paired_value,
                normalized_value,
                state,
                _compute_candidate_confidence(source="preparser", state=state, anchor_hit=paired_anchor_hit, evidence_snippet=paired_snippet, normalized_value=normalized_value),
                paired_snippet,
                _field_reason_codes(state, [error_code]),
                "preparser",
                paired_anchor_hit,
            )
    matched_value, snippet, anchor_hit = _find_field_match(field_name, raw_text, document_type)
    if matched_value is None:
        state = "parse_failed" if anchor_hit else "missing"
        return _ParsedFieldCandidate(
            field_name,
            None,
            None,
            state,
            _compute_candidate_confidence(source="preparser", state=state, anchor_hit=anchor_hit),
            snippet,
            _field_reason_codes(state, []),
            "preparser",
            anchor_hit,
        )
    normalized_value, error_code, _ = _normalize_field_value(field_name, matched_value)
    state = infer_field_state(normalized_value, parse_error=error_code is not None)
    return _ParsedFieldCandidate(
        field_name,
        matched_value,
        normalized_value,
        state,
        _compute_candidate_confidence(source="preparser", state=state, anchor_hit=anchor_hit, evidence_snippet=snippet, normalized_value=normalized_value),
        snippet,
        _field_reason_codes(state, [error_code]),
        "preparser",
        anchor_hit,
    )


def _preparse_document_fields(raw_text: str, document_type: str) -> Dict[str, _ParsedFieldCandidate]:
    if not _preparser_hardening_enabled():
        return {}
    parsed = {field_name: _parse_field_from_text(field_name, raw_text, document_type) for field_name in _PREPARSER_FIELDS}
    return dict(sorted(parsed.items(), key=lambda item: _FIELD_PRIORITY.get(item[0], 99)))


def _build_existing_candidate(
    *,
    document: Dict[str, Any],
    field_name: str,
    selected_value: Any,
    details: Dict[str, Any],
    detail_candidates: Iterable[Dict[str, Any]],
    raw_text: str,
    document_type: str,
) -> _ParsedFieldCandidate:
    evidence_refs = _build_evidence_refs(details, selected_value, raw_text)
    normalized_value = None
    normalize_error = None
    if selected_value not in (None, "", [], {}):
        normalized_value, normalize_error, _ = _normalize_field_value(field_name, selected_value)
    parse_error = _infer_parse_error(detail_candidates) or normalize_error is not None
    state = infer_field_state(normalized_value if normalize_error is None else None, parse_error=parse_error)
    if selected_value not in (None, "", [], {}) and normalize_error is None and normalized_value in (None, "", [], {}):
        state = "missing"
    explicit_confidence = _coerce_confidence(details.get("confidence"))
    evidence_snippet = evidence_refs[0].text_span if evidence_refs else _snippet_from_text(raw_text, selected_value)
    return _ParsedFieldCandidate(
        field_name,
        details.get("raw_value", selected_value),
        normalized_value if state == "found" else None,
        state,
        _compute_candidate_confidence(
            source="existing",
            state=state,
            explicit_confidence=explicit_confidence if explicit_confidence is not None else _field_confidence(document, details),
            anchor_hit=_label_seen(raw_text or evidence_snippet or "", field_name, document_type),
            evidence_snippet=evidence_snippet,
            normalized_value=normalized_value,
        ),
        evidence_snippet,
        _field_reason_codes(
            state,
            [
                details.get("reason_code"),
                details.get("reason"),
                details.get("status"),
                details.get("decision_status"),
                normalize_error,
            ],
        ),
        "existing",
        _label_seen(raw_text or evidence_snippet or "", field_name, document_type),
    )


def _merge_field_candidates(existing_candidate: _ParsedFieldCandidate, parsed_candidate: Optional[_ParsedFieldCandidate]) -> _ParsedFieldCandidate:
    if not parsed_candidate:
        return existing_candidate
    if (
        _top3_field_boost_v1_enabled()
        and existing_candidate.name in _TOP3_FIELD_NAMES
        and existing_candidate.state == "found"
        and parsed_candidate.state == "found"
    ):
        existing_has_evidence = bool(existing_candidate.evidence_snippet)
        parsed_has_evidence = bool(parsed_candidate.evidence_snippet)
        if parsed_has_evidence and (
            not existing_has_evidence
            or parsed_candidate.confidence > existing_candidate.confidence
        ):
            return parsed_candidate
    if existing_candidate.state == "found":
        return existing_candidate
    if parsed_candidate.state == "found":
        return parsed_candidate
    if existing_candidate.state == "parse_failed":
        return existing_candidate
    return parsed_candidate


def _field_numeric_value(field: Optional[FieldExtraction]) -> Optional[float]:
    if not isinstance(field, FieldExtraction) or field.state != "found":
        return None
    value = _normalize_text(field.value_normalized)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _evaluate_cross_field_reasons(
    *,
    fields: Sequence[FieldExtraction],
    auxiliary_fields: Dict[str, _ParsedFieldCandidate],
    cross_checks: Iterable[str],
) -> List[str]:
    checks = [str(check or "").strip().lower() for check in (cross_checks or []) if str(check or "").strip()]
    if not checks:
        return []

    by_name = {field.name: field for field in fields}
    reasons: List[str] = []

    if "weight_consistency" in checks:
        gross_value = _field_numeric_value(by_name.get("gross_weight"))
        net_value = _field_numeric_value(by_name.get("net_weight"))
        if gross_value is not None and net_value is not None and net_value > gross_value:
            reasons.extend(["cross_field_weight_conflict", "CROSS_FIELD_CONFLICT"])

    if "amount_currency_pair" in checks:
        amount = auxiliary_fields.get("amount")
        currency = auxiliary_fields.get("currency")
        amount_found = bool(amount and amount.state == "found" and amount.value_normalized not in (None, ""))
        currency_found = bool(currency and currency.state == "found" and currency.value_normalized not in (None, ""))
        if amount_found != currency_found:
            reasons.extend(["cross_field_amount_currency_conflict", "CROSS_FIELD_CONFLICT"])

    return sorted(dict.fromkeys(reasons))


def _collect_document_reason_codes(document: Dict[str, Any], extraction_artifacts: Dict[str, Any]) -> List[str]:
    if not _failure_taxonomy_v2_enabled():
        return []

    raw_codes: List[Any] = []
    raw_codes.extend(extraction_artifacts.get("reason_codes") or [])
    raw_codes.append(extraction_artifacts.get("error_code"))
    stage_errors = extraction_artifacts.get("stage_errors")
    if isinstance(stage_errors, dict):
        raw_codes.extend(stage_errors.values())
    provider_attempts = extraction_artifacts.get("provider_attempts")
    if isinstance(provider_attempts, list):
        for attempt in provider_attempts:
            if isinstance(attempt, dict):
                raw_codes.append(attempt.get("error"))

    canonical = _canonicalize_reason_codes(raw_codes)
    status = _normalize_text(document.get("extraction_status") or document.get("extractionStatus")).lower()
    raw_text = _normalize_text(extraction_artifacts.get("raw_text") or document.get("raw_text"))
    final_text_length = extraction_artifacts.get("final_text_length")
    no_text = not raw_text and (final_text_length in (None, 0))
    if status == "success" and not no_text:
        return []
    return canonical


def _apply_artifact_metadata(
    *,
    document: Dict[str, Any],
    fields: Sequence[FieldExtraction],
    preparsed_candidates: Dict[str, _ParsedFieldCandidate],
    review_reasons: Sequence[str],
) -> None:
    extraction_artifacts = document.get("extraction_artifacts_v1") if isinstance(document.get("extraction_artifacts_v1"), dict) else {}
    if extraction_artifacts is not document.get("extraction_artifacts_v1"):
        document["extraction_artifacts_v1"] = extraction_artifacts

    field_diagnostics: Dict[str, Dict[str, Any]] = {}
    for field_name, candidate in preparsed_candidates.items():
        field_diagnostics[field_name] = {
            "state": candidate.state,
            "value_normalized": candidate.value_normalized,
            "confidence": candidate.confidence,
            "reason_codes": candidate.reason_codes,
            "source": candidate.source,
            "evidence_snippet": candidate.evidence_snippet,
        }
    for field in fields:
        field_diagnostics[field.name] = {
            "state": field.state,
            "value_normalized": field.value_normalized,
            "confidence": field.confidence,
            "reason_codes": field.reason_codes,
            "source": "document_extraction",
            "evidence_snippet": field.evidence[0].text_span if field.evidence else None,
        }

    canonical_codes = _canonicalize_reason_codes(
        list(extraction_artifacts.get("reason_codes") or [])
        + [extraction_artifacts.get("error_code")]
        + [code for field in fields for code in field.reason_codes]
        + list(review_reasons or [])
    )
    extraction_artifacts["reason_codes"] = sorted(dict.fromkeys(list(extraction_artifacts.get("reason_codes") or []) + canonical_codes))
    extraction_artifacts["canonical_reason_codes"] = canonical_codes
    extraction_artifacts["field_diagnostics"] = field_diagnostics
    extraction_artifacts["review_reasons"] = list(review_reasons or [])


def _gate_profile_settings(profile: Dict[str, Any]) -> Tuple[float, bool, List[str]]:
    if _pass_gate_v2_enabled() and isinstance(profile.get("pass_gate"), dict):
        gate_config = profile.get("pass_gate") or {}
    else:
        gate_config = profile.get("review_gate") if isinstance(profile.get("review_gate"), dict) else {}
    min_confidence = float(gate_config.get("min_confidence", 0.80) or 0.80)
    require_evidence = bool(gate_config.get("require_evidence", True))
    cross_checks = [str(check) for check in (gate_config.get("cross_checks") or []) if str(check or "").strip()]
    return min_confidence, require_evidence, cross_checks


def build_document_extraction(document: Dict[str, Any]) -> DocumentExtraction:
    doc_type = str(document.get("document_type") or document.get("documentType") or "supporting_document")
    extracted_fields = (
        document.get("extracted_fields")
        if isinstance(document.get("extracted_fields"), dict)
        else document.get("extractedFields")
        if isinstance(document.get("extractedFields"), dict)
        else {}
    )
    field_details = (
        document.get("field_details")
        if isinstance(document.get("field_details"), dict)
        else document.get("_field_details")
        if isinstance(document.get("_field_details"), dict)
        else {}
    )
    extraction_artifacts = document.get("extraction_artifacts_v1") if isinstance(document.get("extraction_artifacts_v1"), dict) else {}
    raw_text = _normalize_text(extraction_artifacts.get("raw_text") or document.get("raw_text") or document.get("raw_text_preview"))

    profile = load_profile(doc_type)
    critical_fields = profile.get("critical_fields") or []
    min_confidence, require_evidence, cross_checks = _gate_profile_settings(profile)
    preparsed_candidates = _preparse_document_fields(raw_text, doc_type) if extraction_artifacts else {}

    fields: List[FieldExtraction] = []
    for field_name in critical_fields:
        _, value, details, detail_candidates = _extract_value_and_details(
            document,
            extracted_fields if isinstance(extracted_fields, dict) else {},
            field_details if isinstance(field_details, dict) else {},
            str(field_name),
            doc_type,
        )
        existing_candidate = _build_existing_candidate(
            document=document,
            field_name=str(field_name),
            selected_value=value,
            details=details,
            detail_candidates=detail_candidates,
            raw_text=raw_text,
            document_type=doc_type,
        )
        selected_candidate = _merge_field_candidates(existing_candidate, preparsed_candidates.get(str(field_name)))
        evidence = _build_evidence_refs(details, value, raw_text)
        if not evidence and selected_candidate.source == "preparser":
            evidence = _build_parser_evidence(selected_candidate.evidence_snippet, selected_candidate.confidence)
        fields.append(
            FieldExtraction(
                name=str(field_name),
                value_raw=selected_candidate.value_raw,
                value_normalized=selected_candidate.value_normalized,
                state=selected_candidate.state,  # type: ignore[arg-type]
                confidence=selected_candidate.confidence,
                evidence=evidence,
                reason_codes=selected_candidate.reason_codes,
            )
        )

    cross_field_reasons = _evaluate_cross_field_reasons(fields=fields, auxiliary_fields=preparsed_candidates, cross_checks=cross_checks)
    document_reason_codes = _collect_document_reason_codes(document, extraction_artifacts)
    decision = evaluate_review_gate(
        fields,
        critical_fields,
        min_confidence=min_confidence,
        require_evidence=require_evidence,
        document_reason_codes=document_reason_codes,
        cross_field_reasons=cross_field_reasons,
    )
    _apply_artifact_metadata(document=document, fields=fields, preparsed_candidates=preparsed_candidates, review_reasons=decision.reasons)

    return DocumentExtraction(
        doc_id=str(document.get("id") or document.get("document_id") or ""),
        doc_type_predicted=doc_type,
        doc_type_confidence=_coerce_confidence(document.get("doc_type_confidence")) or 0.0,
        fields=fields,
        review_required=decision.review_required,
        review_reasons=decision.reasons,
        profile_version=str(profile.get("version") or "profiles-v1"),
    )


def build_extraction_core_bundle(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not extraction_core_v1_enabled():
        return None

    document_extractions = [build_document_extraction(document) for document in (documents or []) if isinstance(document, dict)]
    bundle = ExtractionBundle(
        documents=document_extractions,
        meta={
            "feature_flag": EXTRACTION_CORE_V1_ENV,
            "documents_evaluated": len(document_extractions),
            "review_required_count": sum(1 for doc in document_extractions if doc.review_required),
        },
    )
    bundle_dict = asdict(bundle)
    bundle_dict["version"] = "extraction_core_v1"
    bundle_dict["enabled"] = True
    return bundle_dict


def annotate_documents_with_review_metadata(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    bundle = build_extraction_core_bundle(documents)
    if not bundle:
        return None

    bundle_documents = bundle.get("documents") if isinstance(bundle.get("documents"), list) else []
    for document, extraction_doc in zip(documents or [], bundle_documents):
        if not isinstance(document, dict) or not isinstance(extraction_doc, dict):
            continue
        critical_field_states = {
            field.get("name"): field.get("state")
            for field in extraction_doc.get("fields", [])
            if isinstance(field, dict) and field.get("name")
        }
        review_required = bool(extraction_doc.get("review_required", False))
        review_reasons = extraction_doc.get("review_reasons") or []

        document["review_required"] = review_required
        document["reviewRequired"] = review_required
        document["review_reasons"] = review_reasons
        document["reviewReasons"] = review_reasons
        document["critical_field_states"] = critical_field_states
        document["criticalFieldStates"] = critical_field_states

    return bundle
