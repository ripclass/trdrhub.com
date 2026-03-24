from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ResolutionQueueItem:
    document_id: str
    document_type: str
    filename: Optional[str]
    field_name: str
    label: str
    priority: str
    candidate_value: Optional[Any]
    normalized_value: Optional[Any]
    evidence_snippet: Optional[str]
    evidence_source: Optional[str]
    page: Optional[int]
    reason: str
    verification_state: str
    resolvable_by_user: bool
    origin: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolutionQueueSummary:
    total_items: int
    user_resolvable_items: int
    unresolved_documents: int
    document_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolutionQueue:
    version: str
    items: List[ResolutionQueueItem]
    summary: ResolutionQueueSummary

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        payload["summary"] = self.summary.to_dict()
        return payload
