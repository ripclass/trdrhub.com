import { PlanType, type CompanyBillingInfo, type UsageStats } from '@/types/billing';

export type LcopilotQuotaStatus = 'loading' | 'ready' | 'unavailable';

export interface LcopilotQuotaSnapshot {
  used: number;
  limit: number | null;
  remaining: number | null;
}

export interface LcopilotQuotaState {
  status: LcopilotQuotaStatus;
  plan: PlanType | null;
  quota: LcopilotQuotaSnapshot | null;
  isExhausted: boolean;
  canValidate: boolean;
  headline: string;
  detail: string;
  ctaLabel: string;
  ctaUrl: string;
}

interface BuildQuotaStateOptions {
  billingInfo?: CompanyBillingInfo | null;
  usageStats?: UsageStats | null;
  isLoading?: boolean;
  hasBillingError?: boolean;
  hasUsageError?: boolean;
}

export const normalizeQuotaActionUrl = (nextActionUrl?: string | null): string => {
  if (!nextActionUrl || nextActionUrl === '/billing/upgrade') {
    return '/pricing';
  }

  return nextActionUrl;
};

export const buildLcopilotQuotaState = ({
  billingInfo,
  usageStats,
  isLoading = false,
  hasBillingError = false,
  hasUsageError = false,
}: BuildQuotaStateOptions): LcopilotQuotaState => {
  const plan = billingInfo?.plan ?? null;
  const quota = usageStats
    ? {
        used: usageStats.quota_used ?? 0,
        limit: usageStats.quota_limit ?? null,
        remaining: usageStats.quota_remaining ?? null,
      }
    : billingInfo
    ? {
        used: billingInfo.quota_used ?? 0,
        limit: billingInfo.quota_limit ?? null,
        remaining: billingInfo.quota_remaining ?? null,
      }
    : null;

  if (isLoading && !quota) {
    return {
      status: 'loading',
      plan,
      quota,
      isExhausted: false,
      canValidate: true,
      headline: 'Checking usage allowance',
      detail: 'Fetching remaining LC checks for this billing cycle.',
      ctaLabel: 'View pricing',
      ctaUrl: '/pricing',
    };
  }

  if (!quota) {
    return {
      status: 'unavailable',
      plan,
      quota: null,
      isExhausted: false,
      canValidate: true,
      headline: 'Usage status unavailable',
      detail: 'You can still continue. Final quota enforcement happens when validation starts.',
      ctaLabel: 'View pricing',
      ctaUrl: '/pricing',
    };
  }

  const limit = quota.limit;
  const remaining = quota.remaining;
  const isExhausted = limit !== null && ((remaining ?? limit - quota.used) <= 0 || quota.used >= limit);

  if (limit === null) {
    return {
      status: 'ready',
      plan,
      quota,
      isExhausted: false,
      canValidate: true,
      headline: 'Unlimited validations available',
      detail: 'Your current plan does not enforce a monthly LC validation cap.',
      ctaLabel: 'View pricing',
      ctaUrl: '/pricing',
    };
  }

  if (isExhausted) {
    const isFree = plan === PlanType.FREE;
    return {
      status: 'ready',
      plan,
      quota,
      isExhausted: true,
      canValidate: false,
      headline: isFree ? 'Starter allowance exhausted' : 'Validation limit reached',
      detail: isFree
        ? `You have used all ${limit.toLocaleString()} starter checks in the current cycle. Upgrade to continue validating LC documents.`
        : `You have used all ${limit.toLocaleString()} validations in the current cycle. Upgrade or contact support to continue.`,
      ctaLabel: isFree ? 'Upgrade to continue' : 'View upgrade options',
      ctaUrl: '/pricing',
    };
  }

  const descriptor = plan === PlanType.FREE ? 'starter checks' : 'validations';
  const errorNote =
    hasUsageError || hasBillingError
      ? ' A billing refresh is pending; the backend will enforce the final limit when you validate.'
      : '';

  return {
    status: 'ready',
    plan,
    quota,
    isExhausted: false,
    canValidate: true,
    headline: `${(remaining ?? Math.max(limit - quota.used, 0)).toLocaleString()} ${descriptor} remaining`,
    detail: `${quota.used.toLocaleString()} of ${limit.toLocaleString()} used in the current cycle.${errorNote}`,
    ctaLabel: 'View pricing',
    ctaUrl: '/pricing',
  };
};

