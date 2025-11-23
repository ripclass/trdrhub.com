import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '@/api/client';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';
import type {
  ValidationResults,
  IssueCard,
  ReferenceIssue,
  AIEnrichmentPayload,
} from '@/types/lcopilot';

export interface ValidationRequest {
  files: File[];
  lcNumber?: string;
  notes?: string;
  documentTags?: Record<string, string>; // Map of filename to document type
  userType?: string; // 'exporter' or 'importer' or 'bank'
  workflowType?: string; // Specific workflow type
  metadata?: Record<string, any>; // Additional metadata (e.g., clientName, dateReceived)
  lcTypeOverride?: 'auto' | 'export' | 'import';
}

export interface ValidationResponse {
  jobId: string;
  request_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'queued' | 'error';
  job_id?: string; // temporary compatibility field
}

export interface JobStatus {
  jobId: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'queued' | 'error';
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
  type: 'rate_limit' | 'validation' | 'network' | 'server' | 'unknown' | 'quota';
  statusCode?: number;
  quota?: {
    used: number;
    limit: number | null;
    remaining: number | null;
  };
  nextActionUrl?: string | null;
}

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

      // Debug: Log request details
      console.log('🚀 [DEBUG] Making validation request:', {
        url: '/api/validate',
        baseURL: api.defaults.baseURL,
        fullURL: `${api.defaults.baseURL}/api/validate`,
        filesCount: request.files.length,
        fileNames: request.files.map(f => f.name),
        formDataKeys: Array.from(formData.keys()),
      });

      const response = await api.post('/api/validate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('✅ [DEBUG] Validation response received:', {
        status: response.status,
        hasData: !!response.data,
        jobId: response.data?.jobId || response.data?.job_id,
      });

      return response.data;
    } catch (err: any) {
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
          };
        } else {
          validationError = {
            type: 'server',
            message: detail?.message || 'Server error occurred.',
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

  return {
    validate,
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
        console.log('[LCopilot][Job] status update', {
          jobId,
          status: normalizedStatus,
          previousStatus,
          progress: status.progress,
        });
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
        console.log('[LCopilot][Job] polling stopped', {
          jobId,
          status: normalizedStatus,
          reason: isTerminal ? 'terminal' : 'inactive',
        });
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
export const useResults = () => {
  const [results, setResults] = useState<ValidationResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);

  const getResults = useCallback(async (jobId: string): Promise<ValidationResults> => {
    console.log('[LCopilot][Results] fetching results', { jobId });
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/results/${jobId}`);
      const normalized: ValidationResults = buildValidationResponse(response.data);

      if (!normalized.structured_result && response.data?.structured_result) {
        normalized.structured_result = response.data.structured_result;
      }

      if (normalized.ai_enrichment && !normalized.aiEnrichment) {
        normalized.aiEnrichment = normalized.ai_enrichment;
      }

      setResults(normalized);
      console.log('[LCopilot][Results] fetched results', {
        jobId,
        hasStructuredResult: !!normalized.structured_result,
        hasLcStructured: !!(normalized.structured_result?.lc_structured || normalized.lc_structured),
        documents: normalized.documents?.length ?? 0,
        issues: normalized.issues?.length ?? 0,
      });
      return normalized;
    } catch (err: any) {
      let validationError: ValidationError;

      if (err.response) {
        const { status, data } = err.response;
        validationError = {
          type: 'server',
          message: data.message || 'Failed to get validation results.',
          statusCode: status,
        };
      } else {
        validationError = {
          type: 'network',
          message: 'Network error while fetching results.',
        };
      }

      setError(validationError);
      console.warn('[LCopilot][Results] failed to fetch results', {
        jobId,
        error: validationError?.message,
        statusCode: validationError?.statusCode,
      });
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
      console.error('Failed to download package:', err);
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
