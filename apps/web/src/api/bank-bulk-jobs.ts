/**
 * Bank Bulk Jobs API service
 */
import { api } from "./client";

export interface BulkJobConfig {
  description?: string;
  throttle_rate?: number; // Items per minute
  max_concurrent?: number;
  retry_on_failure?: boolean;
  retry_attempts?: number;
  notify_on_completion?: boolean;
  notify_on_failure?: boolean;
}

export interface BulkJobCreate {
  name: string;
  job_type: "lc_validation" | "doc_verification" | "risk_analysis";
  config?: BulkJobConfig;
  template_id?: string;
  priority?: number;
  scheduled_at?: string;
}

export interface BulkJob {
  id: string;
  name: string;
  description?: string;
  job_type: string;
  status: "pending" | "running" | "succeeded" | "failed" | "partial" | "cancelled";
  total_items: number;
  processed_items: number;
  succeeded_items: number;
  failed_items: number;
  skipped_items: number;
  progress_percent: number;
  priority: number;
  started_at?: string;
  finished_at?: string;
  duration_seconds?: number;
  created_at: string;
  estimated_completion?: string;
}

export interface BulkJobListResponse {
  items: BulkJob[];
  total: number;
}

export interface BulkTemplateCreate {
  name: string;
  description?: string;
  job_type: "lc_validation" | "doc_verification" | "risk_analysis";
  config_template: Record<string, any>;
  manifest_schema?: Record<string, any>;
  validation_rules?: Record<string, any>;
  is_public?: boolean;
  allowed_roles?: string[];
}

export interface BulkTemplate {
  id: string;
  name: string;
  description?: string;
  job_type: string;
  config_template: Record<string, any>;
  usage_count: number;
  last_used_at?: string;
  is_public: boolean;
  created_at: string;
}

export interface BulkTemplateListResponse {
  items: BulkTemplate[];
  total: number;
}

export const bankBulkJobsApi = {
  /**
   * List bulk jobs
   */
  async list(params?: {
    status?: "pending" | "running" | "succeeded" | "failed" | "partial" | "cancelled";
    job_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<BulkJobListResponse> {
    const response = await api.get("/bank/bulk-jobs", { params });
    return response.data;
  },

  /**
   * Get a specific bulk job
   */
  async get(jobId: string): Promise<BulkJob> {
    const response = await api.get(`/bank/bulk-jobs/${jobId}`);
    return response.data;
  },

  /**
   * Create a new bulk job
   */
  async create(data: BulkJobCreate, manifestFile?: File): Promise<BulkJob> {
    const response = await api.post("/bank/bulk-jobs", data, {
      headers: manifestFile ? {
        "Content-Type": "multipart/form-data",
      } : {},
    });
    return response.data;
  },

  /**
   * Cancel a bulk job
   */
  async cancel(jobId: string): Promise<BulkJob> {
    const response = await api.post(`/bank/bulk-jobs/${jobId}/cancel`);
    return response.data;
  },

  /**
   * List bulk templates
   */
  async listTemplates(params?: {
    job_type?: string;
    include_public?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<BulkTemplateListResponse> {
    const response = await api.get("/bank/bulk-jobs/templates", { params });
    return response.data;
  },

  /**
   * Create a bulk template
   */
  async createTemplate(data: BulkTemplateCreate): Promise<BulkTemplate> {
    const response = await api.post("/bank/bulk-jobs/templates", data);
    return response.data;
  },

  /**
   * Delete a bulk template
   */
  async deleteTemplate(templateId: string): Promise<void> {
    await api.delete(`/bank/bulk-jobs/templates/${templateId}`);
  },
};

