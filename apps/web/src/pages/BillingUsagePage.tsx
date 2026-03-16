/**
 * Billing Usage Page - detailed usage analytics and records
 */

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TrendingUp,
  Calendar,
  Download,
  Activity,
  DollarSign,
  BarChart3,
  PieChart as PieChartIcon
} from 'lucide-react';

// Billing components
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { UsageTable } from '@/components/billing/UsageTable';
import { QuotaMeter } from '@/components/billing/QuotaMeter';

// Hooks
import {
  useBillingInfo,
  useUsageStats,
  useUsageRecords,
  useExportUsageData,
  useRefreshBillingData
} from '@/hooks/useBilling';

// Types
import { formatCurrency } from '@/types/billing';
import type { UsageRecordsFilters } from '@/types/billing';

export function BillingUsagePage({ onTabChange, mode = 'sme' }: { onTabChange?: (tab: string) => void; mode?: 'sme' | 'bank' }) {
  const [filters, setFilters] = useState<UsageRecordsFilters>({
    page: 1,
    per_page: 25
  });
  const isBankMode = mode === 'bank';

  // Mock data for bank filters (in real app, this would come from API)
  const mockClients = isBankMode ? [
    { id: 'client-1', name: 'ABC Exports Ltd' },
    { id: 'client-2', name: 'XYZ Imports Ltd' },
    { id: 'client-3', name: 'Global Trading Co' },
  ] : [];
  const mockBranches = isBankMode ? [
    { id: 'branch-1', name: 'Dhaka Main' },
    { id: 'branch-2', name: 'Chittagong' },
    { id: 'branch-3', name: 'Sylhet' },
  ] : [];
  const mockProducts = isBankMode ? ['LC_VALIDATION', 'RE_CHECK', 'AMENDMENT'] : [];

  // Queries
  const { data: billingInfo } = useBillingInfo();
  const { data: usageStats, isLoading: statsLoading } = useUsageStats();
  const { data: usageRecords } = useUsageRecords(filters);
  const exportMutation = useExportUsageData();
  const refreshBillingData = useRefreshBillingData();

  const visibleActionBreakdown = useMemo(() => {
    const records = usageRecords?.records || [];
    const grouped = new Map<string, { action: string; count: number; cost: number }>();

    records.forEach((record) => {
      const current = grouped.get(record.action) || { action: record.action, count: 0, cost: 0 };
      current.count += 1;
      current.cost += record.cost || 0;
      grouped.set(record.action, current);
    });

    return Array.from(grouped.values()).sort((a, b) => b.count - a.count);
  }, [usageRecords]);

  const handleExport = () => {
    exportMutation.mutate(filters);
  };

  const handleFilterChange = (newFilters: UsageRecordsFilters) => {
    setFilters(newFilters);
  };

  if (statsLoading || !usageStats) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <BillingBreadcrumb />
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-12 w-full" />
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Usage Analytics</h1>
          <p className="text-muted-foreground">
            Detailed usage history and trends for your LC validation services
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={handleExport}
            disabled={exportMutation.isPending}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <BillingNav 
        currentTab="usage" 
        onTabChange={onTabChange} 
        onRefresh={refreshBillingData}
        mode={mode} 
        hideUpgrade={isBankMode} 
      />

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageStats.current_month}</div>
            <p className="text-xs text-muted-foreground">
              validations used
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageStats.current_week}</div>
            <p className="text-xs text-muted-foreground">
              validations this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(usageStats.total_cost)}
            </div>
            <p className="text-xs text-muted-foreground">
              lifetime spending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(usageStats.current_month / new Date().getDate())}
            </div>
            <p className="text-xs text-muted-foreground">
              validations per day
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Honest beta insights row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Usage Trend Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-4">
              Daily trend charts are not connected to a real billing history feed yet. This page stays visible, but TRDR Hub will not fabricate chart points or spend curves.
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Live month total</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{usageStats.current_month}</div>
                <div className="text-xs text-muted-foreground">Real validations used this month</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Live quota remaining</div>
                <div className="mt-1 text-lg font-semibold text-foreground">
                  {usageStats.quota_remaining === null ? 'Unlimited' : usageStats.quota_remaining}
                </div>
                <div className="text-xs text-muted-foreground">Current backend quota truth</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Live total spend</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{formatCurrency(usageStats.total_cost)}</div>
                <div className="text-xs text-muted-foreground">Real recorded spend to date</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {billingInfo && (
            <QuotaMeter
              usage={usageStats}
              plan={billingInfo.plan}
              showCost={false}
            />
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChartIcon className="h-5 w-5" />
                Recent Actions in View
              </CardTitle>
            </CardHeader>
            <CardContent>
              {visibleActionBreakdown.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-4 text-sm text-muted-foreground">
                  No recent usage records are loaded for the current filter set. This page will not invent an action mix.
                </div>
              ) : (
                <div className="space-y-2">
                  {visibleActionBreakdown.slice(0, 5).map((item) => (
                    <div key={item.action} className="flex items-center justify-between rounded-lg border p-3">
                      <div>
                        <div className="text-sm font-medium text-foreground">{item.action.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-muted-foreground">From the currently loaded usage records</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{item.count}</div>
                        <div className="text-xs text-muted-foreground">{formatCurrency(item.cost)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Detailed Usage Table */}
      <UsageTable
        initialFilters={filters}
        bankMode={isBankMode}
        clients={mockClients}
        branches={mockBranches}
        products={mockProducts}
        onRowClick={(record) => {
          console.log('Usage record clicked:', record);
          // Could open a modal with detailed information
        }}
      />
    </div>
  );
}

export default BillingUsagePage;
