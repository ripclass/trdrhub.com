import { useMemo } from 'react';

import { useBillingInfo, useUsageStats } from '@/hooks/useBilling';
import { buildLcopilotQuotaState } from '@/lib/lcopilot/quota';

export const useLcopilotQuota = () => {
  const billingInfoQuery = useBillingInfo();
  const usageStatsQuery = useUsageStats();

  return useMemo(
    () =>
      buildLcopilotQuotaState({
        billingInfo: billingInfoQuery.data,
        usageStats: usageStatsQuery.data,
        isLoading: billingInfoQuery.isLoading || usageStatsQuery.isLoading,
        hasBillingError: !!billingInfoQuery.error,
        hasUsageError: !!usageStatsQuery.error,
      }),
    [
      billingInfoQuery.data,
      billingInfoQuery.error,
      billingInfoQuery.isLoading,
      usageStatsQuery.data,
      usageStatsQuery.error,
      usageStatsQuery.isLoading,
    ],
  );
};

