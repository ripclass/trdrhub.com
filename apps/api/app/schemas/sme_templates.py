"""
SME Templates Schemas
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.sme_templates import TemplateType, DocumentType


class SMETemplateBase(BaseModel):
    """Base template schema."""
    name: str = Field(..., min_length=1, max_length=255)
    type: TemplateType
    document_type: Optional[DocumentType] = None
    description: Optional[str] = None
    fields: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class SMETemplateCreate(SMETemplateBase):
    """Schema for creating a template."""
    company_id: UUID
    user_id: UUID


class SMETemplateUpdate(BaseModel):
    """Schema for updating a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class SMETemplateRead(SMETemplateBase):
    """Schema for reading a template."""
    id: UUID
    company_id: UUID
    user_id: UUID
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SMETemplateListResponse(BaseModel):
    """Response schema for listing templates."""
    items: list[SMETemplateRead]
    total: int


class TemplatePreFillRequest(BaseModel):
    """Request schema for pre-filling template fields."""
    template_id: UUID
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TemplatePreFillResponse(BaseModel):
    """Response schema for pre-filled template."""
    fields: Dict[str, Any]
    template_name: str

