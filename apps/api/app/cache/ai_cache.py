"""
Simple in-memory cache for AI cross-document summaries.

The cache stores serialized structured document payloads for up to 7 days to
avoid redundant LLM calls for identical validation inputs.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_lock = asyncio.Lock()


def _normalize_payload(payload: Dict[str, Any]) -> str:
    """Serialize the payload deterministically for hashing."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def build_cache_key(payload: Dict[str, Any]) -> str:
    """Create a stable hash for the structured document payload."""
    serialized = _normalize_payload(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def get(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Return cached issues if entry exists and is fresh."""
    now = time.time()
    async with _lock:
        entry = _cache.get(cache_key)
        if not entry:
            return None
        ts, data = entry
        if now - ts > CACHE_TTL_SECONDS:
            _cache.pop(cache_key, None)
            return None
        # Return a deep copy to avoid callers mutating the cache
        return json.loads(json.dumps(data))


async def set(cache_key: str, issues: List[Dict[str, Any]]) -> None:
    """Store crossdoc issues in the cache."""
    async with _lock:
        _cache[cache_key] = (time.time(), json.loads(json.dumps(issues)))
