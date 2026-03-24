import optionEFixture from './__fixtures__/results.optione.json';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';
import { buildValidationResults } from './fixtures/lcopilot';

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

  it('rewrites soft compliance caution text into explicit review workflow action', () => {
    const payload = JSON.parse(JSON.stringify(optionEFixture));
    payload.structured_result.issues = [
      {
        id: 'compliance-2',
        title: 'Potential sanctions match: vessel',
        severity: 'major',
        documents: ['BillOfLading.pdf'],
        expected: 'No sanctions matches for vessel',
        found: 'Potential match: Unknown (75% confidence)',
        suggested_fix: 'PROCEED WITH CAUTION - Flag state has elevated risk. Monitor closely.',
        description: 'The vessel requires sanctions screening review before any presentation decision.',
        rule: 'SANCTIONS-VESSEL-1',
        ruleset_domain: 'compliance.screening',
      },
    ];

    const mapped = buildValidationResponse(payload);
    expect(mapped.issues[0]?.workflow_lane).toBe('compliance_review');
    expect(mapped.issues[0]?.severity_display).toBe('Compliance escalation');
    expect(mapped.issues[0]?.next_action).toBe(
      'Route to internal compliance review, document the screening disposition, and hold bank presentation until compliance clearance is recorded.',
    );
  });

  it('does not inflate LC workflow-unknown warnings into major discrepancies', () => {
    const payload = JSON.parse(JSON.stringify(optionEFixture));
    payload.structured_result.issues = [
      {
        id: 'lc-type-unknown-1',
        rule: 'LC-TYPE-UNKNOWN',
        title: 'LC Type Not Determined',
        severity: 'warning',
        description: 'Workflow orientation could not be determined from uploaded LC.',
        expected: 'Identify workflow orientation',
        found: 'workflow_orientation=unknown',
        suggested_fix: 'Review and set workflow manually.',
        ruleset_domain: 'system.lc_type',
      },
    ];

    const mapped = buildValidationResponse(payload);
    expect(mapped.issues[0]?.severity).toBe('minor');
    expect(mapped.issues[0]?.severity_display).toBe('Review required');
  });

  it('preserves bank context and amendment intelligence on the canonical structured result path', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        bank_profile: {
          bank_code: 'ICBC',
          bank_name: 'Industrial and Commercial Bank of China',
          strictness: 'strict',
        },
        amendments_available: {
          count: 1,
          amendments: [
            {
              issue_id: 'issue-44e',
              field: {
                tag: '44E',
                name: 'Port of Loading',
                current: 'MUMBAI',
                proposed: 'CHITTAGONG',
              },
              narrative: 'Update the nominated port before presentation.',
              swift_mt707_text: ':44E:CHITTAGONG',
              bank_processing_days: 2,
              estimated_fee_usd: 75,
            },
          ],
          total_estimated_fee_usd: 75,
          total_processing_days: 2,
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.structured_result.bank_profile?.strictness).toBe('strict');
    expect(mapped.structured_result.amendments_available?.count).toBe(1);
    expect(mapped.structured_result.amendments_available?.amendments[0]?.field.tag).toBe('44E');
  });

  it('preserves canonical lc_classification for workflow, instrument, and required document continuity', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        lc_type: 'import',
        lc_structured: {
          ...(seeded.structured_result?.lc_structured ?? {}),
          lc_type: 'import',
          lc_classification: {
            workflow_orientation: 'export',
            instrument_type: 'standby_letter_of_credit',
            format_family: 'swift_mt_fin',
            format_variant: 'mt760',
            required_documents: [
              { code: 'commercial_invoice', display_name: 'Commercial Invoice' },
              { code: 'beneficiary_certificate', display_name: 'Beneficiary Statement' },
              { code: 'analysis_certificate', display_name: 'Analysis Certificate' },
              {
                code: 'courier_or_post_receipt_or_certificate_of_posting',
                display_name: 'Courier Receipt',
              },
            ],
          },
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.structured_result.lc_structured?.lc_classification?.workflow_orientation).toBe('export');
    expect(mapped.structured_result.lc_structured?.lc_classification?.instrument_type).toBe('standby_letter_of_credit');
    expect(mapped.structured_result.lc_structured?.lc_classification?.required_documents).toHaveLength(4);
    const requiredCodes =
      mapped.structured_result.lc_structured?.lc_classification?.required_documents?.map((doc) => doc.code) ?? [];
    expect(requiredCodes).toContain('analysis_certificate');
    expect(requiredCodes).toContain('courier_or_post_receipt_or_certificate_of_posting');
  });

  it('surfaces a contract warning for false-pass contradictions instead of masking them', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        validation_contract_v1: {
          final_verdict: 'pass',
        },
        effective_submission_eligibility: {
          can_submit: false,
          reasons: ['bank_verdict_reject'],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(
      mapped.contractWarnings?.some(
        (warning) =>
          warning.field === 'validation_contract_v1.final_verdict' &&
          warning.severity === 'error',
      ),
    ).toBe(true);
  });

  it('prefers current document field state over stale backend extraction-resolution summaries', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        issues: [],
        documents: [
          {
            document_id: 'doc-invoice',
            document_type: 'commercial_invoice',
            filename: 'Invoice.pdf',
            extraction_status: 'success',
            extracted_fields: {
              issue_date: '2026-04-20',
            },
            field_details: {
              issue_date: {
                verification: 'operator_confirmed',
              },
            },
            missing_required_fields: [],
            parse_complete: true,
            review_required: false,
            review_reasons: [],
            extraction_resolution: {
              required: true,
              unresolved_count: 1,
              summary: 'Stale summary should be ignored.',
              fields: [
                {
                  field_name: 'issue_date',
                  label: 'Issue Date',
                  verification: 'not_found',
                },
              ],
            },
          },
        ],
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(false);
  });
});

