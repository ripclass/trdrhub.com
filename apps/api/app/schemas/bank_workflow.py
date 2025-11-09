"""
Pydantic schemas for Bank Workflow (Approvals and Discrepancy Workflow).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.bank_workflow import ApprovalStatus, ApprovalStage, DiscrepancyWorkflowStatus


# ===== Bank Approval Schemas =====

class BankApprovalBase(BaseModel):
    """Base Bank Approval schema."""
    priority: str = Field(default="normal", description="Priority: low, normal, high, urgent")
    metadata: Optional[Dict[str, Any]] = None


class BankApprovalCreate(BankApprovalBase):
    """Schema for creating a new Bank Approval."""
    validation_session_id: UUID
    analyst_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    approver_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None


class BankApprovalUpdate(BaseModel):
    """Schema for updating a Bank Approval."""
    current_stage: Optional[ApprovalStage] = None
    assigned_to_id: Optional[UUID] = None
    priority: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BankApprovalAction(BaseModel):
    """Schema for approval actions (approve/reject/reopen)."""
    action: str = Field(..., description="'approve', 'reject', or 'reopen'")
    reason: Optional[str] = None
    next_stage: Optional[ApprovalStage] = None


class BankApprovalRead(BankApprovalBase):
    """Schema for reading Bank Approval data."""
    id: UUID
    validation_session_id: UUID
    current_stage: ApprovalStage
    status: ApprovalStatus
    analyst_id: Optional[UUID]
    reviewer_id: Optional[UUID]
    approver_id: Optional[UUID]
    assigned_to_id: Optional[UUID]
    decision: Optional[str]
    decision_reason: Optional[str]
    decided_by_id: Optional[UUID]
    decided_at: Optional[datetime]
    reopened_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class BankApprovalListResponse(BaseModel):
    """Schema for listing Bank Approvals."""
    total: int
    items: List[BankApprovalRead]


# ===== Discrepancy Workflow Schemas =====

class DiscrepancyComment(BaseModel):
    """Schema for a comment in discrepancy workflow."""
    user_id: UUID
    comment: str
    created_at: datetime
    attachments: Optional[List[str]] = Field(default_factory=list)


class DiscrepancyWorkflowBase(BaseModel):
    """Base Discrepancy Workflow schema."""
    priority: str = Field(default="normal")
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class DiscrepancyWorkflowCreate(DiscrepancyWorkflowBase):
    """Schema for creating a new Discrepancy Workflow."""
    discrepancy_id: UUID
    validation_session_id: UUID
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    sla_hours: Optional[int] = None


class DiscrepancyWorkflowUpdate(BaseModel):
    """Schema for updating a Discrepancy Workflow."""
    status: Optional[DiscrepancyWorkflowStatus] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DiscrepancyWorkflowComment(BaseModel):
    """Schema for adding a comment to a discrepancy workflow."""
    comment: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = Field(default_factory=list)


class DiscrepancyWorkflowResolve(BaseModel):
    """Schema for resolving a discrepancy workflow."""
    resolution_notes: str = Field(..., min_length=1)


class DiscrepancyWorkflowRead(DiscrepancyWorkflowBase):
    """Schema for reading Discrepancy Workflow data."""
    id: UUID
    discrepancy_id: UUID
    validation_session_id: UUID
    status: DiscrepancyWorkflowStatus
    assigned_to_id: Optional[UUID]
    assigned_by_id: Optional[UUID]
    assigned_at: Optional[datetime]
    due_date: Optional[datetime]
    sla_hours: Optional[int]
    resolved_at: Optional[datetime]
    resolved_by_id: Optional[UUID]
    resolution_notes: Optional[str]
    comments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class DiscrepancyWorkflowListResponse(BaseModel):
    """Schema for listing Discrepancy Workflows."""
    total: int
    items: List[DiscrepancyWorkflowRead]


class BulkDiscrepancyAction(BaseModel):
    """Schema for bulk actions on discrepancies."""
    discrepancy_ids: List[UUID] = Field(..., min_items=1)
    action: str = Field(..., description="'assign', 'resolve', 'close'")
    assigned_to_id: Optional[UUID] = None
    resolution_notes: Optional[str] = None

