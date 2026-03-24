from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .contract import (
    DocumentExtraction,
    EvidenceRef,
    ExtractionBundle,
    ExtractionResolution,
    ExtractionResolutionField,
    FieldExtraction,
)
from .field_states import infer_field_state
from .gate import evaluate_review_gate
from .profiles import load_profile

EXTRACTION_CORE_V1_ENV = "LCCOPILOT_EXTRACTION_CORE_V1_ENABLED"
PREPARSER_HARDENING_ENV = "LCCOPILOT_PREPARSER_HARDENING_ENABLED"
FAILURE_TAXONOMY_V2_ENV = "LCCOPILOT_FAILURE_TAXONOMY_V2_ENABLED"
PASS_GATE_V2_ENV = "LCCOPILOT_PASS_GATE_V2_ENABLED"
TOP3_FIELD_BOOST_V1_ENV = "LCCOPILOT_TOP3_FIELD_BOOST_V1_ENABLED"
TOP3_FIELD_LIFT_V2_ENV = "LCCOPILOT_TOP3_FIELD_LIFT_V2_ENABLED"
PLAINTEXT_PARSER_LIFT_V1_ENV = "LCCOPILOT_PLAINTEXT_PARSER_LIFT_V1_ENABLED"
PLAINTEXT_CONFIDENCE_V1_ENV = "LCCOPILOT_PLAINTEXT_CONFIDENCE_V1_ENABLED"

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
_EXTRACTION_RESOLUTION_REASON_CODES = frozenset(
    {
        "FIELD_NOT_FOUND",
        "FORMAT_INVALID",
        "EVIDENCE_MISSING",
        "LOW_CONFIDENCE_CRITICAL",
        "CROSS_FIELD_CONFLICT",
        "OCR_EMPTY_RESULT",
        "OCR_TIMEOUT",
        "OCR_AUTH_ERROR",
        "OCR_UNSUPPORTED_FORMAT",
    }
)


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


def _humanize_field_label(field_name: str) -> str:
    return str(field_name or "").replace("_", " ").strip().title()


def _is_extraction_resolution_reason(reason: Any) -> bool:
    text = str(reason or "").strip()
    if not text:
        return False
    upper = text.upper()
    lower = text.lower()
    if upper in _EXTRACTION_RESOLUTION_REASON_CODES:
        return True
    if lower.startswith("missing:"):
        return True
    if lower.endswith("_missing_critical_fields"):
        return True
    if lower.startswith("critical_") and lower.endswith("_missing"):
        return True
    if lower.startswith("cross_field_"):
        return True
    return False


def _build_extraction_resolution_from_fields(
    *,
    fields: Sequence[FieldExtraction],
    field_details: Dict[str, Dict[str, Any]],
) -> Optional[ExtractionResolution]:
    unresolved: List[ExtractionResolutionField] = []
    for field in fields:
        detail = field_details.get(field.name) if isinstance(field_details.get(field.name), dict) else {}
        verification = str(detail.get("verification") or "").strip().lower() or None
        resolved = field.state == "found" and verification in {None, "", "confirmed", "text_supported", "operator_confirmed"}
        if resolved:
            continue
        reason_code = next(
            (
                str(code)
                for code in (field.reason_codes or [])
                if _is_extraction_resolution_reason(code)
            ),
            None,
        )
        unresolved.append(
            ExtractionResolutionField(
                field_name=field.name,
                label=_humanize_field_label(field.name),
                verification=verification or ("not_found" if field.state != "found" else "model_suggested"),
                reason_code=reason_code,
            )
        )

    if not unresolved:
        return None

    unresolved_count = len(unresolved)
    return ExtractionResolution(
        required=True,
        unresolved_count=unresolved_count,
        summary=(
            f"{unresolved_count} extracted field"
            f"{'' if unresolved_count == 1 else 's'} still need confirmation before validation can be treated as final."
        ),
        fields=unresolved,
    )


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


def _top3_field_lift_v2_enabled() -> bool:
    return _env_enabled(TOP3_FIELD_LIFT_V2_ENV)


def _plaintext_parser_lift_v1_enabled() -> bool:
    return _env_enabled(PLAINTEXT_PARSER_LIFT_V1_ENV)


def _plaintext_confidence_v1_enabled() -> bool:
    return _env_enabled(PLAINTEXT_CONFIDENCE_V1_ENV)


def _top3_lift_active() -> bool:
    return _top3_field_boost_v1_enabled() and _top3_field_lift_v2_enabled()


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
    "issue_date": ("issue date", "date of issue", "invoice date", "bl date", "packing list date", "issued on", "dated", ":31c:"),
    "amount": (":32b:", "credit amount", "invoice amount", "total amount", "amount"),
    "currency": (":32b:", "currency", "ccy", "credit amount", "invoice amount", "amount"),
    "bin_tin": (
        "bin",
        "tin",
        "bin/tin",
        "tin/bin",
        "tax id",
        "tax identification",
        "taxpayer identification",
        "taxpayer id",
        "vat reg",
        "vat registration",
        "vat registration no",
        "vat no",
        "business identification",
        "business id",
        "etin",
        "e-tin",
        "seller bin",
        "seller tin",
        "exporter bin",
        "exporter tin",
    ),
    "voyage": ("voyage", "voy no", "voy.", "vvd", "vessel/voy", "vessel/voyage", "vessel voyage"),
    "gross_weight": ("gross/net", "gross weight", "gross wt", "gross wgt", "g.w.", "gw", "gross mass"),
    "net_weight": ("gross/net", "net weight", "net wt", "net wgt", "n.w.", "nw", "net mass"),
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
    "MTS": 1000.0,
    "TON": 1000.0,
    "TONS": 1000.0,
    "TONNE": 1000.0,
    "TONNES": 1000.0,
    "LBS": 0.45359237,
    "LB": 0.45359237,
    "POUND": 0.45359237,
    "POUNDS": 0.45359237,
}
_WEIGHT_UNIT_PATTERN = r"(?:KGS?|KG|KILOGRAMS?|KILOGRAM|LBS?|LB|POUNDS?|POUND|MT|MTS|TONS?|TONNES?)"


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


