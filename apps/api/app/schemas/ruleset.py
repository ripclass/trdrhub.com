"""
Pydantic schemas for ruleset management API.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class RulesetCreate(BaseModel):
    """Schema for creating a new ruleset."""
    domain: str = Field(..., description="Rule domain (e.g., 'icc')")
    jurisdiction: str = Field(default="global", description="Jurisdiction (e.g., 'global', 'eu', 'us')")
    ruleset_version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    rulebook_version: str = Field(..., description="Rulebook version (e.g., 'UCP600:2007')")
    effective_from: Optional[datetime] = Field(None, description="Optional effective start date")
    effective_to: Optional[datetime] = Field(None, description="Optional effective end date")
    notes: Optional[str] = Field(None, description="Optional notes")


class RulesetResponse(BaseModel):
    """Schema for ruleset response."""
    id: UUID
    domain: str
    jurisdiction: str
    ruleset_version: str
    rulebook_version: str
    file_path: str
    status: str
    effective_from: Optional[datetime]
    effective_to: Optional[datetime]
    checksum_md5: str
    rule_count: int
    created_by: Optional[UUID]
    created_at: datetime
    published_by: Optional[UUID]
    published_at: Optional[datetime]
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class RulesetListQuery(BaseModel):
    """Query parameters for listing rulesets."""
    domain: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RulesetListResponse(BaseModel):
    """Response for listing rulesets."""
    items: List[RulesetResponse]
    total: int
    page: int
    page_size: int


class ValidationReport(BaseModel):
    """Schema for validation report."""
    valid: bool
    rule_count: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RulesetUploadResponse(BaseModel):
    """Response for ruleset upload."""
    ruleset: RulesetResponse
    validation: ValidationReport


class ActiveRulesetResponse(BaseModel):
    """Response for active ruleset."""
    ruleset: RulesetResponse
    signed_url: Optional[str] = None
    content: Optional[List[Dict[str, Any]]] = None  # Include JSON if requested


class RulesetAuditResponse(BaseModel):
    """Schema for audit log response."""
    id: UUID
    ruleset_id: UUID
    action: str
    actor_id: Optional[UUID]
    detail: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

