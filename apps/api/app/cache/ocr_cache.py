"""
Simple in-memory OCR result cache keyed by document hash.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

OCR_CACHE_TTL_SECONDS = 3 * 24 * 60 * 60  # 72 hours

_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_lock = asyncio.Lock()


async def get(document_hash: str) -> Optional[Dict[str, Any]]:
    """Return cached OCR result if available."""
    now = time.time()
    async with _lock:
        entry = _cache.get(document_hash)
        if not entry:
            return None

        ts, payload = entry
        if now - ts > OCR_CACHE_TTL_SECONDS:
            _cache.pop(document_hash, None)
            return None

        return payload.copy()


async def set(document_hash: str, payload: Dict[str, Any]) -> None:
    """Store OCR result."""
    async with _lock:
        _cache[document_hash] = (time.time(), payload.copy())
