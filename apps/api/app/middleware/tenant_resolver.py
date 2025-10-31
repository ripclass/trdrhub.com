"""
Tenant resolution middleware for multi-institution scoping.
"""

from typing import Callable, Awaitable, List, Optional

import sqlalchemy as sa
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.auth import get_current_user_from_token
from app.database import get_db
from app.models import BankTenant


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enriches the request state with bank and tenant scoping
    information derived from the authenticated user.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        request.state.bank_id = None
        request.state.tenant_ids: Optional[List[str]] = []
        request.state.user_roles: List[str] = []

        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else None

        session = None
        try:
            if token:
                session = next(get_db())
                user = await get_current_user_from_token(token, session)
                if user:
                    request.state.user_roles = [user.role]

                    # System admins operate globally; leave tenant_ids as None for later guards.
                    if user.is_system_admin():
                        request.state.tenant_ids = None
                        request.state.bank_id = None
                    elif user.is_bank_admin() or user.is_bank_officer():
                        request.state.bank_id = str(user.company_id) if user.company_id else None
                        request.state.tenant_ids = self._resolve_bank_tenants(session, user.company_id)
                    else:
                        request.state.tenant_ids = [str(user.company_id)] if user.company_id else []
        finally:
            if session is not None:
                session.close()

        return await call_next(request)

    @staticmethod
    def _resolve_bank_tenants(session, bank_company_id: Optional[str]) -> List[str]:
        if not bank_company_id:
            return []

        stmt = (
            sa.select(BankTenant.tenant_id)
            .where(BankTenant.bank_id == bank_company_id)
            .where(BankTenant.status == "active")
        )
        results = session.execute(stmt).all()
        return [str(row[0]) for row in results if row[0] is not None]
