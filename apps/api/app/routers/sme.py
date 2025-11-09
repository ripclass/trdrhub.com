"""
SME Workspace API endpoints for LC Workspace, Drafts, and Amendments.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, ValidationSession, UserRole
from ..models.sme_workspace import (
    LCWorkspace, Draft, Amendment,
    DraftStatus, AmendmentStatus, DocumentChecklistStatus
)
from ..schemas.sme_workspace import (
    LCWorkspaceCreate, LCWorkspaceUpdate, LCWorkspaceRead, LCWorkspaceListResponse,
    DraftCreate, DraftUpdate, DraftRead, DraftListResponse, DraftPromoteRequest,
    AmendmentCreate, AmendmentUpdate, AmendmentRead, AmendmentListResponse, AmendmentDiffResponse,
    DocumentChecklistItem, DraftFileMetadata
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sme", tags=["sme-workspace"])


def require_sme_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an SME (exporter or importer)."""
    if current_user.role not in [UserRole.EXPORTER, UserRole.IMPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for SME users (exporter/importer)"
        )
    return current_user


# ===== LC Workspace Endpoints =====

@router.post("/lc-workspaces", response_model=LCWorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_lc_workspace(
    workspace_data: LCWorkspaceCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new LC Workspace."""
    try:
        # Check if workspace already exists for this LC and user
        existing = db.query(LCWorkspace).filter(
            and_(
                LCWorkspace.lc_number == workspace_data.lc_number,
                LCWorkspace.user_id == current_user.id,
                LCWorkspace.deleted_at.is_(None),
                LCWorkspace.is_active == True
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Active workspace already exists for LC {workspace_data.lc_number}"
            )
        
        # Calculate completion percentage
        checklist = workspace_data.document_checklist or []
        completed = sum(1 for item in checklist if item.status != DocumentChecklistStatus.MISSING)
        total = len(checklist) if checklist else 1
        completion = int((completed / total) * 100) if total > 0 else 0
        
        workspace = LCWorkspace(
            lc_number=workspace_data.lc_number,
            user_id=current_user.id,
            company_id=current_user.company_id,
            client_name=workspace_data.client_name,
            description=workspace_data.description,
            document_checklist=[item.dict() for item in checklist],
            completion_percentage=completion,
            is_active=True
        )
        
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(request) if request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="lc_workspace",
            resource_id=str(workspace.id),
            lc_number=workspace_data.lc_number,
            result=AuditResult.SUCCESS
        )
        
        return LCWorkspaceRead.model_validate(workspace)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create LC workspace: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create LC workspace"
        )


@router.get("/lc-workspaces", response_model=LCWorkspaceListResponse)
async def list_lc_workspaces(
    lc_number: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List LC Workspaces for the current user."""
    query = db.query(LCWorkspace).filter(
        and_(
            LCWorkspace.user_id == current_user.id,
            LCWorkspace.deleted_at.is_(None)
        )
    )
    
    if lc_number:
        query = query.filter(LCWorkspace.lc_number.ilike(f"%{lc_number}%"))
    
    if active_only:
        query = query.filter(LCWorkspace.is_active == True)
    
    total = query.count()
    items = query.order_by(LCWorkspace.updated_at.desc()).offset(skip).limit(limit).all()
    
    return LCWorkspaceListResponse(
        total=total,
        items=[LCWorkspaceRead.model_validate(item) for item in items]
    )


@router.get("/lc-workspaces/{workspace_id}", response_model=LCWorkspaceRead)
async def get_lc_workspace(
    workspace_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific LC Workspace."""
    workspace = db.query(LCWorkspace).filter(
        and_(
            LCWorkspace.id == workspace_id,
            LCWorkspace.user_id == current_user.id,
            LCWorkspace.deleted_at.is_(None)
        )
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LC Workspace not found"
        )
    
    return LCWorkspaceRead.model_validate(workspace)


@router.patch("/lc-workspaces/{workspace_id}", response_model=LCWorkspaceRead)
async def update_lc_workspace(
    workspace_id: UUID,
    workspace_data: LCWorkspaceUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Update an LC Workspace."""
    workspace = db.query(LCWorkspace).filter(
        and_(
            LCWorkspace.id == workspace_id,
            LCWorkspace.user_id == current_user.id,
            LCWorkspace.deleted_at.is_(None)
        )
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LC Workspace not found"
        )
    
    # Update fields
    if workspace_data.client_name is not None:
        workspace.client_name = workspace_data.client_name
    if workspace_data.description is not None:
        workspace.description = workspace_data.description
    if workspace_data.document_checklist is not None:
        workspace.document_checklist = [item.dict() for item in workspace_data.document_checklist]
        # Recalculate completion
        completed = sum(1 for item in workspace_data.document_checklist if item.status != DocumentChecklistStatus.MISSING)
        total = len(workspace_data.document_checklist) if workspace_data.document_checklist else 1
        workspace.completion_percentage = int((completed / total) * 100) if total > 0 else 0
    
    db.commit()
    db.refresh(workspace)
    
    return LCWorkspaceRead.model_validate(workspace)


# ===== Draft Endpoints =====

@router.post("/drafts", response_model=DraftRead, status_code=status.HTTP_201_CREATED)
async def create_draft(
    draft_data: DraftCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new Draft."""
    try:
        draft = Draft(
            lc_number=draft_data.lc_number,
            user_id=current_user.id,
            company_id=current_user.company_id,
            client_name=draft_data.client_name,
            draft_type=draft_data.draft_type,
            status=DraftStatus.DRAFT,
            uploaded_docs=[doc.dict() for doc in draft_data.uploaded_docs],
            notes=draft_data.notes,
            metadata=draft_data.metadata or {}
        )
        
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return DraftRead.model_validate(draft)
    except Exception as e:
        logger.error(f"Failed to create draft: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create draft"
        )


@router.get("/drafts", response_model=DraftListResponse)
async def list_drafts(
    draft_type: Optional[str] = Query(None),
    status: Optional[DraftStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List Drafts for the current user."""
    query = db.query(Draft).filter(
        and_(
            Draft.user_id == current_user.id,
            Draft.deleted_at.is_(None)
        )
    )
    
    if draft_type:
        query = query.filter(Draft.draft_type == draft_type)
    if status:
        query = query.filter(Draft.status == status.value)
    
    total = query.count()
    items = query.order_by(Draft.updated_at.desc()).offset(skip).limit(limit).all()
    
    return DraftListResponse(
        total=total,
        items=[DraftRead.model_validate(item) for item in items]
    )


@router.get("/drafts/{draft_id}", response_model=DraftRead)
async def get_draft(
    draft_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific Draft."""
    draft = db.query(Draft).filter(
        and_(
            Draft.id == draft_id,
            Draft.user_id == current_user.id,
            Draft.deleted_at.is_(None)
        )
    ).first()
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    return DraftRead.model_validate(draft)


@router.patch("/drafts/{draft_id}", response_model=DraftRead)
async def update_draft(
    draft_id: UUID,
    draft_data: DraftUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Update a Draft."""
    draft = db.query(Draft).filter(
        and_(
            Draft.id == draft_id,
            Draft.user_id == current_user.id,
            Draft.deleted_at.is_(None)
        )
    ).first()
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    # Update fields
    update_data = draft_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "uploaded_docs" and value is not None:
            draft.uploaded_docs = [doc if isinstance(doc, dict) else doc.dict() for doc in value]
        elif field == "status" and value is not None:
            draft.status = DraftStatus(value)
        elif value is not None:
            setattr(draft, field, value)
    
    db.commit()
    db.refresh(draft)
    
    return DraftRead.model_validate(draft)


@router.post("/drafts/{draft_id}/promote", response_model=DraftRead)
async def promote_draft(
    draft_id: UUID,
    promote_data: DraftPromoteRequest,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Promote a draft to ready-for-submission."""
    draft = db.query(Draft).filter(
        and_(
            Draft.id == draft_id,
            Draft.user_id == current_user.id,
            Draft.deleted_at.is_(None)
        )
    ).first()
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
    
    if draft.status != DraftStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot promote draft with status {draft.status}"
        )
    
    draft.status = DraftStatus.READY_FOR_SUBMISSION
    if promote_data.notes:
        draft.notes = (draft.notes or "") + f"\n\nPromoted: {promote_data.notes}"
    
    db.commit()
    db.refresh(draft)
    
    return DraftRead.model_validate(draft)


# ===== Amendment Endpoints =====

@router.post("/amendments", response_model=AmendmentRead, status_code=status.HTTP_201_CREATED)
async def create_amendment(
    amendment_data: AmendmentCreate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Create a new Amendment."""
    try:
        # Find the latest version for this LC
        latest_amendment = db.query(Amendment).filter(
            and_(
                Amendment.lc_number == amendment_data.lc_number,
                Amendment.user_id == current_user.id,
                Amendment.deleted_at.is_(None)
            )
        ).order_by(Amendment.version.desc()).first()
        
        next_version = (latest_amendment.version + 1) if latest_amendment else 1
        
        amendment = Amendment(
            lc_number=amendment_data.lc_number,
            user_id=current_user.id,
            company_id=current_user.company_id,
            version=next_version,
            previous_version_id=latest_amendment.id if latest_amendment else None,
            validation_session_id=amendment_data.validation_session_id,
            previous_validation_session_id=amendment_data.previous_validation_session_id,
            status=AmendmentStatus.PENDING,
            changes_diff=amendment_data.changes_diff,
            document_changes=[change.dict() for change in (amendment_data.document_changes or [])],
            notes=amendment_data.notes,
            metadata=amendment_data.metadata or {}
        )
        
        db.add(amendment)
        db.commit()
        db.refresh(amendment)
        
        return AmendmentRead.model_validate(amendment)
    except Exception as e:
        logger.error(f"Failed to create amendment: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create amendment"
        )


@router.get("/amendments", response_model=AmendmentListResponse)
async def list_amendments(
    lc_number: Optional[str] = Query(None),
    status: Optional[AmendmentStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """List Amendments for the current user."""
    query = db.query(Amendment).filter(
        and_(
            Amendment.user_id == current_user.id,
            Amendment.deleted_at.is_(None)
        )
    )
    
    if lc_number:
        query = query.filter(Amendment.lc_number == lc_number)
    if status:
        query = query.filter(Amendment.status == status.value)
    
    total = query.count()
    items = query.order_by(Amendment.version.desc()).offset(skip).limit(limit).all()
    
    return AmendmentListResponse(
        total=total,
        items=[AmendmentRead.model_validate(item) for item in items]
    )


@router.get("/amendments/{amendment_id}", response_model=AmendmentRead)
async def get_amendment(
    amendment_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get a specific Amendment."""
    amendment = db.query(Amendment).filter(
        and_(
            Amendment.id == amendment_id,
            Amendment.user_id == current_user.id,
            Amendment.deleted_at.is_(None)
        )
    ).first()
    
    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Amendment not found"
        )
    
    return AmendmentRead.model_validate(amendment)


@router.get("/amendments/{amendment_id}/diff", response_model=AmendmentDiffResponse)
async def get_amendment_diff(
    amendment_id: UUID,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Get the diff for an amendment compared to its previous version."""
    amendment = db.query(Amendment).filter(
        and_(
            Amendment.id == amendment_id,
            Amendment.user_id == current_user.id,
            Amendment.deleted_at.is_(None)
        )
    ).first()
    
    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Amendment not found"
        )
    
    previous_version = amendment.version - 1 if amendment.previous_version_id else None
    
    # Calculate summary
    changes = amendment.changes_diff or {}
    summary = {
        "added": len(changes.get("added_fields", [])),
        "removed": len(changes.get("removed_fields", [])),
        "modified": len(changes.get("modified_fields", []))
    }
    
    return AmendmentDiffResponse(
        amendment_id=amendment.id,
        lc_number=amendment.lc_number,
        from_version=previous_version or 1,
        to_version=amendment.version,
        changes=changes,
        document_changes=amendment.document_changes or [],
        summary=summary
    )


@router.patch("/amendments/{amendment_id}", response_model=AmendmentRead)
async def update_amendment(
    amendment_id: UUID,
    amendment_data: AmendmentUpdate,
    current_user: User = Depends(require_sme_user),
    db: Session = Depends(get_db)
):
    """Update an Amendment."""
    amendment = db.query(Amendment).filter(
        and_(
            Amendment.id == amendment_id,
            Amendment.user_id == current_user.id,
            Amendment.deleted_at.is_(None)
        )
    ).first()
    
    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Amendment not found"
        )
    
    # Update fields
    update_data = amendment_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            amendment.status = AmendmentStatus(value)
        elif value is not None:
            setattr(amendment, field, value)
    
    db.commit()
    db.refresh(amendment)
    
    return AmendmentRead.model_validate(amendment)

