"""CSRF protection middleware for FastAPI."""

import asyncio
import secrets
import time
from typing import Optional, Set, Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.exceptions import RedisError

from app.utils.redis_cache import get_redis
from app.utils.token_utils import create_signed_token, verify_signed_token


_LOCAL_TOKEN_STORE: Dict[str, float] = {}
_LOCAL_LOCK = asyncio.Lock()


def _nonce_key(nonce: str) -> str:
    return f"csrf:{nonce}"


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern.
    
    This middleware implements CSRF protection using the double-submit cookie pattern:
    - Token is stored in both cookie and header
    - Token must match in both places for state-changing requests
    - Tokens expire after configured time (default: 1 hour)
    """
    
    def __init__(
        self,
        app,
        *,
        secret_key: str,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exempt_paths: Optional[Set[str]] = None,
        exempt_methods: Optional[Set[str]] = None,
        token_expiry_seconds: int = 3600,  # 1 hour
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_paths = exempt_paths or set()
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}
        self.token_expiry_seconds = token_expiry_seconds
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    def _is_state_changing_method(self, method: str) -> bool:
        """Check if HTTP method modifies state."""
        return method not in self.exempt_methods
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF token."""
        path = request.url.path
        method = request.method
        
        # Skip CSRF check for exempt paths or methods
        if self._is_exempt_path(path) or not self._is_state_changing_method(method):
            return await call_next(request)
        
        # For state-changing methods, verify CSRF token
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)
        
        # Token must be present in both cookie and header
        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token missing. Please refresh the page and try again.",
                    "code": "csrf_token_missing"
                }
            )
        
        # Tokens must match
        if cookie_token != header_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token mismatch. Please refresh the page and try again.",
                    "code": "csrf_token_mismatch"
                }
            )
        
        try:
            payload = verify_signed_token(self.secret_key, cookie_token)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                    "code": "csrf_token_invalid"
                }
            )
        
        nonce = payload.get("nonce")
        if not nonce:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                    "code": "csrf_token_invalid"
                }
            )

        if not await _nonce_is_valid(nonce, self.token_expiry_seconds):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                    "code": "csrf_token_invalid"
                }
            )
        
        return await call_next(request)


async def generate_csrf_token(secret_key: str, expiry_seconds: int = 3600) -> tuple[str, dict]:
    """Generate a new CSRF token and return it with cookie settings."""

    nonce = secrets.token_urlsafe(16)
    token = create_signed_token(
        secret_key=secret_key,
        payload={"nonce": nonce},
        expires_in=expiry_seconds,
    )

    await _store_nonce(nonce, expiry_seconds)

    cookie_settings = {
        "key": "csrf_token",
        "value": token,
        "httponly": False,  # Must be readable by JavaScript for double-submit
        "samesite": "lax",
        "secure": True,  # HTTPS only in production
        "max_age": expiry_seconds,
    }
    
    return token, cookie_settings


async def _store_nonce(nonce: str, expiry_seconds: int) -> None:
    redis = await get_redis()
    if redis:
        try:
            await redis.setex(_nonce_key(nonce), expiry_seconds, "1")
            return
        except RedisError:
            pass

    async with _LOCAL_LOCK:
        _LOCAL_TOKEN_STORE[nonce] = time.time() + expiry_seconds


async def _nonce_is_valid(nonce: str, expiry_seconds: int) -> bool:
    redis = await get_redis()
    if redis:
        try:
            exists = await redis.exists(_nonce_key(nonce))
            if exists:
                await redis.expire(_nonce_key(nonce), expiry_seconds)
                return True
        except RedisError:
            pass

    async with _LOCAL_LOCK:
        expiry_at = _LOCAL_TOKEN_STORE.get(nonce)
        if not expiry_at or time.time() > expiry_at:
            _LOCAL_TOKEN_STORE.pop(nonce, None)
            return False
        _LOCAL_TOKEN_STORE[nonce] = time.time() + expiry_seconds
        return True
