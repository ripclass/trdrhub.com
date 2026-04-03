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
# Structured Validation Payload Types
# ============================================================================

class SeverityBreakdown(BaseModel):
    critical: int = Field(default=0, ge=0)
    major: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    minor: int = Field(default=0, ge=0)


class StructuredProcessingSummary(BaseModel):
    total_documents: int = Field(ge=0)
    successful_extractions: int = Field(ge=0)
    failed_extractions: int = Field(ge=0)
    total_issues: int = Field(ge=0)
    severity_breakdown: SeverityBreakdown


class ProcessingSummaryV2(BaseModel):
    version: str = Field(default="processing_summary_v2")
    total_documents: int = Field(ge=0)
    documents: Optional[int] = Field(default=None, ge=0)
    documents_found: Optional[int] = Field(default=None, ge=0)
    verified: int = Field(ge=0)
    warnings: int = Field(ge=0)
    errors: int = Field(ge=0)
    successful_extractions: int = Field(ge=0)
    failed_extractions: int = Field(ge=0)
    total_issues: int = Field(ge=0)
    discrepancies: Optional[int] = Field(default=None, ge=0)
    severity_breakdown: SeverityBreakdown
    status_counts: Dict[str, int]
    document_status: Optional[Dict[str, int]] = None
    compliance_rate: float = Field(ge=0, le=100)
    processing_time_seconds: Optional[float] = None
    processing_time_display: Optional[str] = None
    processing_time_ms: Optional[float] = None
    extraction_quality: Optional[float] = None


class ExtractionFieldEvidence(BaseModel):
    source: str
    snippet: Optional[str] = None
    strategy: Optional[str] = None


class ExtractionFieldDetail(BaseModel):
    value: Optional[Any] = None
    raw_value: Optional[Any] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    status: Optional[str] = None
    validator_agrees: Optional[bool] = None
    issues: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    verification: Optional[str] = None
    evidence: Optional[ExtractionFieldEvidence] = None


class ExtractionResolutionField(BaseModel):
    field_name: str
    label: str
    verification: Optional[str] = None
    reason_code: Optional[str] = None


class ExtractionResolution(BaseModel):
    required: bool
    unresolved_count: int = Field(ge=0)
    summary: str
    fields: List[ExtractionResolutionField] = Field(default_factory=list)
    source: Optional[str] = None


class WorkflowStageInfo(BaseModel):
    stage: str
    provisional_validation: bool
    ready_for_final_validation: bool
    unresolved_documents: int = Field(ge=0)
    unresolved_fields: int = Field(ge=0)
    document_lane_counts: Dict[str, int] = Field(default_factory=dict)
    summary: str


class FieldOverrideRequest(BaseModel):
    document_id: str
    field_name: str
    override_value: Optional[Any] = None
    verification: Optional[str] = "operator_confirmed"
    note: Optional[str] = Field(default=None, max_length=1000)


class DocumentFact(BaseModel):
    field_name: str
    value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    verification_state: str = "unconfirmed"
    origin: str = "unknown"
    source_field_name: Optional[str] = None
    evidence_snippet: Optional[str] = None
    evidence_source: Optional[str] = None
    page: Optional[int] = Field(default=None, ge=1)


class DocumentFactSet(BaseModel):
    version: str = Field(default="fact_graph_v1")
    document_type: str
    document_subtype: Optional[str] = None
    facts: List[DocumentFact] = Field(default_factory=list)


class RequirementsGraphDocument(BaseModel):
    code: str
    display_name: Optional[str] = None
    category: Optional[str] = None
    raw_text: Optional[str] = None
    aliases_matched: Optional[List[str]] = None
    originals: Optional[int] = None
    copies: Optional[int] = None
    signed: Optional[bool] = None
    negotiable: Optional[bool] = None
    issuer: Optional[str] = None
    exact_wording: Optional[str] = None
    legalized: Optional[bool] = None
    transport_mode: Optional[str] = None
    detection_source: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[List[str]] = None


