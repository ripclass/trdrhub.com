from __future__ import annotations

from typing import Iterable

from .contract import EvidenceRef, FieldExtraction


def has_minimum_evidence(field: FieldExtraction) -> bool:
    if field.state != "found":
        return True
    if not field.evidence:
        return False
    first = field.evidence[0]
    return bool(first.text_span and first.page >= 1)


def count_fields_without_evidence(fields: Iterable[FieldExtraction]) -> int:
    return sum(1 for f in fields if not has_minimum_evidence(f))
