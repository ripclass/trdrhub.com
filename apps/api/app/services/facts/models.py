from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DocumentEvidence:
    evidence_snippet: Optional[str] = None
    evidence_source: Optional[str] = None
    page: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentFact:
    field_name: str
    value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    confidence: Optional[float] = None
    verification_state: str = "unconfirmed"
    origin: str = "unknown"
    source_field_name: Optional[str] = None
    evidence_snippet: Optional[str] = None
    evidence_source: Optional[str] = None
    page: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentFactSet:
    version: str
    document_type: str
    document_subtype: Optional[str]
    facts: List[DocumentFact]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["facts"] = [fact.to_dict() for fact in self.facts]
        return payload
