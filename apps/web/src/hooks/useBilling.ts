/**
 * React Query hooks for billing functionality
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import billingApi, { adminBillingApi } from '../api/billing';
import type {
  UsageRecordsFilters,
  InvoicesFilters,
  CheckoutRequest,
  CompanyBillingUpdate,
  ComplianceFilters
} from '../types/billing';

// Query keys
export const billingKeys = {
  all: ['billing'] as const,
  info: () => [...billingKeys.all, 'info'] as const,
  usage: () => [...billingKeys.all, 'usage'] as const,
  usageRecords: (filters: UsageRecordsFilters) => [...billingKeys.usage(), 'records', filters] as const,
  invoices: (filters: InvoicesFilters) => [...billingKeys.all, 'invoices', filters] as const,
  invoice: (id: string) => [...billingKeys.all, 'invoice', id] as const,
  pricing: () => [...billingKeys.all, 'pricing'] as const,
  admin: {
    all: ['billing', 'admin'] as const,
    kpis: () => [...billingKeys.admin.all, 'kpis'] as const,
    companies: (page: number, perPage: number) => [...billingKeys.admin.all, 'companies', page, perPage] as const,
    usage: (startDate: string, endDate: string) => [...billingKeys.admin.all, 'usage', startDate, endDate] as const,
    trends: (startDate: string, endDate: string) => [...billingKeys.admin.all, 'trends', startDate, endDate] as const,
  },
  bank: {
    all: ['billing', 'bank'] as const,
    compliance: (filters: ComplianceFilters) => [...billingKeys.bank.all, 'compliance', filters] as const,
    smeMetrics: (period: string) => [...billingKeys.bank.all, 'sme-metrics', period] as const,
  }
};

// Company billing info hook
export const useBillingInfo = () => {
  return useQuery({
    queryKey: billingKeys.info(),
    queryFn: billingApi.getBillingInfo,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

// Usage statistics hook
export const useUsageStats = () => {
  return useQuery({
    queryKey: billingKeys.usage(),
    queryFn: billingApi.getUsageStats,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
  });
};

// Usage records hook with filters
export const useUsageRecords = (filters: UsageRecordsFilters = {}) => {
  return useQuery({
    queryKey: billingKeys.usageRecords(filters),
    queryFn: () => billingApi.getUsageRecords(filters),
    staleTime: 30 * 1000, // 30 seconds
    retry: 2,
  });
};

// Invoices hook with filters
export const useInvoices = (filters: InvoicesFilters = {}) => {
  return useQuery({
    queryKey: billingKeys.invoices(filters),
    queryFn: () => billingApi.getInvoices(filters),
    staleTime: 60 * 1000, // 1 minute
    retry: 2,
  });
};

// Single invoice hook
export const useInvoice = (invoiceId: string) => {
  return useQuery({
    queryKey: billingKeys.invoice(invoiceId),
    queryFn: () => billingApi.getInvoice(invoiceId),
    enabled: !!invoiceId,
    staleTime: 60 * 1000, // 1 minute
  });
};

// Pricing information hook
export const usePricing = () => {
  return useQuery({
    queryKey: billingKeys.pricing(),
    queryFn: billingApi.getPricing,
    staleTime: 60 * 60 * 1000, // 1 hour (pricing doesn't change often)
  });
};

// Update billing info mutation
export const useUpdateBillingInfo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: billingApi.updateBillingInfo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.info() });
      toast.success('Billing information updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update billing info: ${error.message}`);
    },
  });
};

// Checkout mutation
export const useCheckout = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CheckoutRequest) => {
      const result = await billingApi.startCheckout(request);
      // Redirect to checkout URL
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
      return result;
    },
    onSuccess: () => {
      toast.success('Redirecting to payment...');
    },
    onError: (error: any) => {
      toast.error(`Checkout failed: ${error.message}`);
    },
    onSettled: () => {
      // Invalidate billing info to reflect any changes
      queryClient.invalidateQueries({ queryKey: billingKeys.info() });
    },
  });
};

// Generate invoice mutation
export const useGenerateInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ startDate, endDate }: { startDate: string; endDate: string }) =>
      billingApi.generateInvoice(startDate, endDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.all });
      toast.success('Invoice generated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to generate invoice: ${error.message}`);
    },
  });
};

// Retry payment mutation
export const useRetryPayment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, provider }: { invoiceId: string; provider?: string }) =>
      billingApi.retryPayment(invoiceId, provider),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.all });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
      toast.success('Payment retry initiated');
    },
    onError: (error: any) => {
      toast.error(`Failed to retry payment: ${error.message}`);
    },
  });
};

// Download invoice mutation
export const useDownloadInvoice = () => {
  return useMutation({
    mutationFn: billingApi.downloadInvoice,
    onSuccess: (blob, invoiceId) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Invoice downloaded');
    },
    onError: (error: any) => {
      toast.error(`Failed to download invoice: ${error.message}`);
    },
  });
};

// Export usage data mutation
export const useExportUsageData = () => {
  return useMutation({
    mutationFn: billingApi.exportUsageData,
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `usage-export-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Usage data exported');
    },
    onError: (error: any) => {
      toast.error(`Failed to export usage data: ${error.message}`);
    },
  });
};

// Check quota hook
export const useCheckQuota = () => {
  return useMutation({
    mutationFn: ({ action, quantity }: { action: string; quantity?: number }) =>
      billingApi.checkQuota(action, quantity),
    onError: (error: any) => {
      toast.error(`Quota check failed: ${error.message}`);
    },
  });
};

// Admin hooks
export const useAdminSystemKPIs = () => {
  return useQuery({
    queryKey: billingKeys.admin.kpis(),
    queryFn: adminBillingApi.getSystemKPIs,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useAdminCompanyStats = (page: number = 1, perPage: number = 50) => {
  return useQuery({
    queryKey: billingKeys.admin.companies(page, perPage),
    queryFn: () => adminBillingApi.getCompanyStats(page, perPage),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useAdminUsageReport = (startDate: string, endDate: string) => {
  return useQuery({
    queryKey: billingKeys.admin.usage(startDate, endDate),
    queryFn: () => adminBillingApi.getUsageReport(startDate, endDate),
    enabled: !!startDate && !!endDate,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useAdminRevenueTrends = (startDate: string, endDate: string) => {
  return useQuery({
    queryKey: billingKeys.admin.trends(startDate, endDate),
    queryFn: () => adminBillingApi.getRevenueTrends(startDate, endDate),
    enabled: !!startDate && !!endDate,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Admin mutations
export const useChangeCompanyPlan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ companyId, plan }: { companyId: string; plan: string }) =>
      adminBillingApi.changeCompanyPlan(companyId, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.admin.all });
      toast.success('Company plan updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update company plan: ${error.message}`);
    },
  });
};

export const useUpdateCompanyStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ companyId, status }: { companyId: string; status: string }) =>
      adminBillingApi.updateCompanyStatus(companyId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.admin.all });
      toast.success('Company status updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update company status: ${error.message}`);
    },
  });
};

export const useSendReminderEmail = () => {
  return useMutation({
    mutationFn: adminBillingApi.sendReminderEmail,
    onSuccess: () => {
      toast.success('Reminder email sent successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to send reminder email: ${error.message}`);
    },
  });
};

export const useExportSystemData = () => {
  return useMutation({
    mutationFn: adminBillingApi.exportSystemData,
    onSuccess: (blob, format) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `system-billing-export-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('System data exported successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to export system data: ${error.message}`);
    },
  });
};

// Utility hooks
export const useRefreshBillingData = () => {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: billingKeys.all });
    toast.success('Billing data refreshed');
  };
};

export const useBillingPolling = (enabled: boolean = false) => {
  const queryClient = useQueryClient();

  // Poll billing info every 30 seconds when enabled
  useQuery({
    queryKey: ['billing-poll'],
    queryFn: async () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.info() });
      queryClient.invalidateQueries({ queryKey: billingKeys.usage() });
      return null;
    },
    refetchInterval: 30 * 1000, // 30 seconds
    enabled,
  });
};

// Bank compliance hooks
export const useBankComplianceReport = (filters: ComplianceFilters, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: billingKeys.bank.compliance(filters),
    queryFn: () => adminBillingApi.getBankComplianceReport(filters),
    staleTime: 10 * 60 * 1000, // 10 minutes
    enabled: options?.enabled ?? true,
  });
};

export const useSMEMetrics = (filters: { period: string }, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: billingKeys.bank.smeMetrics(filters.period),
    queryFn: () => adminBillingApi.getSMEMetrics(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? true,
  });
};

export const useExportComplianceData = () => {
  return useMutation({
    mutationFn: (filters: ComplianceFilters & { format?: string }) =>
      adminBillingApi.exportComplianceData(filters),
    onSuccess: (blob: Blob, variables: ComplianceFilters & { format?: string }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const format = variables.format || 'xlsx';
      a.download = `bank-compliance-report-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Compliance report exported successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to export compliance report: ${error.message}`);
    },
  });
};