def _profile_field_hints(document_type: str, field_name: str) -> Dict[str, Any]:
    profile = load_profile(document_type or "supporting_document")
    field_hints = profile.get("field_hints") if isinstance(profile.get("field_hints"), dict) else {}
    hints = field_hints.get(field_name)
    return hints if isinstance(hints, dict) else {}


def _hint_ints(values: Any, default: Sequence[int]) -> List[int]:
    parsed: List[int] = []
    for value in values or []:
        try:
            parsed.append(int(value))
        except (TypeError, ValueError):
            continue
    return parsed or list(default)


def _hint_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _selected_extraction_stage(document: Dict[str, Any], extraction_artifacts: Dict[str, Any]) -> str:
    return _normalize_text(
        extraction_artifacts.get("selected_stage")
        or extraction_artifacts.get("final_stage")
        or document.get("selected_stage")
        or document.get("final_stage")
    ).lower()


def _plaintext_stage_active(extraction_stage: Optional[str]) -> bool:
    return _plaintext_parser_lift_v1_enabled() and _normalize_text(extraction_stage).lower() == "plaintext_native"


def _plaintext_confidence_config(document_type: str, field_name: str) -> Dict[str, float]:
    profile = load_profile(document_type or "supporting_document")
    base_config = profile.get("plaintext_confidence") if isinstance(profile.get("plaintext_confidence"), dict) else {}
    field_hints = _profile_field_hints(document_type or "supporting_document", field_name)
    field_config = field_hints.get("plaintext_confidence") if isinstance(field_hints.get("plaintext_confidence"), dict) else {}
    merged = {
        "found_base": 0.28,
        "anchor_weight": 0.22,
        "pattern_weight": 0.16,
        "normalization_weight": 0.14,
        "context_weight": 0.10,
        "evidence_weight": 0.12,
        "parse_failed_base": 0.24,
        "anchor_parse_bonus": 0.08,
        "evidence_missing_penalty": 0.18,
    }
    for key, default in tuple(merged.items()):
        merged[key] = _hint_float(field_config.get(key, base_config.get(key)), default)
    return merged


def _parse_numeric_value(token: str) -> Optional[float]:
    normalized = _normalize_numeric_token(token)
    if not normalized:
        return None
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(",", "")
    elif "," in normalized:
        parts = normalized.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            normalized = f"{parts[0]}.{parts[1]}"
        else:
            normalized = "".join(parts)
    try:
        return float(normalized)
    except ValueError:
        return None


def _split_table_columns(line: str) -> List[str]:
    text = _normalize_text(line)
    if not text:
        return []
    if "|" in text:
        parts = text.split("|")
    elif "\t" in text:
        parts = text.split("\t")
    else:
        parts = re.split(r"\s{2,}", text)
    return [part.strip() for part in parts if part and part.strip()]


def _weight_numeric_from_normalized(value: Any) -> Optional[float]:
    text = _normalize_text(value)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _weight_is_sane(normalized_value: Any, document_type: str, field_name: str) -> bool:
    numeric = _weight_numeric_from_normalized(normalized_value)
    if numeric is None:
        return False
    hints = _profile_field_hints(document_type, field_name)
    min_kg = _hint_float(hints.get("min_kg"), 0.01)
    max_kg = _hint_float(hints.get("max_kg"), 500000.0)
    return min_kg <= numeric <= max_kg


def _plaintext_pattern_validity(
    field_name: str,
    raw_value: Any,
    normalized_value: Any,
    document_type: str,
) -> float:
    raw_text = _normalize_text(raw_value)
    normalized_text = _normalize_text(normalized_value)
    if field_name == "bin_tin":
        digits = re.sub(r"\D", "", normalized_text or _normalize_numeric_context(raw_text))
        hints = _profile_field_hints(document_type, field_name)
        preferred_lengths = _hint_ints(hints.get("preferred_lengths"), (13,))
        allowed_lengths = _hint_ints(hints.get("allowed_lengths"), (10, 11, 12, 13))
        if len(digits) in preferred_lengths:
            return 1.0
        if len(digits) in allowed_lengths:
            return 0.82
        return 0.0
    if field_name in {"gross_weight", "net_weight"}:
        if re.search(rf"[0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?\s*{_WEIGHT_UNIT_PATTERN}", raw_text, re.IGNORECASE):
            return 1.0
        if normalized_text.endswith(" KG"):
            return 0.85
        return 0.0
    if field_name == "issue_date":
        return 1.0 if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized_text) else 0.0
    if field_name == "voyage":
        return 1.0 if re.fullmatch(r"[A-Z0-9.-]{2,24}", normalized_text) and re.search(r"[A-Z]", normalized_text) and re.search(r"\d", normalized_text) else 0.0
    return 1.0 if normalized_text else 0.0


