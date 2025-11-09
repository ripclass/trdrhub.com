"""
Bank Workflow API endpoints for Approvals and Discrepancy Workflow.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..core.security import get_current_user, require_bank_or_admin
from ..models import User, ValidationSession, Discrepancy, UserRole
from ..models.bank_workflow import (
    BankApproval, DiscrepancyWorkflow,
    ApprovalStatus, ApprovalStage, DiscrepancyWorkflowStatus
)
from ..schemas.bank_workflow import (
    BankApprovalCreate, BankApprovalUpdate, BankApprovalRead, BankApprovalListResponse, BankApprovalAction,
    DiscrepancyWorkflowCreate, DiscrepancyWorkflowUpdate, DiscrepancyWorkflowRead,
    DiscrepancyWorkflowListResponse, DiscrepancyWorkflowComment, DiscrepancyWorkflowResolve,
    BulkDiscrepancyAction
)
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bank", tags=["bank-workflow"])


# ===== Bank Approval Endpoints =====

@router.post("/approvals", response_model=BankApprovalRead, status_code=status.HTTP_201_CREATED)
async def create_approval(
    approval_data: BankApprovalCreate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new Bank Approval."""
    try:
        # Verify validation session exists and belongs to user's company
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == approval_data.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found or access denied"
            )
        
        # Check if approval already exists
        existing = db.query(BankApproval).filter(
            and_(
                BankApproval.validation_session_id == approval_data.validation_session_id,
                BankApproval.deleted_at.is_(None)
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval already exists for this validation session"
            )
        
        approval = BankApproval(
            validation_session_id=approval_data.validation_session_id,
            current_stage=ApprovalStage.ANALYST.value,
            status=ApprovalStatus.PENDING.value,
            analyst_id=approval_data.analyst_id or current_user.id,
            reviewer_id=approval_data.reviewer_id,
            approver_id=approval_data.approver_id,
            assigned_to_id=approval_data.assigned_to_id or approval_data.analyst_id or current_user.id,
            priority=approval_data.priority,
            metadata=approval_data.metadata or {}
        )
        
        db.add(approval)
        db.commit()
        db.refresh(approval)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(request) if request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="bank_approval",
            resource_id=str(approval.id),
            result=AuditResult.SUCCESS
        )
        
        return BankApprovalRead.model_validate(approval)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create approval: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create approval"
        )


