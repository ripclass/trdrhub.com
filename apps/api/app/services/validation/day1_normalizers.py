from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
from typing import Optional, Tuple


BIN_LENGTH = 13
TIN_MIN_LENGTH = 10
TIN_MAX_LENGTH = 12


@dataclass(frozen=True)
class NormalizeResult:
    raw: Optional[str]
    normalized: Optional[str]
    valid: bool
    error_code: Optional[str] = None


@dataclass(frozen=True)
class WeightResult:
    raw: Optional[str]
    normalized_kg: Optional[float]
    unit: Optional[str]
    valid: bool
    error_code: Optional[str] = None


_OCR_DIGIT_MAP = str.maketrans({
    "O": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
})


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


_UNIT_ALIASES = {
    "KG": "KG",
    "KGS": "KG",
    "KILOGRAM": "KG",
    "KILOGRAMS": "KG",
    "MT": "MT",
    "TON": "MT",
    "TONNE": "MT",
    "LB": "LB",
    "LBS": "LB",
}


def _base_clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def _numeric_context_ocr_fix(text: str) -> str:
    return text.upper().translate(_OCR_DIGIT_MAP)


def _strip_leading_id_labels(text: str) -> str:
    return re.sub(r"\b(BIN|TIN|TAX\s*ID|VAT\s*REG)\b[:\s-]*", " ", text, flags=re.IGNORECASE)


def normalize_bin(raw: Optional[str]) -> NormalizeResult:
    cleaned = _strip_leading_id_labels(_base_clean(raw))
    cleaned = _numeric_context_ocr_fix(cleaned)
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return NormalizeResult(raw, None, False, "ID_EMPTY_AFTER_NORMALIZE")
    if len(digits) != BIN_LENGTH:
        return NormalizeResult(raw, None, False, "BIN_LENGTH_INVALID")
    return NormalizeResult(raw, digits, True)


def normalize_tin(raw: Optional[str]) -> NormalizeResult:
    cleaned = _strip_leading_id_labels(_base_clean(raw))
    cleaned = _numeric_context_ocr_fix(cleaned)
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return NormalizeResult(raw, None, False, "ID_EMPTY_AFTER_NORMALIZE")
    if not (TIN_MIN_LENGTH <= len(digits) <= TIN_MAX_LENGTH):
        return NormalizeResult(raw, None, False, "TIN_LENGTH_INVALID")
    return NormalizeResult(raw, digits, True)


def normalize_voyage(raw: Optional[str]) -> NormalizeResult:
    text = _base_clean(raw).upper()
    if not text:
        return NormalizeResult(raw, None, False, "VOYAGE_FORMAT_INVALID")

    text = re.sub(r"\b(VOYAGE|VOY\.?|VOY\s*NO\.?|VYG|NO\.?|:)\b", " ", text)
    text = re.sub(r"[\s/\\]+", "-", text)
    text = re.sub(r"[^A-Z0-9-]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")

    if not text or not re.search(r"[A-Z]", text) or not re.search(r"\d", text):
        return NormalizeResult(raw, None, False, "VOYAGE_FORMAT_INVALID")
    return NormalizeResult(raw, text, True)


def normalize_weight(raw: Optional[str]) -> WeightResult:
    text = _base_clean(raw).upper()
    if not text:
        return WeightResult(raw, None, None, False, "WEIGHT_NUMBER_MISSING")

    match = re.search(r"([0-9][0-9,]*(?:[\.,][0-9]+)?)\s*([A-Z]+)", text)
    if not match:
        return WeightResult(raw, None, None, False, "WEIGHT_NUMBER_MISSING")

    value_text = match.group(1)
    unit_raw = match.group(2)
    if "," in value_text and "." not in value_text:
        value_text = value_text.replace(",", ".")
    else:
        value_text = value_text.replace(",", "")

    try:
        value = float(value_text)
    except ValueError:
        return WeightResult(raw, None, None, False, "WEIGHT_NUMBER_MISSING")

    unit = _UNIT_ALIASES.get(unit_raw)
    if not unit:
        return WeightResult(raw, None, None, False, "WEIGHT_UNIT_UNKNOWN")

    if unit == "KG":
        kg = value
    elif unit == "MT":
        kg = value * 1000.0
    else:
        kg = value * 0.45359237

    return WeightResult(raw, round(kg, 3), unit, True)


def validate_gross_net_pair(gross: WeightResult, net: WeightResult) -> Optional[str]:
    if not (gross.valid and net.valid):
        return None
    if gross.normalized_kg is None or net.normalized_kg is None:
        return None
    if net.normalized_kg > gross.normalized_kg:
        return "NET_GT_GROSS"
    return None


def normalize_date(raw: Optional[str]) -> NormalizeResult:
    text = _base_clean(raw).upper()
    if not text:
        return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")

    # YYYY-MM-DD
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            parsed = datetime.strptime(text, "%Y-%m-%d")
            return NormalizeResult(raw, parsed.strftime("%Y-%m-%d"), True)
    except ValueError:
        return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")

    # DD/MM/YYYY or D/M/YYYY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            parsed = datetime(year=y, month=mth, day=d)
            return NormalizeResult(raw, parsed.strftime("%Y-%m-%d"), True)
        except ValueError:
            return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")

    # DD-MM-YYYY
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", text)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            parsed = datetime(year=y, month=mth, day=d)
            return NormalizeResult(raw, parsed.strftime("%Y-%m-%d"), True)
        except ValueError:
            return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")

    # DD MON YYYY
    m = re.fullmatch(r"(\d{1,2})\s+([A-Z]{3})\s+(\d{4})", text)
    if m and m.group(2) in _MONTHS:
        d, mon, y = int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3))
        try:
            parsed = datetime(year=y, month=mon, day=d)
            return NormalizeResult(raw, parsed.strftime("%Y-%m-%d"), True)
        except ValueError:
            return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")

    return NormalizeResult(raw, None, False, "DATE_PARSE_INVALID")


def normalize_issuer(raw: Optional[str]) -> NormalizeResult:
    text = _base_clean(raw)
    if not text:
        return NormalizeResult(raw, None, False, "ISSUER_EMPTY")

    out = unicodedata.normalize("NFKC", text).upper()
    out = re.sub(r"\s+", " ", out).strip(" .,")
    out = re.sub(r"\bLIMITED\b", "LTD", out)
    out = re.sub(r"\bLTD\.?\b", "LTD", out)
    out = re.sub(r"\bPRIVATE\b", "PVT", out)
    out = re.sub(r"\bPVT\.?\b", "PVT", out)
    out = re.sub(r"[^A-Z0-9&/\- ]", "", out)
    out = re.sub(r"\s+", " ", out).strip(" .,")

    if not out:
        return NormalizeResult(raw, None, False, "ISSUER_EMPTY")
    return NormalizeResult(raw, out, True)