def _plaintext_normalization_validity(field_name: str, normalized_value: Any, document_type: str) -> float:
    normalized_text = _normalize_text(normalized_value)
    if not normalized_text:
        return 0.0
    if field_name == "bin_tin":
        digits = re.sub(r"\D", "", normalized_text)
        hints = _profile_field_hints(document_type, field_name)
        preferred_lengths = _hint_ints(hints.get("preferred_lengths"), (13,))
        allowed_lengths = _hint_ints(hints.get("allowed_lengths"), (10, 11, 12, 13))
        if len(digits) in preferred_lengths:
            return 1.0
        return 0.8 if len(digits) in allowed_lengths else 0.0
    if field_name in {"gross_weight", "net_weight"}:
        return 1.0 if normalized_text.endswith(" KG") and _weight_is_sane(normalized_text, document_type, field_name) else 0.0
    if field_name == "issue_date":
        return 1.0 if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized_text) else 0.0
    if field_name == "voyage":
        return 1.0 if re.fullmatch(r"[A-Z0-9.-]{2,24}", normalized_text) else 0.0
    return 1.0


def _plaintext_context_coherence(
    field_name: str,
    evidence_snippet: Optional[str],
    raw_value: Any,
    document_type: str,
) -> float:
    snippet = _normalize_text(evidence_snippet or raw_value).lower()
    if not snippet:
        return 0.0
    token_hit = any(token in snippet for token in _field_tokens(field_name, document_type))
    if field_name in {"gross_weight", "net_weight"}:
        target = "gross" if field_name == "gross_weight" else "net"
        other = "net" if field_name == "gross_weight" else "gross"
        if target in snippet and other not in snippet:
            return 1.0
        if target in snippet and other in snippet:
            return 0.78
        return 0.45 if token_hit else 0.0
    if field_name == "issue_date":
        return 1.0 if token_hit and re.search(r"\d", snippet) else 0.45 if token_hit else 0.0
    if field_name == "voyage":
        return 1.0 if token_hit and re.search(r"\d", snippet) else 0.4 if token_hit else 0.0
    return 1.0 if token_hit else 0.35


def _plaintext_candidate_confidence(
    *,
    field_name: str,
    document_type: str,
    state: str,
    anchor_hit: bool,
    evidence_snippet: Optional[str],
    raw_value: Any,
    normalized_value: Any,
) -> float:
    config = _plaintext_confidence_config(document_type, field_name)
    if state == "missing":
        return 0.0
    if state == "parse_failed":
        score = config["parse_failed_base"] + (config["anchor_parse_bonus"] if anchor_hit else 0.0)
        return _clamp_confidence(score)

    anchor_strength = 1.0 if anchor_hit else (0.6 if _label_seen(evidence_snippet or raw_value or "", field_name, document_type) else 0.0)
    pattern_validity = _plaintext_pattern_validity(field_name, raw_value, normalized_value, document_type)
    normalization_validity = _plaintext_normalization_validity(field_name, normalized_value, document_type)
    context_coherence = _plaintext_context_coherence(field_name, evidence_snippet, raw_value, document_type)
    evidence_score = 1.0 if _normalize_text(evidence_snippet) else 0.0
    score = (
        config["found_base"]
        + (config["anchor_weight"] * anchor_strength)
        + (config["pattern_weight"] * pattern_validity)
        + (config["normalization_weight"] * normalization_validity)
        + (config["context_weight"] * context_coherence)
        + (config["evidence_weight"] * evidence_score)
    )
    return _clamp_confidence(score)


def _candidate_confidence_for_field(
    *,
    field_name: str,
    document_type: str,
    source: str,
    state: str,
    explicit_confidence: Optional[float] = None,
    anchor_hit: bool = False,
    evidence_snippet: Optional[str] = None,
    normalized_value: Optional[Any] = None,
    raw_value: Optional[Any] = None,
    extraction_stage: Optional[str] = None,
) -> float:
    if (
        _plaintext_confidence_v1_enabled()
        and _plaintext_stage_active(extraction_stage)
        and source == "preparser"
        and explicit_confidence is None
    ):
        return _plaintext_candidate_confidence(
            field_name=field_name,
            document_type=document_type,
            state=state,
            anchor_hit=anchor_hit,
            evidence_snippet=evidence_snippet,
            raw_value=raw_value,
            normalized_value=normalized_value,
        )

    score = _compute_candidate_confidence(
        source=source,
        state=state,
        explicit_confidence=explicit_confidence,
        anchor_hit=anchor_hit,
        evidence_snippet=evidence_snippet,
        normalized_value=normalized_value,
    )
    if explicit_confidence is not None or not (_top3_lift_active() and field_name in _TOP3_FIELD_NAMES):
        return score
    if state != "found" or normalized_value in (None, "", [], {}):
        return score

    if anchor_hit:
        score += 0.03
    if evidence_snippet and _label_seen(evidence_snippet, field_name, document_type):
        score += 0.04

    if field_name == "bin_tin":
        hints = _profile_field_hints(document_type, field_name)
        preferred_lengths = _hint_ints(hints.get("preferred_lengths"), (13,))
        allowed_lengths = _hint_ints(hints.get("allowed_lengths"), (10, 11, 12, 13))
        digits = re.sub(r"\D", "", _normalize_text(normalized_value))
        if len(digits) in preferred_lengths:
            score += 0.06
        elif len(digits) in allowed_lengths:
            score += 0.02
        else:
            score -= 0.16
    elif field_name in {"gross_weight", "net_weight"}:
        numeric = _weight_numeric_from_normalized(normalized_value)
        if numeric is not None:
            score += 0.04
        if _normalize_text(normalized_value).upper().endswith(" KG"):
            score += 0.04
        if _weight_is_sane(normalized_value, document_type, field_name):
            score += 0.04
        else:
            score -= 0.16

    return _clamp_confidence(score)


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
    text = re.sub(r"^(?:DATE(?:\s+OF)?\s+ISSUE|ISSUE\s+DATE|INVOICE\s+DATE|BL\s+DATE|PACKING\s+LIST\s+DATE|DOC(?:UMENT)?\s+DATE|ISSUED\s+ON|DATED|:31C:)\s*[:#-]*\s*", "", text, flags=re.IGNORECASE)
    compact = re.sub(r"(?<=\d)[,](?=\s*[A-Za-z])", " ", text.strip())
    compact = re.sub(r"(\d)-([A-Za-z]{3,9})", r"\1 \2", compact)
    compact = re.sub(r"([A-Za-z]{3,9})-(\d{4})", r"\1 \2", compact)
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