@router.get("/approvals", response_model=BankApprovalListResponse)
async def list_approvals(
    status_filter: Optional[ApprovalStatus] = Query(None, alias="status"),
    stage: Optional[ApprovalStage] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """List Bank Approvals for the current user's company."""
    # Join with ValidationSession to filter by company_id
    query = db.query(BankApproval).join(
        ValidationSession,
        BankApproval.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            BankApproval.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    )
    
    if status_filter:
        query = query.filter(BankApproval.status == status_filter.value)
    if stage:
        query = query.filter(BankApproval.current_stage == stage.value)
    if assigned_to:
        query = query.filter(BankApproval.assigned_to_id == assigned_to)
    
    total = query.count()
    items = query.order_by(BankApproval.created_at.desc()).offset(skip).limit(limit).all()
    
    return BankApprovalListResponse(
        total=total,
        items=[BankApprovalRead.model_validate(item) for item in items]
    )


@router.get("/approvals/{approval_id}", response_model=BankApprovalRead)
async def get_approval(
    approval_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """Get a specific Bank Approval."""
    # Join with ValidationSession to filter by company_id
    approval = db.query(BankApproval).join(
        ValidationSession,
        BankApproval.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            BankApproval.id == approval_id,
            BankApproval.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or access denied"
        )
    
    return BankApprovalRead.model_validate(approval)


@router.patch("/approvals/{approval_id}", response_model=BankApprovalRead)
async def update_approval(
    approval_id: UUID,
    approval_data: BankApprovalUpdate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Update a Bank Approval."""
    # Join with ValidationSession to filter by company_id
    approval = db.query(BankApproval).join(
        ValidationSession,
        BankApproval.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            BankApproval.id == approval_id,
            BankApproval.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or access denied"
        )
    
    # Update fields
    update_data = approval_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "current_stage" and value is not None:
            approval.current_stage = ApprovalStage(value).value
        elif value is not None:
            setattr(approval, field, value)
    
    db.commit()
    db.refresh(approval)
    
    return BankApprovalRead.model_validate(approval)


@router.post("/approvals/{approval_id}/action", response_model=BankApprovalRead)
async def approve_action(
    approval_id: UUID,
    action_data: BankApprovalAction,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Perform an approval action (approve/reject/reopen)."""
    # Join with ValidationSession to filter by company_id
    approval = db.query(BankApproval).join(
        ValidationSession,
        BankApproval.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            BankApproval.id == approval_id,
            BankApproval.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or access denied"
        )
    
    action = action_data.action.lower()
    
    if action == "approve":
        # Move to next stage or approve
        if approval.current_stage == ApprovalStage.ANALYST.value:
            approval.current_stage = ApprovalStage.REVIEWER.value
            approval.assigned_to_id = approval.reviewer_id
        elif approval.current_stage == ApprovalStage.REVIEWER.value:
            approval.current_stage = ApprovalStage.APPROVER.value
            approval.assigned_to_id = approval.approver_id
        elif approval.current_stage == ApprovalStage.APPROVER.value:
            approval.status = ApprovalStatus.APPROVED.value
            approval.decision = "approve"
            approval.decided_by_id = current_user.id
            approval.decided_at = datetime.now()
        
        approval.decision_reason = action_data.reason
        
    elif action == "reject":
        approval.status = ApprovalStatus.REJECTED.value
        approval.decision = "reject"
        approval.decision_reason = action_data.reason
        approval.decided_by_id = current_user.id
        approval.decided_at = datetime.now()
        
    elif action == "reopen":
        approval.status = ApprovalStatus.REOPENED.value
        approval.reopened_count += 1
        approval.reopened_by_id = current_user.id
        approval.reopened_at = datetime.now()
        approval.reopened_reason = action_data.reason
        approval.current_stage = ApprovalStage.ANALYST.value
        approval.assigned_to_id = approval.analyst_id
    
    db.commit()
    db.refresh(approval)
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="bank_approval",
        resource_id=str(approval.id),
        result=AuditResult.SUCCESS,
        audit_metadata={"action": action, "reason": action_data.reason}
    )
    
    return BankApprovalRead.model_validate(approval)


# ===== Discrepancy Workflow Endpoints =====

@router.post("/discrepancies/workflow", response_model=DiscrepancyWorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_discrepancy_workflow(
    workflow_data: DiscrepancyWorkflowCreate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new Discrepancy Workflow."""
    try:
        # Verify validation session exists and belongs to user's company
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == workflow_data.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found or access denied"
            )
        
        # Verify discrepancy exists and belongs to the same validation session
        discrepancy = db.query(Discrepancy).filter(
            and_(
                Discrepancy.id == workflow_data.discrepancy_id,
                Discrepancy.validation_session_id == workflow_data.validation_session_id
            )
        ).first()
        
        if not discrepancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discrepancy not found"
            )
        
        workflow = DiscrepancyWorkflow(
            discrepancy_id=workflow_data.discrepancy_id,
            validation_session_id=workflow_data.validation_session_id,
            status=DiscrepancyWorkflowStatus.OPEN.value,
            assigned_to_id=workflow_data.assigned_to_id,
            assigned_by_id=current_user.id,
            assigned_at=datetime.now() if workflow_data.assigned_to_id else None,
            due_date=workflow_data.due_date,
            sla_hours=workflow_data.sla_hours,
            priority=workflow_data.priority,
            tags=workflow_data.tags or [],
            metadata=workflow_data.metadata or {}
        )
        
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        return DiscrepancyWorkflowRead.model_validate(workflow)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create discrepancy workflow: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create discrepancy workflow"
        )


@router.get("/discrepancies/workflow", response_model=DiscrepancyWorkflowListResponse)
async def list_discrepancy_workflows(
    status_filter: Optional[DiscrepancyWorkflowStatus] = Query(None, alias="status"),
    assigned_to: Optional[UUID] = Query(None),
    validation_session_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """List Discrepancy Workflows for the current user's company."""
    # Join with ValidationSession to filter by company_id
    query = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    )
    
    if status_filter:
        query = query.filter(DiscrepancyWorkflow.status == status_filter.value)
    if assigned_to:
        query = query.filter(DiscrepancyWorkflow.assigned_to_id == assigned_to)
    if validation_session_id:
        query = query.filter(DiscrepancyWorkflow.validation_session_id == validation_session_id)
    
    total = query.count()
    items = query.order_by(DiscrepancyWorkflow.created_at.desc()).offset(skip).limit(limit).all()
    
    return DiscrepancyWorkflowListResponse(
        total=total,
        items=[DiscrepancyWorkflowRead.model_validate(item) for item in items]
    )


@router.get("/discrepancies/workflow/{workflow_id}", response_model=DiscrepancyWorkflowRead)
async def get_discrepancy_workflow(
    workflow_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """Get a specific Discrepancy Workflow."""
    # Join with ValidationSession to filter by company_id
    workflow = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.id == workflow_id,
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discrepancy workflow not found or access denied"
        )
    
    return DiscrepancyWorkflowRead.model_validate(workflow)


@router.patch("/discrepancies/workflow/{workflow_id}", response_model=DiscrepancyWorkflowRead)
async def update_discrepancy_workflow(
    workflow_id: UUID,
    workflow_data: DiscrepancyWorkflowUpdate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Update a Discrepancy Workflow."""
    # Join with ValidationSession to filter by company_id
    workflow = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.id == workflow_id,
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discrepancy workflow not found or access denied"
        )
    
    # Update fields
    update_data = workflow_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            workflow.status = DiscrepancyWorkflowStatus(value).value
            if value == DiscrepancyWorkflowStatus.RESOLVED:
                workflow.resolved_at = datetime.now()
                workflow.resolved_by_id = current_user.id
        elif field == "assigned_to_id" and value is not None:
            workflow.assigned_to_id = value
            workflow.assigned_by_id = current_user.id
            workflow.assigned_at = datetime.now()
        elif value is not None:
            setattr(workflow, field, value)
    
    db.commit()
    db.refresh(workflow)
    
    return DiscrepancyWorkflowRead.model_validate(workflow)


@router.post("/discrepancies/workflow/{workflow_id}/comment", response_model=DiscrepancyWorkflowRead)
async def add_comment(
    workflow_id: UUID,
    comment_data: DiscrepancyWorkflowComment,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Add a comment to a Discrepancy Workflow."""
    # Join with ValidationSession to filter by company_id
    workflow = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.id == workflow_id,
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discrepancy workflow not found or access denied"
        )
    
    # Add comment
    comments = workflow.comments or []
    comments.append({
        "user_id": str(current_user.id),
        "comment": comment_data.comment,
        "created_at": datetime.now().isoformat(),
        "attachments": comment_data.attachments or []
    })
    workflow.comments = comments
    
    db.commit()
    db.refresh(workflow)
    
    return DiscrepancyWorkflowRead.model_validate(workflow)


@router.post("/discrepancies/workflow/{workflow_id}/resolve", response_model=DiscrepancyWorkflowRead)
async def resolve_discrepancy(
    workflow_id: UUID,
    resolve_data: DiscrepancyWorkflowResolve,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Resolve a Discrepancy Workflow."""
    # Join with ValidationSession to filter by company_id
    workflow = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.id == workflow_id,
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discrepancy workflow not found or access denied"
        )
    
    workflow.status = DiscrepancyWorkflowStatus.RESOLVED.value
    workflow.resolved_at = datetime.now()
    workflow.resolved_by_id = current_user.id
    workflow.resolution_notes = resolve_data.resolution_notes
    
    db.commit()
    db.refresh(workflow)
    
    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.UPDATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="discrepancy_workflow",
        resource_id=str(workflow.id),
        result=AuditResult.SUCCESS,
        audit_metadata={"action": "resolve", "notes": resolve_data.resolution_notes}
    )
    
    return DiscrepancyWorkflowRead.model_validate(workflow)


@router.post("/discrepancies/workflow/bulk-action", response_model=Dict[str, int])
async def bulk_discrepancy_action(
    bulk_data: BulkDiscrepancyAction,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Perform bulk actions on discrepancies."""
    # Join with ValidationSession to filter by company_id
    workflows = db.query(DiscrepancyWorkflow).join(
        ValidationSession,
        DiscrepancyWorkflow.validation_session_id == ValidationSession.id
    ).filter(
        and_(
            DiscrepancyWorkflow.id.in_(bulk_data.discrepancy_ids),
            DiscrepancyWorkflow.deleted_at.is_(None),
            ValidationSession.company_id == current_user.company_id
        )
    ).all()
    
    if len(workflows) != len(bulk_data.discrepancy_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some discrepancy workflows not found or access denied"
        )
    
    action = bulk_data.action.lower()
    updated_count = 0
    
    for workflow in workflows:
        if action == "assign":
            workflow.assigned_to_id = bulk_data.assigned_to_id
            workflow.assigned_by_id = current_user.id
            workflow.assigned_at = datetime.now()
            workflow.status = DiscrepancyWorkflowStatus.IN_PROGRESS.value
            updated_count += 1
        elif action == "resolve":
            workflow.status = DiscrepancyWorkflowStatus.RESOLVED.value
            workflow.resolved_at = datetime.now()
            workflow.resolved_by_id = current_user.id
            workflow.resolution_notes = bulk_data.resolution_notes or "Bulk resolved"
            updated_count += 1
        elif action == "close":
            workflow.status = DiscrepancyWorkflowStatus.CLOSED.value
            updated_count += 1
    
    db.commit()
    
    return {"updated": updated_count, "total": len(workflows)}

