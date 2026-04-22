import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { buildValidationResponse } from '@/lib/lcopilot/resultsMapper';
import { logger } from '@/lib/logger';
import type {
  ValidationResults,
  IssueCard,
  ReferenceIssue,
  AIEnrichmentPayload,
  LcClassificationRequiredDocument,
} from '@/types/lcopilot';
// Schema-first validation (runtime type checking)
import { ValidationResultsSchema, safeValidateApiResponse } from '@shared/types';
// Unified feature flags
import { isLCopilotFeatureEnabled } from '@/config/featureFlagService';

const lcopilotLogger = logger.createLogger('LCopilot');

export interface ValidationRequest {
  files: File[];
  lcNumber?: string;
  notes?: string;
  documentTags?: Record<string, string>; // Map of filename to document type
  userType?: string; // 'exporter' or 'importer' or 'bank'
  workflowType?: string; // Legacy telemetry label (e.g. "export-lc-upload")
  /**
   * WorkflowType enum the backend persists on ValidationSession. Distinct
   * from the legacy `workflowType` telemetry string so callers don't have
   * to choose between the two. When provided, sent as the ?workflow_type=
   * URL query param, which the backend reads first.
   */
  workflowTypeEnum?: 'exporter_presentation' | 'importer_draft_lc' | 'importer_supplier_docs';
  metadata?: Record<string, any>; // Additional metadata (e.g., clientName, dateReceived)
  lcTypeOverride?: 'auto' | 'export' | 'import';
  intakeOnly?: boolean;
  /**
   * When true, the backend runs extraction only and stops BEFORE validation.
   * The response will have status="extraction_ready" and include extracted
   * documents + required_fields map. Use `useResumeValidate` to run the
   * validation pipeline against the user-confirmed field set.
   */
  extractOnly?: boolean;
  mode?: 'intake' | 'lc_intake';
  /**
   * Optional client-generated UUID for SSE progress streaming. When present,
   * sent as the X-Client-Request-ID header so the backend can publish pipeline
   * checkpoint events to a Redis pub/sub channel keyed by this id. The frontend
   * can subscribe to that channel via useValidationProgress BEFORE submitting
   * this request.
   */
  clientRequestId?: string;
  /** Previous extraction job_id — when provided, backend reuses cached
   *  extraction results for unchanged files instead of re-running vision LLM. */
  reuseJobId?: string;
}

import { z } from 'zod';

// ── Zod schemas for runtime validation of the extraction API response ──

const ExtractionReadyDocumentSchema = z.object({
  id: z.string().optional(),
  document_id: z.string().optional(),
  document_type: z.string().optional(),
  documentType: z.string().optional(),
  filename: z.string().optional(),
  name: z.string().optional(),
  extracted_fields: z.record(z.any()).optional(),
  extractedFields: z.record(z.any()).optional(),
  _field_details: z.record(z.any()).optional(),
}).passthrough();  // allow extra keys

const ExtractionReadyMissingDocumentSchema = z.object({
  type: z.string(),
  display_name: z.string().optional(),
  raw_text: z.string().optional(),
  reason_code: z.string().optional(),
});

const ExtractionReadyResponseSchema = z.object({
  status: z.literal('extraction_ready'),
  job_id: z.string().optional(),
  jobId: z.string().optional(),
  documents: z.array(ExtractionReadyDocumentSchema),
  lc_context: z.record(z.any()).optional(),
  lc_type: z.string().optional(),
  required_fields: z.object({
    schema_fields_by_doc_type: z.record(z.array(z.string())).optional(),
  }).optional(),
  missing_required_documents: z.array(ExtractionReadyMissingDocumentSchema).optional(),
  message: z.string().optional(),
  telemetry: z.record(z.any()).optional(),
}).passthrough();

/** Parse an extraction API response with Zod. Returns the typed payload
 *  on success, or null + console warning on shape mismatch. */
export function parseExtractionResponse(raw: unknown): ExtractionReadyResponse | null {
  const result = ExtractionReadyResponseSchema.safeParse(raw);
  if (result.success) return result.data as ExtractionReadyResponse;
  console.warn('[LCopilot] Extraction response shape mismatch:', result.error.format());
  // Fall back to the raw object so we don't hard-break the UI — the old
  // duck-typed path still works. Log the mismatch for debugging.
  return raw as ExtractionReadyResponse;
}