def _normalize_bin_tin(raw_value: Any, document_type: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    text = _normalize_numeric_context(raw_value)
    if not text:
        return None, "FIELD_NOT_FOUND"
    text = re.sub(
        r"\b(?:EXPORTER|SELLER|SHIPPER|BUSINESS\s*IDENTIFICATION|BUSINESS\s*ID|VAT\s*REG(?:ISTRATION)?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|BIN|TIN|TAX\s*PAYER\s*IDENTIFICATION|TAX\s*ID|TAX\s*IDENTIFICATION|E-?TIN|ETIN)\b",
        " ",
        text,
    )
    hints = _profile_field_hints(document_type or "supporting_document", "bin_tin")
    preferred_lengths = _hint_ints(hints.get("preferred_lengths"), (13,))
    allowed_lengths = _hint_ints(hints.get("allowed_lengths"), (10, 11, 12, 13))

    candidates: List[str] = []
    for token in re.findall(r"[A-Z0-9-]{4,}", text):
        digits = re.sub(r"\D", "", token)
        if digits:
            candidates.append(digits)
    flattened = re.sub(r"\D", "", text)
    if flattened:
        candidates.append(flattened)

    ordered_candidates: List[str] = []
    for digits in sorted(candidates, key=lambda item: (-len(item), candidates.index(item))):
        if digits not in ordered_candidates:
            ordered_candidates.append(digits)

    for length in preferred_lengths:
        for digits in ordered_candidates:
            if len(digits) == length:
                return digits, None
    for digits in ordered_candidates:
        if len(digits) in allowed_lengths:
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


def _normalize_weight(
    raw_value: Any,
    field_name: Optional[str] = None,
    document_type: Optional[str] = None,
) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    text = _base_clean(raw_value).upper()
    if not text:
        return None, None, "FIELD_NOT_FOUND"
    text = re.sub(r"\bK[69]S?\b", lambda match: _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(0), match.group(0)), text)
    text = re.sub(r"\bL8S?\b", lambda match: _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(0), match.group(0)), text)
    text = re.sub(r"\bM7S?\b", "MTS", text)
    match = re.search(rf"([0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?)\s*({_WEIGHT_UNIT_PATTERN})", text)
    if not match:
        return None, None, "FORMAT_INVALID"
    number_text = match.group(1)
    unit = re.sub(r"[^A-Z]", "", _WEIGHT_UNIT_OCR_FIXUPS.get(match.group(2).upper(), match.group(2).upper()))
    factor = _WEIGHT_UNIT_ALIASES.get(unit)
    if factor is None:
        return None, None, "FORMAT_INVALID"
    value = _parse_numeric_value(number_text)
    if value is None:
        return None, None, "FORMAT_INVALID"
    kg_value = round(value * factor, 3)
    if abs(kg_value - round(kg_value)) <= 0.01:
        kg_value = float(round(kg_value))
    if field_name and document_type and not _weight_is_sane(f"{_format_decimal(kg_value)} KG", document_type, field_name):
        return None, None, "FORMAT_INVALID"
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


