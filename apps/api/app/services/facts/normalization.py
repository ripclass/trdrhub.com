from __future__ import annotations

from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
)


def _clean_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def normalize_reference(value: Any) -> Optional[str]:
    return _clean_text(value)


def normalize_party_name(value: Any) -> Optional[str]:
    return _clean_text(value)


def normalize_currency(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r"\b([A-Z]{3})\b", text.upper())
    if match:
        return match.group(1)
    return text.upper()


def normalize_date(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    cleaned = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue

    compact = re.sub(r"[^0-9]", "", cleaned)
    if len(compact) == 8:
        for fmt in ("%Y%m%d", "%d%m%Y", "%m%d%Y"):
            try:
                return datetime.strptime(compact, fmt).date().isoformat()
            except ValueError:
                continue
    return text


def normalize_amount(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return format(Decimal(str(value)).quantize(Decimal("0.01")), "f")
        except (InvalidOperation, ValueError):
            return str(value)

    text = _clean_text(value)
    if not text:
        return None

    cleaned = re.sub(r"[^\d,\.\-]", "", text)
    if not cleaned:
        return text

    if cleaned.count(",") > 0 and cleaned.count(".") > 0:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") > 0 and cleaned.count(".") == 0:
        parts = cleaned.split(",")
        if len(parts[-1]) in {1, 2}:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = "".join(parts)

    try:
        return format(Decimal(cleaned).quantize(Decimal("0.01")), "f")
    except (InvalidOperation, ValueError):
        return text
