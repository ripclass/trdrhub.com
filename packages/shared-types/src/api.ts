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
// Schema Collections for Export
// ============================================================================

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
} as const;
