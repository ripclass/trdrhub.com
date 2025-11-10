/**
 * Importer API client functions for supplier fix pack and bank precheck
 */

import { api } from './client';

export interface SupplierFixPackRequest {
  validation_session_id: string;
  lc_number?: string;
}

export interface SupplierFixPackResponse {
  download_url: string;
  file_name: string;
  generated_at: string;
  issue_count: number;
}

export interface NotifySupplierRequest {
  validation_session_id: string;
  supplier_email: string;
  message?: string;
  lc_number?: string;
}

export interface NotifySupplierResponse {
  success: boolean;
  message: string;
  notification_id: string;
  sent_at: string;
}

export interface BankPrecheckRequest {
  validation_session_id: string;
  lc_number: string;
  bank_name?: string;
  notes?: string;
}

export interface BankPrecheckResponse {
  success: boolean;
  message: string;
  request_id: string;
  submitted_at: string;
  bank_name?: string;
}

export const importerApi = {
  /**
   * Generate supplier fix pack
   */
  async generateSupplierFixPack(request: SupplierFixPackRequest): Promise<SupplierFixPackResponse> {
    const response = await api.post<SupplierFixPackResponse>('/api/importer/supplier-fix-pack', request);
    return response.data;
  },

  /**
   * Download supplier fix pack
   */
  async downloadSupplierFixPack(validationSessionId: string): Promise<Blob> {
    const response = await api.get(
      `/api/importer/supplier-fix-pack/${validationSessionId}/download`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  /**
   * Notify supplier with fix pack
   */
  async notifySupplier(request: NotifySupplierRequest): Promise<NotifySupplierResponse> {
    const response = await api.post<NotifySupplierResponse>('/api/importer/notify-supplier', request);
    return response.data;
  },

  /**
   * Request bank precheck review
   */
  async requestBankPrecheck(request: BankPrecheckRequest): Promise<BankPrecheckResponse> {
    const response = await api.post<BankPrecheckResponse>('/api/importer/bank-precheck', request);
    return response.data;
  },
};

