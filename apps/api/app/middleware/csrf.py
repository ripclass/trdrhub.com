"""CSRF protection middleware for FastAPI."""

import secrets
from typing import Optional, Set
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.token_utils import create_signed_token, verify_signed_token


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
            verify_signed_token(self.secret_key, cookie_token)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid or expired. Please refresh the page and try again.",
                    "code": "csrf_token_invalid"
                }
            )
        
        return await call_next(request)


def generate_csrf_token(secret_key: str, expiry_seconds: int = 3600) -> tuple[str, dict]:
    """Generate a new CSRF token and return it with cookie settings."""

    token = create_signed_token(
        secret_key=secret_key,
        payload={"nonce": secrets.token_urlsafe(16)},
        expires_in=expiry_seconds,
    )

    cookie_settings = {
        "key": "csrf_token",
        "value": token,
        "httponly": False,  # Must be readable by JavaScript for double-submit
        "samesite": "lax",
        "secure": True,  # HTTPS only in production
        "max_age": expiry_seconds,
    }
    
    return token, cookie_settings