def _normalize_field_value(
    field_name: str,
    raw_value: Any,
    document_type: str = "supporting_document",
) -> Tuple[Optional[Any], Optional[str], Optional[float]]:
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
        normalized, error = _normalize_bin_tin(raw_value, document_type)
        return normalized, error, None
    if field_name == "voyage":
        normalized, error = _normalize_voyage(raw_value)
        return normalized, error, None
    if field_name in {"gross_weight", "net_weight"}:
        normalized, numeric_kg, error = _normalize_weight(raw_value, field_name, document_type)
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
            re.compile(r"(?:ISSUED\s+ON|DATED)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 ./-]{5,24})", re.IGNORECASE),
        )
    if field_name == "bin_tin":
        return (
            re.compile(r"(?:EXPORTER|SELLER|SHIPPER)\s*(?:BIN|TIN|BIN\s*/\s*TIN|TIN\s*/\s*BIN)\s*(?:(?:NO\.?|NUMBER)\s*)?[:#-]?\s*([A-Z0-9OISBL -]{8,32})", re.IGNORECASE),
            re.compile(r"(?:BIN(?:\s*/\s*TIN)?|VAT\s*REG(?:ISTRATION)?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|BUSINESS\s*IDENTIFICATION(?:\s*NO\.?)?)\s*(?:(?:NO\.?|NUMBER)\s*)?[:#-]?\s*([A-Z0-9OISBL -]{8,32})", re.IGNORECASE),
            re.compile(r"(?:TIN(?:\s*/\s*BIN)?|TAX\s*ID|TAX\s*IDENTIFICATION|TAXPAYER\s*ID(?:ENTIFICATION)?|E-?TIN|ETIN)\s*(?:(?:NO\.?|NUMBER)\s*)?[:#-]?\s*([A-Z0-9OISBL -]{8,32})", re.IGNORECASE),
        )
    if field_name == "voyage":
        return (
            re.compile(r"(?:VSL|VESSEL)\s*(?:/|&|AND)\s*VOY(?:AGE)?\s*[:#-]?\s*[A-Z0-9 .-]{2,80}[/ -]+([A-Z0-9./-]{2,24})", re.IGNORECASE),
            re.compile(r"(?:VESSEL\s*/\s*VOYAGE|VESSEL\s+VOYAGE)\s*[:#-]?\s*[A-Z0-9 .-]{2,80}[/ -]+([A-Z0-9./-]{2,24})", re.IGNORECASE),
            re.compile(r"(?:VOYAGE(?:\s*NO\.?|\s*NUMBER|\s*#)?|VOY\.?|VVD(?:\s*(?:NO\.?|NUMBER|#))?)\s*[:#-]?\s*([A-Z0-9./-]{2,24})", re.IGNORECASE),
        )
    if field_name == "gross_weight":
        return (
            re.compile(rf"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*([0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN}?)\s*/\s*[0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN}?", re.IGNORECASE),
            re.compile(rf"(?:GROSS\s*(?:WEIGHT|WT|WGT)|TOTAL\s+GROSS\s+WEIGHT|G\.?\s*W\.?|GW)\s*[:#-]?\s*([0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN})", re.IGNORECASE),
        )
    if field_name == "net_weight":
        return (
            re.compile(rf"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*[0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN}?\s*/\s*([0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN}?)", re.IGNORECASE),
            re.compile(rf"(?:NET\s*(?:WEIGHT|WT|WGT)|TOTAL\s+NET\s+WEIGHT|N\.?\s*W\.?|NW)\s*[:#-]?\s*([0-9OISBL.,]+\s*{_WEIGHT_UNIT_PATTERN})", re.IGNORECASE),
        )
    if field_name == "issuer":
        tokens = "|".join(re.escape(token) for token in _field_tokens("issuer", document_type))
        return (re.compile(rf"(?:{tokens})\s*[:#-]?\s*([A-Z][A-Z0-9&.,/() -]{{2,90}})", re.IGNORECASE),)
    return ()


def _field_search_windows(lines: Sequence[str], field_name: str, document_type: str = "supporting_document") -> List[str]:
    targeted_plaintext_fields = {"bin_tin", "gross_weight", "net_weight", "voyage", "issue_date"}
    use_expanded_windows = (
        (_top3_field_boost_v1_enabled() and field_name in _TOP3_FIELD_NAMES)
        or (_plaintext_parser_lift_v1_enabled() and field_name in targeted_plaintext_fields)
    )
    if not use_expanded_windows:
        return [line for line in lines if line]

    hints = _profile_field_hints(document_type, field_name)
    default_radius = 2 if field_name in {"bin_tin", "gross_weight", "net_weight"} else 1
    try:
        radius = max(1, int(hints.get("neighbor_window_lines", default_radius) or default_radius))
    except (TypeError, ValueError):
        radius = default_radius

    windows: List[str] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        candidates = [line]
        start_index = max(0, index - radius)
        end_index = min(len(lines), index + radius + 1)
        for left in range(index, start_index - 1, -1):
            for right in range(index + 1, end_index + 1):
                candidates.append(" ".join(lines[left:right]))
        for candidate in candidates:
            normalized = re.sub(r"\s+", " ", _normalize_text(candidate)).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                windows.append(normalized)
    return windows


def _find_weight_pair_match(field_name: str, raw_text: str, document_type: str) -> Tuple[Optional[str], Optional[str], bool]:
    if field_name not in {"gross_weight", "net_weight"}:
        return None, None, False

    pair_pattern = re.compile(
        rf"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:#-]?\s*([0-9OISBL.,]+)\s*/\s*([0-9OISBL.,]+)\s*({_WEIGHT_UNIT_PATTERN})",
        re.IGNORECASE,
    )
    for window in _field_search_windows(_scan_lines(raw_text), field_name, document_type):
        match = pair_pattern.search(window)
        if not match:
            continue
        value = match.group(1) if field_name == "gross_weight" else match.group(2)
        return f"{value} {match.group(3)}", window, True
    return None, None, False


