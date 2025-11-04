"""Centralised Redis client helpers for shared infrastructure state."""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from redis.asyncio import Redis
from redis.exceptions import RedisError


_redis_client: Optional[Redis] = None


def _env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _build_redis_options() -> Optional[Dict[str, Any]]:
    url = os.getenv("REDIS_URL")
    if url:
        return {"url": url}

    host = os.getenv("REDIS_HOST")
    password = os.getenv("REDIS_PASSWORD")

    # If nothing is configured, treat Redis as unavailable
    if not host and not password:
        return None

    host = host or "localhost"
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    ssl_enabled = _env_bool(os.getenv("REDIS_SSL"), default=False)
    cert_reqs = os.getenv("REDIS_SSL_CERT_REQS", "required").lower()

    options: Dict[str, Any] = {
        "host": host,
        "port": port,
        "db": db,
        "password": password or None,
        "decode_responses": True,
    }

    if ssl_enabled:
        options["ssl"] = True
        if cert_reqs in {"none", "false", "0"}:
            options["ssl_cert_reqs"] = None
        else:
            options["ssl_cert_reqs"] = "required"

    return options


async def get_redis() -> Optional[Redis]:
    """Return a shared Redis client or ``None`` when not configured."""

    global _redis_client

    if _redis_client is not None:
        return _redis_client

    options = _build_redis_options()
    if not options:
        return None

    try:
        if "url" in options:
            client = Redis.from_url(options["url"], decode_responses=True)
        else:
            client = Redis(**options)

        await client.ping()
    except RedisError:
        return None

    _redis_client = client
    return _redis_client


