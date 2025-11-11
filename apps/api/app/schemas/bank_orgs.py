"""
Pydantic schemas for Bank Organizations
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.bank_orgs import OrgKind, OrgAccessRole


class BankOrgCreate(BaseModel):
    """Schema for creating a bank organization"""
    bank_company_id: UUID
    parent_id: Optional[UUID] = None
    kind: str = Field(..., description="Organization kind: 'group', 'region', or 'branch'")
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50, description="Short code like 'APAC', 'NYC-001'")
    level: int = Field(0, ge=0)
    sort_order: int = Field(0, ge=0)
    is_active: bool = Field(True)


class BankOrgUpdate(BaseModel):
    """Schema for updating a bank organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class BankOrgRead(BaseModel):
    """Schema for reading a bank organization"""
    id: UUID
    bank_company_id: UUID
    parent_id: Optional[UUID] = None
    kind: str
    name: str
    code: Optional[str] = None
    path: str
    level: int
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserOrgAccessCreate(BaseModel):
    """Schema for creating user org access"""
    user_id: UUID
    org_id: UUID
    role: str = Field(default=OrgAccessRole.MEMBER.value, description="Access role: 'admin', 'member', or 'viewer'")
    granted_by: Optional[UUID] = None


class UserOrgAccessUpdate(BaseModel):
    """Schema for updating user org access"""
    role: Optional[str] = Field(None, description="Access role: 'admin', 'member', or 'viewer'")


class UserOrgAccessRead(BaseModel):
    """Schema for reading user org access"""
    id: UUID
    user_id: UUID
    org_id: UUID
    role: str
    created_at: datetime
    granted_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class PaginatedBankOrgsResponse(BaseModel):
    """Paginated response for bank orgs"""
    total: int
    count: int
    results: List[BankOrgRead]