def _find_weight_table_value(field_name: str, raw_text: str, document_type: str) -> Tuple[Optional[str], Optional[str], bool]:
    if field_name not in {"gross_weight", "net_weight"} or not _top3_lift_active():
        return None, None, False

    lines = _scan_lines(raw_text)
    target_token = "gross" if field_name == "gross_weight" else "net"
    other_token = "net" if field_name == "gross_weight" else "gross"
    value_pattern = re.compile(
        rf"[0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?\s*{_WEIGHT_UNIT_PATTERN}",
        re.IGNORECASE,
    )

    for index, header_line in enumerate(lines[:-1]):
        header_lower = header_line.lower()
        if target_token not in header_lower or other_token not in header_lower:
            continue
        data_line = lines[index + 1]

        header_columns = _split_table_columns(header_line)
        data_columns = _split_table_columns(data_line)
        if len(header_columns) >= 2 and len(data_columns) >= 2:
            target_index = next(
                (
                    position
                    for position, column in enumerate(header_columns)
                    if target_token in column.lower()
                ),
                None,
            )
            if target_index is not None and target_index < len(data_columns):
                match = value_pattern.search(data_columns[target_index])
                if match:
                    return match.group(0), f"{header_line} {data_line}", True

        values = [match.group(0) for match in value_pattern.finditer(data_line)]
        if len(values) >= 2:
            value = values[0] if field_name == "gross_weight" else values[1]
            return value, f"{header_line} {data_line}", True

    return None, None, False


def _find_weight_context_value(field_name: str, raw_text: str, document_type: str) -> Tuple[Optional[str], Optional[str], bool]:
    if field_name not in {"gross_weight", "net_weight"} or not _plaintext_parser_lift_v1_enabled():
        return None, None, False

    label_pattern = re.compile(
        r"(GROSS\s*(?:WEIGHT|WT|WGT)|TOTAL\s+GROSS\s+WEIGHT|G\.?\s*W\.?|GW)"
        if field_name == "gross_weight"
        else r"(NET\s*(?:WEIGHT|WT|WGT)|TOTAL\s+NET\s+WEIGHT|N\.?\s*W\.?|NW)",
        re.IGNORECASE,
    )
    other_pattern = re.compile(
        r"(NET\s*(?:WEIGHT|WT|WGT)|TOTAL\s+NET\s+WEIGHT|N\.?\s*W\.?|NW)"
        if field_name == "gross_weight"
        else r"(GROSS\s*(?:WEIGHT|WT|WGT)|TOTAL\s+GROSS\s+WEIGHT|G\.?\s*W\.?|GW)",
        re.IGNORECASE,
    )
    value_pattern = re.compile(
        rf"([0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?\s*{_WEIGHT_UNIT_PATTERN})",
        re.IGNORECASE,
    )

    for window in _field_search_windows(_scan_lines(raw_text), field_name, document_type):
        target_match = label_pattern.search(window)
        if not target_match:
            continue
        value_matches = list(value_pattern.finditer(window))
        if not value_matches:
            continue
        other_match = other_pattern.search(window)
        target_end = target_match.end()
        other_start = other_match.start() if other_match else len(window) + 1
        for match in value_matches:
            if target_end <= match.start() <= other_start:
                return match.group(1), window, True
        after_target = [match for match in value_matches if match.start() >= target_end]
        if after_target:
            return after_target[0].group(1), window, True
        return value_matches[0].group(1), window, True

    return None, None, False


def _find_field_match(field_name: str, raw_text: str, document_type: str) -> Tuple[Optional[str], Optional[str], bool]:
    lines = _scan_lines(raw_text)
    label_present = _label_seen(raw_text, field_name, document_type)
    patterns = _patterns_for_field(field_name, document_type)
    for line in _field_search_windows(lines, field_name, document_type):
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


def _derive_plaintext_evidence_snippet(
    raw_text: str,
    field_name: str,
    document_type: str,
    raw_value: Any,
    normalized_value: Any,
) -> Optional[str]:
    raw_text_value = _normalize_text(raw_value)
    normalized_text = _normalize_text(normalized_value)
    normalized_digits = re.sub(r"\D", "", normalized_text)
    lines = _scan_lines(raw_text)
    target_tokens = tuple(token for token in _field_tokens(field_name, document_type) if token)
    value_pattern = re.compile(
        rf"[0-9OISBL][0-9OISBL,]*(?:[.][0-9OISBL]+)?\s*{_WEIGHT_UNIT_PATTERN}",
        re.IGNORECASE,
    )
    date_pattern = re.compile(r"(?:\d{4}[-/.]\d{2}[-/.]\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}\s+[A-Z]{3,9}\s+\d{4})", re.IGNORECASE)

    if _plaintext_parser_lift_v1_enabled():
        for window in _field_search_windows(lines, field_name, document_type):
            lowered = window.lower()
            token_hit = any(token in lowered for token in target_tokens)
            if not token_hit:
                continue
            if raw_text_value and raw_text_value.lower() in lowered:
                return window
            if normalized_text and normalized_text.lower() in lowered:
                return window
            if field_name == "bin_tin" and normalized_digits:
                window_digits = re.sub(r"\D", "", _normalize_numeric_context(window))
                if normalized_digits and normalized_digits in window_digits:
                    return window
            if field_name in {"gross_weight", "net_weight"} and value_pattern.search(window):
                return window
            if field_name == "issue_date" and date_pattern.search(window):
                return window
            if field_name == "voyage" and re.search(r"[A-Z0-9./-]{2,24}", window, re.IGNORECASE):
                return window

    for line in lines:
        lowered = line.lower()
        token_hit = any(token in lowered for token in target_tokens)
        if raw_text_value and raw_text_value.lower() in lowered:
            return line
        if normalized_text and normalized_text.lower() in lowered:
            return line
        if field_name == "bin_tin" and normalized_digits:
            line_digits = re.sub(r"\D", "", _normalize_numeric_context(line))
            if normalized_digits and normalized_digits in line_digits and token_hit:
                return line
        if field_name in {"gross_weight", "net_weight"} and token_hit and value_pattern.search(line):
            return line
        if field_name == "issue_date" and token_hit and date_pattern.search(line):
            return line
        if field_name == "voyage" and token_hit and re.search(r"[A-Z0-9./-]{2,24}", line, re.IGNORECASE):
            return line

    return _snippet_from_text(raw_text, raw_text_value or normalized_text)


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


