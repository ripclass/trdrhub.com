"""
Bank Organizations Router
CRUD operations for bank organizations and user org access
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bank_orgs import BankOrg, UserOrgAccess, OrgKind
from app.models import User
from app.routers.bank import require_bank_or_admin, require_bank_admin
from app.services.audit_service import AuditService
from app.utils.audit import create_audit_context
from app.models.audit_log import AuditAction, AuditResult
from app.schemas.bank_orgs import (
    BankOrgCreate, BankOrgRead, BankOrgUpdate,
    UserOrgAccessCreate, UserOrgAccessRead, UserOrgAccessUpdate,
    PaginatedBankOrgsResponse,
)

router = APIRouter(prefix="/bank/orgs", tags=["bank", "orgs"])


@router.post("", response_model=BankOrgRead, status_code=status.HTTP_201_CREATED)
def create_bank_org(
    org_data: BankOrgCreate,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Create a new bank organizational unit.
    Fix: Path is set AFTER insert to use the actual org.id
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Ensure the bank_company_id matches the current user's bank
        if str(org_data.bank_company_id) != str(current_user.company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create organization for another bank"
            )
        
        # Validate parent_id if provided
        parent_org = None
        if org_data.parent_id:
            parent_org = db.query(BankOrg).filter(
                BankOrg.id == org_data.parent_id,
                BankOrg.bank_company_id == current_user.company_id
            ).first()
            if not parent_org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent organization not found"
                )
        
        # Validate kind
        if org_data.kind not in [OrgKind.GROUP.value, OrgKind.REGION.value, OrgKind.BRANCH.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kind must be 'group', 'region', or 'branch'"
            )
        
        # Create org with temporary path (will be set after insert)
        new_org = BankOrg(
            bank_company_id=org_data.bank_company_id,
            parent_id=org_data.parent_id,
            kind=org_data.kind,
            name=org_data.name,
            code=org_data.code,
            path="",  # Temporary - will be set after insert
            level=org_data.level,
            sort_order=org_data.sort_order,
            is_active=org_data.is_active,
        )
        
        db.add(new_org)
        db.flush()  # Get the ID without committing
        
        # Now compute path using the actual id
        if parent_org:
            new_org.path = f"{parent_org.path}/{new_org.id}"
            new_org.level = parent_org.level + 1
        else:
            new_org.path = f"/{new_org.id}"
            new_org.level = 0
        
        db.commit()
        db.refresh(new_org)
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id=str(new_org.id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "name": new_org.name,
                "kind": new_org.kind,
                "code": new_org.code,
                "path": new_org.path,
            }
        )
        
        return BankOrgRead.model_validate(new_org)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id="failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )


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