// ── TypeScript interfaces (kept for backward compat with existing imports) ──

export type ExtractionReadyDocument = z.infer<typeof ExtractionReadyDocumentSchema>;
export type ExtractionReadyMissingDocument = z.infer<typeof ExtractionReadyMissingDocumentSchema>;
export type ExtractionReadyResponse = z.infer<typeof ExtractionReadyResponseSchema>;

export interface ValidationResponse {
  jobId?: string;
  request_id?: string;
  status: 'created' | 'uploading' | 'processing' | 'completed' | 'failed' | 'queued' | 'error' | 'blocked' | 'resolved' | 'invalid' | 'ambiguous' | 'extraction_ready';
  job_id?: string; // temporary compatibility field
  block_reason?: string;
  error?: any;
  detected_documents?: Array<{ type: string; filename?: string; document_type_resolution?: string }>;
  // extract_only response fields
  documents?: ExtractionReadyDocument[];
  lc_context?: Record<string, any>;
  lc_type?: string;
  required_fields?: {
    baseline_required?: string[];
    by_document_type?: Record<string, string[]>;
  };
  lc_detection?: {
    lc_type?: string;
    confidence?: number;
    reason?: string;
    is_draft?: boolean;
    source?: string;
    confidence_mode?: string;
    detection_basis?: string;
  };
  continuation_allowed?: boolean;
  intake_mode?: boolean;
  is_lc?: boolean;
  lc_summary?: Record<string, any>;
  required_document_types?: string[];
  documents_required?: string[];
  required_documents_detailed?: LcClassificationRequiredDocument[];
  requirement_conditions?: string[];
  unmapped_requirements?: string[];
  special_conditions?: string[];
  message?: string;
  action_required?: string;
  redirect_url?: string;
}

export interface JobStatus {
  jobId: string;
  status: 'created' | 'uploading' | 'processing' | 'completed' | 'failed' | 'queued' | 'error';
  progress?: number;
  error?: string;
  results?: any;
  lcNumber?: string;
}

export interface PackageResponse {
  downloadUrl: string;
  fileName: string;
  fileSize: number;
  expiresAt: string;
}

export interface ValidationError {
  message: string;
  type: 'rate_limit' | 'validation' | 'network' | 'server' | 'unknown' | 'quota' | 'parsing';
  statusCode?: number;
  errorCode?: string;  // Backend error_code for actionable errors
  quota?: {
    used: number;
    limit: number | null;
    remaining: number | null;
  };
  nextActionUrl?: string | null;
}

type GetResultsOptions = {
  suppressError?: boolean;
};

const TERMINAL_JOB_STATUSES = new Set(['completed', 'failed', 'error']);
const VALIDATE_RETRYABLE_STATUS_CODES = new Set([502, 503, 504]);
const VALIDATE_RETRY_DELAYS_MS = [1500];

const normalizeJobStatus = (status?: string | null): string =>
  (status || '').toString().toLowerCase();

const hasCanonicalStructuredResult = (value: unknown): value is { structured_result: { version: string } } =>
  Boolean(
    value &&
      typeof value === 'object' &&
      (value as { structured_result?: { version?: unknown } }).structured_result?.version === 'structured_result_v1',
  );

const normalizeValidationResultsResponse = (
  payload: unknown,
  jobId: string,
): ValidationResults | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  if (hasCanonicalStructuredResult(payload)) {
    const candidate = payload as Partial<ValidationResults>;
    const alreadyNormalized =
      typeof candidate.jobId === 'string' &&
      Array.isArray(candidate.documents) &&
      Array.isArray(candidate.issues) &&
      Array.isArray(candidate.timeline) &&
      Boolean(candidate.summary) &&
      Boolean(candidate.analytics);

    if (alreadyNormalized) {
      return candidate as ValidationResults;
    }

    return buildValidationResponse(payload);
  }

  if ((payload as { version?: unknown }).version === 'structured_result_v1') {
    return buildValidationResponse({
      jobId,
      job_id: jobId,
      structured_result: payload,
    });
  }

  return null;
};

