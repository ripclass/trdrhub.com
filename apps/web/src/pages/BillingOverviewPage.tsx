/**
 * Billing Overview Page - main dashboard for billing information
 */

import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { AlertCircle, TrendingUp, Calendar, Download } from 'lucide-react';

// Billing components
import { QuotaMeter } from '@/components/billing/QuotaMeter';
import { PlanCard } from '@/components/billing/PlanCard';
import { ContractCard } from '@/components/billing/ContractCard';
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
import { useAuth } from '@/hooks/use-auth';

// Types
import { InvoiceStatus, PlanType, normalizePlanType, type BankContract } from '@/types/billing';
import { billingApi } from '@/api/billing';

export function BillingOverviewPage({ onTabChange, mode = 'sme' }: { onTabChange?: (tab: string) => void; mode?: 'sme' | 'bank' }) {
  const [searchParams] = useSearchParams();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([]);

  const { user } = useAuth();
  const refreshBillingData = useRefreshBillingData();
  const isBankMode = mode === 'bank';

  // Queries
  const { data: billingInfo, isLoading: billingLoading, error: billingError } = useBillingInfo();
  const { data: usageStats, isLoading: usageLoading, error: usageError } = useUsageStats();
  const { data: recentInvoices, isLoading: invoicesLoading } = useInvoices({
    page: 1,
    per_page: 5
  });

  // Bank contract query (bank mode only)
  const { data: bankContract, isLoading: contractLoading } = useQuery({
    queryKey: ['bankContract'],
    queryFn: () => billingApi.getBankContract(),
    enabled: isBankMode,
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

  const normalizedPlan = normalizePlanType(billingInfo?.plan);
  const normalizedBillingInfo = billingInfo && normalizedPlan
    ? { ...billingInfo, plan: normalizedPlan }
    : null;
  const hasUsageStats = Boolean(usageStats);
  const canRenderAlertBanner = Boolean(usageStats && normalizedPlan);
  const companyDisplayName =
    normalizedBillingInfo?.name || billingInfo?.name || user?.email?.split('@')[0] || 'your company';
  const currentSourceError =
    billingError instanceof Error
      ? billingError.message
      : usageError instanceof Error
        ? usageError.message
        : billingInfo && !normalizedBillingInfo
          ? 'billing plan data is incomplete'
        : 'unknown billing error';

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Billing Dashboard</h1>
          <p className="text-muted-foreground">
            Manage your subscription, usage, and billing for {companyDisplayName}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <BillingNav
        currentTab="overview"
        onTabChange={onTabChange}
        onUpgrade={handleUpgradeClick}
        onRefresh={refreshBillingData}
        mode={mode}
        hideUpgrade={isBankMode}
        pendingInvoicesCount={
          recentInvoices?.invoices.filter(i => i.status === InvoiceStatus.PENDING).length || 0
        }
        overdueInvoicesCount={
          recentInvoices?.invoices.filter(i => i.status === InvoiceStatus.OVERDUE).length || 0
        }
      />

      {/* Alert Banner */}
      {canRenderAlertBanner ? (
        <AlertBanner
          usage={usageStats}
          plan={normalizedPlan}
          lastInvoiceStatus={getLastInvoiceStatus()}
          onUpgrade={handleUpgradeClick}
          onRetryPayment={() => {
            toast.info('Payment retry functionality will be available soon.');
          }}
          onDismiss={handleAlertDismiss}
          dismissedAlerts={dismissedAlerts}
        />
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col gap-3 p-6 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-4 w-4 text-amber-600" />
              <div>
                <p className="font-medium text-foreground">Billing data is temporarily unavailable</p>
                <p>
                  TRDR Hub will not fabricate plan, quota, or spend data when the billing endpoints are unavailable. Retry refresh to load the real account state.
                </p>
              </div>
            </div>
            {(billingError || usageError) && (
              <p className="text-xs text-muted-foreground">
                Current source error: {currentSourceError}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Usage & Activity */}
        <div className="lg:col-span-2 space-y-6">
          {/* Usage Summary Cards */}
          {hasUsageStats ? (
            <UsageSummaryGrid
              usage={usageStats}
              lastInvoiceStatus={getLastInvoiceStatus()}
            />
          ) : (
            <Card className="border-dashed">
              <CardHeader>
                <CardTitle className="text-base">Usage summary unavailable</CardTitle>
                <CardDescription>
                  Quota and spend summaries appear here once the live billing endpoints respond.
                </CardDescription>
              </CardHeader>
            </Card>
          )}

          {/* Recent Usage */}
          {hasUsageStats && <UsageTableCompact maxRows={8} />}

          {/* Recent Invoices */}
          {!invoicesLoading && recentInvoices && recentInvoices.invoices.length > 0 && (
            <InvoicesTableCompact maxRows={5} />
          )}
        </div>

        {/* Right Column - Plan & Quota */}
        <div className="space-y-6">
          {/* Quota Meter */}
          {canRenderAlertBanner ? (
            <QuotaMeter
              usage={usageStats}
              plan={normalizedPlan}
            />
          ) : (
            <Card className="border-dashed">
              <CardHeader>
                <CardTitle className="text-base">Quota meter unavailable</CardTitle>
                <CardDescription>
                  Live quota usage appears here once the billing service returns a complete plan assignment for this account.
                </CardDescription>
              </CardHeader>
            </Card>
          )}

          {/* Plan/Contract Card */}
          {isBankMode && bankContract ? (
            <ContractCard contract={bankContract} />
          ) : !isBankMode && normalizedBillingInfo ? (
            <PlanCard
              billingInfo={normalizedBillingInfo}
              onUpgrade={handleUpgradeClick}
            />
          ) : !isBankMode ? (
            <Card className="border-dashed">
              <CardHeader>
                <CardTitle className="text-base">Plan details unavailable</CardTitle>
                <CardDescription>
                  Live plan details will appear here once the billing service returns a complete plan assignment for this account.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Skeleton className="h-[300px]" />
          )}

          {/* Quick Actions */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">Quick Actions</h3>

            <Button variant="outline" className="w-full gap-2" onClick={() => onTabChange?.('usage')}>
              <Download className="h-4 w-4" />
              View Usage Data
            </Button>

            <Button variant="outline" className="w-full gap-2" onClick={() => onTabChange?.('invoices')}>
              <Calendar className="h-4 w-4" />
              Open Invoices
            </Button>

            {!isBankMode && normalizedPlan && normalizedPlan !== PlanType.ENTERPRISE && (
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

      {/* Upgrade Modal (SME only) */}
      {!isBankMode && normalizedBillingInfo && (
        <UpgradeModal
          open={showUpgradeModal}
          onOpenChange={setShowUpgradeModal}
          currentBillingInfo={normalizedBillingInfo}
          onSuccess={handleUpgradeSuccess}
        />
      )}
    </div>
  );
}

export default BillingOverviewPage;
