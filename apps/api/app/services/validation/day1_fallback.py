from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


REQUIRED_FIELDS = (
    "issuer",
    "bin",
    "tin",
    "voyage",
    "gross_weight",
    "net_weight",
    "doc_date",
)


@dataclass(frozen=True)
class StageResult:
    stage: str
    fields: Dict[str, object]


@dataclass(frozen=True)
class FallbackDecision:
    selected_stage: str
    coverage: int
    llm_assist_required: bool


def count_valid_required_fields(fields: Optional[Dict[str, object]], required: Iterable[str] = REQUIRED_FIELDS) -> int:
    if not isinstance(fields, dict):
        return 0

    total = 0
    for key in required:
        value = fields.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            normalized = value.get("normalized")
            normalized_kg = value.get("normalized_kg")
            iso_date = value.get("iso_date")
            if normalized not in (None, "") or normalized_kg is not None or iso_date not in (None, ""):
                total += 1
            continue
        if value not in ("", [], {}):
            total += 1
    return total


def resolve_fallback_chain(
    *,
    native_fields: Optional[Dict[str, object]],
    ocr_fields: Optional[Dict[str, object]],
    llm_fields: Optional[Dict[str, object]],
    threshold: int = 5,
) -> FallbackDecision:
    native_coverage = count_valid_required_fields(native_fields)
    if native_coverage >= threshold:
        return FallbackDecision("native", native_coverage, False)

    ocr_coverage = count_valid_required_fields(ocr_fields)
    if ocr_coverage >= threshold:
        return FallbackDecision("ocr", ocr_coverage, False)

    llm_coverage = count_valid_required_fields(llm_fields)
    return FallbackDecision("llm_assist", llm_coverage, True)
