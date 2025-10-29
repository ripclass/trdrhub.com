"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from .models import SessionStatus, DocumentType, DiscrepancyType, DiscrepancySeverity, UserRole


# Authentication schemas
class UserRegistration(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = UserRole.EXPORTER  # Default role for new users


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # Token expiration in seconds
    role: str  # Include role in token response


class UserProfile(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Session schemas
class ValidationSessionCreate(BaseModel):
    """Request to create a new validation session."""
    pass


class DocumentUploadUrl(BaseModel):
    """Pre-signed URL for document upload."""
    document_type: DocumentType
    upload_url: str
    s3_key: str


class ValidationSessionResponse(BaseModel):
    """Response after creating a validation session."""
    session_id: UUID
    status: SessionStatus
    upload_urls: List[DocumentUploadUrl]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentInfo(BaseModel):
    """Document information in session response."""
    id: UUID
    document_type: DocumentType
    original_filename: str
    file_size: int
    ocr_confidence: Optional[float] = None
    ocr_processed_at: Optional[datetime] = None
    extracted_fields: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DiscrepancyInfo(BaseModel):
    """Discrepancy information."""
    id: UUID
    discrepancy_type: DiscrepancyType
    severity: DiscrepancySeverity
    rule_name: str
    field_name: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    description: str
    source_document_types: Optional[List[DocumentType]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationSessionDetail(BaseModel):
    """Detailed validation session information."""
    id: UUID
    status: SessionStatus
    ocr_provider: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentInfo] = []
    discrepancies: List[DiscrepancyInfo] = []

    class Config:
        from_attributes = True


class ValidationSessionSummary(BaseModel):
    """Summary validation session information for listing."""
    id: UUID
    status: SessionStatus
    created_at: datetime
    total_documents: int
    total_discrepancies: int
    critical_discrepancies: int

    class Config:
        from_attributes = True


# Report schemas
class ReportInfo(BaseModel):
    """Report information."""
    id: UUID
    report_version: int
    total_discrepancies: int
    critical_discrepancies: int
    major_discrepancies: int
    minor_discrepancies: int
    generated_at: datetime
    file_size: Optional[int] = None

    class Config:
        from_attributes = True


class ReportDownloadResponse(BaseModel):
    """Response for report download endpoint."""
    download_url: str
    expires_at: datetime
    report_info: ReportInfo


# Cross-Check Matrix schemas
class CrossCheckField(BaseModel):
    """Individual field in cross-check matrix."""
    field_name: str
    lc_value: Optional[str] = None
    invoice_value: Optional[str] = None
    bl_value: Optional[str] = None
    is_consistent: bool
    discrepancies: List[str] = []


class CrossCheckMatrix(BaseModel):
    """Cross-document field comparison matrix."""
    session_id: UUID
    fields: List[CrossCheckField]
    overall_consistency: bool
    last_updated: datetime


# Document processing schemas
class ProcessedDocumentInfo(BaseModel):
    """Information about a processed document."""
    document_id: UUID
    document_type: str
    original_filename: str
    s3_url: str
    s3_key: str
    file_size: int
    extracted_text_preview: str  # First 200 chars
    extracted_fields: Dict[str, Any]
    ocr_confidence: float
    page_count: int
    entity_count: int


class DocumentProcessingResponse(BaseModel):
    """Response from document processing endpoint."""
    session_id: UUID
    processor_id: str
    processed_documents: List[ProcessedDocumentInfo]
    discrepancies: List[Dict[str, Any]]  # Placeholder for now
    processing_summary: Dict[str, Any]
    created_at: datetime


# Error schemas
class ApiError(BaseModel):
    """Standard API error response."""
    error: str
    message: str
    timestamp: datetime
    path: str
    method: str