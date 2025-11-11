"""
Bank Saved Views API endpoints for managing filter presets.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..core.security import require_bank_or_admin
from ..models import User, SavedView
from ..schemas.saved_view import (
    SavedViewCreate, SavedViewUpdate, SavedViewRead, SavedViewListResponse
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank/saved-views", tags=["bank-saved-views"])


@router.post("", response_model=SavedViewRead, status_code=status.HTTP_201_CREATED)
def create_saved_view(
    view_data: SavedViewCreate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None,
):
    """Create a new saved view."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Validate resource type
        if view_data.resource not in ['results', 'jobs', 'evidence']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource must be 'results', 'jobs', or 'evidence'"
            )
        
        # If setting as org default, unset other org defaults for this resource
        if view_data.is_org_default:
            db.query(SavedView).filter(
                SavedView.company_id == current_user.company_id,
                SavedView.resource == view_data.resource,
                SavedView.is_org_default == True
            ).update({"is_org_default": False})
        
        # Include org in query_params if present in request
        query_params_dict = view_data.query_params.copy() if view_data.query_params else {}
        org_id = getattr(request.state, "org_id", None) if request else None
        if org_id:
            query_params_dict['org'] = org_id
        
        # Create new saved view
        saved_view = SavedView(
            company_id=current_user.company_id,
            owner_id=current_user.id,
            name=view_data.name,
            resource=view_data.resource,
            query_params=query_params_dict,
            columns=view_data.columns,
            is_org_default=view_data.is_org_default,
            shared=view_data.shared,
        )
        
        db.add(saved_view)
        db.commit()
        db.refresh(saved_view)
        
        # Log creation
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="saved_view",
            resource_id=str(saved_view.id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "name": saved_view.name,
                "resource": saved_view.resource,
                "is_org_default": saved_view.is_org_default,
                "shared": saved_view.shared,
            }
        )
        
        # Build response with owner name
        response = SavedViewRead(
            id=saved_view.id,
            company_id=saved_view.company_id,
            owner_id=saved_view.owner_id,
            owner_name=current_user.full_name,
            name=saved_view.name,
            resource=saved_view.resource,
            query_params=saved_view.query_params,
            columns=saved_view.columns,
            is_org_default=saved_view.is_org_default,
            shared=saved_view.shared,
            created_at=saved_view.created_at,
            updated_at=saved_view.updated_at,
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create saved view: {e}", exc_info=True)
        db.rollback()
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="saved_view",
            resource_id="failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create saved view: {str(e)}"
        )


@router.get("", response_model=SavedViewListResponse)
def list_saved_views(
    resource: Optional[str] = Query(None, description="Filter by resource type"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None,
):
    """List saved views for the current user's company."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        query = db.query(SavedView).filter(
            SavedView.company_id == current_user.company_id
        )
        
        # Filter by resource if provided
        if resource:
            if resource not in ['results', 'jobs', 'evidence']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Resource must be 'results', 'jobs', or 'evidence'"
                )
            query = query.filter(SavedView.resource == resource)
        
        # Show user's own views and shared views
        query = query.filter(
            or_(
                SavedView.owner_id == current_user.id,
                SavedView.shared == True
            )
        )
        
        # Order by org default first, then by name
        views = query.order_by(
            SavedView.is_org_default.desc(),
            SavedView.name.asc()
        ).all()
        
        # Build response with owner names
        view_reads = []
        for view in views:
            owner = db.query(User).filter(User.id == view.owner_id).first()
            view_reads.append(SavedViewRead(
                id=view.id,
                company_id=view.company_id,
                owner_id=view.owner_id,
                owner_name=owner.full_name if owner else None,
                name=view.name,
                resource=view.resource,
                query_params=view.query_params,
                columns=view.columns,
                is_org_default=view.is_org_default,
                shared=view.shared,
                created_at=view.created_at,
                updated_at=view.updated_at,
            ))
        
        return SavedViewListResponse(
            total=len(view_reads),
            count=len(view_reads),
            views=view_reads,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list saved views: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list saved views: {str(e)}"
        )


@router.get("/default", response_model=Optional[SavedViewRead])
def get_default_view(
    resource: str = Query(..., description="Resource type"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None,
):
    """Get the organization default view for a resource."""
    if resource not in ['results', 'jobs', 'evidence']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource must be 'results', 'jobs', or 'evidence'"
        )
    
    view = db.query(SavedView).filter(
        SavedView.company_id == current_user.company_id,
        SavedView.resource == resource,
        SavedView.is_org_default == True
    ).first()
    
    if not view:
        return None
    
    owner = db.query(User).filter(User.id == view.owner_id).first()
    return SavedViewRead(
        id=view.id,
        company_id=view.company_id,
        owner_id=view.owner_id,
        owner_name=owner.full_name if owner else None,
        name=view.name,
        resource=view.resource,
        query_params=view.query_params,
        columns=view.columns,
        is_org_default=view.is_org_default,
        shared=view.shared,
        created_at=view.created_at,
        updated_at=view.updated_at,
    )


@router.put("/{view_id}", response_model=SavedViewRead)
def update_saved_view(
    view_id: UUID,
    view_data: SavedViewUpdate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None,
):
    """Update a saved view."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        view = db.query(SavedView).filter(
            SavedView.id == view_id,
            SavedView.company_id == current_user.company_id
        ).first()
        
        if not view:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved view not found"
            )
        
        # Check ownership or shared access
        if view.owner_id != current_user.id and not view.shared:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own views or shared views"
            )
        
        # Update fields
        if view_data.name is not None:
            view.name = view_data.name
        if view_data.query_params is not None:
            view.query_params = view_data.query_params
        if view_data.columns is not None:
            view.columns = view_data.columns
        if view_data.is_org_default is not None:
            # If setting as org default, unset other org defaults
            if view_data.is_org_default:
                db.query(SavedView).filter(
                    SavedView.company_id == current_user.company_id,
                    SavedView.resource == view.resource,
                    SavedView.id != view.id,
                    SavedView.is_org_default == True
                ).update({"is_org_default": False})
            view.is_org_default = view_data.is_org_default
        if view_data.shared is not None:
            # Only owner can change shared status
            if view.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the owner can change shared status"
                )
            view.shared = view_data.shared
        
        db.commit()
        db.refresh(view)
        
        # Log update
        audit_service.log_action(
            action=AuditAction.UPDATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="saved_view",
            resource_id=str(view.id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
        )
        
        owner = db.query(User).filter(User.id == view.owner_id).first()
        return SavedViewRead(
            id=view.id,
            company_id=view.company_id,
            owner_id=view.owner_id,
            owner_name=owner.full_name if owner else None,
            name=view.name,
            resource=view.resource,
            query_params=view.query_params,
            columns=view.columns,
            is_org_default=view.is_org_default,
            shared=view.shared,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update saved view: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update saved view: {str(e)}"
        )


@router.delete("/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_view(
    view_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None,
):
    """Delete a saved view."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        view = db.query(SavedView).filter(
            SavedView.id == view_id,
            SavedView.company_id == current_user.company_id
        ).first()
        
        if not view:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved view not found"
            )
        
        # Only owner can delete
        if view.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own views"
            )
        
        db.delete(view)
        db.commit()
        
        # Log deletion
        audit_service.log_action(
            action=AuditAction.DELETE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="saved_view",
            resource_id=str(view_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
        )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete saved view: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete saved view: {str(e)}"
        )

