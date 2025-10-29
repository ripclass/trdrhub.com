/**
 * Billing API client functions
 */

import { api } from './client';
import type {
  CompanyBillingInfo,
  CompanyBillingUpdate,
  UsageStats,
  UsageRecordList,
  UsageRecordsFilters,
  InvoiceList,
  InvoicesFilters,
  Invoice,
  PaymentIntent,
  PricingInfo,
  QuotaCheckResult,
  CheckoutRequest,
  AdminCompanyStats,
  AdminUsageReport,
  SystemBillingKPIs,
  BankComplianceReport,
  SMEMetrics,
  ComplianceFilters
} from '../types/billing';

// Company billing endpoints
export const billingApi = {
  // Get company billing information
  getBillingInfo: async (): Promise<CompanyBillingInfo> => {
    const response = await api.get('/billing/company');
    return response.data;
  },

  // Update company billing settings
  updateBillingInfo: async (data: CompanyBillingUpdate): Promise<CompanyBillingInfo> => {
    const response = await api.put('/billing/company', data);
    return response.data;
  },

  // Get usage statistics
  getUsageStats: async (): Promise<UsageStats> => {
    const response = await api.get('/billing/usage');
    return response.data;
  },

  // Get usage records with filtering
  getUsageRecords: async (filters: UsageRecordsFilters = {}): Promise<UsageRecordList> => {
    const response = await api.get('/billing/usage/records', { params: filters });
    return response.data;
  },

  // Get invoices with filtering
  getInvoices: async (filters: InvoicesFilters = {}): Promise<InvoiceList> => {
    const response = await api.get('/billing/invoices', { params: filters });
    return response.data;
  },

  // Get specific invoice
  getInvoice: async (invoiceId: string): Promise<Invoice> => {
    const response = await api.get(`/billing/invoices/${invoiceId}`);
    return response.data;
  },

  // Generate invoice for period
  generateInvoice: async (periodStart: string, periodEnd: string): Promise<Invoice> => {
    const response = await api.post('/billing/invoices/generate', null, {
      params: { period_start: periodStart, period_end: periodEnd }
    });
    return response.data;
  },

  // Create payment intent
  createPaymentIntent: async (request: {
    invoice_id?: string;
    amount?: number;
    currency?: string;
    provider?: string;
    return_url?: string;
    cancel_url?: string;
  }): Promise<PaymentIntent> => {
    const response = await api.post('/billing/payments/intents', request);
    return response.data;
  },

  // Get payment status
  getPaymentStatus: async (paymentId: string, provider: string = 'sslcommerz'): Promise<any> => {
    const response = await api.get(`/billing/payments/${paymentId}`, {
      params: { provider }
    });
    return response.data;
  },

  // Get pricing information
  getPricing: async (): Promise<PricingInfo> => {
    const response = await api.get('/billing/pricing');
    return response.data;
  },

  // Check quota
  checkQuota: async (action: string, quantity: number = 1): Promise<QuotaCheckResult> => {
    const response = await api.post('/billing/quota/check', { action, quantity });
    return response.data;
  },

  // Start checkout process
  startCheckout: async (request: CheckoutRequest): Promise<{ checkout_url: string; payment_intent_id: string }> => {
    // Create payment intent based on plan
    const planPrices = {
      STARTER: 15000,
      PROFESSIONAL: 45000,
      ENTERPRISE: 0 // Custom pricing
    };

    const amount = planPrices[request.plan as keyof typeof planPrices] || 0;

    const paymentIntent = await api.post('/billing/payments/intents', {
      amount,
      currency: 'BDT',
      provider: request.provider,
      return_url: request.return_url || `${window.location.origin}/dashboard/billing?success=true`,
      cancel_url: request.cancel_url || `${window.location.origin}/dashboard/billing?cancelled=true`,
      metadata: {
        plan: request.plan,
        upgrade: true
      }
    });

    return {
      checkout_url: paymentIntent.data.checkout_url,
      payment_intent_id: paymentIntent.data.id
    };
  },

  // Download invoice PDF
  downloadInvoice: async (invoiceId: string): Promise<Blob> => {
    const response = await api.get(`/billing/invoices/${invoiceId}/pdf`, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Export usage data
  exportUsageData: async (filters: UsageRecordsFilters = {}): Promise<Blob> => {
    const response = await api.get('/billing/usage/export', {
      params: filters,
      responseType: 'blob'
    });
    return response.data;
  },

  // Retry failed payment
  retryPayment: async (invoiceId: string, provider: string = 'sslcommerz'): Promise<PaymentIntent> => {
    const response = await api.post(`/billing/invoices/${invoiceId}/retry-payment`, {
      provider
    });
    return response.data;
  }
};

// Admin billing endpoints
export const adminBillingApi = {
  // Get system billing KPIs
  getSystemKPIs: async (): Promise<SystemBillingKPIs> => {
    // This would be calculated from the existing admin endpoints
    const [companiesData, usageReport] = await Promise.all([
      api.get('/billing/admin/companies?per_page=1000'),
      api.get('/billing/admin/usage-report', {
        params: {
          start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
          end_date: new Date().toISOString().split('T')[0]
        }
      })
    ]);

    const companies = companiesData.data;
    const report = usageReport.data;

    // Calculate KPIs
    const activeCompanies = companies.filter((c: AdminCompanyStats) => c.status === 'active').length;
    const delinquentAccounts = companies.filter((c: AdminCompanyStats) => c.status === 'overdue').length;

    return {
      total_revenue_monthly: report.total_revenue,
      active_companies: activeCompanies,
      delinquent_accounts: delinquentAccounts,
      invoices_this_cycle: report.total_companies, // Approximation
      average_revenue_per_company: report.total_revenue / (report.total_companies || 1),
      quota_utilization_average: companies.reduce((sum: number, c: AdminCompanyStats) =>
        sum + (c.quota_limit ? (c.quota_used / c.quota_limit) * 100 : 0), 0) / companies.length
    };
  },

  // Get all company statistics
  getCompanyStats: async (page: number = 1, perPage: number = 50): Promise<AdminCompanyStats[]> => {
    const response = await api.get('/billing/admin/companies', {
      params: { page, per_page: perPage }
    });
    return response.data;
  },

  // Get usage report
  getUsageReport: async (startDate: string, endDate: string): Promise<AdminUsageReport> => {
    const response = await api.get('/billing/admin/usage-report', {
      params: { start_date: startDate, end_date: endDate }
    });
    return response.data;
  },

  // Change company plan (admin only)
  changeCompanyPlan: async (companyId: string, plan: string): Promise<void> => {
    await api.put(`/billing/admin/companies/${companyId}/plan`, { plan });
  },

  // Suspend/reactivate company
  updateCompanyStatus: async (companyId: string, status: string): Promise<void> => {
    await api.put(`/billing/admin/companies/${companyId}/status`, { status });
  },

  // Send reminder email (stub)
  sendReminderEmail: async (companyId: string): Promise<void> => {
    // This would be implemented as a backend endpoint
    console.log(`Sending reminder email to company ${companyId}`);
  },

  // Export system billing data
  exportSystemData: async (format: 'csv' | 'pdf' = 'csv'): Promise<Blob> => {
    const response = await api.get(`/billing/admin/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  // Get revenue trends data
  getRevenueTrends: async (startDate: string, endDate: string): Promise<any[]> => {
    // This would aggregate usage report data by date
    const report = await api.get('/billing/admin/usage-report', {
      params: { start_date: startDate, end_date: endDate }
    });

    // Transform data for chart consumption
    // This is a simplified version - in practice, you'd have daily/weekly/monthly aggregations
    return [{
      date: startDate,
      revenue: report.data.total_revenue,
      companies: report.data.total_companies
    }];
  },

  // Bank compliance endpoints
  getBankComplianceReport: async (filters: ComplianceFilters): Promise<BankComplianceReport> => {
    const response = await api.get('/billing/bank/compliance-report', {
      params: filters
    });
    return response.data;
  },

  getSMEMetrics: async (filters: { period: string }): Promise<SMEMetrics> => {
    const response = await api.get('/billing/bank/sme-metrics', {
      params: filters
    });
    return response.data;
  },

  exportComplianceData: async (filters: ComplianceFilters & { format?: string }): Promise<Blob> => {
    const response = await api.get('/billing/bank/export-compliance', {
      params: filters,
      responseType: 'blob'
    });
    return response.data;
  }
};

// Utility functions
export const downloadFile = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

// Export all billing API functions
export default {
  ...billingApi,
  admin: adminBillingApi,
  utils: {
    downloadFile,
    formatDateForAPI
  }
};