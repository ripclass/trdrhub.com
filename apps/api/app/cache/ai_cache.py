"""
AI cross-document summary cache with Redis persistence and in-memory fallback.

Uses Redis when available for persistence across server restarts.
Falls back to in-memory cache when Redis is not configured.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
AI_CACHE_PREFIX = "ai:crossdoc:v1:"  # Prefix for Redis keys

# In-memory fallback cache
_memory_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_lock = asyncio.Lock()

# Track Redis availability
_redis_available: Optional[bool] = None


async def _get_redis():
    """Get Redis client, caching availability status."""
    global _redis_available
    
    if _redis_available is False:
        return None
    
    try:
        from app.utils.redis_cache import get_redis
        client = await get_redis()
        if client:
            _redis_available = True
            return client
        else:
            _redis_available = False
            logger.info("AI cache: Redis not configured, using in-memory cache")
            return None
    except Exception as e:
        _redis_available = False
        logger.warning(f"AI cache: Redis unavailable ({e}), using in-memory cache")
        return None


def _normalize_payload(payload: Dict[str, Any]) -> str:
    """Serialize the payload deterministically for hashing."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def build_cache_key(payload: Dict[str, Any]) -> str:
    """Create a stable hash for the structured document payload."""
    serialized = _normalize_payload(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def get(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Return cached issues if entry exists and is fresh.
    
    Tries Redis first, falls back to in-memory cache.
    """
    redis = await _get_redis()
    
    if redis:
        try:
            key = f"{AI_CACHE_PREFIX}{cache_key}"
            cached = await redis.get(key)
            if cached:
                data = json.loads(cached)
                logger.debug(f"AI cache HIT (Redis): {cache_key[:16]}...")
                return data
            logger.debug(f"AI cache MISS (Redis): {cache_key[:16]}...")
            return None
        except Exception as e:
            logger.warning(f"Redis AI cache get failed: {e}")
            # Fall through to memory cache
    
    # In-memory fallback
    now = time.time()
    async with _lock:
        entry = _memory_cache.get(cache_key)
        if not entry:
            return None
        ts, data = entry
        if now - ts > CACHE_TTL_SECONDS:
            _memory_cache.pop(cache_key, None)
            return None
        logger.debug(f"AI cache HIT (memory): {cache_key[:16]}...")
        return json.loads(json.dumps(data))


async def set(cache_key: str, issues: List[Dict[str, Any]]) -> None:
    """
    Store crossdoc issues in the cache.
    
    Stores in Redis (persistent) and in-memory (fast fallback).
    """
    redis = await _get_redis()
    
    if redis:
        try:
            key = f"{AI_CACHE_PREFIX}{cache_key}"
            await redis.setex(
                key,
                CACHE_TTL_SECONDS,
                json.dumps(issues)
            )
            logger.debug(f"AI cache SET (Redis): {cache_key[:16]}... TTL={CACHE_TTL_SECONDS}s")
        except Exception as e:
            logger.warning(f"Redis AI cache set failed: {e}")
    
    # Also store in memory
    async with _lock:
        _memory_cache[cache_key] = (time.time(), json.loads(json.dumps(issues)))


async def get_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    redis = await _get_redis()
    
    stats = {
        "memory_entries": len(_memory_cache),
        "redis_available": redis is not None,
    }
    
    if redis:
        try:
            keys = await redis.keys(f"{AI_CACHE_PREFIX}*")
            stats["redis_entries"] = len(keys)
        except Exception:
            stats["redis_entries"] = "unknown"
    
    return stats
