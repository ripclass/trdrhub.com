"""Redis-backed per-IP, per-scope abuse limiter for public, no-auth endpoints.

The generic ``RateLimiterMiddleware`` is an in-memory, per-process, per-IP
*request-count* limiter over a short rolling window — it CANNOT express
"1 request per IP per 24 hours, scoped to one path". The public LC checker
(``POST /api/check``) needs exactly that: an un-rate-limited public endpoint
that runs Sonnet/Opus on every hit is unbounded free model spend, so the limit
has to be a long-window, path-scoped, shared (cross-process) counter — hence
Redis.

Usage::

    retry_after = await reserve_anon_run(request=req, scope="lc_check")
    if retry_after is not None:
        raise HTTPException(429, ..., headers={"Retry-After": str(retry_after)})
    try:
        ... run the expensive thing ...
    except SomethingCheapAndPreLLM:
        await release_anon_run(request=req, scope="lc_check")   # refund
        raise

Failure semantics:
  * Redis genuinely *not configured* (``REDIS_URL`` / ``REDIS_HOST`` unset) —
    only happens in local/stub dev: ``get_redis()`` returns ``None`` and we
    fail **open** (return ``None`` = allowed, unmetered).
  * Redis configured but *unreachable* — ``get_redis()`` raises; we let it
    propagate so the caller can fail **closed** (503). For a cost-critical
    public LLM endpoint, "briefly unavailable" beats "unmetered".
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request

from app.utils.redis_cache import get_redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "anon_run"


def client_ip(request: Request) -> str:
    """Best-effort client IP, honouring the proxy headers Render/Vercel set.

    Mirrors ``AuditMiddleware.get_client_ip`` so the limiter keys on the same
    address the rest of the stack attributes the request to.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return host or "unknown"


def _key(scope: str, ip: str) -> str:
    return f"{_KEY_PREFIX}:{scope}:{ip}"


async def reserve_anon_run(
    *,
    request: Request,
    scope: str,
    window_seconds: int = 24 * 60 * 60,
    limit: int = 1,
) -> Optional[int]:
    """Reserve one anonymous run for ``(client IP, scope)``.

    Returns ``None`` when the run is allowed (and reserved). Returns an ``int``
    — seconds remaining until the window resets — when the IP has already used
    its allowance.

    Raises whatever ``get_redis()`` raises when Redis is configured but
    unreachable (caller should treat that as 503).
    """
    redis = await get_redis()
    if redis is None:
        # Not configured at all — local/stub dev only. Fail open.
        return None

    ip = client_ip(request)
    key = _key(scope, ip)

    count = await redis.incr(key)
    if count == 1:
        # First request in this window — arm the TTL.
        await redis.expire(key, window_seconds)
        return None
    if count > limit:
        ttl = await redis.ttl(key)
        if not isinstance(ttl, int) or ttl <= 0:
            # Key exists without a TTL (shouldn't happen) — repair it.
            await redis.expire(key, window_seconds)
            ttl = window_seconds
        return ttl
    return None


async def release_anon_run(*, request: Request, scope: str) -> None:
    """Best-effort refund of a previously-reserved run.

    Call this only when the reservation did not actually result in expensive
    work (e.g. the upload was malformed and rejected before the LLM ran).
    Never raises.
    """
    try:
        redis = await get_redis()
        if redis is None:
            return
        ip = client_ip(request)
        await redis.decr(_key(scope, ip))
    except Exception:  # noqa: BLE001 — refund is purely best-effort
        logger.debug("anon_rate_limit: refund failed for scope=%s", scope, exc_info=True)


async def peek_anon_run(*, request: Request, scope: str, limit: int = 1) -> Optional[int]:
    """Non-consuming check: returns seconds-until-reset if the IP is over its
    allowance, else ``None``. Used by GET-style "can I run?" probes."""
    try:
        redis = await get_redis()
        if redis is None:
            return None
        ip = client_ip(request)
        raw = await redis.get(_key(scope, ip))
        if raw is None:
            return None
        try:
            count = int(raw)
        except (TypeError, ValueError):
            return None
        if count < limit:
            return None
        ttl = await redis.ttl(_key(scope, ip))
        return ttl if isinstance(ttl, int) and ttl > 0 else 1
    except Exception:  # noqa: BLE001
        return None
