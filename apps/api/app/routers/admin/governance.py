"""
Admin Governance API - Approval workflows and delegation management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import logging

from app.database import get_db
from app.services.governance_service import GovernanceService
from app.models.audit import GovernanceApproval
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ApprovalRequest(BaseModel):
    decision: str  # "approve" or "reject"
    comments: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: UUID
    request_id: UUID
    tenant_id: str
    action_type: str
    resource_type: str
    resource_id: str
    status: str
    required_approvals: int
    approvals_received: int
    requested_by: UUID
    requested_at: datetime
    expires_at: Optional[datetime]
    approval_history: Optional[List[dict]]


@router.get("/approvals/pending", response_model=List[ApprovalResponse])
async def get_pending_approvals(
    tenant_id: str = Query(..., description="Tenant ID"),
    approver_role: Optional[str] = Query(None, description="Filter by approver role"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Get pending approval requests"""
    try:
        # TODO: Extract current user from authentication context
        current_user_id = None  # Would come from JWT token

        approvals = await GovernanceService.get_pending_approvals(
            db=db,
            tenant_id=tenant_id,
            approver_role=approver_role,
            limit=limit
        )

        return [
            ApprovalResponse(
                id=approval.id,
                request_id=approval.request_id,
                tenant_id=approval.tenant_id,
                action_type=approval.action_type,
                resource_type=approval.resource_type,
                resource_id=approval.resource_id,
                status=approval.status,
                required_approvals=approval.required_approvals,
                approvals_received=approval.approvals_received,
                requested_by=approval.requested_by,
                requested_at=approval.requested_at,
                expires_at=approval.expires_at,
                approval_history=approval.approval_history
            )
            for approval in approvals
        ]

    except Exception as e:
        logger.error(f"Failed to get pending approvals: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/approvals/{approval_id}/decision")
async def provide_approval_decision(
    approval_id: UUID,
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """Provide approval or rejection for a request"""
    try:
        # TODO: Extract current user from authentication context
        current_user_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
        current_user_role = "admin"  # Would come from JWT token

        if request.decision not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

        approval = await GovernanceService.provide_approval(
            db=db,
            approval_id=approval_id,
            approver_id=current_user_id,
            approver_role=current_user_role,
            decision=request.decision,
            comments=request.comments
        )

        return {
            "status": "success",
            "message": f"Approval {request.decision}d successfully",
            "approval_status": approval.status,
            "approvals_received": approval.approvals_received,
            "required_approvals": approval.required_approvals
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to provide approval decision: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/approvals/history", response_model=List[ApprovalResponse])
async def get_approval_history(
    tenant_id: str = Query(..., description="Tenant ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Get approval history with filters"""
    try:
        approvals = await GovernanceService.get_approval_history(
            db=db,
            tenant_id=tenant_id,
            action_type=action_type,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return [
            ApprovalResponse(
                id=approval.id,
                request_id=approval.request_id,
                tenant_id=approval.tenant_id,
                action_type=approval.action_type,
                resource_type=approval.resource_type,
                resource_id=approval.resource_id,
                status=approval.status,
                required_approvals=approval.required_approvals,
                approvals_received=approval.approvals_received,
                requested_by=approval.requested_by,
                requested_at=approval.requested_at,
                expires_at=approval.expires_at,
                approval_history=approval.approval_history
            )
            for approval in approvals
        ]

    except Exception as e:
        logger.error(f"Failed to get approval history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval_details(
    approval_id: UUID,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific approval request"""
    try:
        approval = db.query(GovernanceApproval).filter(
            GovernanceApproval.id == approval_id
        ).first()

        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        return ApprovalResponse(
            id=approval.id,
            request_id=approval.request_id,
            tenant_id=approval.tenant_id,
            action_type=approval.action_type,
            resource_type=approval.resource_type,
            resource_id=approval.resource_id,
            status=approval.status,
            required_approvals=approval.required_approvals,
            approvals_received=approval.approvals_received,
            requested_by=approval.requested_by,
            requested_at=approval.requested_at,
            expires_at=approval.expires_at,
            approval_history=approval.approval_history
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get approval details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/approvals/cleanup-expired")
async def cleanup_expired_approvals(
    db: Session = Depends(get_db)
):
    """Clean up expired approval requests"""
    try:
        expired_count = await GovernanceService.cleanup_expired_approvals(db)

        return {
            "status": "success",
            "message": f"Cleaned up {expired_count} expired approval requests",
            "expired_count": expired_count
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired approvals: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/governance/stats")
async def get_governance_stats(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get governance statistics for admin dashboard"""
    try:
        # Get counts for different approval statuses
        pending_count = db.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant_id,
            GovernanceApproval.status == "pending"
        ).count()

        approved_count = db.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant_id,
            GovernanceApproval.status == "approved"
        ).count()

        rejected_count = db.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant_id,
            GovernanceApproval.status == "rejected"
        ).count()

        expired_count = db.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant_id,
            GovernanceApproval.status == "expired"
        ).count()

        # Get approval types breakdown
        approval_types = db.query(
            GovernanceApproval.action_type,
            db.func.count(GovernanceApproval.id).label('count')
        ).filter(
            GovernanceApproval.tenant_id == tenant_id
        ).group_by(GovernanceApproval.action_type).all()

        return {
            "tenant_id": tenant_id,
            "approval_counts": {
                "pending": pending_count,
                "approved": approved_count,
                "rejected": rejected_count,
                "expired": expired_count,
                "total": pending_count + approved_count + rejected_count + expired_count
            },
            "approval_types": [
                {"action_type": action_type, "count": count}
                for action_type, count in approval_types
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get governance stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")