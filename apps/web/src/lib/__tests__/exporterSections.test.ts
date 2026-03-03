import { describe, it, expect } from 'vitest';
import { sectionToResultsTab, resultsTabToSection } from '@/lib/exporter/exporterSections';

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

describe('resultsTabToSection', () => {
  it('keeps customs tab aligned with the customs section for deep links', () => {
    expect(resultsTabToSection('customs')).toBe('customs');
  });

  it('maps known results tabs back to their sections', () => {
    expect(resultsTabToSection('documents')).toBe('documents');
    expect(resultsTabToSection('discrepancies')).toBe('issues');
  });
});
