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
  q?: string;
  status?: string;
  client_name?: string;
  assignee?: string;
  queue?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: 'created_at' | 'completed_at' | 'client_name' | 'lc_number';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface BankResultsFilters {
  q?: string; // Free text search
  start_date?: string; // ISO date string
  end_date?: string; // ISO date string
  client_name?: string;
  status?: 'compliant' | 'discrepancies';
  min_score?: number; // 0-100
  max_score?: number; // 0-100
  discrepancy_type?: 'date_mismatch' | 'amount_mismatch' | 'party_mismatch' | 'port_mismatch' | 'missing_field' | 'invalid_format';
  assignee?: string; // User ID
  queue?: string;
  sort_by?: 'completed_at' | 'created_at' | 'compliance_score' | 'client_name' | 'lc_number';
  sort_order?: 'asc' | 'desc';
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

export interface BankClientStatsFilters {
  query?: string;
  limit?: number;
  offset?: number;
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

export interface NotificationPreferences {
  email_enabled: boolean;
  sms_enabled: boolean;
  job_completion_enabled: boolean;
  high_discrepancy_enabled: boolean;
  high_discrepancy_threshold: number;
}

export interface UpdateNotificationPreferencesRequest {
  email_enabled?: boolean;
  sms_enabled?: boolean;
  job_completion_enabled?: boolean;
  high_discrepancy_enabled?: boolean;
  high_discrepancy_threshold?: number;
}

export const bankApi = {
  /**
   * Get user's notification preferences
   */
  getNotificationPreferences: async (): Promise<NotificationPreferences> => {
    const response = await api.get<NotificationPreferences>('/bank/notification-preferences');
    return response.data;
  },

  /**
   * Update user's notification preferences
   */
  updateNotificationPreferences: async (
    preferences: UpdateNotificationPreferencesRequest
  ): Promise<{ message: string; preferences: NotificationPreferences }> => {
    const response = await api.put<{ message: string; preferences: NotificationPreferences }>(
      '/bank/notification-preferences',
      null,
      {
        params: preferences,
      }
    );
    return response.data;
  },

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
   * Export filtered results as PDF (POST with async job support)
   */
  exportResultsPDF: async (filters?: BankResultsFilters): Promise<Blob | { job_id: string; status: string; total_rows: number; message: string }> => {
    const response = await api.post<Blob | { job_id: string; status: string; total_rows: number; message: string }>('/bank/results/export/pdf', null, {
      params: filters,
      responseType: 'blob',
    });
    
    // Check if response is a job object (JSON) or blob
    if (response.headers['content-type']?.includes('application/json')) {
      return JSON.parse(await response.data.text());
    }
    return response.data;
  },

  /**
   * Export filtered results as CSV (POST with async job support)
   */
  exportResultsCSV: async (filters?: BankResultsFilters): Promise<Blob | { job_id: string; status: string; total_rows: number; message: string }> => {
    const response = await api.post<Blob | { job_id: string; status: string; total_rows: number; message: string }>('/bank/results/export/csv', null, {
      params: filters,
      responseType: 'blob',
    });
    
    // Check if response is a job object (JSON) or blob
    if (response.headers['content-type']?.includes('application/json')) {
      return JSON.parse(await response.data.text());
    }
    return response.data;
  },

  /**
   * Get export job status
   */
  getExportJobStatus: async (jobId: string): Promise<{
    job_id: string;
    status: string;
    created_at?: string;
    started_at?: string;
    completed_at?: string;
    error_message?: string;
    download_url?: string;
  }> => {
    const response = await api.get(`/bank/exports/${jobId}`);
    return response.data;
  },

  /**
   * Get client statistics with validation counts and compliance metrics
   */
  getClientStats: async (filters?: BankClientStatsFilters): Promise<BankClientStatsResponse> => {
    try {
      const response = await api.get<BankClientStatsResponse>('/bank/clients/stats', {
        params: filters,
      });
      return response.data;
    } catch (error: any) {
      throw error;
    }
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

  /**
   * Get client dashboard with statistics, trends, and LC results
   */
  getClientDashboard: async (
    clientName: string,
    filters?: ClientDashboardFilters
  ): Promise<ClientDashboardResponse> => {
    try {
      const response = await api.get<ClientDashboardResponse>(
        `/bank/clients/${encodeURIComponent(clientName)}/dashboard`,
        {
          params: filters,
        }
      );
      return response.data;
    } catch (error: any) {
      // Re-throw error instead of returning mock data
      throw error;
    }
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

// Bank User Management API
export interface BankUser {
  id: string;
  email: string;
  full_name: string;
  role: 'bank_officer' | 'bank_admin';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BankUserInviteRequest {
  email: string;
  full_name: string;
  password: string;
  role: 'bank_officer' | 'bank_admin';
}

export interface BankUserListResponse {
  users: BankUser[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface BankUserListQuery {
  role?: 'bank_officer' | 'bank_admin';
  is_active?: boolean;
  search?: string;
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface RoleUpdateRequest {
  user_id: string;
  role: 'bank_officer' | 'bank_admin';
  reason?: string;
}

// Mock bank users for fallback/demo
const MOCK_BANK_USERS: BankUser[] = [
  {
    id: "bank-user-1",
    email: "admin@bankone.com",
    full_name: "Sarah Johnson",
    role: "bank_admin",
    is_active: true,
    created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "bank-user-2",
    email: "officer1@bankone.com",
    full_name: "Michael Chen",
    role: "bank_officer",
    is_active: true,
    created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "bank-user-3",
    email: "officer2@bankone.com",
    full_name: "Emily Rodriguez",
    role: "bank_officer",
    is_active: true,
    created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "bank-user-4",
    email: "officer3@bankone.com",
    full_name: "David Kumar",
    role: "bank_officer",
    is_active: false,
    created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "bank-user-5",
    email: "manager@bankone.com",
    full_name: "Lisa Anderson",
    role: "bank_admin",
    is_active: true,
    created_at: new Date(Date.now() - 120 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
];

// Helper function to filter and paginate mock users
function getMockUsersResponse(query?: BankUserListQuery): BankUserListResponse {
  let filteredUsers = [...MOCK_BANK_USERS];
  
  // Apply filters
  if (query?.role) {
    filteredUsers = filteredUsers.filter(u => u.role === query.role);
  }
  if (query?.is_active !== undefined) {
    filteredUsers = filteredUsers.filter(u => u.is_active === query.is_active);
  }
  if (query?.search) {
    const searchLower = query.search.toLowerCase();
    filteredUsers = filteredUsers.filter(u => 
      u.email.toLowerCase().includes(searchLower) || 
      u.full_name.toLowerCase().includes(searchLower)
    );
  }
  
  // Sort
  const sortBy = query?.sort_by || 'created_at';
  const sortOrder = query?.sort_order || 'desc';
  filteredUsers.sort((a, b) => {
    const aVal = (a as any)[sortBy];
    const bVal = (b as any)[sortBy];
    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortOrder === 'desc' ? -comparison : comparison;
  });
  
  // Paginate
  const page = query?.page || 1;
  const perPage = query?.per_page || 20;
  const start = (page - 1) * perPage;
  const end = start + perPage;
  const paginatedUsers = filteredUsers.slice(start, end);
  const totalPages = Math.ceil(filteredUsers.length / perPage);
  
  return {
    users: paginatedUsers,
    total: filteredUsers.length,
    page,
    per_page: perPage,
    pages: totalPages,
    has_next: page < totalPages,
    has_prev: page > 1,
  };
}

export const bankUsersApi = {
  /**
   * List users in the bank tenant
   */
  listUsers: async (query?: BankUserListQuery): Promise<BankUserListResponse> => {
    try {
      const params = new URLSearchParams();
      if (query?.role) params.append('role', query.role);
      if (query?.is_active !== undefined) params.append('is_active', String(query.is_active));
      if (query?.search) params.append('search', query.search);
      if (query?.page) params.append('page', String(query.page));
      if (query?.per_page) params.append('per_page', String(query.per_page));
      if (query?.sort_by) params.append('sort_by', query.sort_by);
      if (query?.sort_order) params.append('sort_order', query.sort_order);
      
      const response = await api.get<BankUserListResponse>(`/bank/users?${params.toString()}`);
      return response.data;
    } catch (error) {
      // Re-throw error instead of returning mock data
      throw error;
    }
  },

  /**
   * Invite/create a new user
   */
  inviteUser: async (data: BankUserInviteRequest): Promise<BankUser> => {
    const response = await api.post<BankUser>('/bank/users/invite', data);
    return response.data;
  },

  /**
   * Update user role
   */
  updateUserRole: async (userId: string, data: RoleUpdateRequest): Promise<{ success: boolean; message: string }> => {
    const response = await api.put(`/bank/users/${userId}/role`, data);
    return response.data;
  },

  /**
   * Suspend a user
   */
  suspendUser: async (userId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.put(`/bank/users/${userId}/suspend`);
    return response.data;
  },

  /**
   * Reactivate a user
   */
  reactivateUser: async (userId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.put(`/bank/users/${userId}/reactivate`);
    return response.data;
  },

  /**
   * Reset 2FA for a user
   */
  reset2FA: async (userId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/bank/users/${userId}/reset-2fa`);
    return response.data;
  },
};

// Bank Policy API
export interface PolicyOverlay {
  id: string;
  bank_id: string;
  version: number;
  active: boolean;
  config: {
    stricter_checks?: {
      max_date_slippage_days?: number;
      mandatory_documents?: string[];
      require_expiry_date?: boolean;
      min_amount_threshold?: number;
    };
    thresholds?: {
      discrepancy_severity_override?: string;
      auto_reject_on?: string[];
    };
  };
  created_by_id: string;
  published_by_id?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyException {
  id: string;
  bank_id: string;
  overlay_id?: string;
  rule_code: string;
  scope: {
    client?: string;
    branch?: string;
    product?: string;
  };
  reason: string;
  expires_at?: string;
  effect: "waive" | "downgrade" | "override";
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyOverlayCreate {
  config: {
    stricter_checks: Record<string, any>;
    thresholds: Record<string, any>;
  };
  version?: number;
}

export interface PolicyExceptionCreate {
  rule_code: string;
  scope: Record<string, string>;
  reason: string;
  expires_at?: string;
  effect: "waive" | "downgrade" | "override";
}

export const bankPolicyApi = {
  /**
   * List policy overlays
   */
  listOverlays: async (): Promise<PolicyOverlay[]> => {
    const response = await api.get<PolicyOverlay[]>("/bank/policy/overlays");
    return response.data;
  },

  /**
   * Create or update policy overlay
   */
  createOverlay: async (data: PolicyOverlayCreate): Promise<PolicyOverlay> => {
    const response = await api.post<PolicyOverlay>("/bank/policy/overlays", data);
    return response.data;
  },

  /**
   * Publish (activate) a policy overlay
   */
  publishOverlay: async (overlayId: string): Promise<PolicyOverlay> => {
    const response = await api.post<PolicyOverlay>(`/bank/policy/overlays/publish?overlay_id=${overlayId}`);
    return response.data;
  },

  /**
   * List policy exceptions
   */
  listExceptions: async (ruleCode?: string): Promise<PolicyException[]> => {
    const params = ruleCode ? `?rule_code=${ruleCode}` : "";
    const response = await api.get<PolicyException[]>(`/bank/policy/overlays/exceptions${params}`);
    return response.data;
  },

  /**
   * Create policy exception
   */
  createException: async (data: PolicyExceptionCreate, overlayId?: string): Promise<PolicyException> => {
    const params = overlayId ? `?overlay_id=${overlayId}` : "";
    const response = await api.post<PolicyException>(`/bank/policy/overlays/exceptions${params}`, data);
    return response.data;
  },

  /**
   * Delete policy exception
   */
  deleteException: async (exceptionId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/bank/policy/overlays/exceptions/${exceptionId}`);
    return response.data;
  },

  /**
   * Get policy analytics
   */
  getAnalytics: async (timeRange: string = "30d"): Promise<PolicyAnalytics> => {
    const response = await api.get<PolicyAnalytics>(`/bank/policy/analytics?time_range=${timeRange}`);
    return response.data;
  },
};

export interface PolicyUsageStats {
  overlay_id?: string;
  overlay_version?: number;
  total_applications: number;
  unique_sessions: number;
  avg_discrepancy_reduction: number;
  avg_processing_time_ms: number;
  last_applied_at?: string;
}

export interface ExceptionEffectivenessStats {
  exception_id: string;
  rule_code: string;
  effect: string;
  total_applications: number;
  waived_count: number;
  downgraded_count: number;
  overridden_count: number;
  avg_discrepancy_reduction: number;
  last_applied_at?: string;
}

export interface PolicyImpactMetrics {
  total_validations: number;
  validations_with_policy: number;
  policy_usage_rate: number;
  total_discrepancy_reduction: number;
  avg_discrepancy_reduction_per_validation: number;
  severity_changes: Record<string, number>;
  most_affected_rules: Array<{
    rule_code: string;
    application_count: number;
    avg_discrepancy_reduction: number;
  }>;
}

// Bank Authentication API (2FA)
export interface Request2FAResponse {
  success: boolean;
  session_id: string;
  message: string;
  code?: string; // Only in development
}

export interface Verify2FAResponse {
  success: boolean;
  message: string;
  verified_at: string;
}

export interface SessionStatusResponse {
  user_id: string;
  email: string;
  role: string;
  idle_timeout_minutes: number;
  "2fa_enabled": boolean;
  session_active: boolean;
}

export const bankAuthApi = {
  /**
   * Request 2FA code
   */
  request2FA: async (): Promise<Request2FAResponse> => {
    const response = await api.post<Request2FAResponse>("/bank/auth/request-2fa");
    return response.data;
  },

  /**
   * Verify 2FA code
   */
  verify2FA: async (code: string, sessionId: string): Promise<Verify2FAResponse> => {
    const response = await api.post<Verify2FAResponse>(
      `/bank/auth/verify-2fa?code=${code}&session_id=${sessionId}`
    );
    return response.data;
  },

  /**
   * Get session status
   */
  getSessionStatus: async (): Promise<SessionStatusResponse> => {
    const response = await api.get<SessionStatusResponse>("/bank/auth/session-status");
    return response.data;
  },
};

// Bank Compliance API (Data Retention) - Updated to match backend
export interface RetentionPolicyRead {
  id: string;
  name: string;
  data_type: string;
  retention_period_days: number;
  archive_after_days?: number;
  delete_after_days?: number;
  legal_basis?: string;
  applies_to_regions?: string[];
  is_active: boolean;
  created_by: string;
  approved_by?: string;
  event_metadata?: Record<string, any>;
  created_at: string;
}

export interface RetentionPolicyCreate {
  name: string;
  data_type: string;
  retention_period_days: number;
  archive_after_days?: number;
  delete_after_days?: number;
  legal_basis?: string;
  applies_to_regions?: string[];
  is_active?: boolean;
}

export interface RetentionPolicyUpdate {
  name?: string;
  data_type?: string;
  retention_period_days?: number;
  archive_after_days?: number;
  delete_after_days?: number;
  legal_basis?: string;
  applies_to_regions?: string[];
  is_active?: boolean;
}

export enum DataRequestType {
  DOWNLOAD = "download",
  DELETION = "deletion",
}

export enum DataRequestStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export interface DataRequestCreate {
  data_scope: string[];
  reason?: string;
}

export interface DataRequestRead {
  id: string;
  type: DataRequestType;
  status: DataRequestStatus;
  requested_at: string;
  requested_by: string;
  organization_id: string;
  data_scope: string[];
  reason?: string;
  completed_at?: string;
  expires_at?: string;
  download_url?: string;
}

export const bankComplianceApi = {
  // Retention Policies
  createRetentionPolicy: async (policy: RetentionPolicyCreate): Promise<RetentionPolicyRead> => {
    const response = await api.post<RetentionPolicyRead>("/bank/compliance/retention-policy", policy);
    return response.data;
  },
  getRetentionPolicies: async (): Promise<RetentionPolicyRead[]> => {
    const response = await api.get<RetentionPolicyRead[]>("/bank/compliance/retention-policy");
    return response.data;
  },
  updateRetentionPolicy: async (policyId: string, policy: RetentionPolicyUpdate): Promise<RetentionPolicyRead> => {
    const response = await api.put<RetentionPolicyRead>(`/bank/compliance/retention-policy/${policyId}`, policy);
    return response.data;
  },
  deleteRetentionPolicy: async (policyId: string): Promise<void> => {
    await api.delete(`/bank/compliance/retention-policy/${policyId}`);
  },

  // Data Requests (Export/Erasure)
  requestDataExport: async (request: DataRequestCreate): Promise<DataRequestRead> => {
    const response = await api.post<DataRequestRead>("/bank/compliance/export", request);
    return response.data;
  },
  listDataRequests: async (): Promise<DataRequestRead[]> => {
    const response = await api.get<DataRequestRead[]>("/bank/compliance/data-requests");
    return response.data;
  },
  getDataRequestStatus: async (requestId: string): Promise<DataRequestRead> => {
    const response = await api.get<DataRequestRead>(`/bank/compliance/data-requests/${requestId}`);
    return response.data;
  },
  cancelDataRequest: async (requestId: string): Promise<DataRequestRead> => {
    const response = await api.post<DataRequestRead>(`/bank/compliance/data-requests/${requestId}/cancel`);
    return response.data;
  },
  requestDataErasure: async (request: DataRequestCreate): Promise<DataRequestRead> => {
    const response = await api.post<DataRequestRead>("/bank/compliance/erase", request);
    return response.data;
  },
};

// Bank Queue Operations API
export interface BankQueueJob {
  id: string;
  job_type: string;
  job_data: Record<string, any>;
  priority: number;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  attempts: number;
  max_attempts: number;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  worker_id?: string;
  organization_id?: string;
  user_id?: string;
  lc_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface BankQueueFilters {
  status?: string;
  job_type?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface BankQueueStats {
  time_range: string;
  total_jobs: number;
  status_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
  avg_processing_time_ms: number;
  queue_depth: number;
}

// Bank SLA API
export interface SLAMetric {
  name: string;
  target: number;
  current: number;
  unit: string;
  status: 'met' | 'at_risk' | 'breached';
  trend: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

export interface SLABreach {
  id: string;
  lc_number: string;
  client_name: string;
  metric: string;
  target: number;
  actual: number;
  breach_time: string;
  severity: 'critical' | 'major' | 'minor';
}

export interface SLAThroughputData {
  hour: string;
  lcs: number;
}

export interface SLAAgingData {
  time_range: string;
  count: number;
  percentage: number;
}

export interface SLAMetricsResponse {
  metrics: SLAMetric[];
  overall_compliance: number;
  throughput_data: SLAThroughputData[];
  aging_data: SLAAgingData[];
}

export interface SLABreachesResponse {
  breaches: SLABreach[];
  total: number;
}

// Bank Evidence Packs API
export interface ValidationSessionRead {
  id: string;
  lc_number: string;
  client_name: string;
  status: string;
  completed_at: string;
  discrepancy_count: number;
  document_count: number;
  compliance_score: number;
}

export interface EvidencePackFilters {
  limit?: number;
  offset?: number;
  status?: string;
}

export interface GeneratePackRequest {
  session_ids: string[];
  format: 'pdf' | 'zip';
  include_documents?: boolean;
  include_findings?: boolean;
  include_audit_trail?: boolean;
}

export interface GeneratePackResponse {
  pack_id: string;
  download_url: string;
  format: string;
  size_bytes: number;
  expires_at: string;
}

export interface BulkJobActionRequest {
  job_ids: string[];
  action: 'retry' | 'cancel' | 'requeue';
  reason: string;
}

export interface BulkJobActionResponse {
  action: string;
  success_count: number;
  failed_jobs: string[];
  reason: string;
}

export const bankQueueApi = {
  /**
   * Get job queue for bank tenant with filtering and pagination
   */
  getQueue: async (filters?: BankQueueFilters): Promise<PaginatedResponse<BankQueueJob>> => {
    try {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.job_type) params.append('job_type', filters.job_type);
      if (filters?.search) params.append('search', filters.search);
      if (filters?.limit) params.append('limit', String(filters.limit));
      if (filters?.offset) params.append('offset', String(filters.offset));
      
      const response = await api.get<PaginatedResponse<BankQueueJob>>(`/bank/queue?${params.toString()}`);
      return response.data;
    } catch (error: any) {
      console.warn('Bank queue API unavailable, returning empty response:', error?.message);
      return {
        items: [],
        total: 0,
        page: 1,
        size: filters?.limit || 20,
        pages: 0
      };
    }
  },

  /**
   * Get queue statistics
   */
  getQueueStats: async (timeRange: string = '24h'): Promise<BankQueueStats> => {
    try {
      const response = await api.get<BankQueueStats>(`/bank/queue/stats?time_range=${timeRange}`);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Retry a specific job
   */
  retryJob: async (jobId: string, reason: string): Promise<{ message: string; job_id: string }> => {
    const response = await api.post<{ message: string; job_id: string }>(
      `/bank/queue/${jobId}/retry?reason=${encodeURIComponent(reason)}`
    );
    return response.data;
  },

  /**
   * Cancel a specific job
   */
  cancelJob: async (jobId: string, reason: string): Promise<{ message: string; job_id: string }> => {
    const response = await api.post<{ message: string; job_id: string }>(
      `/bank/queue/${jobId}/cancel?reason=${encodeURIComponent(reason)}`
    );
    return response.data;
  },

  /**
   * Requeue a specific job
   */
  requeueJob: async (jobId: string, reason?: string): Promise<{ message: string; job_id: string }> => {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    const response = await api.post<{ message: string; job_id: string }>(
      `/bank/queue/${jobId}/requeue${params}`
    );
    return response.data;
  },

  /**
   * Perform bulk actions on multiple jobs
   */
  bulkAction: async (request: BulkJobActionRequest): Promise<BulkJobActionResponse> => {
    const response = await api.post<BulkJobActionResponse>('/bank/queue/bulk-action', request);
    return response.data;
  },

  /**
   * Get SLA metrics for the bank
   */
  getSLAMetrics: async (timeRange: string = 'week'): Promise<SLAMetricsResponse> => {
    try {
      const response = await api.get<SLAMetricsResponse>('/bank/sla/metrics', {
        params: { time_range: timeRange },
      });
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Get SLA breaches
   */
  getSLABreaches: async (timeRange: string = 'week', severity?: string): Promise<SLABreachesResponse> => {
    try {
      const response = await api.get<SLABreachesResponse>('/bank/sla/breaches', {
        params: { time_range: timeRange, severity },
      });
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Export SLA report
   */
  exportSLAReport: async (timeRange: string = 'week', format: string = 'pdf'): Promise<void> => {
    const response = await api.post('/bank/sla/export', null, {
      params: { time_range: timeRange, format },
      responseType: 'blob',
    });
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `sla-report-${timeRange}.${format}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /**
   * List validation sessions for evidence pack generation
   */
  listValidationSessions: async (filters?: EvidencePackFilters): Promise<ValidationSessionRead[]> => {
    try {
      const response = await api.get<ValidationSessionRead[]>('/bank/evidence-packs/sessions', {
        params: filters,
      });
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Generate evidence pack
   */
  generateEvidencePack: async (request: GeneratePackRequest): Promise<GeneratePackResponse> => {
    const response = await api.post<GeneratePackResponse>('/bank/evidence-packs/generate', request);
    return response.data;
  },
};

/**
 * Bank AI Assistance API Client
 */
export interface AIUsageQuota {
  feature: string;
  used: number;
  limit: number;
  remaining: number;
  reset_at?: string;
}

export interface DiscrepancyExplainRequest {
  discrepancy: string;
  lc_number?: string;
  validation_session_id?: string;
  language?: string;
}

export interface LetterGenerateRequest {
  letter_type: 'approval' | 'rejection';
  client_name: string;
  lc_number: string;
  context?: string;
  discrepancy_list?: Array<{ rule: string; description: string; severity: string }>;
  language?: string;
}

export interface SummarizeRequest {
  document_text: string;
  lc_number?: string;
  language?: string;
}

export interface TranslateRequest {
  text: string;
  target_language: string;
  source_language?: string;
}

export interface AIResponse {
  content: string;
  rule_basis?: Array<{ rule_id: string; clause: string; description: string }>;
  confidence_score?: number;
  usage_remaining?: number;
  event_id?: string;
}

export const bankAiApi = {
  /**
   * Get AI usage quota for a feature
   */
  getQuota: async (feature: string): Promise<AIUsageQuota> => {
    try {
      const response = await api.get<AIUsageQuota>('/bank/ai/quota', {
        params: { feature },
      });
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Explain a discrepancy
   */
  explainDiscrepancy: async (request: DiscrepancyExplainRequest): Promise<AIResponse> => {
    try {
      const response = await api.post<AIResponse>('/bank/ai/discrepancy-explain', request);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Generate approval/rejection letter
   */
  generateLetter: async (request: LetterGenerateRequest): Promise<AIResponse> => {
    try {
      const response = await api.post<AIResponse>('/bank/ai/generate-letter', request);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Summarize document
   */
  summarizeDocument: async (request: SummarizeRequest): Promise<AIResponse> => {
    try {
      const response = await api.post<AIResponse>('/bank/ai/summarize', request);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },

  /**
   * Translate text
   */
  translateText: async (request: TranslateRequest): Promise<AIResponse> => {
    try {
      const response = await api.post<AIResponse>('/bank/ai/translate', request);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  },
};

// Saved Views API
export interface SavedView {
  id: string;
  company_id: string;
  owner_id: string;
  owner_name?: string;
  name: string;
  resource: 'results' | 'jobs' | 'evidence';
  query_params: Record<string, any>;
  columns?: Record<string, any>;
  is_org_default: boolean;
  shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavedViewCreate {
  name: string;
  resource: 'results' | 'jobs' | 'evidence';
  query_params: Record<string, any>;
  columns?: Record<string, any>;
  is_org_default?: boolean;
  shared?: boolean;
}

export interface SavedViewUpdate {
  name?: string;
  query_params?: Record<string, any>;
  columns?: Record<string, any>;
  is_org_default?: boolean;
  shared?: boolean;
}

export interface SavedViewListResponse {
  total: number;
  count: number;
  views: SavedView[];
}

export const bankSavedViewsApi = {
  /**
   * Create a saved view
   */
  create: async (view: SavedViewCreate): Promise<SavedView> => {
    const response = await api.post<SavedView>('/bank/saved-views', view);
    return response.data;
  },

  /**
   * List saved views
   */
  list: async (resource?: string): Promise<SavedViewListResponse> => {
    const response = await api.get<SavedViewListResponse>('/bank/saved-views', {
      params: resource ? { resource } : undefined,
    });
    return response.data;
  },

  /**
   * Get default view for a resource
   */
  getDefault: async (resource: string): Promise<SavedView | null> => {
    const response = await api.get<SavedView | null>('/bank/saved-views/default', {
      params: { resource },
    });
    return response.data;
  },

  /**
   * Update a saved view
   */
  update: async (viewId: string, updates: SavedViewUpdate): Promise<SavedView> => {
    const response = await api.put<SavedView>(`/bank/saved-views/${viewId}`, updates);
    return response.data;
  },

  /**
   * Delete a saved view
   */
  delete: async (viewId: string): Promise<void> => {
    await api.delete(`/bank/saved-views/${viewId}`);
  },
};

// Duplicate Detection API
export interface DuplicateCandidate {
  session_id: string;
  lc_number: string;
  client_name?: string;
  similarity_score: number;
  content_similarity?: number;
  metadata_similarity?: number;
  field_matches?: Record<string, any>;
  detected_at: string;
  completed_at?: string;
}

export interface DuplicateCandidatesResponse {
  session_id: string;
  candidates: DuplicateCandidate[];
  total_count: number;
}

export interface MergeRequest {
  source_session_id: string;
  target_session_id: string;
  merge_type?: 'duplicate' | 'amendment' | 'correction' | 'manual';
  merge_reason?: string;
  fields_to_merge?: string[];
}

export interface MergeResponse {
  merge_id: string;
  source_session_id: string;
  target_session_id: string;
  merge_type: string;
  merged_at: string;
  fields_merged?: Record<string, any>;
}

export interface MergeHistoryItem {
  id: string;
  source_session_id: string;
  target_session_id: string;
  merge_type: string;
  merge_reason?: string;
  merged_by: string;
  merged_at: string;
  fields_merged?: Record<string, any>;
  preserved_data?: Record<string, any>;
}

export interface MergeHistoryResponse {
  merges: MergeHistoryItem[];
  total_count: number;
}

export const bankDuplicatesApi = {
  /**
   * Get duplicate candidates for a session
   */
  getCandidates: async (
    sessionId: string,
    threshold?: number,
    limit?: number
  ): Promise<DuplicateCandidatesResponse> => {
    const response = await api.get<DuplicateCandidatesResponse>(
      `/bank/duplicates/candidates/${sessionId}`,
      {
        params: {
          threshold,
          limit,
        },
      }
    );
    return response.data;
  },

  /**
   * Merge two sessions
   */
  merge: async (request: MergeRequest): Promise<MergeResponse> => {
    const response = await api.post<MergeResponse>('/bank/duplicates/merge', request);
    return response.data;
  },

  /**
   * Get merge history for a session
   */
  getMergeHistory: async (sessionId: string): Promise<MergeHistoryResponse> => {
    const response = await api.get<MergeHistoryResponse>(
      `/bank/duplicates/history/${sessionId}`
    );
    return response.data;
  },
};

// API Tokens & Webhooks API
export interface APIToken {
  id: string;
  company_id: string;
  created_by: string;
  name: string;
  description?: string;
  token_prefix: string;
  is_active: boolean;
  scopes: string[];
  expires_at?: string;
  last_used_at?: string;
  last_used_ip?: string;
  usage_count: number;
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  created_at: string;
  updated_at: string;
  revoked_at?: string;
  revoked_by?: string;
  revoke_reason?: string;
}

export interface APITokenCreate {
  name: string;
  description?: string;
  scopes: string[];
  expires_at?: string;
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
}

export interface APITokenCreateResponse {
  token: string; // Full token - only shown once!
  token_id: string;
  token_prefix: string;
  expires_at?: string;
  warning: string;
}

export interface APITokenUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  expires_at?: string;
  scopes?: string[];
}

export interface APITokenRevokeRequest {
  reason?: string;
}

export interface APITokenListResponse {
  tokens: APIToken[];
  total: number;
}

export interface WebhookSubscription {
  id: string;
  company_id: string;
  created_by: string;
  name: string;
  description?: string;
  url: string;
  events: string[];
  is_active: boolean;
  timeout_seconds: number;
  retry_count: number;
  retry_backoff_multiplier: number;
  headers?: Record<string, string>;
  success_count: number;
  failure_count: number;
  last_delivery_at?: string;
  last_success_at?: string;
  last_failure_at?: string;
  created_at: string;
  updated_at: string;
}

export interface WebhookSubscriptionCreate {
  name: string;
  description?: string;
  url: string;
  events: string[];
  timeout_seconds?: number;
  retry_count?: number;
  retry_backoff_multiplier?: number;
  headers?: Record<string, string>;
}

export interface WebhookSubscriptionCreateResponse {
  subscription: WebhookSubscription;
  secret: string; // Secret shown once for signing
  warning: string;
}

export interface WebhookSubscriptionUpdate {
  name?: string;
  description?: string;
  url?: string;
  events?: string[];
  is_active?: boolean;
  timeout_seconds?: number;
  headers?: Record<string, string>;
}

export interface WebhookSubscriptionListResponse {
  subscriptions: WebhookSubscription[];
  total: number;
}

export interface WebhookDelivery {
  id: string;
  subscription_id: string;
  company_id: string;
  event_type: string;
  event_id?: string;
  status: string;
  attempt_number: number;
  max_attempts: number;
  http_status_code?: number;
  response_body?: string;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  next_retry_at?: string;
  retry_reason?: string;
}

export interface WebhookDeliveryListResponse {
  deliveries: WebhookDelivery[];
  total: number;
}

export interface WebhookTestRequest {
  payload?: Record<string, any>;
}

export interface WebhookTestResponse {
  delivery_id: string;
  status: string;
  http_status_code?: number;
  response_body?: string;
  duration_ms?: number;
  error_message?: string;
}

export interface WebhookReplayRequest {
  delivery_id: string;
}

export interface WebhookReplayResponse {
  new_delivery_id: string;
  status: string;
}

export const bankTokensApi = {
  /**
   * Create a new API token
   */
  create: async (tokenData: APITokenCreate): Promise<APITokenCreateResponse> => {
    const response = await api.post<APITokenCreateResponse>('/bank/tokens', tokenData);
    return response.data;
  },

  /**
   * List all API tokens
   */
  list: async (includeRevoked?: boolean): Promise<APITokenListResponse> => {
    const response = await api.get<APITokenListResponse>('/bank/tokens', {
      params: { include_revoked: includeRevoked },
    });
    return response.data;
  },

  /**
   * Get a specific API token
   */
  get: async (tokenId: string): Promise<APIToken> => {
    const response = await api.get<APIToken>(`/bank/tokens/${tokenId}`);
    return response.data;
  },

  /**
   * Update an API token
   */
  update: async (tokenId: string, updates: APITokenUpdate): Promise<APIToken> => {
    const response = await api.put<APIToken>(`/bank/tokens/${tokenId}`, updates);
    return response.data;
  },

  /**
   * Revoke an API token
   */
  revoke: async (tokenId: string, reason?: string): Promise<APIToken> => {
    const response = await api.post<APIToken>(`/bank/tokens/${tokenId}/revoke`, { reason });
    return response.data;
  },
};

export const bankWebhooksApi = {
  /**
   * Create a new webhook subscription
   */
  create: async (subscriptionData: WebhookSubscriptionCreate): Promise<WebhookSubscriptionCreateResponse> => {
    const response = await api.post<WebhookSubscriptionCreateResponse>('/bank/webhooks', subscriptionData);
    return response.data;
  },

  /**
   * List all webhook subscriptions
   */
  list: async (): Promise<WebhookSubscriptionListResponse> => {
    const response = await api.get<WebhookSubscriptionListResponse>('/bank/webhooks');
    return response.data;
  },

  /**
   * Get a specific webhook subscription
   */
  get: async (subscriptionId: string): Promise<WebhookSubscription> => {
    const response = await api.get<WebhookSubscription>(`/bank/webhooks/${subscriptionId}`);
    return response.data;
  },

  /**
   * Update a webhook subscription
   */
  update: async (subscriptionId: string, updates: WebhookSubscriptionUpdate): Promise<WebhookSubscription> => {
    const response = await api.put<WebhookSubscription>(`/bank/webhooks/${subscriptionId}`, updates);
    return response.data;
  },

  /**
   * Delete a webhook subscription
   */
  delete: async (subscriptionId: string): Promise<void> => {
    await api.delete(`/bank/webhooks/${subscriptionId}`);
  },

  /**
   * Test a webhook subscription
   */
  test: async (subscriptionId: string, testData?: WebhookTestRequest): Promise<WebhookTestResponse> => {
    const response = await api.post<WebhookTestResponse>(
      `/bank/webhooks/${subscriptionId}/test`,
      testData || {}
    );
    return response.data;
  },

  /**
   * List webhook deliveries for a subscription
   */
  listDeliveries: async (
    subscriptionId: string,
    filters?: {
      status?: string;
      event_type?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<WebhookDeliveryListResponse> => {
    const response = await api.get<WebhookDeliveryListResponse>(
      `/bank/webhooks/${subscriptionId}/deliveries`,
      { params: filters }
    );
    return response.data;
  },

  /**
   * Replay a failed webhook delivery
   */
  replay: async (deliveryId: string): Promise<WebhookReplayResponse> => {
    const response = await api.post<WebhookReplayResponse>(
      `/bank/webhooks/deliveries/${deliveryId}/replay`
    );
    return response.data;
  },
};

// Bank Organizations API
export interface BankOrg {
  id: string;
  name: string;
  code?: string;
  kind: "group" | "region" | "branch";
  path: string;
  level: number;
  role: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface BankOrgCreate {
  bank_company_id: string;
  parent_id?: string;
  kind: "group" | "region" | "branch";
  name: string;
  code?: string;
  level?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface BankOrgUpdate {
  name?: string;
  code?: string;
  is_active?: boolean;
  sort_order?: number;
}

export const bankOrgsApi = {
  /**
   * List organizations accessible to the current user
   */
  listOrgs: async (): Promise<{ orgs: BankOrg[] }> => {
    const response = await api.get<{ total: number; count: number; results: BankOrg[] }>("/bank/orgs");
    return { orgs: response.data.results };
  },

  /**
   * Create a new organization
   */
  createOrg: async (data: BankOrgCreate): Promise<BankOrg> => {
    const response = await api.post<BankOrg>("/bank/orgs", data);
    return response.data;
  },

  /**
   * Update an organization
   */
  updateOrg: async (orgId: string, data: BankOrgUpdate): Promise<BankOrg> => {
    const response = await api.put<BankOrg>(`/bank/orgs/${orgId}`, data);
    return response.data;
  },

  /**
   * Delete an organization
   */
  deleteOrg: async (orgId: string): Promise<void> => {
    await api.delete(`/bank/orgs/${orgId}`);
  },
};