def _parse_field_from_text(field_name: str, raw_text: str, document_type: str, extraction_stage: Optional[str] = None) -> _ParsedFieldCandidate:
    if field_name in {"amount", "currency"}:
        return _parse_amount_currency_fields(raw_text).get(field_name, _ParsedFieldCandidate(field_name, None, None, "missing", 0.0, None, ["FIELD_NOT_FOUND"], "preparser"))
    if _top3_field_boost_v1_enabled() and field_name in {"gross_weight", "net_weight"}:
        tabular_value, tabular_snippet, tabular_anchor_hit = _find_weight_table_value(field_name, raw_text, document_type)
        if tabular_value is not None:
            normalized_value, error_code, _ = _normalize_field_value(field_name, tabular_value, document_type)
            state = infer_field_state(normalized_value, parse_error=error_code is not None)
            return _ParsedFieldCandidate(
                field_name,
                tabular_value,
                normalized_value,
                state,
                _candidate_confidence_for_field(
                    field_name=field_name,
                    document_type=document_type,
                    source="preparser",
                    state=state,
                    anchor_hit=tabular_anchor_hit,
                    evidence_snippet=tabular_snippet,
                    normalized_value=normalized_value,
                    raw_value=tabular_value,
                    extraction_stage=extraction_stage,
                ),
                tabular_snippet,
                _field_reason_codes(state, [error_code]),
                "preparser",
                tabular_anchor_hit,
            )
        contextual_value, contextual_snippet, contextual_anchor_hit = _find_weight_context_value(field_name, raw_text, document_type)
        if contextual_value is not None:
            normalized_value, error_code, _ = _normalize_field_value(field_name, contextual_value, document_type)
            state = infer_field_state(normalized_value, parse_error=error_code is not None)
            return _ParsedFieldCandidate(
                field_name,
                contextual_value,
                normalized_value,
                state,
                _candidate_confidence_for_field(
                    field_name=field_name,
                    document_type=document_type,
                    source="preparser",
                    state=state,
                    anchor_hit=contextual_anchor_hit,
                    evidence_snippet=contextual_snippet,
                    normalized_value=normalized_value,
                    raw_value=contextual_value,
                    extraction_stage=extraction_stage,
                ),
                contextual_snippet,
                _field_reason_codes(state, [error_code]),
                "preparser",
                contextual_anchor_hit,
            )
        paired_value, paired_snippet, paired_anchor_hit = _find_weight_pair_match(field_name, raw_text, document_type)
        if paired_value is not None:
            normalized_value, error_code, _ = _normalize_field_value(field_name, paired_value, document_type)
            state = infer_field_state(normalized_value, parse_error=error_code is not None)
            return _ParsedFieldCandidate(
                field_name,
                paired_value,
                normalized_value,
                state,
                _candidate_confidence_for_field(
                    field_name=field_name,
                    document_type=document_type,
                    source="preparser",
                    state=state,
                    anchor_hit=paired_anchor_hit,
                    evidence_snippet=paired_snippet,
                    normalized_value=normalized_value,
                    raw_value=paired_value,
                    extraction_stage=extraction_stage,
                ),
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
    normalized_value, error_code, _ = _normalize_field_value(field_name, matched_value, document_type)
    state = infer_field_state(normalized_value, parse_error=error_code is not None)
    return _ParsedFieldCandidate(
        field_name,
        matched_value,
        normalized_value,
        state,
        _candidate_confidence_for_field(
            field_name=field_name,
            document_type=document_type,
            source="preparser",
            state=state,
            anchor_hit=anchor_hit,
            evidence_snippet=snippet,
            normalized_value=normalized_value,
            raw_value=matched_value,
            extraction_stage=extraction_stage,
        ),
        snippet,
        _field_reason_codes(state, [error_code]),
        "preparser",
        anchor_hit,
    )


def _preparse_document_fields(raw_text: str, document_type: str, extraction_stage: Optional[str] = None) -> Dict[str, _ParsedFieldCandidate]:
    if not _preparser_hardening_enabled():
        return {}
    parsed = {field_name: _parse_field_from_text(field_name, raw_text, document_type, extraction_stage) for field_name in _PREPARSER_FIELDS}
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
    extraction_stage: Optional[str] = None,
) -> _ParsedFieldCandidate:
    evidence_refs = _build_evidence_refs(details, selected_value, raw_text)
    normalized_value = None
    normalize_error = None
    if selected_value not in (None, "", [], {}):
        normalized_value, normalize_error, _ = _normalize_field_value(field_name, selected_value, document_type)
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
        _candidate_confidence_for_field(
            field_name=field_name,
            document_type=document_type,
            source="existing",
            state=state,
            explicit_confidence=explicit_confidence if explicit_confidence is not None else _field_confidence(document, details),
            anchor_hit=_label_seen(raw_text or evidence_snippet or "", field_name, document_type),
            evidence_snippet=evidence_snippet,
            normalized_value=normalized_value,
            raw_value=selected_value,
            extraction_stage=extraction_stage,
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
    return existing_candidate


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
        amount = by_name.get("amount")
        currency = by_name.get("currency")
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


def _gate_profile_settings(profile: Dict[str, Any], extraction_stage: Optional[str] = None) -> Tuple[float, bool, List[str]]:
    if _pass_gate_v2_enabled() and isinstance(profile.get("pass_gate"), dict):
        gate_config = profile.get("pass_gate") or {}
    else:
        gate_config = profile.get("review_gate") if isinstance(profile.get("review_gate"), dict) else {}
    if _plaintext_stage_active(extraction_stage):
        min_confidence = float(gate_config.get("plaintext_min_confidence", gate_config.get("min_confidence", 0.80)) or 0.80)
    else:
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
    extraction_stage = _selected_extraction_stage(document, extraction_artifacts)

    profile = load_profile(doc_type)
    critical_fields = profile.get("critical_fields") or []
    min_confidence, require_evidence, cross_checks = _gate_profile_settings(profile, extraction_stage)
    preparsed_candidates = _preparse_document_fields(raw_text, doc_type, extraction_stage) if extraction_artifacts else {}

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
            extraction_stage=extraction_stage,
        )
        selected_candidate = _merge_field_candidates(existing_candidate, preparsed_candidates.get(str(field_name)))
        evidence = _build_evidence_refs(details, value, raw_text)
        if not evidence and selected_candidate.source == "preparser":
            derived_evidence = (
                _derive_plaintext_evidence_snippet(
                    raw_text,
                    str(field_name),
                    doc_type,
                    selected_candidate.value_raw,
                    selected_candidate.value_normalized,
                )
                if _plaintext_stage_active(extraction_stage)
                else selected_candidate.evidence_snippet
            )
            evidence = _build_parser_evidence(derived_evidence or selected_candidate.evidence_snippet, selected_candidate.confidence)
        effective_confidence = selected_candidate.confidence
        explicit_detail_confidence = _coerce_confidence(details.get("confidence"))
        if (
            _top3_lift_active()
            and str(field_name) in _TOP3_FIELD_NAMES
            and selected_candidate.source == "preparser"
            and explicit_detail_confidence is not None
        ):
            effective_confidence = min(effective_confidence, explicit_detail_confidence)
        field_reason_codes = list(selected_candidate.reason_codes)
        if (
            _plaintext_stage_active(extraction_stage)
            and selected_candidate.source == "preparser"
            and selected_candidate.state == "found"
            and not evidence
        ):
            if "EVIDENCE_MISSING" not in field_reason_codes:
                field_reason_codes.append("EVIDENCE_MISSING")
            effective_confidence = _clamp_confidence(
                effective_confidence - _plaintext_confidence_config(doc_type, str(field_name)).get("evidence_missing_penalty", 0.18)
            )
        final_state = selected_candidate.state
        final_value_normalized = selected_candidate.value_normalized
        if (
            _plaintext_stage_active(extraction_stage)
            and selected_candidate.source == "preparser"
            and final_state == "found"
            and effective_confidence < min_confidence
        ):
            final_state = "parse_failed"
            final_value_normalized = None
            if "LOW_CONFIDENCE_CRITICAL" not in field_reason_codes:
                field_reason_codes.append("LOW_CONFIDENCE_CRITICAL")
        elif (
            _top3_lift_active()
            and str(field_name) in _TOP3_FIELD_NAMES
            and final_state == "found"
            and effective_confidence < min_confidence
            and "LOW_CONFIDENCE_CRITICAL" not in field_reason_codes
        ):
            field_reason_codes.append("LOW_CONFIDENCE_CRITICAL")
        fields.append(
            FieldExtraction(
                name=str(field_name),
                value_raw=selected_candidate.value_raw,
                value_normalized=final_value_normalized,
                state=final_state,  # type: ignore[arg-type]
                confidence=effective_confidence,
                evidence=evidence,
                reason_codes=sorted(dict.fromkeys(field_reason_codes)),
            )
        )

    extraction_resolution = _build_extraction_resolution_from_fields(
        fields=fields,
        field_details=field_details if isinstance(field_details, dict) else {},
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
    review_reasons = [reason for reason in (decision.reasons or []) if not _is_extraction_resolution_reason(reason)]
    review_required = bool(review_reasons) or bool(extraction_resolution and extraction_resolution.required)
    _apply_artifact_metadata(document=document, fields=fields, preparsed_candidates=preparsed_candidates, review_reasons=review_reasons)

    return DocumentExtraction(
        doc_id=str(document.get("id") or document.get("document_id") or ""),
        doc_type_predicted=doc_type,
        doc_type_confidence=_coerce_confidence(document.get("doc_type_confidence")) or 0.0,
        fields=fields,
        review_required=review_required,
        review_reasons=review_reasons,
        extraction_resolution=extraction_resolution,
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
        extraction_resolution = (
            extraction_doc.get("extraction_resolution")
            if isinstance(extraction_doc.get("extraction_resolution"), dict)
            else None
        )

        document["review_required"] = review_required
        document["reviewRequired"] = review_required
        document["review_reasons"] = review_reasons
        document["reviewReasons"] = review_reasons
        if extraction_resolution:
            document["extraction_resolution"] = extraction_resolution
            document["extractionResolution"] = extraction_resolution
        document["critical_field_states"] = critical_field_states
        document["criticalFieldStates"] = critical_field_states

    return bundle
