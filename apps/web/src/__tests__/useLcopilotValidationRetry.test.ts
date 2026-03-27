import { describe, expect, it } from 'vitest';

import { vi } from 'vitest';

vi.mock('@/api/client', () => ({
  api: {},
}));

import { shouldRetryValidationRequest } from '@/hooks/use-lcopilot';

describe('useValidate transient retry guard', () => {
  it('retries transient gateway failures before the final attempt', () => {
    expect(
      shouldRetryValidationRequest(
        {
          response: {
            status: 502,
          },
        },
        1,
        2,
      ),
    ).toBe(true);
  });

  it('does not retry non-transient server failures', () => {
    expect(
      shouldRetryValidationRequest(
        {
          response: {
            status: 500,
          },
        },
        1,
        2,
      ),
    ).toBe(false);
  });

  it('does not retry after the final attempt budget is exhausted', () => {
    expect(
      shouldRetryValidationRequest(
        {
          response: {
            status: 503,
          },
        },
        2,
        2,
      ),
    ).toBe(false);
  });

  it('retries transient client/network transport failures', () => {
    expect(
      shouldRetryValidationRequest(
        {
          code: 'ERR_NETWORK',
        },
        1,
        2,
      ),
    ).toBe(true);
  });
});