const isAuthHydrationError = (error: ValidationError | null | undefined): boolean => {
  if (!error) {
    return false;
  }

  if (error.statusCode === 401 || error.statusCode === 403) {
    return true;
  }

  const message = String(error.message || '').toLowerCase();
  return (
    message.includes('not authenticated') ||
    message.includes('unauthorized') ||
    message.includes('forbidden') ||
    message.includes('auth')
  );
};

const toResultsError = (err: any): ValidationError => {
  if (err?.type && err?.message) {
    return err as ValidationError;
  }

  if (err?.response) {
    const { status, data } = err.response;
    return {
      type: 'server',
      message: data?.message || data?.detail || 'Failed to get validation results.',
      statusCode: status,
      errorCode: data?.detail?.error_code || data?.error_code,
    };
  }

  if (err instanceof Error) {
    return {
      type: 'parsing',
      message: err.message || 'Failed to parse validation results.',
    };
  }

  return {
    type: 'network',
    message: 'Network error while fetching results.',
  };
};

const waitFor = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

export const shouldRetryValidationRequest = (
  err: unknown,
  attempt: number,
  maxAttempts: number,
): boolean => {
  if (attempt >= maxAttempts) {
    return false;
  }

  const statusCode = Number((err as { response?: { status?: number } })?.response?.status ?? 0);
  if (VALIDATE_RETRYABLE_STATUS_CODES.has(statusCode)) {
    return true;
  }

  const errorCode = String((err as { code?: string })?.code || '').toUpperCase();
  return errorCode === 'ECONNABORTED' || errorCode === 'ERR_NETWORK';
};

const getValidationRetryDelayMs = (attempt: number): number => {
  const index = Math.max(0, Math.min(attempt - 1, VALIDATE_RETRY_DELAYS_MS.length - 1));
  return VALIDATE_RETRY_DELAYS_MS[index] ?? 0;
};

export const fetchValidationResults = async (jobId: string): Promise<ValidationResults> => {
  const response = await api.get(`/api/results/${jobId}`);
  const payload = response.data;

  if (payload?.telemetry?.timings) {
    console.group('⏱️ Validation Timing Breakdown');
    console.table(payload.telemetry.timings);
    console.log(`Total backend time: ${payload.telemetry.total_time_seconds}s`);
    console.groupEnd();
  }

  lcopilotLogger.debug('API response received', { jobId });

  const normalized = normalizeValidationResultsResponse(payload, jobId);
  if (!normalized) {
    throw new Error('Results payload missing structured_result');
  }

  if (isLCopilotFeatureEnabled('schema_validation')) {
    const validationResult = safeValidateApiResponse(
      ValidationResultsSchema,
      normalized,
      `results/${jobId}`
    );
    if (!validationResult) {
      lcopilotLogger.warn('Schema validation warning - response may have unexpected shape', { jobId });
    }
  }

  return normalized;
};

