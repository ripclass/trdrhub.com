from __future__ import annotations

from typing import Any, Dict, List


def prepare_customs_pack(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare a serialized 'customs pack' payload based purely on Option-E data.
    """
    docs: List[Dict[str, Any]] = structured_result.get("documents_structured", []) or []
    manifest = [
        {
            "name": doc.get("filename"),
            "document_type": doc.get("document_type"),
            "extraction_status": doc.get("extraction_status"),
        }
        for doc in docs
    ]
    return {
        "ready": True,
        "manifest": manifest,
        "format": "option-e-zip-manifest-v1",
    }
