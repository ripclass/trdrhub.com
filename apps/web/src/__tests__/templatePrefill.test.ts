import { buildTemplateUploadPrefill } from '@/lib/exporter/templatePrefill';
import { describe, expect, it } from 'vitest';

describe('templatePrefill', () => {
  it('maps direct upload fields and notes from template data', () => {
    const result = buildTemplateUploadPrefill(
      {
        lc_number: 'LC-123',
        issue_date: '2026-03-16',
        notes: 'Use buyer-approved wording.',
      },
      'Standard Export LC',
    );

    expect(result.lcNumber).toBe('LC-123');
    expect(result.issueDate).toBe('2026-03-16');
    expect(result.notes).toContain('Use buyer-approved wording.');
    expect(result.appliedFields).toEqual(['LC number', 'issue date', 'notes']);
  });

  it('converts supported template context into deterministic upload notes', () => {
    const result = buildTemplateUploadPrefill(
      {
        beneficiary: '{{company_name}}',
        amount: 'USD {{amount}}',
        shipment_terms: 'FOB Chattogram',
      },
      'FOB Buyer Standard',
    );

    expect(result.lcNumber).toBeUndefined();
    expect(result.issueDate).toBeUndefined();
    expect(result.notes).toContain('Template context (FOB Buyer Standard):');
    expect(result.notes).toContain('Beneficiary: {{company_name}}');
    expect(result.notes).toContain('Shipment terms: FOB Chattogram');
    expect(result.appliedFields).toEqual(['template notes']);
  });
});
