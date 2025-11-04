"""Lightweight in-memory rate limiting middleware for FastAPI."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette import status


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple IP-based rate limiter to provide baseline abuse protection.

    The middleware uses an in-memory sliding window counter and is designed to
    offer protection in single-instance deployments (e.g. stub/dev environments
    or low-volume production tiers). For horizontally scaled environments,
    replace this with a Redis-backed shared limiter.
    """

    def __init__(
        self,
        app,
        *,
        limit: int = 120,
        window_seconds: int = 60,
        exempt_paths: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(app)
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self.exempt_paths = tuple(exempt_paths or ())
        self._lock = asyncio.Lock()
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if self._is_exempt_path(path):
            return await call_next(request)

        client_host = getattr(request.client, "host", "anonymous")
        now = time.monotonic()

        async with self._lock:
            bucket = self._requests[client_host]
            # Drop timestamps outside of the sliding window
            while bucket and (now - bucket[0]) > self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.exempt_paths)

