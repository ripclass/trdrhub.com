import { describe, expect, it } from 'vitest';

import { buildImporterValidationFailureToast } from '@/lib/lcopilot/importerUpload';

describe('buildImporterValidationFailureToast', () => {
  it('maps network failures to a truthful validation error instead of demo-mode messaging', () => {
    expect(
      buildImporterValidationFailureToast({
        type: 'network',
        message: 'Backend unavailable',
        errorCode: 'network_down',
      }),
    ).toEqual({
      title: 'Validation Failed',
      description: 'Backend unavailable (network_down)',
      variant: 'destructive',
    });
  });

  it('preserves rate-limit messaging for importer upload', () => {
    expect(
      buildImporterValidationFailureToast({
        type: 'rate_limit',
        message: 'Slow down',
      }),
    ).toEqual({
      title: 'Rate Limit Exceeded',
      description: 'Slow down',
      variant: 'destructive',
    });
  });
});