// Hook for validating documents
export const useValidate = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);

  const validate = useCallback(async (request: ValidationRequest): Promise<ValidationResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();

      // Add files
      request.files.forEach((file) => {
        formData.append('files', file);
      });

      // Add metadata
      if (request.lcNumber) {
        formData.append('lc_number', request.lcNumber);
      }
      if (request.notes) {
        formData.append('notes', request.notes);
      }

      // Add document tags
      if (request.documentTags) {
        formData.append('document_tags', JSON.stringify(request.documentTags));
      }

      // Add user and workflow type for enhanced validation
      formData.append('user_type', request.userType || 'exporter');
      formData.append('workflow_type', request.workflowType || 'export-lc-upload');

      // Add metadata if provided
      if (request.metadata) {
        formData.append('metadata', JSON.stringify(request.metadata));
      }

      if (request.lcTypeOverride && request.lcTypeOverride !== 'auto') {
        formData.append('lc_type_override', request.lcTypeOverride);
      }

      if (request.intakeOnly) {
        formData.append('intake_only', 'true');
      }
      if (request.extractOnly) {
        formData.append('extract_only', 'true');
      }
      if (request.mode) {
        formData.append('mode', request.mode);
      }
      if (request.reuseJobId) {
        formData.append('reuse_job_id', request.reuseJobId);
      }

      lcopilotLogger.debug('Making validation request', {
        filesCount: request.files.length,
        intakeOnly: request.intakeOnly,
        mode: request.mode,
      });

      const maxAttempts = VALIDATE_RETRY_DELAYS_MS.length + 1;
      let response = null as Awaited<ReturnType<typeof api.post>> | null;
      let attempt = 0;
      let lastError: any = null;

      const validateHeaders: Record<string, string> = {
        'Content-Type': 'multipart/form-data',
      };
      if (request.clientRequestId) {
        validateHeaders['X-Client-Request-ID'] = request.clientRequestId;
      }

      const validateUrl = request.workflowTypeEnum
        ? `/api/validate/?workflow_type=${encodeURIComponent(request.workflowTypeEnum)}`
        : '/api/validate/';

      while (attempt < maxAttempts && !response) {
        attempt += 1;
        try {
          // Trailing slash avoids the Render 307 redirect to /api/validate/
          // which strips CORS headers and forces a retry.
          response = await api.post(validateUrl, formData, {
            headers: validateHeaders,
          });
        } catch (err: any) {
          lastError = err;
          if (!shouldRetryValidationRequest(err, attempt, maxAttempts)) {
            throw err;
          }

          const retryDelayMs = getValidationRetryDelayMs(attempt);
          lcopilotLogger.warn('Transient /api/validate failure, retrying request', {
            attempt,
            maxAttempts,
            retryDelayMs,
            statusCode: err?.response?.status,
            code: err?.code,
          });
          await waitFor(retryDelayMs);
        }
      }

      if (!response) {
        throw lastError || new Error('Validation request failed before a response was received.');
      }

      lcopilotLogger.debug('Validation response received', { jobId: response.data?.jobId });

      // 🔍 TIMING TELEMETRY - See where time is spent during validation
      if (response.data?.telemetry?.timings) {
        console.group('⏱️ Validation Timing Breakdown');
        console.table(response.data.telemetry.timings);
        console.log(`Total backend time: ${response.data.telemetry.total_time_seconds}s`);
        console.groupEnd();
      }

      return response.data;
    } catch (err: any) {
      // Log full error details for debugging
      const errorDetails = {
        error: {
          message: err.message,
          name: err.name,
          stack: err.stack,
        },
        response: err.response ? {
          status: err.response.status,
          statusText: err.response.statusText,
          data: err.response.data,
          headers: err.response.headers,
        } : null,
        request: err.request ? {
          url: err.config?.url,
          method: err.config?.method,
          baseURL: err.config?.baseURL,
        } : null,
      };
      lcopilotLogger.error('Validation error', errorDetails);
      
      let validationError: ValidationError;

      if (err.response) {
        const { status, data } = err.response;
        const detail = data?.detail ?? data;

        if (status === 402) {
          const quotaData = detail?.quota;
          validationError = {
            type: 'quota',
            message: detail?.message || 'Your validation quota has been reached.',
            statusCode: status,
            quota: quotaData
              ? {
                  used: quotaData.used ?? 0,
                  limit: quotaData.limit ?? null,
                  remaining: quotaData.remaining ?? null,
                }
              : undefined,
            nextActionUrl: detail?.next_action_url ?? detail?.nextActionUrl ?? null,
          };
        } else if (status === 429) {
          validationError = {
            type: 'rate_limit',
            message: detail?.message || 'Too many requests. Please try again later.',
            statusCode: status,
          };
        } else if (status >= 400 && status < 500) {
          validationError = {
            type: 'validation',
            message: detail?.message || 'Validation request failed.',
            statusCode: status,
            errorCode: detail?.error_code || detail?.errorCode,
          };
        } else {
          validationError = {
            type: 'server',
            message: detail?.message || 'Server error occurred.',
            statusCode: status,
            errorCode: detail?.error_code || detail?.errorCode,
          };
        }
      } else if (err.request) {
        validationError = {
          type: 'network',
          message: 'Network error. Please check your connection.',
        };
      } else {
        validationError = {
          type: 'unknown',
          message: err.message || 'An unexpected error occurred.',
        };
      }

      setError(validationError);
      throw validationError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    validate,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};

