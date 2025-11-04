"""Bank-specific rate limiting decorator for sensitive operations."""

from functools import wraps
from typing import Callable
from fastapi import Request, HTTPException, status
from collections import defaultdict, deque
import time
import asyncio


# In-memory rate limiters for bank operations
_bank_rate_limiters = {
    "upload": defaultdict(lambda: deque()),  # File uploads: 10 per minute
    "export": defaultdict(lambda: deque()),  # Exports: 20 per minute
    "api": defaultdict(lambda: deque()),     # General API: 60 per minute
}

_rate_limit_locks: dict[tuple[str, str], asyncio.Lock] = {}


async def _check_rate_limit(limiter_key: str, user_id: str, limit: int, window_seconds: int) -> bool:
    """Check if user is within rate limit."""
    bucket = _bank_rate_limiters[limiter_key][user_id]
    now = time.monotonic()
    
    # Remove old entries outside window
    while bucket and (now - bucket[0]) > window_seconds:
        bucket.popleft()
    
    if len(bucket) >= limit:
        return False
    
    bucket.append(now)
    return True


def bank_rate_limit(
    limiter_type: str = "api",
    limit: int = 60,
    window_seconds: int = 60,
    error_message: str = "Rate limit exceeded. Please try again later."
):
    """Decorator for bank endpoint rate limiting.
    
    Args:
        limiter_type: Type of limiter ("upload", "export", "api")
        limit: Maximum requests per window
        window_seconds: Time window in seconds
        error_message: Custom error message
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs or args
            current_user = None
            for arg in args:
                if hasattr(arg, 'id') and hasattr(arg, 'role'):
                    current_user = arg
                    break
            
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                # If no user found, skip rate limiting (shouldn't happen with auth)
                return await func(*args, **kwargs)
            
            user_id = str(current_user.id)
            
            # Check rate limit with per-user lock
            lock_key = (limiter_type, user_id)
            lock = _rate_limit_locks.setdefault(lock_key, asyncio.Lock())
            async with lock:
                allowed = await _check_rate_limit(limiter_type, user_id, limit, window_seconds)
            
            if not allowed:
                retry_after = window_seconds
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message,
                    headers={"Retry-After": str(retry_after)},
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

