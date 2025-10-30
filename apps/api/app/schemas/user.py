"""
User management schemas with role-based access control.
"""

from datetime import datetime
from typing import Optional, Literal, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

# Role type definition
Role = Literal["exporter", "importer", "bank", "admin"]


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[Role] = "exporter"  # Default role, can only be overridden by admin

    @validator('role')
    def validate_role(cls, v):
        """Validate role is in allowed values."""
        if v not in ["exporter", "importer", "bank", "admin"]:
            raise ValueError('Role must be one of: exporter, importer, bank, admin')
        return v


class UserCreateAdmin(UserBase):
    """Schema for admin user creation (allows setting any role)."""
    password: str = Field(..., min_length=8, max_length=128)
    role: Role = "exporter"  # Admin can set any role


class UserRead(UserBase):
    """Schema for user information response."""
    id: UUID
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfile(UserRead):
    """Extended user profile for /me endpoint."""
    # Can add additional fields here like preferences, last_login, etc.
    pass


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    # Note: role updates are handled separately for security


class PasswordUpdate(BaseModel):
    """Schema for password changes."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RoleUpdateRequest(BaseModel):
    """Schema for role change requests (admin only)."""
    user_id: UUID
    role: Role
    reason: Optional[str] = Field(None, max_length=500, description="Reason for role change")

    @validator('role')
    def validate_role(cls, v):
        """Validate role is in allowed values."""
        if v not in ["exporter", "importer", "bank", "admin"]:
            raise ValueError('Role must be one of: exporter, importer, bank, admin')
        return v


class RoleUpdateResponse(BaseModel):
    """Response for role update operations."""
    success: bool
    message: str
    user_id: UUID
    old_role: Role
    new_role: Role
    updated_by: UUID
    updated_at: datetime


class UserListQuery(BaseModel):
    """Query parameters for user listing."""
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=255, description="Search in email or name")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserRead]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class UserStats(BaseModel):
    """User statistics for admin dashboard."""
    total_users: int
    active_users: int
    users_by_role: dict[Role, int]
    recent_registrations: int  # Last 30 days
    recent_role_changes: int   # Last 30 days


class RolePermissions(BaseModel):
    """Role permissions matrix."""
    role: Role
    permissions: dict[str, bool]
    description: str


# Permission checking schemas
class PermissionCheck(BaseModel):
    """Request to check specific permission."""
    action: str = Field(..., description="Action to check (e.g., 'read_all_jobs')")
    resource: Optional[str] = Field(None, description="Specific resource ID")


class PermissionResult(BaseModel):
    """Result of permission check."""
    allowed: bool
    reason: Optional[str] = None
    user_role: Role


# User authentication schemas (extending existing)
class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role  # Include role in token response


class TokenData(BaseModel):
    """JWT token payload data."""
    sub: str  # user_id
    role: Role
    exp: int
    iat: int


# Role-specific schemas
class ExporterProfile(UserRead):
    """Exporter-specific profile information."""
    # Can add exporter-specific fields like company info, etc.
    pass


class ImporterProfile(UserRead):
    """Importer-specific profile information."""
    # Can add importer-specific fields
    pass


class BankProfile(UserRead):
    """Bank-specific profile information."""
    # Can add bank-specific fields like institution info
    pass


class AdminProfile(UserRead):
    """Admin-specific profile information."""
    # Can add admin-specific fields like permissions granted, etc.
    pass