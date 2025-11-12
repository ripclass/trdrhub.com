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
  ComplianceFilters,
  BankContract,
  Allocation,
  AllocationList,
  AllocationUpdate
} from '../types/billing';
import { PaymentProvider, PlanType, Currency, InvoiceStatus } from '../types/billing';

// Mock data for when backend is unavailable
const getMockBillingInfo = (): CompanyBillingInfo => ({
  id: 'mock-company-1',
  name: 'Your Company',
  plan: PlanType.FREE,
  quota_limit: 100,
  quota_used: 0,
  quota_remaining: 100,
  billing_email: null,
  payment_customer_id: null,
});

const getMockUsageStats = (): UsageStats => ({
  company_id: 'mock-company-1',
  current_month: 0,
  current_week: 0,
  today: 0,
  total_usage: 0,
  total_cost: 0,
  quota_limit: 100,
  quota_used: 0,
  quota_remaining: 100,
});

const getMockInvoices = (filters: InvoicesFilters = {}): InvoiceList => {
  const mockInvoices: Invoice[] = [];
  const page = filters.page || 1;
  const perPage = filters.per_page || 20;
  
  return {
    invoices: mockInvoices,
    total: 0,
    page,
    per_page: perPage,
    pages: 0,
  };
};

const getMockUsageRecords = (filters: UsageRecordsFilters = {}): UsageRecordList => {
  return {
    records: [],
    total: 0,
    page: filters.page || 1,
    per_page: filters.per_page || 20,
    pages: 0,
  };
};

const getMockBankContract = (): BankContract => ({
  id: 'mock-contract-1',
  bank_id: 'mock-bank-1',
  contract_number: 'CNT-2024-001',
  plan: PlanType.ENTERPRISE,
  contract_term_months: 12,
  start_date: new Date(new Date().getFullYear(), 0, 1).toISOString(),
  end_date: new Date(new Date().getFullYear() + 1, 0, 1).toISOString(),
  quota_limit: null, // unlimited
  overage_rate: 50,
  billing_contact_name: 'John Doe',
  billing_contact_email: 'billing@bank.com',
  billing_contact_phone: '+880-1234-567890',
  po_reference: 'PO-2024-001',
  next_settlement_date: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString(),
  payment_terms: 'Net-30',
  currency: Currency.BDT,
  status: 'active',
  created_at: new Date(new Date().getFullYear(), 0, 1).toISOString(),
  updated_at: null,
});

const getMockAllocations = (filters: { page?: number; per_page?: number } = {}): AllocationList => {
  const page = filters.page || 1;
  const perPage = filters.per_page || 20;
  
  const mockAllocations: Allocation[] = [
    {
      id: 'alloc-1',
      bank_id: 'mock-bank-1',
      client_id: 'client-1',
      client_name: 'ABC Exports Ltd',
      branch_id: null,
      branch_name: null,
      product: 'LC_VALIDATION',
      budget_limit: 100000,
      quota_limit: 1000,
      usage_current_period: 450,
      usage_cost_current_period: 22500,
      remaining_budget: 77500,
      alerts_enabled: true,
      alert_threshold_percent: 80,
      period_start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString(),
      period_end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: null,
    },
  ];
  
  return {
    allocations: mockAllocations,
    total: mockAllocations.length,
    page,
    per_page: perPage,
    pages: Math.ceil(mockAllocations.length / perPage),
  };
};

// Removed mock fallback - API calls should fail properly

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
  startCheckout: async (request: CheckoutRequest): Promise<PaymentIntent> => {
    const planPrices: Record<string, number> = {
      FREE: 0,
      STARTER: 15000,
      PROFESSIONAL: 45000,
      ENTERPRISE: 0,
    };

    const payload: Record<string, unknown> = {
      provider: request.provider,
      return_url: request.return_url || `${window.location.origin}/dashboard/billing?success=true`,
      cancel_url: request.cancel_url || `${window.location.origin}/dashboard/billing?cancelled=true`,
      metadata: {
        plan: request.plan,
        ...(request.metadata || {}),
      },
    };

    if (typeof request.amount === 'number') {
      payload.amount = request.amount;
    }

    if (request.currency) {
      payload.currency = request.currency.toUpperCase();
    }

    if (request.priceId) {
      payload.price_id = request.priceId;
      payload.mode = request.mode || 'subscription';
      payload.quantity = request.quantity || 1;
      payload.currency = (request.currency || 'USD').toUpperCase();
    } else if (request.provider === PaymentProvider.SSLCOMMERZ) {
      payload.amount = payload.amount ?? planPrices[request.plan] ?? 0;
      payload.currency = 'BDT';
    }

    if (request.paymentMethodTypes) {
      payload.payment_method_types = request.paymentMethodTypes;
    }

    const response = await api.post('/billing/payments/intents', payload, {
      params: { provider: request.provider },
    });

    return response.data;
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
  },

  // Bank-specific endpoints
  // Get bank contract
  getBankContract: async (): Promise<BankContract> => {
    const response = await api.get('/billing/bank/contract');
    return response.data;
  },

  // Get allocations
  getAllocations: async (filters: { page?: number; per_page?: number } = {}): Promise<AllocationList> => {
    const response = await api.get('/billing/bank/allocations', { params: filters });
    return response.data;
  },

  // Update allocation
  updateAllocation: async (allocationId: string, data: AllocationUpdate): Promise<Allocation> => {
    const response = await api.put(`/billing/bank/allocations/${allocationId}`, data);
    return response.data;
  },
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