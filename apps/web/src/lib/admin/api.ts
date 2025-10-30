/**
 * Admin API Client and React Query Hooks
 *
 * Provides typed API client and React Query hooks for admin console functionality.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios, { AxiosResponse } from 'axios';

// Configure axios instance for admin API
const adminApi = axios.create({
  baseURL: '/api/admin',
  timeout: 30000,
});

// Add auth interceptor
adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('admin_token');
      window.location.href = '/admin/login';
    }
    return Promise.reject(error);
  }
);

// Types
interface KPIData {
  uptime_percentage: number;
  avg_response_time_ms: number;
  error_rate_percentage: number;
  active_users_24h: number;
  jobs_processed_24h: number;
  revenue_24h_usd: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  alerts_active: number;
}

interface SystemStatus {
  overall_status: 'healthy' | 'degraded' | 'down';
  services: {
    [key: string]: {
      status: 'healthy' | 'degraded' | 'down';
      response_time_ms?: number;
      error_rate?: number;
      details?: any;
    };
  };
  last_updated: string;
}

interface Activity {
  id: string;
  type: string;
  actor: string;
  action: string;
  resource: string;
  timestamp: string;
  details?: any;
}

interface JobFilter {
  status?: string;
  job_type?: string;
  organization_id?: string;
  created_after?: string;
  limit?: number;
  offset?: number;
}

interface Job {
  id: string;
  job_type: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  organization_id?: string;
  user_id?: string;
  created_at: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface AuditFilter {
  actor_id?: string;
  organization_id?: string;
  resource_type?: string;
  action?: string;
  time_start?: string;
  time_end?: string;
  ip_address?: string;
  limit?: number;
  offset?: number;
}

interface AuditEvent {
  id: string;
  event_type: string;
  actor_id?: string;
  actor_type: string;
  resource_type: string;
  resource_id?: string;
  organization_id?: string;
  action: string;
  changes?: any;
  metadata: any;
  ip_address?: string;
  user_agent?: string;
  session_id?: string;
  created_at: string;
}

interface Approval {
  id: string;
  request_type: string;
  resource_type: string;
  resource_id: string;
  requester_id: string;
  approver_id?: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';
  requested_changes: any;
  approval_reason?: string;
  rejection_reason?: string;
  auto_expires_at?: string;
  approved_at?: string;
  rejected_at?: string;
  created_at: string;
  updated_at: string;
}

// API Functions
const api = {
  // KPIs and Monitoring
  getKPIs: (timeRange = '24h'): Promise<AxiosResponse<KPIData>> =>
    adminApi.get(`/ops/kpis?time_range=${timeRange}`),

  getSystemStatus: (): Promise<AxiosResponse<SystemStatus>> =>
    adminApi.get('/ops/status'),

  getRecentActivity: (limit = 20): Promise<AxiosResponse<Activity[]>> =>
    adminApi.get(`/audit/recent?limit=${limit}`),

  // Job Management
  getJobQueue: (filters: JobFilter): Promise<AxiosResponse<PaginatedResponse<Job>>> =>
    adminApi.get('/jobs/queue', { params: filters }),

  getJobStats: (timeRange = '24h'): Promise<AxiosResponse<any>> =>
    adminApi.get(`/jobs/queue/stats?time_range=${timeRange}`),

  retryJob: (jobId: string, reason: string): Promise<AxiosResponse<any>> =>
    adminApi.post(`/jobs/queue/${jobId}/retry?reason=${encodeURIComponent(reason)}`),

  cancelJob: (jobId: string, reason: string): Promise<AxiosResponse<any>> =>
    adminApi.post(`/jobs/queue/${jobId}/cancel?reason=${encodeURIComponent(reason)}`),

  bulkJobAction: (data: {
    job_ids: string[];
    action: 'retry' | 'cancel' | 'requeue';
    reason: string;
  }): Promise<AxiosResponse<any>> =>
    adminApi.post('/jobs/queue/bulk-action', data),

  // Audit and Approvals
  getAuditEvents: (filters: AuditFilter): Promise<AxiosResponse<PaginatedResponse<AuditEvent>>> =>
    adminApi.get('/audit/events', { params: filters }),

  exportAuditEvents: (data: {
    filters: AuditFilter;
    format: 'csv' | 'json' | 'pdf';
    include_pii: boolean;
  }): Promise<AxiosResponse<any>> =>
    adminApi.post('/audit/export', data),

  getApprovals: (status?: string): Promise<AxiosResponse<PaginatedResponse<Approval>>> =>
    adminApi.get('/approvals', { params: status ? { status } : {} }),

  approveRequest: (approvalId: string, data: {
    decision: 'approve' | 'reject';
    reason: string;
    conditions?: any;
  }): Promise<AxiosResponse<any>> =>
    adminApi.put(`/approvals/${approvalId}/${data.decision}`, {
      reason: data.reason,
      conditions: data.conditions
    }),

  // Feature Flags
  getFeatureFlags: (): Promise<AxiosResponse<any[]>> =>
    adminApi.get('/system/feature-flags'),

  updateFeatureFlag: (flagId: string, data: {
    is_active?: boolean;
    rollout_percentage?: number;
    targeting_rules?: any;
  }): Promise<AxiosResponse<any>> =>
    adminApi.put(`/system/feature-flags/${flagId}`, data),

  // Users and Security
  getUsers: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/security/users', { params: filters }),

  getAPIKeys: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/security/api-keys', { params: filters }),

  getSessions: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/security/sessions', { params: filters }),

  // Billing
  getBillingPlans: (): Promise<AxiosResponse<any[]>> =>
    adminApi.get('/billing/plans'),

  getBillingAdjustments: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/billing/adjustments', { params: filters }),

  getDisputes: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/billing/disputes', { params: filters }),

  // Partners
  getPartners: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/partners', { params: filters }),

  getWebhookDeliveries: (filters?: any): Promise<AxiosResponse<PaginatedResponse<any>>> =>
    adminApi.get('/partners/webhooks/deliveries', { params: filters }),
};

// React Query Hooks

// KPIs and Monitoring
export const useAdminKPIs = (timeRange = '24h') => {
  return useQuery({
    queryKey: ['admin', 'kpis', timeRange],
    queryFn: () => api.getKPIs(timeRange).then(res => res.data),
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 15000, // Consider stale after 15 seconds
  });
};

export const useSystemStatus = () => {
  return useQuery({
    queryKey: ['admin', 'system', 'status'],
    queryFn: () => api.getSystemStatus().then(res => res.data),
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000,
  });
};

export const useRecentActivity = (limit = 20) => {
  return useQuery({
    queryKey: ['admin', 'activity', 'recent', limit],
    queryFn: () => api.getRecentActivity(limit).then(res => res.data),
    refetchInterval: 15000, // Refetch every 15 seconds
    staleTime: 10000,
  });
};

// Job Management
export const useJobQueue = (filters: JobFilter) => {
  return useQuery({
    queryKey: ['admin', 'jobs', 'queue', filters],
    queryFn: () => api.getJobQueue(filters).then(res => res.data),
    refetchInterval: 5000, // Refetch every 5 seconds for job queue
    staleTime: 2000,
    keepPreviousData: true,
  });
};

export const useJobStats = (timeRange = '24h') => {
  return useQuery({
    queryKey: ['admin', 'jobs', 'stats', timeRange],
    queryFn: () => api.getJobStats(timeRange).then(res => res.data),
    refetchInterval: 30000,
    staleTime: 15000,
  });
};

export const useRetryJobMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, reason }: { jobId: string; reason: string }) =>
      api.retryJob(jobId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'jobs']);
    },
  });
};

export const useCancelJobMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, reason }: { jobId: string; reason: string }) =>
      api.cancelJob(jobId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'jobs']);
    },
  });
};

export const useBulkJobActionMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.bulkJobAction,
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'jobs']);
    },
  });
};

// Audit and Approvals
export const useAuditEvents = (filters: AuditFilter) => {
  return useQuery({
    queryKey: ['admin', 'audit', 'events', filters],
    queryFn: () => api.getAuditEvents(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 30000,
  });
};

export const useAuditExportMutation = () => {
  return useMutation({
    mutationFn: api.exportAuditEvents,
  });
};

export const useApprovals = (status?: string) => {
  return useQuery({
    queryKey: ['admin', 'approvals', status],
    queryFn: () => api.getApprovals(status).then(res => res.data),
    refetchInterval: 10000, // Refetch every 10 seconds
    staleTime: 5000,
  });
};

export const useApprovalMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ approvalId, ...data }: {
      approvalId: string;
      decision: 'approve' | 'reject';
      reason: string;
      conditions?: any;
    }) => api.approveRequest(approvalId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'approvals']);
    },
  });
};

// Feature Flags
export const useFeatureFlags = () => {
  return useQuery({
    queryKey: ['admin', 'feature-flags'],
    queryFn: () => api.getFeatureFlags().then(res => res.data),
    staleTime: 60000,
  });
};

export const useUpdateFeatureFlagMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ flagId, ...data }: {
      flagId: string;
      is_active?: boolean;
      rollout_percentage?: number;
      targeting_rules?: any;
    }) => api.updateFeatureFlag(flagId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'feature-flags']);
    },
  });
};

// Users and Security
export const useUsers = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'users', filters],
    queryFn: () => api.getUsers(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 60000,
  });
};

export const useAPIKeys = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'api-keys', filters],
    queryFn: () => api.getAPIKeys(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 60000,
  });
};

export const useSessions = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'sessions', filters],
    queryFn: () => api.getSessions(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 30000,
  });
};

// Billing
export const useBillingPlans = () => {
  return useQuery({
    queryKey: ['admin', 'billing', 'plans'],
    queryFn: () => api.getBillingPlans().then(res => res.data),
    staleTime: 300000, // 5 minutes
  });
};

export const useBillingAdjustments = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'billing', 'adjustments', filters],
    queryFn: () => api.getBillingAdjustments(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 60000,
  });
};

export const useDisputes = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'billing', 'disputes', filters],
    queryFn: () => api.getDisputes(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 60000,
  });
};

// Partners
export const usePartners = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'partners', filters],
    queryFn: () => api.getPartners(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 120000, // 2 minutes
  });
};

export const useWebhookDeliveries = (filters?: any) => {
  return useQuery({
    queryKey: ['admin', 'webhooks', 'deliveries', filters],
    queryFn: () => api.getWebhookDeliveries(filters).then(res => res.data),
    keepPreviousData: true,
    staleTime: 30000,
  });
};

export default api;