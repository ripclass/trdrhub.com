/**
 * Exporter-specific API client for customs pack generation and bank submissions.
 */

import { api } from './client';

export interface CustomsPackGenerateRequest {
  validation_session_id: string;
  lc_number?: string;
}

export interface CustomsPackManifest {
  lc_number: string;
  validation_session_id: string;
  generated_at: string;
  documents: Array<{
    name: string;
    type: string;
    sha256: string;
    size_bytes: number;
  }>;
  generator_version: string;
}

export interface CustomsPackGenerateResponse {
  download_url: string;
  file_name: string;
  manifest: CustomsPackManifest;
  sha256: string;
  generated_at: string;
}

export interface BankSubmissionCreate {
  validation_session_id: string;
  lc_number: string;
  bank_id?: string;
  bank_name?: string;
  note?: string;
  idempotency_key?: string;
}

export type SubmissionStatus = 'pending' | 'accepted' | 'rejected' | 'failed' | 'cancelled';

export interface BankSubmissionRead {
  id: string;
  company_id: string;
  user_id: string;
  validation_session_id: string;
  lc_number: string;
  bank_id?: string;
  bank_name?: string;
  status: SubmissionStatus;
  manifest_hash?: string;
  note?: string;
  receipt_url?: string;
  created_at: string;
  submitted_at?: string;
  result_at?: string;
}

export interface BankSubmissionListResponse {
  items: BankSubmissionRead[];
  total: number;
}

export type SubmissionEventType = 'created' | 'bank_ack' | 'bank_reject' | 'retry' | 'cancel' | 'manifest_generated' | 'receipt_generated';

export interface SubmissionEventRead {
  id: string;
  submission_id: string;
  event_type: SubmissionEventType;
  payload?: Record<string, any>;
  actor_id?: string;
  actor_name?: string;
  created_at: string;
}

export interface SubmissionEventListResponse {
  items: SubmissionEventRead[];
  total: number;
}

export interface GuardrailCheckRequest {
  validation_session_id: string;
  lc_number?: string;
}

export interface GuardrailCheckResponse {
  can_submit: boolean;
  blocking_issues: string[];
  warnings: string[];
  required_docs_present: boolean;
  high_severity_discrepancies: number;
  policy_checks_passed: boolean;
}

export const exporterApi = {
  /**
   * Generate a customs pack ZIP file with all documents, manifest, and coversheet.
   */
  async generateCustomsPack(data: CustomsPackGenerateRequest): Promise<CustomsPackGenerateResponse> {
    const response = await api.post('/api/exporter/customs-pack', data);
    return response.data;
  },

  /**
   * Download the customs pack ZIP file.
   */
  async downloadCustomsPack(validationSessionId: string): Promise<Blob> {
    const response = await api.get(`/api/exporter/customs-pack/${validationSessionId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Create a bank submission (with guardrails).
   */
  async createBankSubmission(data: BankSubmissionCreate): Promise<BankSubmissionRead> {
    const response = await api.post('/api/exporter/bank-submissions', data);
    return response.data;
  },

  /**
   * List bank submissions for the current exporter.
   */
  async listBankSubmissions(params?: {
    lc_number?: string;
    validation_session_id?: string;
    status?: SubmissionStatus;
    skip?: number;
    limit?: number;
  }): Promise<BankSubmissionListResponse> {
    const response = await api.get('/api/exporter/bank-submissions', { params });
    return response.data;
  },

  /**
   * Get event timeline for a submission.
   */
  async getSubmissionEvents(submissionId: string): Promise<SubmissionEventListResponse> {
    const response = await api.get(`/api/exporter/bank-submissions/${submissionId}/events`);
    return response.data;
  },

  /**
   * Cancel a pending submission.
   */
  async cancelSubmission(submissionId: string): Promise<BankSubmissionRead> {
    const response = await api.post(`/api/exporter/bank-submissions/${submissionId}/cancel`);
    return response.data;
  },

  /**
   * Check guardrails before submission (for client-side pre-check).
   */
  async checkGuardrails(data: GuardrailCheckRequest): Promise<GuardrailCheckResponse> {
    const response = await api.post('/api/exporter/guardrails/check', data);
    return response.data;
  },
};

