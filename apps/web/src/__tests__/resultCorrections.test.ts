import { describe, expect, it } from 'vitest';
import { hydrateManifestFromCustomsPack, resolveIssueDateFromLc } from '@/lib/exporter/resultCorrections';

describe('resultCorrections', () => {
  it('prefers MT700 31C date when legacy issue date is inverted', () => {
    const resolved = resolveIssueDateFromLc({
      dates: { issue: '2015-04-26' },
      mt700: { blocks: { '31C': '260415' } },
    });

    expect(resolved).toBe('2026-04-15');
  });

  it('hydrates manifest payload from customs_pack manifest to keep state consistent', () => {
    const manifest = hydrateManifestFromCustomsPack(
      {
        format: 'zip-manifest-v1',
        manifest: [{ name: 'Invoice.pdf', tag: 'commercial_invoice' }],
      },
      'LC-123',
      'session-1',
    );

    expect(manifest).not.toBeNull();
    expect(manifest?.documents).toHaveLength(1);
    expect(manifest?.documents[0]?.name).toBe('Invoice.pdf');
    expect(manifest?.documents[0]?.type).toBe('commercial_invoice');
  });
});
