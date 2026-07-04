"""Public marketing stats — live-fetched counts (launch honesty checklist).

The rule count on landing pages must never be a hardcoded number again: the
corpus grows continuously (playbook said 4,000+; it's headed past 20k), so
any literal is stale the day it ships. This endpoint asks RulHub for the
current approved-rule count (corpus_stats on /v1/rules/lookup), caches it
in-process for 24h, and returns null on any failure — the frontend then
falls back to a safe FLOOR ("4,000+"), which under-claims rather than lies.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["Public Stats"])

_CACHE_TTL_SECONDS = 24 * 60 * 60
_cache: Dict[str, Any] = {"at": 0.0, "value": None}


async def _fetch_rule_count() -> Optional[int]:
    from app.services.rulhub_client import get_rulhub_client

    client = get_rulhub_client()
    result = await client.lookup_rules(per_page=1)
    stats = result.get("corpus_stats") or {}
    active = stats.get("active")
    return int(active) if isinstance(active, (int, float)) and active > 0 else None


@router.get("/stats")
async def public_stats():
    """Live platform counts for marketing surfaces. Cached 24h in-process."""
    now = time.monotonic()
    if _cache["value"] is not None and (now - _cache["at"]) < _CACHE_TTL_SECONDS:
        return {"rules_total": _cache["value"], "cached": True}

    try:
        count = await _fetch_rule_count()
    except Exception as exc:
        logger.info("public stats: rule count unavailable (%s)", str(exc)[:120])
        count = None

    if count is not None:
        _cache["value"] = count
        _cache["at"] = now
        return {"rules_total": count, "cached": False}

    # Stale-if-error: serve the last good value beyond its TTL rather than
    # nothing — an old true count beats no count.
    if _cache["value"] is not None:
        return {"rules_total": _cache["value"], "cached": True, "stale": True}
    return {"rules_total": None}
