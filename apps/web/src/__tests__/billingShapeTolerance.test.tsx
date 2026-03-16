import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { BillingOverviewPage } from '@/pages/BillingOverviewPage';
import { BillingUsagePage } from '@/pages/BillingUsagePage';
import { PlanType, type CompanyBillingInfo, type UsageStats } from '@/types/billing';

import { renderWithProviders } from './testUtils';

const billingState: {
  billingInfo: CompanyBillingInfo | null;
  usageStats: UsageStats | null;
  usageRecords: { records: Array<{ action: string; cost: number }>; total: number; page: number; per_page: number; pages: number } | null;
  invoices: { invoices: Array<{ status: string }>; total: number; page: number; per_page: number; pages: number } | null;
} = {
  billingInfo: null,
  usageStats: null,
  usageRecords: null,
  invoices: null,
};

vi.mock('@/hooks/useBilling', () => ({
  useBillingInfo: () => ({
    data: billingState.billingInfo,
    isLoading: false,
    error: null,
  }),
  useUsageStats: () => ({
    data: billingState.usageStats,
    isLoading: false,
    error: null,
  }),
  useUsageRecords: () => ({
    data: billingState.usageRecords,
    isLoading: false,
    error: null,
  }),
  useInvoices: () => ({
    data: billingState.invoices,
    isLoading: false,
    error: null,
  }),
  useRefreshBillingData: () => vi.fn(),
  useBillingPolling: () => undefined,
  useExportUsageData: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({
    user: {
      email: 'exporter@example.com',
      role: 'exporter',
    },
  }),
}));

vi.mock('@/api/billing', () => ({
  billingApi: {
    getBankContract: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/components/billing/BillingNav', () => ({
  BillingNav: ({ currentTab }: { currentTab?: string }) => <div>BillingNav:{currentTab}</div>,
  BillingBreadcrumb: () => <div>BillingBreadcrumb</div>,
}));

vi.mock('@/components/billing/QuotaMeter', () => ({
  QuotaMeter: ({ plan }: { plan: string }) => <div>QuotaMeter:{plan}</div>,
}));

vi.mock('@/components/billing/PlanCard', () => ({
  PlanCard: ({ billingInfo }: { billingInfo: { plan: string } }) => <div>PlanCard:{billingInfo.plan}</div>,
}));

vi.mock('@/components/billing/ContractCard', () => ({
  ContractCard: () => <div>ContractCard</div>,
}));

vi.mock('@/components/billing/UsageSummaryCard', () => ({
  UsageSummaryGrid: () => <div>UsageSummaryGrid</div>,
}));

vi.mock('@/components/billing/AlertBanner', () => ({
  AlertBanner: ({ plan }: { plan: string }) => <div>AlertBanner:{plan}</div>,
}));

vi.mock('@/components/billing/UpgradeModal', () => ({
  UpgradeModal: () => null,
}));

vi.mock('@/components/billing/UsageTable', () => ({
  UsageTableCompact: () => <div>UsageTableCompact</div>,
  UsageTable: () => <div>UsageTable</div>,
}));

vi.mock('@/components/billing/InvoicesTable', () => ({
  InvoicesTableCompact: () => <div>InvoicesTableCompact</div>,
}));

const baseBillingInfo = (): CompanyBillingInfo =>
  ({
    id: 'company-1',
    name: 'Acme Exports',
    plan: PlanType.FREE,
    quota_limit: null,
    quota_used: 0,
    quota_remaining: null,
    billing_email: null,
    payment_customer_id: null,
  }) as CompanyBillingInfo;

const baseUsageStats = (): UsageStats => ({
  company_id: 'company-1',
  current_month: 0,
  current_week: 0,
  today: 0,
  total_usage: 0,
  total_cost: 0,
  quota_limit: null,
  quota_used: 0,
  quota_remaining: null,
});

describe('billing shape tolerance', () => {
  beforeEach(() => {
    billingState.billingInfo = baseBillingInfo();
    billingState.usageStats = baseUsageStats();
    billingState.usageRecords = {
      records: [],
      total: 0,
      page: 1,
      per_page: 25,
      pages: 0,
    };
    billingState.invoices = {
      invoices: [],
      total: 0,
      page: 1,
      per_page: 5,
      pages: 0,
    };
  });

  it('normalizes lowercase plan values on the billing overview page', () => {
    billingState.billingInfo = {
      ...baseBillingInfo(),
      plan: 'free' as unknown as PlanType,
    };

    render(renderWithProviders(<BillingOverviewPage />, '/lcopilot/exporter-dashboard?section=billing'));

    expect(screen.getByText('AlertBanner:FREE')).toBeInTheDocument();
    expect(screen.getByText('QuotaMeter:FREE')).toBeInTheDocument();
    expect(screen.getByText('PlanCard:FREE')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View Usage Data/i })).toBeInTheDocument();
  });

  it('shows an honest unavailable quota state when the plan assignment is missing on the usage page', () => {
    billingState.billingInfo = {
      ...baseBillingInfo(),
      plan: undefined as unknown as PlanType,
    };

    render(renderWithProviders(<BillingUsagePage />, '/lcopilot/exporter-dashboard?section=billing-usage'));

    expect(screen.getByText(/Quota meter unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/returns a complete plan assignment/i)).toBeInTheDocument();
    expect(screen.queryByText(/QuotaMeter:/i)).not.toBeInTheDocument();
  });
});
