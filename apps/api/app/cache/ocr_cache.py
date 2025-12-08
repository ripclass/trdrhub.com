"""
OCR result cache with Redis persistence and in-memory fallback.

Uses Redis when available for persistence across server restarts.
Falls back to in-memory cache when Redis is not configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

OCR_CACHE_TTL_SECONDS = 3 * 24 * 60 * 60  # 72 hours
OCR_CACHE_PREFIX = "ocr:v1:"  # Prefix for Redis keys

# In-memory fallback cache
_memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_lock = asyncio.Lock()

# Track Redis availability to avoid repeated connection attempts
_redis_available: Optional[bool] = None


async def _get_redis():
    """Get Redis client, caching availability status."""
    global _redis_available
    
    # If we know Redis is unavailable, don't try again
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
            logger.info("OCR cache: Redis not configured, using in-memory cache")
            return None
    except Exception as e:
        _redis_available = False
        logger.warning(f"OCR cache: Redis unavailable ({e}), using in-memory cache")
        return None


async def get(document_hash: str) -> Optional[Dict[str, Any]]:
    """
    Return cached OCR result if available.
    
    Tries Redis first, falls back to in-memory cache.
    """
    redis = await _get_redis()
    
    if redis:
        try:
            key = f"{OCR_CACHE_PREFIX}{document_hash}"
            cached = await redis.get(key)
            if cached:
                payload = json.loads(cached)
                logger.debug(f"OCR cache HIT (Redis): {document_hash[:16]}...")
                return payload
            logger.debug(f"OCR cache MISS (Redis): {document_hash[:16]}...")
            return None
        except Exception as e:
            logger.warning(f"Redis OCR cache get failed: {e}")
            # Fall through to memory cache
    
    # In-memory fallback
    now = time.time()
    async with _lock:
        entry = _memory_cache.get(document_hash)
        if not entry:
            return None

        ts, payload = entry
        if now - ts > OCR_CACHE_TTL_SECONDS:
            _memory_cache.pop(document_hash, None)
            return None

        logger.debug(f"OCR cache HIT (memory): {document_hash[:16]}...")
        return payload.copy()


async def set(document_hash: str, payload: Dict[str, Any]) -> None:
    """
    Store OCR result in cache.
    
    Stores in Redis (persistent) and in-memory (fast fallback).
    """
    redis = await _get_redis()
    
    if redis:
        try:
            key = f"{OCR_CACHE_PREFIX}{document_hash}"
            # Store as JSON with TTL
            await redis.setex(
                key,
                OCR_CACHE_TTL_SECONDS,
                json.dumps(payload)
            )
            logger.debug(f"OCR cache SET (Redis): {document_hash[:16]}... TTL={OCR_CACHE_TTL_SECONDS}s")
        except Exception as e:
            logger.warning(f"Redis OCR cache set failed: {e}")
            # Fall through to memory cache
    
    # Also store in memory for fast access (double-write)
    async with _lock:
        _memory_cache[document_hash] = (time.time(), payload.copy())


async def get_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    redis = await _get_redis()
    
    stats = {
        "memory_entries": len(_memory_cache),
        "redis_available": redis is not None,
    }
    
    if redis:
        try:
            # Count OCR keys in Redis
            keys = await redis.keys(f"{OCR_CACHE_PREFIX}*")
            stats["redis_entries"] = len(keys)
        except Exception:
            stats["redis_entries"] = "unknown"
    
    return stats


async def clear_memory_cache() -> int:
    """Clear in-memory cache (useful for testing)."""
    async with _lock:
        count = len(_memory_cache)
        _memory_cache.clear()
        return count
