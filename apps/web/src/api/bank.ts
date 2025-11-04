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

export interface BankClientStatsFilters {
  query?: string;
  limit?: number;
  offset?: number;
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
};

