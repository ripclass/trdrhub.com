"""
Locale Middleware
Reads Accept-Language header and attaches locale to request state
"""
from typing import Callable, Awaitable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Middleware that reads Accept-Language header and attaches locale to request state.
    
    Behavior:
    - Reads Accept-Language header or 'lang' query param
    - Validates against supported locales (en, bn)
    - Sets request.state.locale (defaults to 'en')
    - Passes locale to AI endpoints, exports, and audit logs
    """
    
    SUPPORTED_LOCALES = ['en', 'bn']
    DEFAULT_LOCALE = 'en'
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        # Initialize locale as default
        request.state.locale = self.DEFAULT_LOCALE
        
        # Check query param first (takes precedence)
        lang_param = request.query_params.get('lang')
        if lang_param and lang_param in self.SUPPORTED_LOCALES:
            request.state.locale = lang_param
            return await call_next(request)
        
        # Check Accept-Language header
        accept_language = request.headers.get('Accept-Language', '')
        if accept_language:
            # Parse Accept-Language header (e.g., "en-US,en;q=0.9,bn;q=0.8")
            # Extract first supported locale
            for part in accept_language.split(','):
                lang = part.split(';')[0].strip().lower()
                # Extract base language (e.g., "en" from "en-US")
                base_lang = lang.split('-')[0]
                if base_lang in self.SUPPORTED_LOCALES:
                    request.state.locale = base_lang
                    break
        
        return await call_next(request)