class RequirementsGraphConditionRequirement(BaseModel):
    requirement_type: str
    identifier_type: Optional[str] = None
    value: Optional[str] = None
    applies_to: Optional[str] = None
    document_type: Optional[str] = None
    field_name: Optional[str] = None
    originals_required: Optional[int] = None
    copies_required: Optional[int] = None
    exact_wording: Optional[str] = None
    source_text: Optional[str] = None
    source_bucket: Optional[str] = None


class RequirementsGraphV1(BaseModel):
    version: str = Field(default="requirements_graph_v1")
    source_document_id: Optional[str] = None
    source_document_type: Optional[str] = None
    source_lane: Optional[str] = None
    workflow_orientation: Optional[str] = None
    applicable_rules: Optional[str] = None
    required_documents: List[RequirementsGraphDocument] = Field(default_factory=list)
    required_document_types: List[str] = Field(default_factory=list)
    documentary_conditions: List[str] = Field(default_factory=list)
    non_documentary_conditions: List[str] = Field(default_factory=list)
    ambiguous_conditions: List[str] = Field(default_factory=list)
    condition_requirements: List[RequirementsGraphConditionRequirement] = Field(default_factory=list)
    required_fact_fields: List[str] = Field(default_factory=list)
    core_terms: Dict[str, Any] = Field(default_factory=dict)


class ResolutionQueueItem(BaseModel):
    document_id: str
    document_type: str
    filename: Optional[str] = None
    field_name: str
    label: str
    priority: str
    candidate_value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    evidence_snippet: Optional[str] = None
    evidence_source: Optional[str] = None
    page: Optional[int] = Field(default=None, ge=1)
    reason: str
    verification_state: str
    resolvable_by_user: bool
    origin: Optional[str] = None


class ResolutionQueueSummary(BaseModel):
    total_items: int = Field(ge=0)
    user_resolvable_items: int = Field(ge=0)
    unresolved_documents: int = Field(ge=0)
    document_counts: Dict[str, int] = Field(default_factory=dict)


class ResolutionQueueV1(BaseModel):
    version: str = Field(default="resolution_queue_v1")
    items: List[ResolutionQueueItem] = Field(default_factory=list)
    summary: ResolutionQueueSummary


class FactResolutionDocument(BaseModel):
    document_id: str
    document_type: str
    filename: Optional[str] = None
    resolution_required: bool
    ready_for_validation: bool
    unresolved_count: int = Field(ge=0)
    summary: str
    fact_graph_v1: Optional[DocumentFactSet] = None
    requirements_graph_v1: Optional[RequirementsGraphV1] = None
    resolution_items: List[ResolutionQueueItem] = Field(default_factory=list)


class FactResolutionSummary(BaseModel):
    total_documents: int = Field(ge=0)
    unresolved_documents: int = Field(ge=0)
    total_items: int = Field(ge=0)
    user_resolvable_items: int = Field(ge=0)
    ready_for_validation: bool


class FactResolutionV1(BaseModel):
    version: str = Field(default="fact_resolution_v1")
    workflow_stage: Optional[WorkflowStageInfo] = None
    documents: List[FactResolutionDocument] = Field(default_factory=list)
    summary: FactResolutionSummary


class DocumentExtractionDocument(BaseModel):
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    filename: Optional[str] = None
    status: Optional[str] = None
    extraction_status: Optional[str] = None
    extraction_lane: Optional[str] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    field_details: Dict[str, ExtractionFieldDetail] = Field(default_factory=dict)
    fact_graph_v1: Optional[DocumentFactSet] = None
    requirements_graph_v1: Optional[RequirementsGraphV1] = None
    extraction_resolution: Optional[ExtractionResolution] = None
    issues_count: Optional[int] = Field(default=None, ge=0)
    ocr_confidence: Optional[float] = None
    review_required: Optional[bool] = None
    review_reasons: List[str] = Field(default_factory=list)
    critical_field_states: Dict[str, str] = Field(default_factory=dict)
    extraction_debug: Optional[Dict[str, Any]] = None


class DocumentExtractionSummary(BaseModel):
    total_documents: int = Field(ge=0)
    status_counts: Dict[str, int]


class DocumentExtractionV1(BaseModel):
    version: str = Field(default="document_extraction_v1")
    documents: List[DocumentExtractionDocument]
    summary: DocumentExtractionSummary


