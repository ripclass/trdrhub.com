import { api } from './client';

export interface BankJob {
  id: string;
  job_id: string;
  client_name?: string;
  lc_number?: string;
  date_received?: string;
  status: string;
  progress: number;
  submitted_at?: string;
  processing_started_at?: string;
  completed_at?: string;
  processing_time_seconds?: number | null;
  discrepancy_count?: number;
  document_count?: number;
}

export interface BankResult {
  id: string;
  job_id: string;
  jobId: string;
  client_name?: string;
  lc_number?: string;
  date_received?: string;
  submitted_at?: string;
  processing_started_at?: string;
  completed_at?: string;
  processing_time_seconds?: number;
  status: 'compliant' | 'discrepancies' | 'failed';
  compliance_score: number;
  discrepancy_count: number;
  document_count: number;
  duplicate_count?: number; // Number of previous validations for same LC+client
}

export interface DuplicateCheckResponse {
  is_duplicate: boolean;
  duplicate_count: number;
  previous_validations: BankResult[];
}

export interface BankJobsResponse {
  total: number;
  count: number;
  jobs: BankJob[];
}

export interface BankResultsResponse {
  total: number;
  count: number;
  results: BankResult[];
}

export interface BankJobFilters {
  status?: string;
  limit?: number;
  offset?: number;
}

export interface BankResultsFilters {
  start_date?: string; // ISO date string
  end_date?: string; // ISO date string
  client_name?: string;
  status?: 'compliant' | 'discrepancies';
  min_score?: number; // 0-100
  max_score?: number; // 0-100
  discrepancy_type?: 'date_mismatch' | 'amount_mismatch' | 'party_mismatch' | 'port_mismatch' | 'missing_field' | 'invalid_format';
  limit?: number;
  offset?: number;
  job_ids?: string; // Comma-separated job IDs for bulk export
}

export interface BankClientsResponse {
  count: number;
  clients: string[];
}

export interface ClientStats {
  client_name: string;
  total_validations: number;
  compliant_count: number;
  discrepancies_count: number;
  failed_count: number;
  total_discrepancies: number;
  average_compliance_score: number;
  compliance_rate: number;
  last_validation_date: string | null;
  first_validation_date: string | null;
}

export interface BankClientStatsResponse {
  total: number;
  count: number;
  clients: ClientStats[];
}

export interface LCSetDetected {
  lc_number: string;
  client_name: string;
  files: Array<{
    filename: string;
    size: number;
    valid: boolean;
    s3_key?: string; // S3 key for file retrieval
  }>;
  file_count: number;
  detected_document_types: Record<string, string>;
  detection_method: string;
}

export interface BulkUploadExtractResponse {
  status: string;
  zip_filename: string;
  zip_size: number;
  bulk_session_id: string; // Session ID for later submission
  lc_sets: LCSetDetected[];
  total_lc_sets: number;
}

export interface BulkUploadSubmitRequest {
  bulk_session_id: string;
  lc_sets: Array<{
    client_name: string;
    lc_number?: string;
    date_received?: string;
    files: Array<{
      filename: string;
      s3_key: string;
      valid: boolean;
    }>;
  }>;
}

export interface ClientDashboardResponse {
  client_name: string;
  statistics: {
    total_validations: number;
    compliant_count: number;
    discrepancies_count: number;
    failed_count: number;
    total_discrepancies: number;
    average_compliance_score: number;
    compliance_rate: number;
    average_processing_time_seconds: number | null;
    first_validation_date: string | null;
    last_validation_date: string | null;
  };
  trend_data: Array<{
    date: string;
    validations: number;
    compliant: number;
    discrepancies: number;
    failed: number;
    avg_compliance_score: number;
  }>;
  lc_results: BankResult[];
}

export interface ClientDashboardFilters {
  start_date?: string; // ISO date string
  end_date?: string; // ISO date string
}

export const bankApi = {
  /**
   * Get list of bank validation jobs
   */
  getJobs: async (filters?: BankJobFilters): Promise<BankJobsResponse> => {
    const response = await api.get<BankJobsResponse>('/bank/jobs', {
      params: filters,
    });
    return response.data;
  },

  /**
   * Get status of a specific job
   */
  getJobStatus: async (jobId: string): Promise<BankJob> => {
    const response = await api.get<BankJob>(`/bank/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Get validation results with filters
   */
  getResults: async (filters?: BankResultsFilters): Promise<BankResultsResponse> => {
    const response = await api.get<BankResultsResponse>('/bank/results', {
      params: filters,
    });
    return response.data;
  },

  /**
   * Get distinct client names for autocomplete
   */
  getClients: async (query?: string, limit?: number): Promise<BankClientsResponse> => {
    const response = await api.get<BankClientsResponse>('/bank/clients', {
      params: { query, limit },
    });
    return response.data;
  },

  /**
   * Export filtered results as PDF
   */
  exportResultsPDF: async (filters?: BankResultsFilters): Promise<Blob> => {
    const response = await api.get<Blob>('/bank/results/export-pdf', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Get client statistics with validation counts and compliance metrics
   */
  getClientStats: async (filters?: BankClientStatsFilters): Promise<BankClientStatsResponse> => {
    const response = await api.get<BankClientStatsResponse>('/bank/clients/stats', {
      params: filters,
    });
    return response.data;
  },

  /**
   * Check for duplicate LC (same LC number + client name)
   */
  checkDuplicate: async (
    lcNumber: string,
    clientName: string
  ): Promise<DuplicateCheckResponse> => {
    const response = await api.get<DuplicateCheckResponse>('/bank/duplicates/check', {
      params: {
        lc_number: lcNumber,
        client_name: clientName,
      },
    });
    return response.data;
  },
    clientName: string,
    filters?: ClientDashboardFilters
  ): Promise<ClientDashboardResponse> => {
    const response = await api.get<ClientDashboardResponse>(
      `/bank/clients/${encodeURIComponent(clientName)}/dashboard`,
      {
        params: filters,
      }
    );
    return response.data;
  },

  /**
   * Extract ZIP file and detect LC sets
   */
  extractZipFile: async (zipFile: File): Promise<BulkUploadExtractResponse> => {
    const formData = new FormData();
    formData.append('zip_file', zipFile);
    
    const response = await api.post<BulkUploadExtractResponse>('/bank/bulk-upload/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Submit bulk LC sets for validation
   */
  submitBulkUpload: async (request: BulkUploadSubmitRequest): Promise<BulkUploadSubmitResponse> => {
    const formData = new FormData();
    formData.append('bulk_session_id', request.bulk_session_id);
    formData.append('lc_sets_data', JSON.stringify(request.lc_sets));
    
    const response = await api.post<BulkUploadSubmitResponse>('/bank/bulk-upload/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

