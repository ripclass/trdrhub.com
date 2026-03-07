from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


_PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "extraction_profiles"


def load_profile(doc_type: str) -> Dict[str, Any]:
    path = _PROFILES_DIR / f"{doc_type}.yaml"
    if not path.exists():
        path = _PROFILES_DIR / "supporting_document.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_profiles() -> list[str]:
    if not _PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.yaml"))
