"""Narrow adapter contract used by the persisted Proofline orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class AdapterResult:
    state: str
    summary: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    source_record_type: str | None = None
    source_record_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProoflineAdapter(Protocol):
    module: str
    version: str

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        """Evaluate bounded case context and return a structured source result."""


__all__ = ["AdapterResult", "ProoflineAdapter"]

