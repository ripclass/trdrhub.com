import optionEFixture from './__fixtures__/results.optione.json';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';

describe('results mapper - option e payload', () => {
  it('maps documents, issues, and customs risk from structured_result', () => {
    const mapped = buildValidationResponse(optionEFixture);
    expect(mapped.documents).toHaveLength(6);
    expect(mapped.structured_result.analytics?.customs_risk?.tier).toBe('med');
    expect(mapped.structured_result.customs_pack?.ready).toBe(true);
  });

  it('uses document_status as the canonical source for extraction counters', () => {
    const payload = JSON.parse(JSON.stringify(optionEFixture));
    payload.structured_result.processing_summary_v2 = {
      ...payload.structured_result.processing_summary_v2,
      verified: 99,
      warnings: 99,
      errors: 99,
      successful_extractions: 99,
      failed_extractions: 99,
      document_status: { success: 4, warning: 1, error: 1 },
      status_counts: { success: 4, warning: 1, error: 1 },
      total_documents: 6,
      documents: 6,
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.summary.verified).toBe(4);
    expect(mapped.summary.warnings).toBe(1);
    expect(mapped.summary.errors).toBe(1);
    expect(mapped.summary.successful_extractions).toBe(4);
    expect(mapped.summary.failed_extractions).toBe(1);
  });

  it('normalizes compliance findings into internal review actions', () => {
    const payload = JSON.parse(JSON.stringify(optionEFixture));
    payload.structured_result.issues = [
      {
        id: 'compliance-1',
        title: 'Potential sanctions match',
        severity: 'critical',
        documents: ['BillOfLading.pdf'],
        expected: 'No sanctioned vessel or party involvement',
        found: 'Potential OFAC vessel watchlist match',
        suggested_fix: 'Resolve discrepancy before presentation.',
        description: 'Sanctions screening requires escalation before any submission decision.',
        rule: 'SANCTIONS-1',
        ruleset_domain: 'icc.lcopilot.crossdoc',
      },
    ];

    const mapped = buildValidationResponse(payload);
    expect(mapped.issues[0]?.workflow_lane).toBe('compliance_review');
    expect(mapped.issues[0]?.fix_owner).toBe('Internal Compliance Review');
    expect(mapped.issues[0]?.severity_display).toBe('Compliance hold');
    expect(mapped.issues[0]?.next_action).toContain('internal compliance review');
  });
});

