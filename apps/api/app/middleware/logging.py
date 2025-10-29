"""
Request ID middleware for tracking requests across the application.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from ..utils.logger import get_logger, log_api_request, log_exception


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to every request.

    Features:
    - Generates UUID4 for each request
    - Preserves client-provided X-Request-ID if present
    - Adds request ID to response headers
    - Injects request ID into log context
    - Logs request/response with timing
    """

    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
        self.logger = get_logger("request_middleware")

    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request and add request ID context."""

        # Start timing
        start_time = time.time()

        # Generate or extract request ID
        request_id = self._get_or_generate_request_id(request)

        # Bind request ID to logger context
        request_logger = get_logger("api_request", request_id=request_id)

        # Add request ID to request state for access in endpoints
        request.state.request_id = request_id
        request.state.logger = request_logger

        # Log incoming request
        request_logger.info(
            "Request received",
            http_method=request.method,
            http_path=str(request.url.path),
            http_query=str(request.url.query) if request.url.query else None,
            user_agent=request.headers.get("user-agent"),
            client_ip=self._get_client_ip(request),
            content_length=request.headers.get("content-length"),
        )

        response = None
        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response
            log_api_request(
                request_logger,
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms,
                response_size=response.headers.get("content-length"),
            )

            # Add request ID to response headers
            response.headers[self.header_name] = request_id

            return response

        except Exception as exc:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000

            # Log exception
            log_exception(
                request_logger,
                exc,
                http_method=request.method,
                http_path=str(request.url.path),
                request_duration_ms=duration_ms,
            )

            # Create error response if none exists
            if response is None:
                from fastapi.responses import JSONResponse
                response = JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error", "request_id": request_id},
                    headers={self.header_name: request_id}
                )

            # Log error response
            log_api_request(
                request_logger,
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                duration_ms=duration_ms,
            )

            # Re-raise the exception to let FastAPI handle it
            raise exc

    def _get_or_generate_request_id(self, request: Request) -> str:
        """Get request ID from header or generate new one."""

        # Check if client provided request ID
        client_request_id = request.headers.get(self.header_name)

        if client_request_id:
            # Validate that it looks like a UUID (basic validation)
            try:
                uuid.UUID(client_request_id)
                return client_request_id
            except ValueError:
                # Invalid UUID, generate new one
                pass

        # Generate new request ID
        return str(uuid.uuid4())

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxy headers."""

        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides request context utilities.

    This middleware runs after RequestIDMiddleware and provides
    additional utilities for accessing request context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Add context utilities to request."""

        # Add helper functions to request state
        request.state.get_logger = lambda name=None: get_logger(
            name=name,
            request_id=getattr(request.state, "request_id", None)
        )

        return await call_next(request)


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_request_logger(request: Request, name: str = None):
    """Get logger with request context."""
    request_id = get_request_id(request)
    return get_logger(name=name, request_id=request_id)