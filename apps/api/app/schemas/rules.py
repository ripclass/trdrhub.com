from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from uuid import UUID


class RuleRecordResponse(BaseModel):
    rule_id: str
    rule_version: Optional[str] = None
    article: Optional[str] = None
    version: Optional[str] = None
    domain: str
    jurisdiction: str
    document_type: str
    rule_type: str
    severity: str
    deterministic: bool
    requires_llm: bool
    title: str
    reference: Optional[str] = None
    description: Optional[str] = None
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    expected_outcome: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    checksum: str
    ruleset_id: Optional[UUID] = None
    ruleset_version: Optional[str] = None
    is_active: bool
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    items: List[RuleRecordResponse]
    total: int
    page: int
    page_size: int


class RuleUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    severity: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    rule_json: Optional[Dict[str, Any]] = None


class RuleDeleteResponse(BaseModel):
    rule_id: str
    archived: bool


class BulkSyncResponseItem(BaseModel):
    ruleset_id: UUID
    status: str
    domain: str
    jurisdiction: str
    summary: Dict[str, Any]


class BulkSyncResponse(BaseModel):
    items: List[BulkSyncResponseItem]


class BulkSyncRequest(BaseModel):
    ruleset_id: Optional[UUID] = None
    include_inactive: bool = False

