import { useState, useCallback, useEffect } from 'react';
import { api } from '@/api/client';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';

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
  status: 'created' | 'processing' | 'completed' | 'failed';
  job_id?: string; // temporary compatibility field
}

export interface JobStatus {
  jobId: string;
  status: 'created' | 'processing' | 'completed' | 'failed';
  progress?: number;
  error?: string;
  results?: any;
  lcNumber?: string;
}

export interface IssueCard {
  id: string;
  rule?: string;
  title: string;
  description: string;
  severity: string;
  documentName?: string;
  documentType?: string;
  documents?: string[];
  expected?: string;
  actual?: string;
  suggestion?: string;
  field?: string;
  ucpReference?: string;
}

export interface ReferenceIssue {
  rule?: string;
  title?: string;
  severity?: string;
  message?: string;
  article?: string;
  ruleset_domain?: string;
}

export interface AIEnrichmentPayload {
  summary?: string;
  suggestions?: string[];
  confidence?: string;
  rule_references?: Array<{
    rule_code: string;
    title?: string;
  }>;
}

export interface SeverityBreakdown {
  critical: number;
  major: number;
  medium: number;
  minor: number;
}

export interface ProcessingSummaryPayload {
  total_documents: number;
  successful_extractions: number;
  failed_extractions: number;
  total_issues: number;
  severity_breakdown: SeverityBreakdown;
}

export interface ValidationDocument {
  id: string;
  documentId: string;
  name: string;
  filename: string;
  type: string;
  typeKey?: string;
  extractionStatus: string;
  status: 'success' | 'warning' | 'error';
  issuesCount: number;
  extractedFields: Record<string, any>;
}

export interface DocumentRiskEntry {
  document_id?: string;
  filename?: string;
  risk?: string;
}

export interface ValidationAnalytics {
  compliance_score: number;
  issue_counts: SeverityBreakdown;
  document_risk: DocumentRiskEntry[];
}

export interface TimelineEvent {
  title: string;
  status: string;
  description?: string;
  timestamp?: string;
}

export interface ValidationResults {
  jobId: string;
  summary: ProcessingSummaryPayload;
  documents: ValidationDocument[];
  issues: IssueCard[];
  analytics: ValidationAnalytics;
  timeline: TimelineEvent[];
  results?: any[];
  discrepancies?: any[];
  lcNumber?: string;
  completedAt?: string;
  status?: string;
  reference_issues?: ReferenceIssue[];
  ai_enrichment?: AIEnrichmentPayload;
  aiEnrichment?: AIEnrichmentPayload;
  extracted_data?: Record<string, any>;
  extraction_status?: 'success' | 'partial' | 'empty' | 'error' | 'unknown';
  lc_type?: string;
  lc_type_reason?: string;
  lc_type_confidence?: number;
  lc_type_source?: string;
  overallStatus?: 'success' | 'error' | 'warning';
  packGenerated?: boolean;
  processingTime?: string;
  processing_time?: string;
  processingTimeMinutes?: string;
  processedAt?: string;
  processingCompletedAt?: string;
  processed_at?: string;
  processing_summary?: ProcessingSummaryPayload;
  issue_cards?: IssueCard[];
  overall_status?: string;
  structured_result?: {
    processing_summary?: ProcessingSummaryPayload;
    documents?: any[];
    issues?: any[];
    analytics?: any;
    timeline?: any[];
  };
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

      const response = await api.post('/api/validate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
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

  const pollJob = useCallback(async () => {
    if (!jobId) return;

    setIsPolling(true);
    setError(null);

    try {
      const response = await api.get(`/api/jobs/${jobId}`);
      const status: JobStatus = response.data;

      setJobStatus(status);

      // Continue polling if job is still processing
      if (status.status === 'processing' || status.status === 'created') {
        setTimeout(() => {
          pollJob();
        }, 2000); // Poll every 2 seconds
      } else {
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
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/results/${jobId}`);
      const normalized: ValidationResults = buildValidationResponse(response.data);
      if (normalized.ai_enrichment && !normalized.aiEnrichment) {
        normalized.aiEnrichment = normalized.ai_enrichment;
      }

      setResults(normalized);
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
      throw validationError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    results,
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
