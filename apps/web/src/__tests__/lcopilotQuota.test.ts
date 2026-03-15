import { describe, expect, it } from 'vitest';

import { buildLcopilotQuotaState } from '@/lib/lcopilot/quota';
import { PlanType, type CompanyBillingInfo, type UsageStats } from '@/types/billing';

const billingInfo: CompanyBillingInfo = {
  id: 'company-1',
  name: 'Acme Exports',
  plan: PlanType.FREE,
  quota_limit: 5,
  quota_used: 5,
  quota_remaining: 0,
  billing_email: null,
  payment_customer_id: null,
};

const usageStats = (overrides: Partial<UsageStats> = {}): UsageStats => ({
  company_id: 'company-1',
  current_month: 3,
  current_week: 1,
  today: 0,
  total_usage: 3,
  total_cost: 0,
  quota_limit: 5,
  quota_used: 3,
  quota_remaining: 2,
  ...overrides,
});

describe('buildLcopilotQuotaState', () => {
  it('keeps validation available when usage stats show remaining quota', () => {
    const state = buildLcopilotQuotaState({
      billingInfo,
      usageStats: usageStats(),
    });

    expect(state.status).toBe('ready');
    expect(state.canValidate).toBe(true);
    expect(state.isExhausted).toBe(false);
    expect(state.headline).toContain('2 starter checks remaining');
  });

  it('blocks validation when starter allowance is exhausted', () => {
    const state = buildLcopilotQuotaState({
      billingInfo,
      usageStats: usageStats({
        quota_used: 5,
        quota_remaining: 0,
      }),
    });

    expect(state.status).toBe('ready');
    expect(state.canValidate).toBe(false);
    expect(state.isExhausted).toBe(true);
    expect(state.headline).toBe('Starter allowance exhausted');
  });

  it('prefers usage stats over stale company billing totals', () => {
    const state = buildLcopilotQuotaState({
      billingInfo: {
        ...billingInfo,
        quota_used: 5,
        quota_remaining: 0,
      },
      usageStats: usageStats({
        quota_used: 4,
        quota_remaining: 1,
      }),
    });

    expect(state.canValidate).toBe(true);
    expect(state.isExhausted).toBe(false);
    expect(state.headline).toContain('1 starter checks remaining');
  });

  it('does not pre-block when quota state is unavailable', () => {
    const state = buildLcopilotQuotaState({
      billingInfo: null,
      usageStats: null,
      hasBillingError: true,
      hasUsageError: true,
    });

    expect(state.status).toBe('unavailable');
    expect(state.canValidate).toBe(true);
    expect(state.isExhausted).toBe(false);
  });
});

