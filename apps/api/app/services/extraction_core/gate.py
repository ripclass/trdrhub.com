from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .contract import FieldExtraction
from .field_states import is_critical_missing_or_failed
from .evidence import has_minimum_evidence


@dataclass(frozen=True)
class ReviewDecision:
    review_required: bool
    reasons: list[str]


def evaluate_review_gate(
    fields: Sequence[FieldExtraction],
    critical_field_names: Iterable[str],
    min_confidence: float = 0.80,
    require_evidence: bool = True,
) -> ReviewDecision:
    critical = set(critical_field_names)
    reasons: list[str] = []

    for f in fields:
        if f.name not in critical:
            continue
        if is_critical_missing_or_failed(f.state):
            reasons.append(f"critical_{f.name}_{f.state}")
        if f.state == "found" and f.confidence < min_confidence:
            reasons.append(f"critical_{f.name}_low_confidence")
        if require_evidence and f.state == "found" and not has_minimum_evidence(f):
            reasons.append(f"critical_{f.name}_evidence_missing")

    return ReviewDecision(review_required=len(reasons) > 0, reasons=sorted(set(reasons)))
