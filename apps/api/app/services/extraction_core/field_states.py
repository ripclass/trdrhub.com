from __future__ import annotations

from typing import Any, Iterable, Literal

FieldState = Literal["found", "parse_failed", "missing"]


def infer_field_state(value_normalized: Any, parse_error: bool = False) -> FieldState:
    if isinstance(value_normalized, str):
        value_normalized = value_normalized.strip()
    if value_normalized in (None, "", [], {}):
        return "parse_failed" if parse_error else "missing"
    return "found"


def is_critical_missing_or_failed(state: FieldState) -> bool:
    return state in {"missing", "parse_failed"}


def missing_critical_fields(states: Iterable[tuple[str, FieldState]]) -> list[str]:
    return [name for name, st in states if is_critical_missing_or_failed(st)]
