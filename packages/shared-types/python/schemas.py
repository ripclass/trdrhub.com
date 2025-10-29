"""
Shared Pydantic schemas for API contracts.
This file should be kept in sync with the TypeScript definitions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, HttpUrl


# ============================================================================
# Health Check Types
# ============================================================================

class ServiceStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class HealthServices(BaseModel):
    database: ServiceStatus
    redis: Optional[ServiceStatus] = None


class HealthResponse(BaseModel):
    status: HealthStatus
    timestamp: datetime
    version: str
    services: HealthServices


# ============================================================================
# Error Response Types
# ============================================================================

class ApiError(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    path: Optional[str] = None
    method: Optional[str] = None


class FieldError(BaseModel):
    field: str
    message: str
    code: str


class ValidationErrorDetails(BaseModel):
    field_errors: List[FieldError]


class ValidationError(BaseModel):
    error: str = Field(default="validation_error")
    message: str
    details: ValidationErrorDetails
    timestamp: datetime


# ============================================================================
# Authentication Types
# ============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")
    expires_in: int


class UserProfile(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime


# ============================================================================
# File Upload Types
# ============================================================================

class FileUploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileUploadRequest(BaseModel):
    filename: str
    content_type: str
    size: int = Field(gt=0)


class FileUploadResponse(BaseModel):
    upload_id: UUID
    upload_url: HttpUrl
    fields: Dict[str, str]
    expires_at: datetime


class FileInfo(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size: int
    status: FileUploadStatus
    upload_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# OCR Processing Types
# ============================================================================

class OcrJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OcrOptions(BaseModel):
    deskew: bool = True
    remove_background: bool = False
    enhance_contrast: bool = True


class OcrJobRequest(BaseModel):
    file_id: UUID
    language: str = "eng+ben"  # English + Bengali
    options: Optional[OcrOptions] = None


class OcrResult(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=100)
    language_detected: str
    processing_time_ms: int
    word_count: int
    character_count: int


class OcrJobResponse(BaseModel):
    job_id: UUID
    file_id: UUID
    status: OcrJobStatus
    result: Optional[OcrResult] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# Report Generation Types
# ============================================================================

class ReportFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class ReportTemplate(str, Enum):
    STANDARD = "standard"
    DETAILED = "detailed"
    SUMMARY = "summary"


class ReportOptions(BaseModel):
    include_original_images: bool = False
    include_confidence_scores: bool = True
    language: str = "en"


class ReportRequest(BaseModel):
    ocr_job_ids: List[UUID]
    format: ReportFormat
    template: ReportTemplate
    options: Optional[ReportOptions] = None


class ReportJobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportJob(BaseModel):
    job_id: UUID
    status: ReportJobStatus
    download_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Pagination Types
# ============================================================================

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel):
    """Generic paginated response. Use with specific item types."""
    items: List[Any]
    meta: PaginationMeta


# ============================================================================
# API Response Wrappers
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response wrapper."""
    success: bool = True
    data: Any
    timestamp: datetime


class ErrorResponse(BaseModel):
    success: bool = False
    error: ApiError
    timestamp: datetime


# ============================================================================
# Schema Registry for Runtime Access
# ============================================================================

SCHEMAS = {
    # Health
    'HealthResponse': HealthResponse,
    'ServiceStatus': ServiceStatus,
    
    # Errors
    'ApiError': ApiError,
    'ValidationError': ValidationError,
    
    # Auth
    'AuthToken': AuthToken,
    'UserProfile': UserProfile,
    
    # Files
    'FileUploadRequest': FileUploadRequest,
    'FileUploadResponse': FileUploadResponse,
    'FileInfo': FileInfo,
    
    # OCR
    'OcrJobRequest': OcrJobRequest,
    'OcrJobResponse': OcrJobResponse,
    'OcrResult': OcrResult,
    
    # Reports
    'ReportRequest': ReportRequest,
    'ReportJob': ReportJob,
    
    # Pagination
    'PaginationParams': PaginationParams,
    'PaginationMeta': PaginationMeta,
}


def get_schema(name: str) -> BaseModel:
    """Get a schema by name for runtime validation."""
    if name not in SCHEMAS:
        raise ValueError(f"Schema '{name}' not found. Available schemas: {list(SCHEMAS.keys())}")
    return SCHEMAS[name]


def validate_data(schema_name: str, data: Dict[str, Any]) -> BaseModel:
    """Validate data against a named schema."""
    schema_class = get_schema(schema_name)
    return schema_class.model_validate(data)