class IssueProvenanceEntry(BaseModel):
    issue_id: str
    source: str
    ruleset_domain: Optional[str] = None
    rule: Optional[str] = None
    severity: Optional[str] = None
    document_ids: Optional[Any] = None
    document_types: Optional[Any] = None
    document_names: Optional[Any] = None


class IssueProvenanceV1(BaseModel):
    version: str = Field(default="issue_provenance_v1")
    issues: List[IssueProvenanceEntry]


class StructuredResultDocument(BaseModel):
    document_id: str
    document_type: str
    filename: str
    extraction_status: str
    extraction_lane: Optional[str] = None
    extracted_fields: Dict[str, Any]
    field_details: Dict[str, ExtractionFieldDetail] = Field(default_factory=dict)
    fact_graph_v1: Optional[DocumentFactSet] = None
    requirements_graph_v1: Optional[RequirementsGraphV1] = None
    extraction_resolution: Optional[ExtractionResolution] = None
    issues_count: int = Field(ge=0)
    review_required: Optional[bool] = None
    review_reasons: List[str] = Field(default_factory=list)
    critical_field_states: Dict[str, str] = Field(default_factory=dict)
    extraction_debug: Optional[Dict[str, Any]] = None


class FieldOverrideResponse(BaseModel):
    job_id: str
    jobId: str
    document_id: str
    field_name: str
    override_value: Optional[Any] = None
    verification: str = Field(default="operator_confirmed")
    applied_at: datetime
    updated_document: Optional[StructuredResultDocument] = None


class StructuredResultIssue(BaseModel):
    id: str
    title: str
    severity: str
    priority: Optional[str] = None
    documents: List[str]
    expected: str
    found: str
    suggested_fix: str
    description: Optional[str] = None
    reference: Optional[str] = None
    ucp_reference: Optional[str] = None
    requirement_source: Optional[str] = None
    requirement_kind: Optional[str] = None
    requirement_text: Optional[str] = None


class DocumentRiskEntry(BaseModel):
    document_id: Optional[str] = None
    filename: Optional[str] = None
    risk: Optional[str] = None


class StructuredResultAnalytics(BaseModel):
    compliance_score: int
    issue_counts: SeverityBreakdown
    document_risk: List[DocumentRiskEntry]
    lc_compliance_score: Optional[int] = None
    document_status_distribution: Optional[Dict[str, int]] = None
    documents_processed: Optional[int] = None
    processing_time_display: Optional[str] = None
    compliance_level: Optional[str] = None
    compliance_cap_reason: Optional[str] = None
    customs_risk: Optional[Dict[str, Any]] = None


class TimelineEntry(BaseModel):
    title: Optional[str] = None
    label: Optional[str] = None
    status: str
    description: Optional[str] = None
    timestamp: Optional[str] = None


class AIValidationLayer(BaseModel):
    layer: str
    label: str
    executed: bool
    verdict: str
    issue_count: int = Field(ge=0)
    critical_issues: int = Field(ge=0)
    major_issues: int = Field(ge=0)
    minor_issues: int = Field(ge=0)
    checks_performed: List[str]
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class AIValidationLayers(BaseModel):
    l1: Optional[AIValidationLayer] = None
    l2: Optional[AIValidationLayer] = None
    l3: Optional[AIValidationLayer] = None

    class Config:
        extra = "allow"


class AIValidationSummary(BaseModel):
    issue_count: Optional[int] = Field(default=None, ge=0)
    critical_issues: Optional[int] = Field(default=None, ge=0)
    major_issues: Optional[int] = Field(default=None, ge=0)
    minor_issues: Optional[int] = Field(default=None, ge=0)
    documents_checked: Optional[int] = Field(default=None, ge=0)
    derived_ai_verdict: Optional[str] = None
    layer_contract_version: Optional[str] = None
    execution_position: Optional[str] = None
    layers: Optional[AIValidationLayers] = None
    metadata: Optional[Dict[str, Any]] = None
    timed_out: Optional[bool] = None

    class Config:
        extra = "allow"


