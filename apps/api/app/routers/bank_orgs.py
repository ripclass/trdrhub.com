"""
Bank Organizations Router
CRUD operations for bank organizations and user org access
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bank_orgs import BankOrg, UserOrgAccess
from app.models import User
from app.routers.bank import require_bank_or_admin
from app.services.audit_service import AuditService
from app.utils.audit import create_audit_context
from app.models.audit_log import AuditAction, AuditResult

router = APIRouter(prefix="/bank/orgs", tags=["bank", "orgs"])


@router.get("", response_model=dict)
def list_user_orgs(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    List organizations accessible to the current user.
    Returns hierarchical org structure with user's access level.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # System admins can see all orgs
        if current_user.is_system_admin():
            orgs = db.query(BankOrg).all()
        # Bank admins can see all orgs in their bank
        elif current_user.is_bank_admin():
            bank_id = current_user.company_id
            if bank_id:
                orgs = db.query(BankOrg).filter(
                    BankOrg.bank_company_id == bank_id
                ).all()
            else:
                orgs = []
        # Bank officers can only see orgs they have access to
        elif current_user.is_bank_officer():
            bank_id = current_user.company_id
            if bank_id:
                # Get orgs via user_org_access
                orgs = db.query(BankOrg).join(UserOrgAccess).filter(
                    UserOrgAccess.user_id == current_user.id,
                    BankOrg.bank_company_id == bank_id
                ).all()
            else:
                orgs = []
        else:
            orgs = []
        
        # Format response
        result = []
        for org in orgs:
            # Get user's role in this org
            access = db.query(UserOrgAccess).filter(
                UserOrgAccess.user_id == current_user.id,
                UserOrgAccess.org_id == org.id
            ).first()
            
            # Calculate level from path depth
            level = len([p for p in org.path.split('/') if p]) - 1
            
            result.append({
                "id": str(org.id),
                "name": org.name,
                "code": org.code,
                "kind": org.kind,
                "path": org.path,
                "level": level,
                "role": access.role if access else ("admin" if current_user.is_bank_admin() else "viewer"),
            })
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_orgs",
            resource_id="list",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={"org_count": len(result)},
        )
        
        return {
            "total": len(result),
            "count": len(result),
            "results": result
        }
        
    except Exception as e:
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_orgs",
            resource_id="list",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizations: {str(e)}"
        )

