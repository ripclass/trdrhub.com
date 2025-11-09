"""
Pydantic schemas for SME Workspace (LC Workspace, Drafts, Amendments).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.sme_workspace import DraftStatus, AmendmentStatus, DocumentChecklistStatus


# ===== LC Workspace Schemas =====

class DocumentChecklistItem(BaseModel):
    """Schema for a single document checklist item."""
    document_type: str = Field(..., description="Type of document (e.g., 'letter_of_credit', 'commercial_invoice')")
    required: bool = Field(default=True, description="Whether this document is required")
    status: DocumentChecklistStatus = Field(default=DocumentChecklistStatus.MISSING)
    document_id: Optional[UUID] = None
    uploaded_at: Optional[datetime] = None
    validation_status: Optional[str] = None  # "valid", "invalid", "pending"


class LCWorkspaceBase(BaseModel):
    """Base LC Workspace schema."""
    lc_number: str = Field(..., min_length=1, max_length=100)
    client_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    document_checklist: List[DocumentChecklistItem] = Field(default_factory=list)


class LCWorkspaceCreate(LCWorkspaceBase):
    """Schema for creating a new LC Workspace."""
    pass


class LCWorkspaceUpdate(BaseModel):
    """Schema for updating an LC Workspace."""
    client_name: Optional[str] = None
    description: Optional[str] = None
    document_checklist: Optional[List[DocumentChecklistItem]] = None


class LCWorkspaceRead(LCWorkspaceBase):
    """Schema for reading LC Workspace data."""
    id: UUID
    user_id: UUID
    company_id: Optional[UUID]
    latest_validation_session_id: Optional[UUID]
    is_active: bool
    completion_percentage: int = Field(..., ge=0, le=100)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class LCWorkspaceListResponse(BaseModel):
    """Schema for listing LC Workspaces."""
    total: int
    items: List[LCWorkspaceRead]


# ===== Draft Schemas =====

class DraftFileMetadata(BaseModel):
    """Schema for draft file metadata."""
    file_id: Optional[UUID] = None
    filename: str
    document_type: str
    uploaded_at: datetime
    file_size: Optional[int] = None


class DraftBase(BaseModel):
    """Base Draft schema."""
    lc_number: Optional[str] = Field(None, max_length=100)
    client_name: Optional[str] = Field(None, max_length=255)
    draft_type: str = Field(..., description="Type: 'importer_draft', 'exporter_draft', 'importer_supplier'")
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DraftCreate(DraftBase):
    """Schema for creating a new Draft."""
    uploaded_docs: List[DraftFileMetadata] = Field(default_factory=list)


class DraftUpdate(BaseModel):
    """Schema for updating a Draft."""
    lc_number: Optional[str] = None
    client_name: Optional[str] = None
    status: Optional[DraftStatus] = None
    uploaded_docs: Optional[List[DraftFileMetadata]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DraftRead(DraftBase):
    """Schema for reading Draft data."""
    id: UUID
    user_id: UUID
    company_id: Optional[UUID]
    status: DraftStatus
    uploaded_docs: List[DraftFileMetadata]
    validation_session_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class DraftListResponse(BaseModel):
    """Schema for listing Drafts."""
    total: int
    items: List[DraftRead]


class DraftPromoteRequest(BaseModel):
    """Schema for promoting a draft to ready-for-submission."""
    notes: Optional[str] = None


# ===== Amendment Schemas =====

class AmendmentChange(BaseModel):
    """Schema for a single change in an amendment."""
    field: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_type: str = Field(..., description="'added', 'removed', 'modified'")


class AmendmentDocumentChange(BaseModel):
    """Schema for document-level changes in an amendment."""
    document_type: str
    action: str = Field(..., description="'added', 'removed', 'modified'")
    old_document_id: Optional[UUID] = None
    new_document_id: Optional[UUID] = None


class AmendmentBase(BaseModel):
    """Base Amendment schema."""
    lc_number: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AmendmentCreate(AmendmentBase):
    """Schema for creating a new Amendment."""
    validation_session_id: UUID
    previous_validation_session_id: Optional[UUID] = None
    changes_diff: Optional[Dict[str, Any]] = None
    document_changes: Optional[List[AmendmentDocumentChange]] = None


class AmendmentUpdate(BaseModel):
    """Schema for updating an Amendment."""
    status: Optional[AmendmentStatus] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AmendmentRead(AmendmentBase):
    """Schema for reading Amendment data."""
    id: UUID
    user_id: UUID
    company_id: Optional[UUID]
    version: int
    previous_version_id: Optional[UUID]
    validation_session_id: UUID
    previous_validation_session_id: Optional[UUID]
    status: AmendmentStatus
    changes_diff: Optional[Dict[str, Any]] = None
    document_changes: Optional[List[AmendmentDocumentChange]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str
        }


class AmendmentListResponse(BaseModel):
    """Schema for listing Amendments."""
    total: int
    items: List[AmendmentRead]


class AmendmentDiffResponse(BaseModel):
    """Schema for amendment diff comparison."""
    amendment_id: UUID
    lc_number: str
    from_version: int
    to_version: int
    changes: Dict[str, Any]
    document_changes: List[AmendmentDocumentChange]
    summary: Dict[str, int] = Field(default_factory=dict)  # {"added": 0, "removed": 0, "modified": 0}

    class Config:
        json_encoders = {
            UUID: str
        }

