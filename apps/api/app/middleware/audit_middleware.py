"""
Audit middleware for automatic request correlation and logging.
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from sqlalchemy.orm import Session

from ..database import get_db
from app.models import AuditAction, AuditResult
from ..services.audit_service import AuditService
from ..auth import get_current_user_from_token


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging and request correlation.

    Automatically logs all requests with correlation IDs and basic request info.
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/favicon.ico",
            "/health", "/ping", "/metrics"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add audit logging."""

        # Skip audit logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Store correlation ID in request state
        request.state.correlation_id = correlation_id

        # Extract client information
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log the request asynchronously (in background)
        await self.log_request(
            request=request,
            response=response,
            correlation_id=correlation_id,
            client_ip=client_ip,
            user_agent=user_agent,
            duration_ms=duration_ms
        )

        return response

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies."""
        # Check for X-Forwarded-For header (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check for X-Real-IP header (nginx proxy)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if hasattr(request.client, 'host'):
            return request.client.host

        return "unknown"

    async def log_request(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        client_ip: str,
        user_agent: Optional[str],
        duration_ms: int
    ):
        """Log the request to audit trail."""
        try:
            # Get database session
            db: Session = next(get_db())

            # Initialize audit service
            audit_service = AuditService(db)

            # Try to get current user from Authorization header
            user = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    user = await get_current_user_from_token(token, db)
                except Exception:
                    # Token might be invalid, that's okay
                    pass

            # Determine action based on endpoint and method
            action = self.determine_action(request)

            # Determine result based on status code
            result = self.determine_result(response.status_code)

            # Extract resource information from URL
            resource_type, resource_id, lc_number = self.extract_resource_info(request)

            # Prepare request data (sanitized)
            request_data = {
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "headers": dict(request.headers)
            }

            # Get session ID from cookies or headers
            session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")

            # Log the audit event
            audit_service.log_action(
                action=action,
                user=user,
                correlation_id=correlation_id,
                session_id=session_id,
                resource_type=resource_type,
                resource_id=resource_id,
                lc_number=lc_number,
                result=result,
                ip_address=client_ip,
                user_agent=user_agent,
                endpoint=str(request.url.path),
                http_method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_data=request_data,
                metadata={
                    "query_params": dict(request.query_params),
                    "path_params": getattr(request, 'path_params', {}),
                    "content_type": request.headers.get("content-type"),
                    "content_length": request.headers.get("content-length"),
                    "referer": request.headers.get("referer"),
                    "response_size": len(response.body) if hasattr(response, 'body') else None
                }
            )

            db.close()

        except Exception as e:
            # Don't let audit logging break the request
            print(f"Audit logging error: {e}")

    def determine_action(self, request: Request) -> str:
        """Determine audit action based on request."""
        path = request.url.path.lower()
        method = request.method.upper()

        # Map common endpoints to actions
        if "/upload" in path and method == "POST":
            return AuditAction.UPLOAD
        elif "/validate" in path and method == "POST":
            return AuditAction.VALIDATE
        elif "/download" in path and method == "GET":
            return AuditAction.DOWNLOAD
        elif "/versions" in path and method == "POST":
            return AuditAction.CREATE_VERSION
        elif "/versions" in path and "compare" in path and method == "GET":
            return AuditAction.COMPARE_VERSIONS
        elif "/versions" in path and method == "PUT":
            return AuditAction.UPDATE_VERSION
        elif "/auth/login" in path:
            return AuditAction.LOGIN
        elif "/auth/logout" in path:
            return AuditAction.LOGOUT
        elif method == "DELETE":
            return AuditAction.DELETE
        else:
            # Generic action based on HTTP method
            return f"{method.lower()}_request"

    def determine_result(self, status_code: int) -> str:
        """Determine result based on HTTP status code."""
        if 200 <= status_code < 300:
            return AuditResult.SUCCESS
        elif 400 <= status_code < 500:
            if status_code == 401 or status_code == 403:
                return AuditResult.FAILURE  # Authentication/authorization failure
            else:
                return AuditResult.ERROR  # Client error
        elif 500 <= status_code < 600:
            return AuditResult.ERROR  # Server error
        else:
            return AuditResult.PARTIAL  # Unknown status

    def extract_resource_info(self, request: Request) -> tuple:
        """Extract resource information from request URL."""
        path = request.url.path
        path_parts = path.strip("/").split("/")

        resource_type = None
        resource_id = None
        lc_number = None

        try:
            # Pattern: /lc/{lc_number}/versions/{version_id}
            if "lc" in path_parts:
                lc_index = path_parts.index("lc")
                if lc_index + 1 < len(path_parts):
                    lc_number = path_parts[lc_index + 1]
                    resource_type = "lc"

            # Pattern: /versions/{version_id}
            if "versions" in path_parts:
                version_index = path_parts.index("versions")
                if version_index + 1 < len(path_parts):
                    resource_id = path_parts[version_index + 1]
                    resource_type = "lc_version"

            # Pattern: /upload/{session_id}
            if "upload" in path_parts:
                upload_index = path_parts.index("upload")
                if upload_index + 1 < len(path_parts):
                    resource_id = path_parts[upload_index + 1]
                    resource_type = "upload_session"

            # Pattern: /validation/{session_id}
            if "validation" in path_parts:
                validation_index = path_parts.index("validation")
                if validation_index + 1 < len(path_parts):
                    resource_id = path_parts[validation_index + 1]
                    resource_type = "validation_session"

            # Pattern: /users/{user_id}
            if "users" in path_parts:
                users_index = path_parts.index("users")
                if users_index + 1 < len(path_parts):
                    resource_id = path_parts[users_index + 1]
                    resource_type = "user"

        except (ValueError, IndexError):
            # Couldn't parse path, that's okay
            pass

        return resource_type, resource_id, lc_number


class AuditContextMiddleware(BaseHTTPMiddleware):
    """
    Lighter middleware that just adds correlation context without full logging.

    Use this if you want correlation IDs but handle audit logging manually.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add correlation context to request."""
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, 'correlation_id', str(uuid.uuid4()))


def create_audit_context(request: Request) -> dict:
    """Create audit context dictionary from request."""
    return {
        'correlation_id': get_correlation_id(request),
        'ip_address': request.client.host if hasattr(request.client, 'host') else None,
        'user_agent': request.headers.get('user-agent'),
        'endpoint': str(request.url.path),
        'http_method': request.method,
        'session_id': request.cookies.get('session_id') or request.headers.get('X-Session-ID')
    }