"""
Security headers middleware for FastAPI.

Adds security headers to all responses:
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Strict-Transport-Security (HSTS)
"""

from typing import Callable, Awaitable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Security headers help protect against common web vulnerabilities:
    - XSS attacks
    - Clickjacking
    - MIME type sniffing
    - Information leakage
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Content-Security-Policy: Prevent XSS and injection attacks
        # Allow same-origin, API endpoints, and common CDNs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for React/Vite
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
            "img-src 'self' data: https: https://*.vercel.sh https://via.placeholder.com; "  # Allow images from same origin, data URIs, HTTPS, Vercel domains, and placeholder images
            "font-src 'self' data:; "  # Allow fonts from same origin and data URIs
            "connect-src 'self' https://api.openai.com https://api.anthropic.com; "  # Allow API calls to AI providers
            "frame-ancestors 'none'; "  # Prevent embedding in frames (clickjacking protection)
            "base-uri 'self'; "  # Restrict base tag
            "form-action 'self'; "  # Restrict form submissions
        )
        
        # X-Frame-Options: Prevent clickjacking (redundant with CSP frame-ancestors but good for older browsers)
        x_frame_options = "DENY"
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        x_content_type_options = "nosniff"
        
        # X-XSS-Protection: Enable browser XSS filter (legacy, but still useful)
        x_xss_protection = "1; mode=block"
        
        # Referrer-Policy: Control referrer information leakage
        referrer_policy = "strict-origin-when-cross-origin"
        
        # Strict-Transport-Security (HSTS): Force HTTPS in production
        hsts = None
        if settings.is_production():
            hsts = "max-age=31536000; includeSubDomains; preload"  # 1 year
        
        # Add headers to response
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Frame-Options"] = x_frame_options
        response.headers["X-Content-Type-Options"] = x_content_type_options
        response.headers["X-XSS-Protection"] = x_xss_protection
        response.headers["Referrer-Policy"] = referrer_policy
        
        if hsts:
            response.headers["Strict-Transport-Security"] = hsts
        
        return response

