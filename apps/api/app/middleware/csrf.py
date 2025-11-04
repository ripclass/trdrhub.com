"""CSRF protection middleware for FastAPI."""

import secrets
import time
import asyncio
from typing import Optional, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern.
    
    This middleware implements CSRF protection using the double-submit cookie pattern:
    - Token is stored in both cookie and header
    - Token must match in both places for state-changing requests
    - Tokens expire after configured time (default: 1 hour)
    """
    
    # In-memory token storage (in production, use Redis or database)
    _token_store: dict[str, dict] = {}
    _lock: dict[str, asyncio.Lock] = {}
    
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
        
        # Cleanup expired tokens periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _should_cleanup(self) -> bool:
        """Check if cleanup is needed."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            return True
        return False
    
    def _cleanup_expired_tokens(self):
        """Remove expired tokens from store."""
        now = time.time()
        expired = [
            token for token, data in self._token_store.items()
            if now > data.get("expires_at", 0)
        ]
        for token in expired:
            del self._token_store[token]
    
    def _generate_token(self) -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(32)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    def _is_state_changing_method(self, method: str) -> bool:
        """Check if HTTP method modifies state."""
        return method not in self.exempt_methods
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF token."""
        
        # Cleanup expired tokens periodically
        if self._should_cleanup():
            self._cleanup_expired_tokens()
        
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
        
        # Verify token exists and hasn't expired (thread-safe)
        if cookie_token not in self._token_store:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                    "code": "csrf_token_invalid"
                }
            )
        
        # Use lock for thread-safe access
        if cookie_token not in self._lock:
            self._lock[cookie_token] = asyncio.Lock()
        
        async with self._lock[cookie_token]:
            token_data = self._token_store.get(cookie_token)
            if not token_data:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                        "code": "csrf_token_invalid"
                    }
                )
            
            if time.time() > token_data.get("expires_at", 0):
                del self._token_store[cookie_token]
                if cookie_token in self._lock:
                    del self._lock[cookie_token]
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "CSRF token expired. Please refresh the page and try again.",
                        "code": "csrf_token_expired"
                    }
                )
            
            # Token is valid, proceed with request
            response = await call_next(request)
            
            # Refresh token expiry on successful request
            token_data["expires_at"] = time.time() + self.token_expiry_seconds
        
        return response


def generate_csrf_token(secret_key: str, expiry_seconds: int = 3600) -> tuple[str, dict]:
    """Generate a new CSRF token and return it with cookie settings.
    
    Returns:
        tuple: (token_string, cookie_dict)
    """
    token = secrets.token_urlsafe(32)
    
    # Store token with expiry
    CSRFMiddleware._token_store[token] = {
        "expires_at": time.time() + expiry_seconds,
        "created_at": time.time()
    }
    
    cookie_settings = {
        "key": "csrf_token",
        "value": token,
        "httponly": False,  # Must be readable by JavaScript for double-submit
        "samesite": "lax",
        "secure": True,  # HTTPS only in production
        "max_age": expiry_seconds,
    }
    
    return token, cookie_settings

