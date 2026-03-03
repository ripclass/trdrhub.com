import { describe, it, expect } from 'vitest';
import { sectionToResultsTab } from '@/lib/exporter/exporterSections';

describe('sectionToResultsTab', () => {
  it('maps non-tab result sections to overview deterministically', () => {
    expect(sectionToResultsTab('extracted-data' as any)).toBe('overview');
    expect(sectionToResultsTab('history' as any)).toBe('overview');
    expect(sectionToResultsTab('analytics' as any)).toBe('overview');
  });

  it('maps canonical sections to supported dashboard tabs', () => {
    expect(sectionToResultsTab('documents' as any)).toBe('documents');
    expect(sectionToResultsTab('issues' as any)).toBe('discrepancies');
    expect(sectionToResultsTab('customs' as any)).toBe('customs');
    expect(sectionToResultsTab('reviews' as any)).toBe('overview');
  });
});
