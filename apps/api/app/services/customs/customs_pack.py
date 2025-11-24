from __future__ import annotations

from typing import Any, Dict, List


def build_customs_manifest_from_option_e(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a customs pack manifest using Option-E structured_result data.
    """

    lc_structured = structured_result.get("lc_structured") or {}
    docs: List[Dict[str, Any]] = (
        structured_result.get("documents_structured")
        or lc_structured.get("documents_structured")
        or []
    )

    manifest = [
        {
            "name": doc.get("filename"),
            "tag": doc.get("document_type"),
        }
        for doc in docs
    ]

    return {
        "ready": bool(manifest),
        "manifest": manifest,
        "format": "zip-manifest-v1",
    }
