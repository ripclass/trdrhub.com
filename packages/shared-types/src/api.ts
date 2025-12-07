import { z } from 'zod';

// ============================================================================
// Health Check Types
// ============================================================================

export const ServiceStatusSchema = z.enum(['connected', 'disconnected']);
export type ServiceStatus = z.infer<typeof ServiceStatusSchema>;

export const HealthStatusSchema = z.enum(['healthy', 'unhealthy']);
export type HealthStatus = z.infer<typeof HealthStatusSchema>;

export const HealthResponseSchema = z.object({
  status: HealthStatusSchema,
  timestamp: z.string().datetime(),
  version: z.string(),
  services: z.object({
    database: ServiceStatusSchema,
    redis: ServiceStatusSchema.optional(),
  }),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// ============================================================================
// Error Response Types
// ============================================================================

export const ApiErrorSchema = z.object({
  error: z.string(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
  timestamp: z.string().datetime(),
  path: z.string().optional(),
  method: z.string().optional(),
});
export type ApiError = z.infer<typeof ApiErrorSchema>;

export const ValidationErrorSchema = z.object({
  error: z.literal('validation_error'),
  message: z.string(),
  details: z.object({
    field_errors: z.array(z.object({
      field: z.string(),
      message: z.string(),
      code: z.string(),
    })),
  }),
  timestamp: z.string().datetime(),
});
export type ValidationError = z.infer<typeof ValidationErrorSchema>;

// ============================================================================
// Authentication Types
// ============================================================================

export const UserRoleSchema = z.enum(['admin', 'user', 'viewer']);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const AuthTokenSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.literal('bearer'),
  expires_in: z.number(),
});
export type AuthToken = z.infer<typeof AuthTokenSchema>;

export const UserProfileSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  role: UserRoleSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type UserProfile = z.infer<typeof UserProfileSchema>;

// ============================================================================
// File Upload Types
// ============================================================================

export const FileUploadStatusSchema = z.enum([
  'pending',
  'uploading',
  'processing',
  'completed',
  'failed',
]);
export type FileUploadStatus = z.infer<typeof FileUploadStatusSchema>;

export const FileUploadRequestSchema = z.object({
  filename: z.string(),
  content_type: z.string(),
  size: z.number().positive(),
});
export type FileUploadRequest = z.infer<typeof FileUploadRequestSchema>;

export const FileUploadResponseSchema = z.object({
  upload_id: z.string().uuid(),
  upload_url: z.string().url(),
  fields: z.record(z.string()),
  expires_at: z.string().datetime(),
});
export type FileUploadResponse = z.infer<typeof FileUploadResponseSchema>;

export const FileInfoSchema = z.object({
  id: z.string().uuid(),
  filename: z.string(),
  content_type: z.string(),
  size: z.number(),
  status: FileUploadStatusSchema,
  upload_url: z.string().url().optional(),
  download_url: z.string().url().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type FileInfo = z.infer<typeof FileInfoSchema>;

// ============================================================================
// OCR Processing Types
// ============================================================================

export const OcrJobStatusSchema = z.enum([
  'queued',
  'processing',
  'completed',
  'failed',
  'cancelled',
]);
export type OcrJobStatus = z.infer<typeof OcrJobStatusSchema>;

export const OcrJobRequestSchema = z.object({
  file_id: z.string().uuid(),
  language: z.string().default('eng+ben'), // English + Bengali
  options: z.object({
    deskew: z.boolean().default(true),
    remove_background: z.boolean().default(false),
    enhance_contrast: z.boolean().default(true),
  }).optional(),
});
export type OcrJobRequest = z.infer<typeof OcrJobRequestSchema>;

export const OcrResultSchema = z.object({
  text: z.string(),
  confidence: z.number().min(0).max(100),
  language_detected: z.string(),
  processing_time_ms: z.number(),
  word_count: z.number(),
  character_count: z.number(),
});
export type OcrResult = z.infer<typeof OcrResultSchema>;

export const OcrJobResponseSchema = z.object({
  job_id: z.string().uuid(),
  file_id: z.string().uuid(),
  status: OcrJobStatusSchema,
  result: OcrResultSchema.optional(),
  error_message: z.string().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  completed_at: z.string().datetime().optional(),
});
export type OcrJobResponse = z.infer<typeof OcrJobResponseSchema>;

// ============================================================================
// Report Generation Types
// ============================================================================

export const ReportFormatSchema = z.enum(['pdf', 'docx', 'html']);
export type ReportFormat = z.infer<typeof ReportFormatSchema>;

export const ReportTemplateSchema = z.enum(['standard', 'detailed', 'summary']);
export type ReportTemplate = z.infer<typeof ReportTemplateSchema>;

export const ReportRequestSchema = z.object({
  ocr_job_ids: z.array(z.string().uuid()),
  format: ReportFormatSchema,
  template: ReportTemplateSchema,
  options: z.object({
    include_original_images: z.boolean().default(false),
    include_confidence_scores: z.boolean().default(true),
    language: z.string().default('en'),
  }).optional(),
});
export type ReportRequest = z.infer<typeof ReportRequestSchema>;

export const ReportJobSchema = z.object({
  job_id: z.string().uuid(),
  status: z.enum(['queued', 'generating', 'completed', 'failed']),
  download_url: z.string().url().optional(),
  expires_at: z.string().datetime().optional(),
  error_message: z.string().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type ReportJob = z.infer<typeof ReportJobSchema>;

// ============================================================================
// Pagination Types
// ============================================================================

export const SeverityBreakdownSchema = z.object({
  critical: z.number().nonnegative(),
  major: z.number().nonnegative(),
  medium: z.number().nonnegative(),
  minor: z.number().nonnegative(),
});
export type SeverityBreakdown = z.infer<typeof SeverityBreakdownSchema>;

export const ProcessingSummarySchema = z.object({
  total_documents: z.number().nonnegative(),
  successful_extractions: z.number().nonnegative(),
  failed_extractions: z.number().nonnegative(),
  total_issues: z.number().nonnegative(),
  severity_breakdown: SeverityBreakdownSchema,
});
export type ProcessingSummary = z.infer<typeof ProcessingSummarySchema>;

export const StructuredResultDocumentSchema = z.object({
  document_id: z.string().optional(),
  document_type: z.string().optional(),
  filename: z.string().optional(),
  extraction_status: z.string().optional(),
  extracted_fields: z.record(z.unknown()).optional(),
  issues_count: z.number().nonnegative().optional(),
  // Legacy camelCase fields for backward compatibility
  id: z.string().optional(),
  name: z.string().optional(),
  type: z.string().optional(),
  extractionStatus: z.string().optional(),
  extractedFields: z.record(z.unknown()).optional(),
  discrepancy_count: z.number().nonnegative().optional(),
  discrepancyCount: z.number().nonnegative().optional(),
  issues: z.number().nonnegative().optional(),
}).passthrough();
export type StructuredResultDocument = z.infer<typeof StructuredResultDocumentSchema>;

export const StructuredResultIssueSchema = z.object({
  id: z.string(),
  title: z.string(),
  severity: z.string(),
  priority: z.string().optional(),
  documents: z.array(z.string()),
  expected: z.string(),
  found: z.string(),
  suggested_fix: z.string(),
  description: z.string().optional(),
  reference: z.string().optional().nullable(),
  ucp_reference: z.string().optional().nullable(),
});
export type StructuredResultIssue = z.infer<typeof StructuredResultIssueSchema>;

export const DocumentRiskEntrySchema = z.object({
  document_id: z.string().optional(),
  filename: z.string().optional(),
  risk: z.string().default('low'),
});
export type DocumentRiskEntry = z.infer<typeof DocumentRiskEntrySchema>;

export const StructuredResultAnalyticsSchema = z.object({
  compliance_score: z.number(),
  issue_counts: SeverityBreakdownSchema,
  document_risk: z.array(DocumentRiskEntrySchema),
});
export type StructuredResultAnalytics = z.infer<typeof StructuredResultAnalyticsSchema>;

export const StructuredTimelineEntrySchema = z.object({
  title: z.string().optional(),
  status: z.string(),
  description: z.string().optional(),
  timestamp: z.string().optional(),
  label: z.string().optional(),
});
export type StructuredTimelineEntry = z.infer<typeof StructuredTimelineEntrySchema>;
export const TimelineEntrySchema = StructuredTimelineEntrySchema;
export type TimelineEntry = StructuredTimelineEntry;

export const StructuredResultSchema = z.object({
  processing_summary: ProcessingSummarySchema,
  documents: z.array(StructuredResultDocumentSchema),
  issues: z.array(StructuredResultIssueSchema),
  analytics: StructuredResultAnalyticsSchema,
  timeline: z.array(StructuredTimelineEntrySchema),
  extracted_documents: z.record(z.unknown()).optional(),
  lc_structured: z.record(z.unknown()).optional(), // Structured LC data from extractor (MT700, goods, clauses, etc.)
}).passthrough(); // Allow extra fields for backward compatibility
export type StructuredResult = z.infer<typeof StructuredResultSchema>;
export const StructuredProcessingSummarySchema = ProcessingSummarySchema;
export type StructuredProcessingSummary = ProcessingSummary;
export const PaginationParamsSchema = z.object({
  page: z.number().int().positive().default(1),
  limit: z.number().int().positive().max(100).default(20),
  sort_by: z.string().optional(),
  sort_order: z.enum(['asc', 'desc']).default('desc'),
});
export type PaginationParams = z.infer<typeof PaginationParamsSchema>;

export const PaginationMetaSchema = z.object({
  page: z.number(),
  limit: z.number(),
  total: z.number(),
  total_pages: z.number(),
  has_next: z.boolean(),
  has_prev: z.boolean(),
});
export type PaginationMeta = z.infer<typeof PaginationMetaSchema>;

export const PaginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    meta: PaginationMetaSchema,
  });

// ============================================================================
// API Response Wrappers
// ============================================================================

export const SuccessResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    success: z.literal(true),
    data: dataSchema,
    timestamp: z.string().datetime(),
  });

export const ErrorResponseSchema = z.object({
  success: z.literal(false),
  error: ApiErrorSchema,
  timestamp: z.string().datetime(),
});

// ============================================================================
// LCopilot Issue Card Schema
// ============================================================================

export const ToleranceAppliedSchema = z.object({
  tolerance_percent: z.number(),
  source: z.string(),
  explicit: z.boolean(),
});
export type ToleranceApplied = z.infer<typeof ToleranceAppliedSchema>;

export const IssueCardSchema = z.object({
  id: z.string(),
  rule: z.string().optional(),
  title: z.string(),
  description: z.string(),
  severity: z.string(),
  priority: z.string().optional(),
  documentName: z.string().optional(),
  documentType: z.string().optional(),
  documents: z.array(z.string()).optional(),
  expected: z.string().optional(),
  actual: z.string().optional(),
  suggestion: z.string().optional(),
  field: z.string().optional(),
  ucpReference: z.string().optional().nullable(),
  ucpDescription: z.string().optional().nullable(),
  ruleset_domain: z.string().optional(),
  auto_generated: z.boolean().optional(),
  isbpReference: z.string().optional().nullable(),
  isbpDescription: z.string().optional().nullable(),
  tolerance_applied: ToleranceAppliedSchema.optional(),
  extraction_confidence: z.number().optional(),
  amendment_available: z.boolean().optional(),
});
export type IssueCard = z.infer<typeof IssueCardSchema>;

export const ReferenceIssueSchema = z.object({
  rule: z.string().optional(),
  title: z.string().optional(),
  severity: z.string().optional(),
  message: z.string().optional(),
  article: z.string().optional(),
  ruleset_domain: z.string().optional(),
});
export type ReferenceIssue = z.infer<typeof ReferenceIssueSchema>;

// ============================================================================
// AI Enrichment Schema
// ============================================================================

export const RuleReferenceSchema = z.object({
  rule_code: z.string(),
  title: z.string().optional(),
});
export type RuleReference = z.infer<typeof RuleReferenceSchema>;

export const AIEnrichmentPayloadSchema = z.object({
  summary: z.string().optional(),
  suggestions: z.array(z.string()).optional(),
  confidence: z.string().optional(),
  rule_references: z.union([
    z.array(z.string()),
    z.array(RuleReferenceSchema),
  ]).optional(),
  fallback_used: z.boolean().optional(),
});
export type AIEnrichmentPayload = z.infer<typeof AIEnrichmentPayloadSchema>;

// ============================================================================
// V2 Validation Pipeline Schemas
// ============================================================================

export const GateResultSchema = z.object({
  status: z.enum(['passed', 'blocked', 'warning']),
  can_proceed: z.boolean(),
  block_reason: z.string().optional().nullable(),
  completeness: z.number(),
  critical_completeness: z.number(),
  missing_critical: z.array(z.string()),
  missing_required: z.array(z.string()).optional(),
  blocking_issues: z.array(z.record(z.unknown())).optional(),
  warning_issues: z.array(z.record(z.unknown())).optional(),
});
export type GateResult = z.infer<typeof GateResultSchema>;

export const ExtractionSummarySchema = z.object({
  completeness: z.number(),
  critical_completeness: z.number(),
  missing_critical: z.array(z.string()),
  missing_required: z.array(z.string()).optional(),
  total_fields: z.number().optional(),
  extracted_fields: z.number().optional(),
});
export type ExtractionSummary = z.infer<typeof ExtractionSummarySchema>;

export const LCBaselineSchema = z.object({
  lc_number: z.string().optional().nullable(),
  lc_type: z.string().optional().nullable(),
  applicant: z.string().optional().nullable(),
  beneficiary: z.string().optional().nullable(),
  issuing_bank: z.string().optional().nullable(),
  advising_bank: z.string().optional().nullable(),
  amount: z.string().optional().nullable(),
  currency: z.string().optional().nullable(),
  expiry_date: z.string().optional().nullable(),
  issue_date: z.string().optional().nullable(),
  latest_shipment: z.string().optional().nullable(),
  port_of_loading: z.string().optional().nullable(),
  port_of_discharge: z.string().optional().nullable(),
  goods_description: z.string().optional().nullable(),
  incoterm: z.string().optional().nullable(),
  extraction_completeness: z.number(),
  critical_completeness: z.number(),
});
export type LCBaseline = z.infer<typeof LCBaselineSchema>;

// ============================================================================
// Sanctions Screening Schemas
// ============================================================================

export const SanctionsScreeningIssueSchema = z.object({
  party: z.string().nullable(),
  type: z.string().nullable(),
  status: z.enum(['match', 'potential_match', 'clear']),
  score: z.number().nullable(),
});
export type SanctionsScreeningIssue = z.infer<typeof SanctionsScreeningIssueSchema>;

export const SanctionsScreeningSummarySchema = z.object({
  screened: z.boolean(),
  parties_screened: z.number(),
  matches: z.number(),
  potential_matches: z.number(),
  clear: z.number(),
  should_block: z.boolean(),
  screened_at: z.string(),
  issues: z.array(SanctionsScreeningIssueSchema),
  error: z.string().optional(),
});
export type SanctionsScreeningSummary = z.infer<typeof SanctionsScreeningSummarySchema>;

// ============================================================================
// Validation Document Schema (Frontend-specific normalization)
// ============================================================================

export const ValidationDocumentSchema = z.object({
  id: z.string(),
  documentId: z.string(),
  name: z.string(),
  filename: z.string(),
  type: z.string(),
  typeKey: z.string().optional(),
  extractionStatus: z.string(),
  status: z.enum(['success', 'warning', 'error']),
  issuesCount: z.number(),
  extractedFields: z.record(z.unknown()),
});
export type ValidationDocument = z.infer<typeof ValidationDocumentSchema>;

// ============================================================================
// Full Validation Results Schema (LCopilot Response)
// ============================================================================

export const ValidationResultsSchema = z.object({
  jobId: z.string(),
  summary: ProcessingSummarySchema,
  documents: z.array(ValidationDocumentSchema),
  issues: z.array(IssueCardSchema),
  analytics: StructuredResultAnalyticsSchema,
  timeline: z.array(StructuredTimelineEntrySchema),
  structured_result: StructuredResultSchema,
  lc_structured: z.record(z.unknown()).optional().nullable(),
  ai_enrichment: AIEnrichmentPayloadSchema.optional().nullable(),
  telemetry: z.record(z.unknown()).optional(),
  reference_issues: z.array(ReferenceIssueSchema).optional(),
  
  // V2 Validation Pipeline additions
  validationBlocked: z.boolean().optional(),
  validationStatus: z.string().optional(),
  gateResult: GateResultSchema.optional().nullable(),
  extractionSummary: ExtractionSummarySchema.optional().nullable(),
  lcBaseline: LCBaselineSchema.optional().nullable(),
  complianceLevel: z.string().optional(),
  complianceCapReason: z.string().optional().nullable(),
  
  // Sanctions Screening additions
  sanctionsScreening: SanctionsScreeningSummarySchema.optional().nullable(),
  sanctionsBlocked: z.boolean().optional(),
  sanctionsBlockReason: z.string().optional().nullable(),
});
export type ValidationResults = z.infer<typeof ValidationResultsSchema>;

// ============================================================================
// API Response Validation Helper
// ============================================================================

/**
 * Safely parse and validate an API response against a Zod schema.
 * Returns the parsed data or throws a detailed error.
 */
export function validateApiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown,
  context?: string
): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    const errorMessage = result.error.errors
      .map((e) => `${e.path.join('.')}: ${e.message}`)
      .join('; ');
    throw new Error(
      `API Response Validation Failed${context ? ` (${context})` : ''}: ${errorMessage}`
    );
  }
  return result.data;
}

