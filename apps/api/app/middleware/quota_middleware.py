"""
Quota enforcement middleware for LCopilot API.

This middleware automatically enforces quota limits on validation operations
by intercepting requests to validation endpoints and checking quota before
allowing the operation to proceed.
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import get_db
from app.services.billing_service import BillingService, QuotaExceededException, BillingServiceError
from app.core.pricing import BillingAction
from app.models.user import User


class QuotaEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce quota limits on LC validation operations.

    This middleware:
    1. Intercepts requests to validation endpoints
    2. Extracts company_id from authenticated user
    3. Checks quota limits before allowing operation
    4. Records usage after successful operation
    5. Returns quota exceeded errors when limits are hit
    """

    # Endpoints that require quota checking
    QUOTA_ENDPOINTS = {
        "/sessions/*/process": BillingAction.PER_CHECK.value,
        "/sessions/*/import-draft": BillingAction.IMPORT_DRAFT.value,
        "/sessions/*/import-bundle": BillingAction.IMPORT_BUNDLE.value,
        "/documents/*/validate": BillingAction.PER_CHECK.value,
    }

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce quota if needed.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from next handler or quota error
        """
        # Check if this endpoint requires quota enforcement
        action = self._get_billing_action(request)

        if not action:
            # No quota enforcement needed, proceed normally
            return await call_next(request)

        # Get user and company from request context
        user = await self._get_current_user(request)
        if not user or not user.company_id:
            # No authenticated user or company, proceed normally
            # (auth will be handled by endpoint decorators)
            return await call_next(request)

        # Enforce quota before processing request
        try:
            db = next(get_db())
            billing_service = BillingService(db)

            # Check quota limit
            quota_allowed = billing_service.enforce_quota(user.company_id, action)

            if not quota_allowed:
                return await self._quota_exceeded_response(user.company_id, action, billing_service)

            # Quota check passed, process the request
            response = await call_next(request)

            # Record usage after successful operation (only for 2xx responses)
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    billing_service.record_usage(
                        company_id=user.company_id,
                        action=action,
                        user_id=user.id,
                        session_id=self._extract_session_id(request)
                    )
                except Exception as e:
                    # Log but don't fail the request for usage recording errors
                    print(f"Failed to record usage: {e}")

            db.close()
            return response

        except QuotaExceededException as e:
            return await self._quota_exceeded_response(user.company_id, action, billing_service, e)

        except BillingServiceError as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Billing service error",
                    "error_code": "BILLING_ERROR",
                    "message": str(e)
                }
            )

        except Exception as e:
            # For any other errors, log and proceed (don't break the request)
            print(f"Quota middleware error: {e}")
            return await call_next(request)

    def _get_billing_action(self, request: Request) -> Optional[str]:
        """
        Determine if request path requires quota enforcement.

        Args:
            request: FastAPI request

        Returns:
            Billing action string or None if no quota needed
        """
        path = request.url.path
        method = request.method.upper()

        # Only check POST/PUT operations (read operations don't use quota)
        if method not in ["POST", "PUT", "PATCH"]:
            return None

        # Check against configured quota endpoints
        for endpoint_pattern, action in self.QUOTA_ENDPOINTS.items():
            if self._path_matches_pattern(path, endpoint_pattern):
                return action

        return None

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if request path matches quota enforcement pattern.

        Args:
            path: Request path
            pattern: Pattern with * wildcards

        Returns:
            True if path matches pattern
        """
        # Convert pattern to regex-like matching
        # For now, simple wildcard matching
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")

        if len(pattern_parts) != len(path_parts):
            return False

        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part == "*":
                continue  # Wildcard matches anything
            if pattern_part != path_part:
                return False

        return True

    async def _get_current_user(self, request: Request) -> Optional[User]:
        """
        Extract current user from request context.

        This assumes the user has been set by authentication middleware.

        Args:
            request: FastAPI request

        Returns:
            User object or None
        """
        try:
            # Check if user was set by auth middleware
            if hasattr(request.state, 'user'):
                return request.state.user

            # Alternative: try to get from dependency injection context
            # This might need adjustment based on your auth implementation
            return None

        except Exception:
            return None

    def _extract_session_id(self, request: Request) -> Optional[uuid.UUID]:
        """
        Extract session ID from request path for usage recording.

        Args:
            request: FastAPI request

        Returns:
            Session UUID or None
        """
        try:
            path_parts = request.url.path.split("/")

            # Look for sessions/{id} pattern
            if "sessions" in path_parts:
                session_index = path_parts.index("sessions")
                if session_index + 1 < len(path_parts):
                    session_id_str = path_parts[session_index + 1]
                    return uuid.UUID(session_id_str)

            return None

        except (ValueError, IndexError):
            return None

    async def _quota_exceeded_response(
        self,
        company_id: uuid.UUID,
        action: str,
        billing_service: BillingService,
        exception: Optional[QuotaExceededException] = None
    ) -> JSONResponse:
        """
        Create quota exceeded error response.

        Args:
            company_id: Company ID
            action: Billing action
            billing_service: Billing service instance
            exception: Optional quota exception with details

        Returns:
            JSON error response
        """
        try:
            # Get current quota status
            quota_status = billing_service.get_quota_status(company_id)
            action_quota = quota_status.get("quotas", {}).get(action, {})

            company_info = billing_service.get_company_billing_info(company_id)

            error_detail = {
                "detail": "Quota limit exceeded",
                "error_code": "QUOTA_EXCEEDED",
                "action": action,
                "quota_info": {
                    "used": action_quota.get("used", 0),
                    "limit": action_quota.get("limit", 0),
                    "remaining": action_quota.get("remaining", 0),
                    "percentage_used": action_quota.get("percentage_used", 100)
                },
                "company": {
                    "id": str(company_id),
                    "name": company_info.get("name", ""),
                    "plan": company_info.get("plan", "").value if company_info.get("plan") else ""
                },
                "upgrade_info": {
                    "message": "Consider upgrading your plan to increase quota limits",
                    "contact_email": "billing@lcopilot.com"
                }
            }

            if exception:
                error_detail["quota_info"].update({
                    "current_usage": exception.current_usage,
                    "quota_limit": exception.quota_limit
                })

        except Exception as e:
            # Fallback error response if quota status retrieval fails
            error_detail = {
                "detail": "Quota limit exceeded",
                "error_code": "QUOTA_EXCEEDED",
                "action": action,
                "message": "Your quota limit has been reached. Please upgrade your plan or wait for your quota to reset.",
                "contact_email": "billing@lcopilot.com"
            }

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_detail
        )