class ValidationContractV1(BaseModel):
    ai_verdict: Optional[str] = None
    ai_layers: Optional[AIValidationLayers] = None
    ai_execution_position: Optional[str] = None
    ai_layer_contract_version: Optional[str] = None
    ruleset_verdict: Optional[str] = None
    final_verdict: Optional[str] = None
    arbitration_mode: Optional[str] = None
    next_action: Optional[str] = None
    review_required_reason: Optional[List[str]] = None
    escalation_triggers: Optional[List[str]] = None
    rules_evidence: Optional[Dict[str, Any]] = None
    evidence_summary: Optional[Dict[str, Any]] = None


class SubmissionEligibility(BaseModel):
    can_submit: Optional[bool] = None
    reasons: Optional[List[str]] = None
    source: Optional[str] = None
    missing_reason_codes: Optional[List[str]] = None
    unresolved_critical_fields: Optional[List[Any]] = None


class BankVerdictActionItem(BaseModel):
    priority: Optional[str] = None
    issue: Optional[str] = None
    action: Optional[str] = None


class BankVerdict(BaseModel):
    verdict: Optional[str] = None
    verdict_color: Optional[str] = None
    verdict_message: Optional[str] = None
    recommendation: Optional[str] = None
    can_submit: Optional[bool] = None
    will_be_rejected: Optional[bool] = None
    estimated_discrepancy_fee: Optional[float] = None
    issue_summary: Optional[Dict[str, Any]] = None
    action_items: Optional[List[BankVerdictActionItem]] = None
    action_items_count: Optional[int] = None
    reasons: Optional[List[str]] = None
    risk_flags: Optional[List[str]] = None


class BankProfile(BaseModel):
    bank_code: str
    bank_name: str
    strictness: str
    country: Optional[str] = None
    region: Optional[str] = None
    document_preferences: Optional[List[str]] = None
    special_requirements: Optional[List[str]] = None
    blocked_conditions: Optional[List[str]] = None
    tolerance_level: Optional[float] = None
    port_rules: Optional[Dict[str, Any]] = None
    date_rules: Optional[Dict[str, Any]] = None
    amount_rules: Optional[Dict[str, Any]] = None
    party_rules: Optional[Dict[str, Any]] = None


class AmendmentFieldChange(BaseModel):
    tag: str
    name: str
    current: str
    proposed: str


class Amendment(BaseModel):
    issue_id: str
    field: AmendmentFieldChange
    narrative: str
    swift_mt707_text: Optional[str] = None
    mt707_text: Optional[str] = None
    iso20022_xml: Optional[str] = None
    bank_processing_days: Optional[int] = None
    estimated_fee_usd: Optional[float] = None


class AmendmentsAvailable(BaseModel):
    count: int
    amendments: List[Amendment]
    total_estimated_fee_usd: Optional[float] = None
    total_processing_days: Optional[int] = None


class LcRequiredDocument(BaseModel):
    code: str
    display_name: str
    category: str
    raw_text: str
    aliases_matched: List[str]
    originals: Optional[int] = None
    copies: Optional[int] = None
    signed: Optional[bool] = None
    negotiable: Optional[bool] = None
    issuer: Optional[str] = None
    exact_wording: Optional[str] = None
    legalized: Optional[bool] = None
    transport_mode: Optional[str] = None
    detection_source: str
    confidence: float
    evidence: List[str]

    class Config:
        extra = "allow"


class LcClassificationAttributes(BaseModel):
    revocability: str
    availability: str
    available_with_scope: str
    confirmation: str
    transferability: str
    assignment_of_proceeds: str
    revolving: str
    revolving_mode: Optional[str] = None
    red_clause: str
    green_clause: str
    back_to_back: str
    documentation_basis: str
    partial_shipments: str
    transshipment: str
    latest_shipment_date: Optional[str] = None
    expiry_date: Optional[str] = None
    expiry_place: Optional[str] = None
    presentation_period_days: Optional[int] = None
    tenor_kind: str
    tenor_days: Optional[int] = None
    tolerance_min_pct: Optional[float] = None
    tolerance_max_pct: Optional[float] = None
    reimbursement_present: str

    class Config:
        extra = "allow"


