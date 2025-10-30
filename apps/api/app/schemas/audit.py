"""
Pydantic schemas for audit logging.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.audit_log import AuditAction, AuditResult


class AuditActionEnum(str, Enum):
    """Audit action types for API."""
    UPLOAD = "upload"
    VALIDATE = "validate"
    DOWNLOAD = "download"
    CREATE_VERSION = "create_version"
    UPDATE_VERSION = "update_version"
    COMPARE_VERSIONS = "compare_versions"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"


class AuditResultEnum(str, Enum):
    """Audit result types for API."""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    PARTIAL = "partial"


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Type of resource")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    lc_number: Optional[str] = Field(None, description="LC number if applicable")
    lc_version: Optional[str] = Field(None, description="LC version if applicable")
    result: str = Field(..., description="Action result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs."""
    correlation_id: str = Field(..., description="Request correlation ID")
    session_id: Optional[str] = Field(None, description="User session ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    http_method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    duration_ms: Optional[int] = Field(None, description="Action duration in milliseconds")
    file_hash: Optional[str] = Field(None, description="File hash for integrity")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_count: Optional[int] = Field(None, description="Number of files")
    request_data: Optional[Dict[str, Any]] = Field(None, description="Request payload")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Response data")


class AuditLogRead(AuditLogBase):
    """Schema for reading audit logs."""
    id: UUID = Field(..., description="Audit log ID")
    correlation_id: str = Field(..., description="Request correlation ID")
    session_id: Optional[str] = Field(None, description="User session ID")
    user_id: Optional[UUID] = Field(None, description="User ID")
    user_email: Optional[str] = Field(None, description="User email")
    user_role: Optional[str] = Field(None, description="User role")
    timestamp: datetime = Field(..., description="Action timestamp")
    duration_ms: Optional[int] = Field(None, description="Action duration")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    http_method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    file_hash: Optional[str] = Field(None, description="File hash")
    file_size: Optional[int] = Field(None, description="File size")
    file_count: Optional[int] = Field(None, description="Number of files")
    retention_until: Optional[datetime] = Field(None, description="Retention deadline")
    archived: Optional[str] = Field(None, description="Archive status")

    class Config:
        from_attributes = True


class AuditLogSummary(BaseModel):
    """Summary view of audit log."""
    id: UUID = Field(..., description="Audit log ID")
    correlation_id: str = Field(..., description="Request correlation ID")
    user_email: Optional[str] = Field(None, description="User email")
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Resource type")
    lc_number: Optional[str] = Field(None, description="LC number")
    timestamp: datetime = Field(..., description="Action timestamp")
    result: str = Field(..., description="Action result")
    ip_address: Optional[str] = Field(None, description="Client IP")

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """Schema for audit log queries."""
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    user_email: Optional[str] = Field(None, description="Filter by user email")
    action: Optional[AuditActionEnum] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    lc_number: Optional[str] = Field(None, description="Filter by LC number")
    result: Optional[AuditResultEnum] = Field(None, description="Filter by result")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: str = Field("timestamp", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""
    logs: List[AuditLogRead] = Field(..., description="Audit logs")
    total: int = Field(..., description="Total number of logs")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")


class AuditLogSummaryResponse(BaseModel):
    """Paginated audit log summary response."""
    logs: List[AuditLogSummary] = Field(..., description="Audit log summaries")
    total: int = Field(..., description="Total number of logs")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")


class ComplianceReportQuery(BaseModel):
    """Schema for compliance report queries."""
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[AuditActionEnum] = Field(None, description="Filter by action")
    include_details: bool = Field(False, description="Include detailed logs")

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    @validator('start_date')
    def start_date_not_future(cls, v):
        if v > datetime.utcnow():
            raise ValueError('start_date cannot be in the future')
        return v


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""
    report_period: Dict[str, str] = Field(..., description="Report date range")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    action_breakdown: Dict[str, int] = Field(..., description="Actions by type")
    user_activity: Dict[str, int] = Field(..., description="Activity by user")
    logs: Optional[List[AuditLogRead]] = Field(None, description="Detailed logs if requested")


class FileIntegrityCheck(BaseModel):
    """Schema for file integrity verification."""
    file_hash: str = Field(..., description="Current file hash")
    expected_hash: str = Field(..., description="Expected file hash")
    verified: bool = Field(..., description="Integrity verification result")
    timestamp: datetime = Field(..., description="Verification timestamp")


class AuditStatistics(BaseModel):
    """Audit statistics response."""
    total_actions: int = Field(..., description="Total actions logged")
    success_rate: float = Field(..., description="Success percentage")
    most_active_user: Optional[str] = Field(None, description="Most active user email")
    most_common_action: Optional[str] = Field(None, description="Most common action")
    recent_failures: int = Field(..., description="Recent failures count")
    file_operations: int = Field(..., description="File operations count")
    last_24h_actions: int = Field(..., description="Actions in last 24 hours")


class AuditSearchResult(BaseModel):
    """Search result for audit logs."""
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(..., description="Action timestamp")
    user_email: Optional[str] = Field(None, description="User email")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource identifier")
    result: str = Field(..., description="Action result")
    relevance_score: float = Field(..., description="Search relevance score")

    class Config:
        from_attributes = True


class AuditExportRequest(BaseModel):
    """Request for exporting audit logs."""
    query: AuditLogQuery = Field(..., description="Query parameters")
    format: str = Field("json", pattern="^(json|csv|xlsx)$", description="Export format")
    include_sensitive: bool = Field(False, description="Include sensitive data")


class AuditRetentionPolicy(BaseModel):
    """Audit log retention policy."""
    default_retention_days: int = Field(2555, ge=1, description="Default retention period")
    critical_action_retention_days: int = Field(3650, ge=1, description="Critical actions retention")
    min_retention_days: int = Field(365, ge=1, description="Minimum retention period")
    auto_archive_enabled: bool = Field(True, description="Enable automatic archiving")

    @validator('critical_action_retention_days')
    def critical_retention_gte_default(cls, v, values):
        if v < values.get('default_retention_days', 0):
            raise ValueError('critical_action_retention_days must be >= default_retention_days')
        return v

    @validator('default_retention_days')
    def default_retention_gte_min(cls, v, values):
        if v < values.get('min_retention_days', 0):
            raise ValueError('default_retention_days must be >= min_retention_days')
        return v