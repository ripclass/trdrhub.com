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
from ..core.security import require_bank_or_admin, require_bank_admin
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
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
                "is_active": org.is_active,
                "sort_order": org.sort_order,
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


@router.put("/{org_id}", response_model=BankOrgRead)
def update_bank_org(
    org_id: UUID,
    org_data: BankOrgUpdate,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Update a bank organization.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        org = db.query(BankOrg).filter(
            BankOrg.id == org_id,
            BankOrg.bank_company_id == current_user.company_id
        ).first()
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Update fields
        if org_data.name is not None:
            org.name = org_data.name
        if org_data.code is not None:
            org.code = org_data.code
        if org_data.is_active is not None:
            org.is_active = org_data.is_active
        if org_data.sort_order is not None:
            org.sort_order = org_data.sort_order
        
        db.commit()
        db.refresh(org)
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.UPDATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id=str(org.id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "name": org.name,
                "code": org.code,
                "is_active": org.is_active,
            }
        )
        
        return BankOrgRead.model_validate(org)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_action(
            action=AuditAction.UPDATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id=str(org_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank_org(
    org_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Soft delete a bank organization.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        org = db.query(BankOrg).filter(
            BankOrg.id == org_id,
            BankOrg.bank_company_id == current_user.company_id,
            BankOrg.deleted_at.is_(None)
        ).first()
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Check for child orgs
        child_orgs = db.query(BankOrg).filter(
            BankOrg.parent_id == org_id,
            BankOrg.deleted_at.is_(None)
        ).count()
        
        if child_orgs > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete organization with child organizations"
            )
        
        # Soft delete
        from datetime import datetime
        org.deleted_at = datetime.utcnow()
        org.is_active = False
        
        db.commit()
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.DELETE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id=str(org.id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "name": org.name,
            }
        )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        audit_service.log_action(
            action=AuditAction.DELETE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_org",
            resource_id=str(org_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organization: {str(e)}"
        )