// =============================================================================
// useResumeValidate — runs validation against a previously-extracted session
// =============================================================================
//
// After /api/validate?extract_only=true returns an extraction_ready job_id, the
// user reviews / confirms fields on the extraction review screen, then this
// hook POSTs /api/validate/resume/{jobId} with their corrections. The backend
// merges the overrides into the extracted context and runs the full validation
// pipeline (tiered AI + deterministic rules + Opus veto).
export interface ResumeValidateRequest {
  jobId: string;
  /**
   * Map of { doc_key: { field_name: value } }. doc_key matches by document id,
   * document_id, or filename (first match wins on the backend).
   */
  fieldOverrides?: Record<string, Record<string, any>>;
  /** Optional passthrough payload (metadata, doc_type, etc). */
  payload?: Record<string, any>;
}

export const useResumeValidate = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);

  const resumeValidate = useCallback(
    async (request: ResumeValidateRequest): Promise<any> => {
      if (!request.jobId) {
        throw new Error('resumeValidate requires a jobId');
      }
      setIsLoading(true);
      setError(null);
      try {
        const body = {
          field_overrides: request.fieldOverrides || {},
          payload: request.payload || {},
        };
        const response = await api.post(`/api/validate/resume/${request.jobId}`, body, {
          headers: { 'Content-Type': 'application/json' },
        });
        return response.data;
      } catch (err: any) {
        const validationError: ValidationError = {
          type: 'server',
          message: err?.response?.data?.detail || err?.message || 'Resume validation failed',
          statusCode: err?.response?.status,
        };
        setError(validationError);
        throw validationError;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return {
    resumeValidate,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};

// Hook for polling job status
export const useJob = (jobId: string | null) => {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastStatusRef = useRef<string | null>(null);

  const pollJob = useCallback(async () => {
    if (!jobId) return;

    setIsPolling(true);
    setError(null);

    try {
      const response = await api.get(`/api/jobs/${jobId}`);
      const status: JobStatus = response.data;

      // Normalize status to lowercase for reliable comparisons
      const normalizedStatus = (status.status || '').toString().toLowerCase() as JobStatus['status'];
      const previousStatus = lastStatusRef.current;
      // Overwrite the status we store with normalized to keep UI logic consistent
      status.status = normalizedStatus;

      if (normalizedStatus !== previousStatus) {
        lcopilotLogger.debug('Job status update', { jobId, status: normalizedStatus });
        lastStatusRef.current = normalizedStatus;
      }

      setJobStatus(status);

      const isTerminal =
        normalizedStatus === 'completed' || normalizedStatus === 'failed' || normalizedStatus === 'error';
      const isActive =
        normalizedStatus === 'processing' ||
        normalizedStatus === 'created' ||
        normalizedStatus === 'queued' ||
        normalizedStatus === 'uploading';

      // Continue polling if job is still active (processing, uploading, queued, created)
      if (isActive && !isTerminal) {
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current);
        }
        pollTimeoutRef.current = setTimeout(() => {
          pollJob();
        }, 2000); // Poll every 2 seconds
      } else {
        lcopilotLogger.debug('Job polling stopped', { jobId, status: normalizedStatus });
        setIsPolling(false);
      }
    } catch (err: any) {
      let validationError: ValidationError;

      if (err.response) {
        const { status, data } = err.response;
        validationError = {
          type: 'server',
          message: data.message || 'Failed to get job status.',
          statusCode: status,
        };
      } else {
        validationError = {
          type: 'network',
          message: 'Network error while checking job status.',
        };
      }

      setError(validationError);
      setIsPolling(false);
    }
  }, [jobId]);

  // Start polling when jobId is provided
  useEffect(() => {
    if (jobId && !isPolling) {
      pollJob();
    }
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [jobId, isPolling, pollJob]);

  return {
    jobStatus,
    isPolling,
    error,
    startPolling: pollJob,
    clearError: () => setError(null),
  };
};

// Hook for getting validation results
export const useResults = (currentJobId?: string | null) => {
  const [results, setResults] = useState<ValidationResults | null>(null);
  const [resultsJobId, setResultsJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (currentJobId === undefined) {
      return;
    }

    if (!currentJobId) {
      setResults(null);
      setResultsJobId(null);
      setError(null);
      return;
    }

    const cached = normalizeValidationResultsResponse(
      queryClient.getQueryData(['results', currentJobId]) ?? null,
      currentJobId,
    );
    setResults(cached);
    setResultsJobId(currentJobId);
    setError(null);
  }, [currentJobId, queryClient]);

  const getResults = useCallback(async (jobId: string, options?: GetResultsOptions): Promise<ValidationResults> => {
    lcopilotLogger.debug('Fetching results', { jobId });
    setIsLoading(true);
    if (!options?.suppressError) {
      setError(null);
    }

    try {
      // Invalidate any cached results first
      await queryClient.invalidateQueries({ queryKey: ['results', jobId] });
      
      // Direct API call with proper auth - no race conditions
      const response = await api.get(`/api/results/${jobId}`);
      const payload = response.data;
      
      // 🔍 TIMING TELEMETRY - See where time is spent
      if (payload?.telemetry?.timings) {
        console.group('⏱️ Validation Timing Breakdown');
        console.table(payload.telemetry.timings);
        console.log(`Total backend time: ${payload.telemetry.total_time_seconds}s`);
        console.groupEnd();
      }
      
      lcopilotLogger.debug('API response received', { jobId });
      
      const normalized = normalizeValidationResultsResponse(payload, jobId);
      if (!normalized) {
        throw new Error('Results payload missing structured_result');
      }

      // Schema-first validation: verify response matches expected contract
      // Controlled by 'schema_validation' feature flag (enabled in dev by default)
      if (isLCopilotFeatureEnabled('schema_validation')) {
        const validationResult = safeValidateApiResponse(
          ValidationResultsSchema,
          normalized,
          `results/${jobId}`
        );
        if (!validationResult) {
          lcopilotLogger.warn('Schema validation warning - response may have unexpected shape', { jobId });
        }
      }

      setResults(normalized);
      lcopilotLogger.debug('Results fetched', { jobId, issues: normalized.issues?.length ?? 0 });
      
      // Update cache with the fetched data
      queryClient.setQueryData(['results', jobId], normalized);
      
      return normalized;
    } catch (err: any) {
      let validationError: ValidationError;

      if (err.response) {
        // Axios error with response
        const { status, data } = err.response;
        validationError = {
          type: 'server',
          message: data?.message || data?.detail || 'Failed to get validation results.',
          statusCode: status,
          errorCode: data?.detail?.error_code || data?.error_code,
        };
      } else if (err instanceof Error) {
        // JavaScript Error (e.g. from buildValidationResponse)
        validationError = {
          type: 'parsing',
          message: err.message || 'Failed to parse validation results.',
        };
      } else {
        validationError = {
          type: 'network',
          message: 'Network error while fetching results.',
        };
      }

      setError(validationError);
      lcopilotLogger.error('Failed to fetch results', { jobId, error: validationError?.message });
      throw validationError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    results,
    structuredResult: results?.structured_result ?? null,
    getResults,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};

export const useCanonicalJobResult = (
  jobId: string | null,
  options: {
    enabled?: boolean;
    fallbackDelayMs?: number;
    terminalResultsTimeoutMs?: number;
    authRetryDelayMs?: number;
  } = {},
) => {
  const enabled = (options.enabled ?? true) && !!jobId;
  const fallbackDelayMs = options.fallbackDelayMs ?? 1000;
  const terminalResultsTimeoutMs = options.terminalResultsTimeoutMs ?? 8000;
  const authRetryDelayMs = options.authRetryDelayMs ?? 1200;
  const queryClient = useQueryClient();
  const { jobStatus, isPolling, error: jobError } = useJob(enabled ? jobId : null);
  const [results, setResults] = useState<ValidationResults | null>(null);
  const [resultsJobId, setResultsJobId] = useState<string | null>(null);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [resultsError, setResultsError] = useState<ValidationError | null>(null);
  const [terminalResultsTimedOut, setTerminalResultsTimedOut] = useState(false);
  const [authRetryCount, setAuthRetryCount] = useState(0);
  const inFlightRef = useRef<Promise<ValidationResults | null> | null>(null);

  useEffect(() => {
    if (!jobId) {
      setResults(null);
      setResultsJobId(null);
      setResultsError(null);
      return;
    }

    const cached = normalizeValidationResultsResponse(
      queryClient.getQueryData(['results', jobId]) ?? null,
      jobId,
    );
    setResults(cached);
    setResultsJobId(jobId);
    setResultsError(null);
    setAuthRetryCount(0);
    inFlightRef.current = null;
  }, [jobId, queryClient]);

  const refreshResults = useCallback(
    async (reason: 'auto' | 'manual' = 'manual'): Promise<ValidationResults | null> => {
      if (!enabled || !jobId) {
        return null;
      }

      if (inFlightRef.current) {
        return inFlightRef.current;
      }

      const status = normalizeJobStatus(jobStatus?.status);
      const suppressError =
        reason !== 'manual' &&
        (!TERMINAL_JOB_STATUSES.has(status) || !terminalResultsTimedOut);

      const request = (async () => {
        setIsLoadingResults(true);
        if (!suppressError) {
          setResultsError(null);
        }

        try {
          const data = await fetchValidationResults(jobId);
          queryClient.setQueryData(['results', jobId], data);
          setResults(data);
          setResultsJobId(jobId);
          setResultsError(null);
          setAuthRetryCount(0);
          setTerminalResultsTimedOut(false);
          return data;
        } catch (err: any) {
          const validationError = toResultsError(err);
          const authHydrationFailure = reason === 'auto' && isAuthHydrationError(validationError) && authRetryCount < 3;
          if (authHydrationFailure) {
            setAuthRetryCount((count) => count + 1);
            return null;
          }
          if (!suppressError) {
            setResultsError(validationError);
            throw validationError;
          }
          return null;
        } finally {
          setIsLoadingResults(false);
          inFlightRef.current = null;
        }
      })();

      inFlightRef.current = request;
      return request;
    },
    [authRetryCount, enabled, jobId, jobStatus?.status, queryClient, terminalResultsTimedOut],
  );

  const cachedResults =
    jobId
      ? normalizeValidationResultsResponse(queryClient.getQueryData(['results', jobId]) ?? null, jobId)
      : null;

  const visibleResults =
    jobId && resultsJobId !== jobId
      ? cachedResults
      : results ?? cachedResults;

  const normalizedStatus = normalizeJobStatus(jobStatus?.status);
  const isTerminal = TERMINAL_JOB_STATUSES.has(normalizedStatus);
  const isAwaitingInitialState = !jobStatus && !jobError && !resultsError;
  const isAuthRetrying = enabled && isTerminal && !visibleResults && authRetryCount > 0 && authRetryCount <= 3 && !resultsError;
  const isTerminalWithoutResults = enabled && isTerminal && !visibleResults && !isAuthRetrying;

  useEffect(() => {
    if (!enabled || !isTerminalWithoutResults) {
      setTerminalResultsTimedOut(false);
      return;
    }

    const timeoutId = setTimeout(() => {
      setTerminalResultsTimedOut(true);
    }, terminalResultsTimeoutMs);

    return () => clearTimeout(timeoutId);
  }, [enabled, isTerminalWithoutResults, terminalResultsTimeoutMs]);

  useEffect(() => {
    if (!enabled || !jobId || visibleResults || isLoadingResults || !isTerminal) {
      return;
    }

    const delayMs = authRetryCount > 0 ? authRetryDelayMs : 0;
    const timeoutId = setTimeout(() => {
      refreshResults('auto').catch(() => {
        // surfaced through hook state once the job is terminal
      });
    }, delayMs);

    return () => clearTimeout(timeoutId);
  }, [authRetryCount, authRetryDelayMs, enabled, isLoadingResults, isTerminal, jobId, refreshResults, visibleResults]);

  useEffect(() => {
    if (!enabled || !jobId || visibleResults || isLoadingResults || jobStatus?.status) {
      return;
    }

    const timeoutId = setTimeout(() => {
      refreshResults('auto').catch(() => {
        // keep waiting until either job status or results become available
      });
    }, fallbackDelayMs);

    return () => clearTimeout(timeoutId);
  }, [enabled, fallbackDelayMs, isLoadingResults, jobId, jobStatus?.status, refreshResults, visibleResults]);

  const isFinalizingResults =
    enabled &&
    isTerminalWithoutResults &&
    !terminalResultsTimedOut &&
    !resultsError;

  return {
    jobStatus,
    isPolling,
    jobError,
    results: visibleResults,
    isLoading:
      enabled &&
      !visibleResults &&
      !terminalResultsTimedOut &&
      (isLoadingResults || isFinalizingResults || (!isTerminal && isPolling) || isAwaitingInitialState),
    resultsError: visibleResults ? null : resultsError ?? jobError,
    refreshResults,
    isFinalizingResults,
    terminalResultsTimedOut,
  };
};

// Hook for generating customs-ready package
export const usePackage = () => {
  const [packageInfo, setPackageInfo] = useState<PackageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);

  const generatePackage = useCallback(async (jobId: string): Promise<PackageResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post(`/api/package/${jobId}`);
      const packageResponse: PackageResponse = response.data;

      setPackageInfo(packageResponse);
      return packageResponse;
    } catch (err: any) {
      let validationError: ValidationError;

      if (err.response) {
        const { status, data } = err.response;

        if (status === 429) {
          validationError = {
            type: 'rate_limit',
            message: data.message || 'Too many requests. Please try again later.',
            statusCode: status,
          };
        } else if (status >= 400 && status < 500) {
          validationError = {
            type: 'validation',
            message: data.message || 'Package generation failed.',
            statusCode: status,
          };
        } else {
          validationError = {
            type: 'server',
            message: data.message || 'Server error occurred.',
            statusCode: status,
          };
        }
      } else if (err.request) {
        validationError = {
          type: 'network',
          message: 'Network error. Please check your connection.',
        };
      } else {
        validationError = {
          type: 'unknown',
          message: err.message || 'An unexpected error occurred.',
        };
      }

      setError(validationError);
      throw validationError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const downloadPackage = useCallback(async (downloadUrl: string, fileName: string) => {
    try {
      const response = await fetch(downloadUrl);
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch (err) {
      lcopilotLogger.error('Failed to download package:', err);
      throw new Error('Failed to download package');
    }
  }, []);

  return {
    packageInfo,
    generatePackage,
    downloadPackage,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};

export interface ValidationHistoryItem {
  jobId: string;
  status: string;
  progress?: number;
  lcNumber?: string;
  createdAt?: string;
  completedAt?: string;
  documentCount?: number;
  discrepancyCount?: number;
  supplierName?: string;
  invoiceAmount?: string;
  invoiceCurrency?: string;
  documentStatus?: {
    success?: number;
    warning?: number;
    error?: number;
  } | null;
  topIssue?: {
    title?: string;
    severity?: string;
    documentName?: string;
    rule?: string;
  } | null;
}

export interface ValidationHistoryResponse {
  jobs: ValidationHistoryItem[];
  total: number;
}

// Hook for fetching validation history
export const useValidationHistory = (limit: number = 10, statusFilter?: string) => {
  const [history, setHistory] = useState<ValidationHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);

  const fetchHistory = useCallback(async (): Promise<ValidationHistoryItem[]> => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      if (statusFilter) {
        params.append('status_filter', statusFilter);
      }

      const response = await api.get<ValidationHistoryResponse>(`/api/jobs?${params.toString()}`);
      const historyItems = response.data.jobs || [];

      setHistory(historyItems);
      return historyItems;
    } catch (err: any) {
      let validationError: ValidationError;

      if (err.response) {
        const { status, data } = err.response;
        validationError = {
          type: 'server',
          message: data.message || 'Failed to fetch validation history.',
          statusCode: status,
        };
      } else {
        validationError = {
          type: 'network',
          message: 'Network error while fetching validation history.',
        };
      }

      setError(validationError);
      throw validationError;
    } finally {
      setIsLoading(false);
    }
  }, [limit, statusFilter]);

  useEffect(() => {
    fetchHistory().catch(() => {
      // Error already handled in fetchHistory
    });
  }, [fetchHistory]);

  return {
    history,
    isLoading,
    error,
    refetch: fetchHistory,
    clearError: () => setError(null),
  };
};
