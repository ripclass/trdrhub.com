from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

FieldState = Literal["found", "parse_failed", "missing"]


@dataclass(frozen=True)
class EvidenceRef:
    page: int
    text_span: str
    bbox: Optional[List[float]] = None
    source_layer: Optional[str] = None  # native|ocr|llm_repair
    confidence: Optional[float] = None


@dataclass(frozen=True)
class FieldExtraction:
    name: str
    value_raw: Optional[Any]
    value_normalized: Optional[Any]
    state: FieldState
    confidence: float
    evidence: List[EvidenceRef] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentExtraction:
    doc_id: str
    doc_type_predicted: str
    doc_type_confidence: float
    fields: List[FieldExtraction]
    review_required: bool
    review_reasons: List[str] = field(default_factory=list)
    pipeline_version: str = "extraction-core-v1"
    profile_version: str = "profiles-v1"
    model_route_version: str = "routing-v1"


@dataclass(frozen=True)
class ExtractionBundle:
    documents: List[DocumentExtraction]
    meta: Dict[str, Any] = field(default_factory=dict)