/**
 * Safely parse API response, returning null on failure instead of throwing.
 * Logs validation errors to console in development.
 */
export function safeValidateApiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown,
  context?: string
): T | null {
  const result = schema.safeParse(data);
  if (!result.success) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(
        `API Response Validation Warning${context ? ` (${context})` : ''}:`,
        result.error.errors
      );
    }
    return null;
  }
  return result.data;
}

// ============================================================================
// Schema Collections for Export
// ============================================================================

export type StructuredResultPayload = StructuredResult;

export const schemas = {
  // Health
  HealthResponse: HealthResponseSchema,
  ServiceStatus: ServiceStatusSchema,
  
  // Errors
  ApiError: ApiErrorSchema,
  ValidationError: ValidationErrorSchema,
  
  // Auth
  AuthToken: AuthTokenSchema,
  UserProfile: UserProfileSchema,
  
  // Files
  FileUploadRequest: FileUploadRequestSchema,
  FileUploadResponse: FileUploadResponseSchema,
  FileInfo: FileInfoSchema,
  
  // OCR
  OcrJobRequest: OcrJobRequestSchema,
  OcrJobResponse: OcrJobResponseSchema,
  OcrResult: OcrResultSchema,
  
  // Reports
  ReportRequest: ReportRequestSchema,
  ReportJob: ReportJobSchema,
  
  // Pagination
  PaginationParams: PaginationParamsSchema,
  PaginationMeta: PaginationMetaSchema,

  // Structured validation payload
  StructuredProcessingSummary: StructuredProcessingSummarySchema,
  StructuredResultDocument: StructuredResultDocumentSchema,
  StructuredResultIssue: StructuredResultIssueSchema,
  StructuredResultDocumentRiskEntry: DocumentRiskEntrySchema,
  StructuredResultAnalytics: StructuredResultAnalyticsSchema,
  StructuredResultTimelineEntry: TimelineEntrySchema,
  StructuredResult: StructuredResultSchema,
  
  // LCopilot-specific schemas
  IssueCard: IssueCardSchema,
  ReferenceIssue: ReferenceIssueSchema,
  AIEnrichmentPayload: AIEnrichmentPayloadSchema,
  ToleranceApplied: ToleranceAppliedSchema,
  
  // V2 Validation Pipeline
  GateResult: GateResultSchema,
  ExtractionSummary: ExtractionSummarySchema,
  LCBaseline: LCBaselineSchema,
  
  // Sanctions Screening
  SanctionsScreeningIssue: SanctionsScreeningIssueSchema,
  SanctionsScreeningSummary: SanctionsScreeningSummarySchema,
  
  // Full validation results
  ValidationDocument: ValidationDocumentSchema,
  ValidationResults: ValidationResultsSchema,
} as const;