class LcClassification(BaseModel):
    format_family: str
    format_variant: str
    embedded_variant: Optional[str] = None
    instrument_type: str
    workflow_orientation: str
    applicable_rules: str
    attributes: LcClassificationAttributes
    required_documents: List[LcRequiredDocument]
    requirement_conditions: Optional[List[str]] = None
    unmapped_requirements: Optional[List[str]] = None

    class Config:
        extra = "allow"


class LcStructuredPayload(BaseModel):
    lc_classification: Optional[LcClassification] = None
    documents_required: Optional[Any] = None
    required_document_types: Optional[List[str]] = None
    required_documents_detailed: Optional[List[LcRequiredDocument]] = None
    requirement_conditions: Optional[List[str]] = None
    unmapped_requirements: Optional[List[str]] = None
    additional_conditions: Optional[Any] = None
    documents_structured: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "allow"


class StructuredResultPayload(BaseModel):
    version: str = Field(default="structured_result_v1")
    processing_summary: StructuredProcessingSummary
    processing_summary_v2: Optional[ProcessingSummaryV2] = None
    document_extraction_v1: Optional[DocumentExtractionV1] = None
    requirements_graph_v1: Optional[RequirementsGraphV1] = None
    resolution_queue_v1: Optional[ResolutionQueueV1] = None
    fact_resolution_v1: Optional[FactResolutionV1] = None
    issue_provenance_v1: Optional[IssueProvenanceV1] = None
    documents: List[StructuredResultDocument]
    issues: List[StructuredResultIssue]
    analytics: StructuredResultAnalytics
    timeline: List[TimelineEntry]
    lc_structured: Optional[LcStructuredPayload] = None
    extraction_core_v1: Optional[Dict[str, Any]] = Field(default=None, alias="_extraction_core_v1")
    extraction_diagnostics: Optional[Dict[str, Any]] = Field(default=None, alias="_extraction_diagnostics")
    ai_validation: Optional[AIValidationSummary] = None
    validation_contract_v1: Optional[ValidationContractV1] = None
    submission_eligibility: Optional[SubmissionEligibility] = None
    raw_submission_eligibility: Optional[SubmissionEligibility] = None
    effective_submission_eligibility: Optional[SubmissionEligibility] = None
    workflow_stage: Optional[WorkflowStageInfo] = None
    bank_verdict: Optional[BankVerdict] = None
    bank_profile: Optional[BankProfile] = None
    amendments_available: Optional[AmendmentsAvailable] = None


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
# Exporter Bank Directory Types
# ============================================================================

class ExporterBankDirectoryItem(BaseModel):
    id: UUID
    name: str
    legal_name: Optional[str] = None
    country: Optional[str] = None
    regulator_id: Optional[str] = None
    active_user_count: int = Field(default=0, ge=0)


class ExporterBankDirectoryResponse(BaseModel):
    items: List[ExporterBankDirectoryItem]
    total: int = Field(default=0, ge=0)


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
# LCopilot Issue Card Types
# ============================================================================

class ToleranceApplied(BaseModel):
    tolerance_percent: float
    source: str
    explicit: bool


class WorkflowLane(str, Enum):
    DOCUMENTARY_REVIEW = "documentary_review"
    COMPLIANCE_REVIEW = "compliance_review"
    MANUAL_REVIEW = "manual_review"


class IssueCard(BaseModel):
    id: str
    rule: Optional[str] = None
    title: str
    description: str
    severity: str
    priority: Optional[str] = None
    documentName: Optional[str] = None
    documentType: Optional[str] = None
    documents: Optional[List[str]] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    suggestion: Optional[str] = None
    field: Optional[str] = None
    ucpReference: Optional[str] = None
    ucpDescription: Optional[str] = None
    ruleset_domain: Optional[str] = None
    auto_generated: Optional[bool] = None
    isbpReference: Optional[str] = None
    isbpDescription: Optional[str] = None
    tolerance_applied: Optional[ToleranceApplied] = None
    extraction_confidence: Optional[float] = None
    amendment_available: Optional[bool] = None
    workflow_lane: Optional[WorkflowLane] = None
    requirement_source: Optional[str] = None
    requirement_kind: Optional[str] = None
    requirement_text: Optional[str] = None


