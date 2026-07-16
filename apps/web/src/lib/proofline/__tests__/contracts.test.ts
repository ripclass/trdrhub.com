import { describe, expect, it } from 'vitest';

import {
  ProoflineFindingSchema,
  TradeCaseSummarySchema,
} from '@shared/types';

const baseCase = {
  id: '72c47e47-a8d4-49f2-9512-c9ca2a15b9d2',
  case_reference: 'PL-7QG4M2',
  company_id: '25c8cbb4-9d77-4350-9f4e-fffd2f0f7fb2',
  title: 'US buyer July shipment',
  status: 'draft',
  service_package_id: 'proofline_standard',
  recommended_decision: null,
  final_decision: null,
  currency: 'USD',
  amount: '125000.00',
  origin_country: 'BD',
  destination_country: 'US',
  document_count: 0,
  finding_counts: { high: 0, medium: 0, low: 0 },
  created_at: '2026-07-16T08:00:00Z',
  updated_at: '2026-07-16T08:00:00Z',
};

describe('Proofline shared contracts', () => {
  it.each(['letter_of_credit', 'open_account'] as const)(
    'parses a %s trade case through one response shape',
    (paymentArrangement) => {
      const result = TradeCaseSummarySchema.parse({
        ...baseCase,
        payment_arrangement: paymentArrangement,
      });

      expect(result.payment_arrangement).toBe(paymentArrangement);
    },
  );

  it('keeps Expected, Found, and SuggestedFix data structured', () => {
    const result = ProoflineFindingSchema.parse({
      id: 'f6ac91d9-2ed4-4645-adbb-f7448837860b',
      source_module: 'open_account',
      source_finding_id: 'OA-PAYMENT-TERMS-1',
      category: 'payment_terms',
      severity: 'high',
      title: 'Payment trigger is not evidenced',
      explanation: 'The submitted contract does not identify the invoice approval trigger.',
      expected: 'A dated, identifiable invoice approval or payment trigger',
      observed: 'No approval trigger was found in the submitted evidence',
      suggested_correction: 'Add or upload the agreed approval and payment terms.',
      automated: true,
      visibility: 'customer',
      status: 'customer_action_required',
      rule_reference: null,
      evidence_references: [],
      created_at: '2026-07-16T08:00:00Z',
      updated_at: '2026-07-16T08:00:00Z',
    });

    expect(result.expected).toContain('approval');
    expect(result.observed).toContain('No approval');
    expect(result.suggested_correction).toContain('upload');
  });
});
