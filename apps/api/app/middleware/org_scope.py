"""
Organization Scope Middleware
Resolves and validates org_id from request for multi-org switching
"""
from typing import Callable, Awaitable, Optional
from uuid import UUID

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import sqlalchemy as sa

from app.auth import get_current_user_from_token
from app.database import get_db
from app.models.bank_orgs import BankOrg, UserOrgAccess
from app.models import User


class OrgScopeMiddleware(BaseHTTPMiddleware):
    """
    Middleware that resolves org_id from request and validates user access.
    
    Behavior:
    - Reads 'org' query param or 'X-Org-Id' header
    - Validates user has access to the org (or is admin)
    - Sets request.state.org_id (None means "All Orgs" for admins)
    - Bank admins can access any org or "All Orgs" (None)
    - Bank officers must have explicit access via user_org_access
    """
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        # Initialize org_id as None (All Orgs)
        request.state.org_id = None
        
        # Only process bank endpoints
        if not request.url.path.startswith("/bank"):
            return await call_next(request)
        
        # Get org from query param or header
        org_param = request.query_params.get("org")
        org_header = request.headers.get("X-Org-Id")
        org_id_str = org_param or org_header
        
        # If no org specified, leave as None (All Orgs for admins)
        if not org_id_str:
            return await call_next(request)
        
        # Parse org_id
        try:
            org_id = UUID(org_id_str)
        except ValueError:
            # Invalid UUID format - ignore and continue with None
            return await call_next(request)
        
        # Get authenticated user
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else None
        
        if not token:
            # No auth - leave org_id as None
            return await call_next(request)
        
        session = None
        try:
            session = next(get_db())
            user = await get_current_user_from_token(token, session)
            
            if not user:
                # Not authenticated - leave org_id as None
                return await call_next(request)
            
            # System admins can access any org or All Orgs
            if user.is_system_admin():
                request.state.org_id = str(org_id)
                return await call_next(request)
            
            # Bank admins can access any org within their bank
            if user.is_bank_admin():
                bank_id = user.company_id
                if bank_id:
                    # Verify org belongs to this bank
                    org = session.query(BankOrg).filter(
                        BankOrg.id == org_id,
                        BankOrg.bank_company_id == bank_id,
                        BankOrg.deleted_at.is_(None),
                        BankOrg.is_active == True
                    ).first()
                    
                    if org:
                        request.state.org_id = str(org_id)
                    # If org not found, leave as None (All Orgs)
                return await call_next(request)
            
            # Bank officers must have explicit access
            if user.is_bank_officer():
                bank_id = user.company_id
                if bank_id:
                    # Check user_org_access
                    access = session.query(UserOrgAccess).join(BankOrg).filter(
                        UserOrgAccess.user_id == user.id,
                        UserOrgAccess.org_id == org_id,
                        BankOrg.bank_company_id == bank_id,
                        BankOrg.deleted_at.is_(None),
                        BankOrg.is_active == True
                    ).first()
                    
                    if access:
                        request.state.org_id = str(org_id)
                    else:
                        # No access - raise 403 or leave as None?
                        # For now, leave as None to allow "All Orgs" fallback
                        # Individual endpoints can enforce stricter checks
                        pass
            
            # Non-bank users don't get org scoping
            return await call_next(request)
            
        except Exception as e:
            # On error, log but don't block request
            # Individual endpoints can handle missing org_id
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error resolving org scope: {e}")
            return await call_next(request)
        finally:
            if session is not None:
                session.close()

