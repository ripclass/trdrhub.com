from __future__ import annotations

from typing import Any, Dict


class ExtractionOrchestratorV1:
    """Placeholder orchestration interface for Extraction Core v1.

    Intended flow:
    1) native parse
    2) OCR parse
    3) deterministic extraction
    4) bounded LLM repair for unresolved fields
    5) review gating
    """

    def run(self, doc_payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Wire orchestration to existing validate pipeline")
