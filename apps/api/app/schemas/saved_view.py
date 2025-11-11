"""
Saved Views schemas for API requests/responses.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class SavedViewCreate(BaseModel):
    """Request schema for creating a saved view."""
    name: str = Field(..., min_length=1, max_length=255)
    resource: str = Field(..., description="Resource type: 'results', 'jobs', or 'evidence'")
    query_params: Dict[str, Any] = Field(..., description="Filter parameters as JSON")
    columns: Optional[Dict[str, Any]] = Field(None, description="Visible columns configuration")
    is_org_default: bool = Field(False, description="Set as organization default")
    shared: bool = Field(False, description="Share with other users in company")


class SavedViewUpdate(BaseModel):
    """Request schema for updating a saved view."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    query_params: Optional[Dict[str, Any]] = Field(None, description="Filter parameters as JSON")
    columns: Optional[Dict[str, Any]] = Field(None, description="Visible columns configuration")
    is_org_default: Optional[bool] = Field(None, description="Set as organization default")
    shared: Optional[bool] = Field(None, description="Share with other users in company")


class SavedViewRead(BaseModel):
    """Response schema for reading a saved view."""
    id: UUID
    company_id: UUID
    owner_id: UUID
    owner_name: Optional[str] = None
    name: str
    resource: str
    query_params: Dict[str, Any]
    columns: Optional[Dict[str, Any]] = None
    is_org_default: bool
    shared: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavedViewListResponse(BaseModel):
    """Response schema for listing saved views."""
    total: int
    count: int
    views: List[SavedViewRead]