class ReferenceIssue(BaseModel):
    rule: Optional[str] = None
    title: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    article: Optional[str] = None
    ruleset_domain: Optional[str] = None


# ============================================================================
# AI Enrichment Types
# ============================================================================

class RuleReference(BaseModel):
    rule_code: str
    title: Optional[str] = None


class AIEnrichmentPayload(BaseModel):
    summary: Optional[str] = None
    suggestions: Optional[List[str]] = None
    confidence: Optional[str] = None
    rule_references: Optional[List[Any]] = None  # Can be strings or RuleReference objects
    fallback_used: Optional[bool] = None


# ============================================================================
# V2 Validation Pipeline Types
# ============================================================================

class GateStatus(str, Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"


class GateResult(BaseModel):
    status: GateStatus
    can_proceed: bool
    block_reason: Optional[str] = None
    completeness: float
    critical_completeness: float
    missing_critical: List[str]
    missing_required: Optional[List[str]] = None
    blocking_issues: Optional[List[Dict[str, Any]]] = None
    warning_issues: Optional[List[Dict[str, Any]]] = None


class ExtractionSummary(BaseModel):
    completeness: float
    critical_completeness: float
    missing_critical: List[str]
    missing_required: Optional[List[str]] = None
    total_fields: Optional[int] = None
    extracted_fields: Optional[int] = None


class LCBaseline(BaseModel):
    lc_number: Optional[str] = None
    lc_type: Optional[str] = None
    applicant: Optional[str] = None
    beneficiary: Optional[str] = None
    issuing_bank: Optional[str] = None
    advising_bank: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    latest_shipment: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    goods_description: Optional[str] = None
    incoterm: Optional[str] = None
    extraction_completeness: float
    critical_completeness: float


# ============================================================================
# Sanctions Screening Types
# ============================================================================

class SanctionsStatus(str, Enum):
    MATCH = "match"
    POTENTIAL_MATCH = "potential_match"
    CLEAR = "clear"


class SanctionsScreeningIssue(BaseModel):
    party: Optional[str] = None
    type: Optional[str] = None
    status: SanctionsStatus
    score: Optional[float] = None


class SanctionsScreeningSummary(BaseModel):
    screened: bool
    parties_screened: int
    matches: int
    potential_matches: int
    clear: int
    should_block: bool
    screened_at: str
    issues: List[SanctionsScreeningIssue]
    error: Optional[str] = None


# ============================================================================
# Validation Document (Frontend-normalized)
# ============================================================================

class ValidationDocumentStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class DocumentRequirementStatus(str, Enum):
    MATCHED = "matched"
    PARTIAL = "partial"
    MISSING = "missing"


class DocumentReviewState(str, Enum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ValidationDocument(BaseModel):
    id: str
    documentId: str
    name: str
    filename: str
    type: str
    typeKey: Optional[str] = None
    extractionStatus: str
    extractionLane: Optional[str] = None
    status: ValidationDocumentStatus
    issuesCount: int
    extractedFields: Dict[str, Any]
    missingRequiredFields: Optional[List[str]] = None
    requiredFieldsFound: Optional[int] = None
    requiredFieldsTotal: Optional[int] = None
    reviewRequired: Optional[bool] = None
    reviewReasons: Optional[List[str]] = None
    criticalFieldStates: Optional[Dict[str, str]] = None
    extractionResolution: Optional[Dict[str, Any]] = None
    requirementStatus: Optional[DocumentRequirementStatus] = None
    reviewState: Optional[DocumentReviewState] = None


class ContractWarning(BaseModel):
    field: str
    message: str
    severity: str
    source: str
    suggestion: Optional[str] = None


class ContractValidation(BaseModel):
    valid: bool
    error_count: int
    warning_count: int
    info_count: int


class ValidationResults(BaseModel):
    jobId: str
    job_id: Optional[str] = None
    validation_session_id: Optional[str] = None
    summary: StructuredProcessingSummary
    documents: List[ValidationDocument]
    issues: List[IssueCard]
    provisional_issues: Optional[List[IssueCard]] = None
    analytics: StructuredResultAnalytics
    timeline: List[TimelineEntry]
    structured_result: StructuredResultPayload
    lc_structured: Optional[LcStructuredPayload] = None
    ai_enrichment: Optional[AIEnrichmentPayload] = None
    telemetry: Optional[Dict[str, Any]] = None
    reference_issues: Optional[List[ReferenceIssue]] = None
    validationBlocked: Optional[bool] = None
    validationStatus: Optional[str] = None
    gateResult: Optional[GateResult] = None
    extractionSummary: Optional[ExtractionSummary] = None
    lcBaseline: Optional[LCBaseline] = None
    complianceLevel: Optional[str] = None
    complianceCapReason: Optional[str] = None
    sanctionsScreening: Optional[SanctionsScreeningSummary] = None
    sanctionsBlocked: Optional[bool] = None
    sanctionsBlockReason: Optional[str] = None
    validation_contract_v1: Optional[ValidationContractV1] = None
    submission_eligibility: Optional[SubmissionEligibility] = None
    raw_submission_eligibility: Optional[SubmissionEligibility] = None
    effective_submission_eligibility: Optional[SubmissionEligibility] = None
    bank_verdict: Optional[BankVerdict] = None
    ruleset_verdict: Optional[str] = None
    final_verdict: Optional[str] = None
    submission_can_submit: Optional[bool] = None
    submission_reasons: Optional[List[str]] = None
    contractWarnings: Optional[List[ContractWarning]] = None
    contractValidation: Optional[ContractValidation] = None


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
    
    # Structured validation payload
    'StructuredProcessingSummary': StructuredProcessingSummary,
    'ProcessingSummaryV2': ProcessingSummaryV2,
    'DocumentExtractionV1': DocumentExtractionV1,
    'IssueProvenanceV1': IssueProvenanceV1,
    'StructuredResultDocument': StructuredResultDocument,
    'StructuredResultIssue': StructuredResultIssue,
    'StructuredResultDocumentRiskEntry': DocumentRiskEntry,
    'StructuredResultAnalytics': StructuredResultAnalytics,
    'StructuredResultTimelineEntry': TimelineEntry,
    'AIValidationLayer': AIValidationLayer,
    'AIValidationLayers': AIValidationLayers,
    'AIValidationSummary': AIValidationSummary,
    'ValidationContractV1': ValidationContractV1,
    'SubmissionEligibility': SubmissionEligibility,
    'BankVerdict': BankVerdict,
    'BankProfile': BankProfile,
    'AmendmentFieldChange': AmendmentFieldChange,
    'Amendment': Amendment,
    'AmendmentsAvailable': AmendmentsAvailable,
    'LcRequiredDocument': LcRequiredDocument,
    'LcClassificationAttributes': LcClassificationAttributes,
    'LcClassification': LcClassification,
    'LcStructuredPayload': LcStructuredPayload,
    'StructuredResultPayload': StructuredResultPayload,
    
    # LCopilot-specific types
    'IssueCard': IssueCard,
    'ReferenceIssue': ReferenceIssue,
    'AIEnrichmentPayload': AIEnrichmentPayload,
    'ToleranceApplied': ToleranceApplied,
    'WorkflowLane': WorkflowLane,
    
    # V2 Validation Pipeline
    'GateResult': GateResult,
    'ExtractionSummary': ExtractionSummary,
    'LCBaseline': LCBaseline,
    
    # Sanctions Screening
    'SanctionsScreeningIssue': SanctionsScreeningIssue,
    'SanctionsScreeningSummary': SanctionsScreeningSummary,
    
    # Validation Document
    'ValidationDocument': ValidationDocument,
    'DocumentRequirementStatus': DocumentRequirementStatus,
    'DocumentReviewState': DocumentReviewState,
    'ContractWarning': ContractWarning,
    'ContractValidation': ContractValidation,
    'ValidationResults': ValidationResults,
    
    # Pagination
    'PaginationParams': PaginationParams,
    'PaginationMeta': PaginationMeta,
    'ExporterBankDirectoryItem': ExporterBankDirectoryItem,
    'ExporterBankDirectoryResponse': ExporterBankDirectoryResponse,
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