# Helper functions for manual quota checks (if needed)

def check_quota_manually(company_id: uuid.UUID, action: str) -> bool:
    """
    Manual quota check function for use in endpoints.

    Args:
        company_id: Company ID
        action: Billing action

    Returns:
        True if quota allows action

    Raises:
        QuotaExceededException: If quota exceeded
    """
    db = next(get_db())
    billing_service = BillingService(db)

    try:
        result = billing_service.enforce_quota(company_id, action)
        db.close()
        return result
    except Exception:
        db.close()
        raise


def record_usage_manually(
    company_id: uuid.UUID,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    session_id: Optional[uuid.UUID] = None
) -> None:
    """
    Manual usage recording function for use in endpoints.

    Args:
        company_id: Company ID
        action: Billing action
        user_id: Optional user ID
        session_id: Optional session ID
    """
    db = next(get_db())
    billing_service = BillingService(db)

    try:
        billing_service.record_usage(
            company_id=company_id,
            action=action,
            user_id=user_id,
            session_id=session_id
        )
        db.close()
    except Exception as e:
        db.close()
        # Log the error but don't raise (usage recording shouldn't break the request)
        print(f"Failed to record usage manually: {e}")


# Quota check decorator for endpoints
def requires_quota(action: str):
    """
    Decorator to enforce quota on specific endpoint functions.

    Usage:
        @requires_quota(BillingAction.PER_CHECK.value)
        def validate_lc(session_id: str, current_user: User = Depends(get_current_user)):
            # endpoint logic

    Args:
        action: Billing action string

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract user from kwargs (assumes current_user is a parameter)
            current_user = kwargs.get('current_user')
            if current_user and current_user.company_id:
                check_quota_manually(current_user.company_id, action)

            # Execute the original function
            result = func(*args, **kwargs)

            # Record usage after successful execution
            if current_user and current_user.company_id:
                session_id = kwargs.get('session_id')
                if isinstance(session_id, str):
                    try:
                        session_uuid = uuid.UUID(session_id)
                    except ValueError:
                        session_uuid = None
                else:
                    session_uuid = session_id

                record_usage_manually(
                    company_id=current_user.company_id,
                    action=action,
                    user_id=current_user.id,
                    session_id=session_uuid
                )

            return result

        return wrapper
    return decorator