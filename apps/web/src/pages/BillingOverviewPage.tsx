/**
 * Billing Overview Page - main dashboard for billing information
 */

import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { AlertCircle, TrendingUp, Calendar, Download } from 'lucide-react';

// Billing components
import { QuotaMeter } from '@/components/billing/QuotaMeter';
import { PlanCard } from '@/components/billing/PlanCard';
import { UsageSummaryGrid } from '@/components/billing/UsageSummaryCard';
import { AlertBanner } from '@/components/billing/AlertBanner';
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { UpgradeModal } from '@/components/billing/UpgradeModal';
import { UsageTableCompact } from '@/components/billing/UsageTable';
import { InvoicesTableCompact } from '@/components/billing/InvoicesTable';

// Hooks
import {
  useBillingInfo,
  useUsageStats,
  useInvoices,
  useRefreshBillingData,
  useBillingPolling
} from '@/hooks/useBilling';
import { useAuth } from '@/hooks/useAuth';

// Types
import { InvoiceStatus } from '@/types/billing';

export function BillingOverviewPage() {
  const [searchParams] = useSearchParams();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([]);

  const { user } = useAuth();
  const refreshBillingData = useRefreshBillingData();

  // Queries
  const { data: billingInfo, isLoading: billingLoading, error: billingError } = useBillingInfo();
  const { data: usageStats, isLoading: usageLoading } = useUsageStats();
  const { data: recentInvoices, isLoading: invoicesLoading } = useInvoices({
    page: 1,
    per_page: 5
  });

  // Enable polling when there are pending payments
  const hasPendingPayments = recentInvoices?.invoices.some(
    invoice => invoice.status === InvoiceStatus.PENDING
  );
  useBillingPolling(hasPendingPayments);

  // Handle URL parameters for payment success/failure
  React.useEffect(() => {
    const success = searchParams.get('success');
    const cancelled = searchParams.get('cancelled');
    const plan = searchParams.get('plan');

    if (success === 'true') {
      toast.success(
        plan
          ? `Plan upgrade successful! Welcome to ${plan}.`
          : 'Payment completed successfully!'
      );
      refreshBillingData();
    } else if (cancelled === 'true') {
      toast.info('Payment was cancelled. You can retry anytime.');
    }

    // Clean up URL params
    if (success || cancelled) {
      const newSearchParams = new URLSearchParams(searchParams);
      newSearchParams.delete('success');
      newSearchParams.delete('cancelled');
      newSearchParams.delete('plan');
      window.history.replaceState({}, '', `${window.location.pathname}?${newSearchParams}`);
    }
  }, [searchParams, refreshBillingData]);

  const handleAlertDismiss = (alertId: string) => {
    setDismissedAlerts(prev => [...prev, alertId]);
  };

  const handleUpgradeClick = () => {
    setShowUpgradeModal(true);
  };

  const handleUpgradeSuccess = () => {
    refreshBillingData();
    toast.success('Plan upgrade initiated! You will be redirected to complete payment.');
  };

  const getLastInvoiceStatus = (): InvoiceStatus | undefined => {
    return recentInvoices?.invoices[0]?.status;
  };

  // Loading state
  if (billingLoading || usageLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <BillingBreadcrumb />

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>

        <Skeleton className="h-12 w-full" />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-80 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (billingError || !billingInfo || !usageStats) {
    return (
      <div className="container mx-auto p-6">
        <BillingBreadcrumb />

        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">Unable to load billing information</h2>
          <p className="text-muted-foreground mb-4">
            There was an error loading your billing data. Please try again.
          </p>
          <Button onClick={refreshBillingData} variant="outline">
            Try Again
          </Button>
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
          <h1 className="text-2xl font-bold">Billing Dashboard</h1>
          <p className="text-muted-foreground">
            Manage your subscription, usage, and billing for {billingInfo.name}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={refreshBillingData}
            className="gap-2"
          >
            <TrendingUp className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <BillingNav
        onUpgrade={handleUpgradeClick}
        onRefresh={refreshBillingData}
        pendingInvoicesCount={
          recentInvoices?.invoices.filter(i => i.status === InvoiceStatus.PENDING).length || 0
        }
        overdueInvoicesCount={
          recentInvoices?.invoices.filter(i => i.status === InvoiceStatus.OVERDUE).length || 0
        }
      />

      {/* Alert Banner */}
      <AlertBanner
        usage={usageStats}
        plan={billingInfo.plan}
        lastInvoiceStatus={getLastInvoiceStatus()}
        onUpgrade={handleUpgradeClick}
        onRetryPayment={() => {
          // This would trigger payment retry for the failed invoice
          toast.info('Payment retry functionality will be available soon.');
        }}
        onDismiss={handleAlertDismiss}
        dismissedAlerts={dismissedAlerts}
      />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Usage & Activity */}
        <div className="lg:col-span-2 space-y-6">
          {/* Usage Summary Cards */}
          <UsageSummaryGrid
            usage={usageStats}
            lastInvoiceStatus={getLastInvoiceStatus()}
            trends={{
              validations: {
                value: 12.5,
                isPositive: true,
                period: 'last month'
              },
              cost: {
                value: -5.2,
                isPositive: false,
                period: 'last month'
              }
            }}
          />

          {/* Recent Usage */}
          <UsageTableCompact maxRows={8} />

          {/* Recent Invoices */}
          {!invoicesLoading && recentInvoices && recentInvoices.invoices.length > 0 && (
            <InvoicesTableCompact maxRows={5} />
          )}
        </div>

        {/* Right Column - Plan & Quota */}
        <div className="space-y-6">
          {/* Quota Meter */}
          <QuotaMeter
            usage={usageStats}
            plan={billingInfo.plan}
          />

          {/* Plan Card */}
          <PlanCard
            billingInfo={billingInfo}
            onUpgrade={handleUpgradeClick}
          />

          {/* Quick Actions */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">Quick Actions</h3>

            <Button variant="outline" className="w-full gap-2">
              <Download className="h-4 w-4" />
              Export Usage Data
            </Button>

            <Button variant="outline" className="w-full gap-2">
              <Calendar className="h-4 w-4" />
              Generate Invoice
            </Button>

            {billingInfo.plan !== 'ENTERPRISE' && (
              <Button
                onClick={handleUpgradeClick}
                className="w-full gap-2"
              >
                <TrendingUp className="h-4 w-4" />
                Upgrade Plan
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Upgrade Modal */}
      <UpgradeModal
        open={showUpgradeModal}
        onOpenChange={setShowUpgradeModal}
        currentBillingInfo={billingInfo}
        onSuccess={handleUpgradeSuccess}
      />
    </div>
  );
}

export default BillingOverviewPage;