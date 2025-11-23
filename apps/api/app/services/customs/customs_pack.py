from __future__ import annotations

from typing import Dict, Any

def prepare_customs_pack(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare a serialized 'customs pack' payload. For now we mark it as ready
    and attach a minimal manifest so the UI can offer a download link.
    """
    docs = validation_results.get("documents", [])
    manifest = [{"name": d.get("name"), "tag": d.get("tag")} for d in docs]
    return {
        "ready": True,
        "manifest": manifest,
        "format": "zip-manifest-v1",
    }
