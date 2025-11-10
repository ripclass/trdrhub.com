/**
 * SME Templates API service
 */
import { api } from "@/api/client";

export interface SMETemplate {
  id: string;
  company_id: string;
  user_id: string;
  name: string;
  type: "lc" | "document";
  document_type?: "commercial_invoice" | "bill_of_lading" | "packing_list" | "certificate_of_origin" | "inspection_certificate" | "insurance_certificate" | "other";
  description?: string;
  fields: Record<string, any>;
  is_default: boolean;
  is_active: boolean;
  usage_count: number;
  last_used_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SMETemplateCreate {
  name: string;
  type: "lc" | "document";
  document_type?: "commercial_invoice" | "bill_of_lading" | "packing_list" | "certificate_of_origin" | "inspection_certificate" | "insurance_certificate" | "other";
  description?: string;
  fields: Record<string, any>;
  is_default?: boolean;
}

export interface SMETemplateUpdate {
  name?: string;
  description?: string;
  fields?: Record<string, any>;
  is_default?: boolean;
  is_active?: boolean;
}

export interface SMETemplateListResponse {
  items: SMETemplate[];
  total: number;
}

export interface TemplatePreFillRequest {
  template_id: string;
  variables?: Record<string, any>;
}

export interface TemplatePreFillResponse {
  fields: Record<string, any>;
  template_name: string;
}

export const smeTemplatesApi = {
  /**
   * List templates
   */
  async list(params?: {
    type?: "lc" | "document";
    document_type?: string;
    active_only?: boolean;
  }): Promise<SMETemplateListResponse> {
    const response = await api.get("/sme/templates", { params });
    return response.data;
  },

  /**
   * Get a specific template
   */
  async get(templateId: string): Promise<SMETemplate> {
    const response = await api.get(`/sme/templates/${templateId}`);
    return response.data;
  },

  /**
   * Create a new template
   */
  async create(data: SMETemplateCreate & { company_id: string; user_id: string }): Promise<SMETemplate> {
    const response = await api.post("/sme/templates", data);
    return response.data;
  },

  /**
   * Update a template
   */
  async update(templateId: string, data: SMETemplateUpdate): Promise<SMETemplate> {
    const response = await api.put(`/sme/templates/${templateId}`, data);
    return response.data;
  },

  /**
   * Delete a template
   */
  async delete(templateId: string): Promise<void> {
    await api.delete(`/sme/templates/${templateId}`);
  },

  /**
   * Mark a template as used
   */
  async use(templateId: string): Promise<SMETemplate> {
    const response = await api.post(`/sme/templates/${templateId}/use`);
    return response.data;
  },

  /**
   * Pre-fill template fields with company profile data
   */
  async prefill(request: TemplatePreFillRequest): Promise<TemplatePreFillResponse> {
    const response = await api.post("/sme/templates/prefill", request);
    return response.data;
  },
};

