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

  it('derives reportable documentary counts from validation contract issue lanes', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        validation_contract_v1: {
          final_verdict: 'pass',
          rules_evidence: {
            issue_lanes: {
              documentary: { count: 0 },
              advisory: { count: 1 },
            },
            advisory_review_needed: true,
            primary_decision_lane: 'advisory',
          },
          evidence_summary: {
            primary_decision_lane: 'advisory',
            advisory_review_needed: true,
          },
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect((mapped.summary as any).reportable_issue_count).toBe(0);
    expect((mapped.summary as any).documentary_issue_count).toBe(0);
    expect((mapped.summary as any).advisory_issue_count).toBe(1);
    expect(mapped.summary.total_issues).toBe(0);
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

  it('uses resolution_queue_v1 as the invoice unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        resolution_queue_v1: {
          version: 'resolution_queue_v1',
          items: [
            {
              document_id: 'doc-invoice',
              document_type: 'commercial_invoice',
              filename: 'Invoice.pdf',
              field_name: 'invoice_date',
              label: 'Invoice Date',
              priority: 'high',
              candidate_value: '2026-04-20',
              normalized_value: '2026-04-20',
              evidence_snippet: 'Invoice Date: 20 Apr 2026',
              evidence_source: 'native_text',
              page: 1,
              reason: 'system_could_not_confirm',
              verification_state: 'model_suggested',
              resolvable_by_user: true,
              origin: 'document_ai',
            },
          ],
          summary: {
            total_items: 1,
            user_resolvable_items: 1,
            unresolved_documents: 1,
            document_counts: { commercial_invoice: 1 },
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-invoice',
              document_type: 'commercial_invoice',
              filename: 'Invoice.pdf',
              extraction_status: 'success',
              extracted_fields: {
                invoice_number: 'INV-022',
              },
              field_details: {
                seller: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['seller'],
              parse_complete: true,
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields.map((field) => field.fieldName)).toEqual([
      'invoice_date',
    ]);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('2026-04-20');
  });

  it('classifies requirements-driven exact-wording issues as LC required statements', () => {
    const payload = JSON.parse(JSON.stringify(optionEFixture));
    payload.structured_result.issues = [
      {
        id: 'wording-1',
        title: 'LC-required wording missing from Beneficiary Certificate',
        severity: 'critical',
        documents: ['Beneficiary_Certificate.pdf'],
        expected: "Beneficiary Certificate contains exact wording 'WE HEREBY CERTIFY GOODS ARE BRAND NEW'",
        found: 'Beneficiary Certificate does not contain the required wording.',
        suggested_fix: 'Review and correct the discrepancy.',
        description: 'LC requires exact wording on Beneficiary Certificate.',
        rule: 'CROSSDOC-EXACT-WORDING',
        ruleset_domain: 'icc.lcopilot.crossdoc',
        requirement_source: 'requirements_graph_v1',
        requirement_kind: 'document_exact_wording',
        requirement_text: 'WE HEREBY CERTIFY GOODS ARE BRAND NEW',
      },
    ];

    const mapped = buildValidationResponse(payload);
    expect(mapped.issues[0]?.bucket).toBe('LC Required Statements');
    expect(mapped.issues[0]?.fix_owner).toBe('Beneficiary');
    expect(mapped.issues[0]?.workflow_lane).toBe('documentary_review');
    expect(mapped.issues[0]?.lc_basis).toContain('WE HEREBY CERTIFY GOODS ARE BRAND NEW');
    expect(mapped.issues[0]?.next_action).toBe(
      'Update the document to include the exact LC-required statement or seek an LC amendment before presentation.',
    );
    expect(mapped.issues[0]?.requirement_kind).toBe('document_exact_wording');
  });

  it('prefers fact_resolution_v1 over stale invoice queue and legacy extraction fields', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'validation_results',
          provisional_validation: false,
          ready_for_final_validation: true,
          unresolved_documents: 0,
          unresolved_fields: 0,
          summary: 'Extraction is sufficiently resolved. Validation findings reflect the current confirmed document set.',
        },
        resolution_queue_v1: {
          version: 'resolution_queue_v1',
          items: [
            {
              document_id: 'doc-invoice',
              document_type: 'commercial_invoice',
              filename: 'Invoice.pdf',
              field_name: 'invoice_date',
              label: 'Invoice Date',
              priority: 'high',
              candidate_value: '2026-04-20',
              normalized_value: '2026-04-20',
              reason: 'system_could_not_confirm',
              verification_state: 'candidate',
              resolvable_by_user: true,
            },
          ],
          summary: {
            total_items: 1,
            user_resolvable_items: 1,
            unresolved_documents: 1,
            document_counts: { commercial_invoice: 1 },
          },
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'validation_results',
            provisional_validation: false,
            ready_for_final_validation: true,
            unresolved_documents: 0,
            unresolved_fields: 0,
            summary: 'resolved',
          },
          documents: [
            {
              document_id: 'doc-invoice',
              document_type: 'commercial_invoice',
              filename: 'Invoice.pdf',
              resolution_required: false,
              ready_for_validation: true,
              unresolved_count: 0,
              summary: 'Invoice facts required for validation are resolved.',
              resolution_items: [],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 0,
            total_items: 0,
            user_resolvable_items: 0,
            ready_for_validation: true,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-invoice',
              document_type: 'commercial_invoice',
              filename: 'Invoice.pdf',
              extraction_status: 'success',
              field_details: {
                seller: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['seller'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.factResolution?.summary.ready_for_validation).toBe(true);
    expect(mapped.documents[0]?.resolutionItems ?? []).toHaveLength(0);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(false);
    expect(mapped.documents[0]?.missingRequiredFields ?? []).toEqual([]);
    expect(mapped.documents[0]?.reviewReasons ?? []).toEqual([]);
    expect(mapped.documents[0]?.reviewRequired).toBe(false);
    expect(mapped.documents[0]?.parseComplete).toBeUndefined();
    expect(mapped.documents[0]?.requiredFieldsFound).toBeUndefined();
    expect(mapped.documents[0]?.requiredFieldsTotal).toBeUndefined();
    expect(mapped.documents[0]?.status).toBe('success');
  });

  it('uses fact_resolution_v1 as the B/L unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-bl',
              document_type: 'bill_of_lading',
              filename: 'Bill_of_Lading.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: '1 field still needs confirmation before document validation input is treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-bl',
                  document_type: 'bill_of_lading',
                  filename: 'Bill_of_Lading.pdf',
                  field_name: 'on_board_date',
                  label: 'On Board Date',
                  priority: 'high',
                  candidate_value: '2026-04-21',
                  normalized_value: '2026-04-21',
                  evidence_snippet: 'Shipped on board 21 Apr 2026',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-bl',
              document_type: 'bill_of_lading',
              filename: 'Bill_of_Lading.pdf',
              extraction_status: 'success',
              field_details: {
                shipper: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['shipper'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.fieldName).toBe('on_board_date');
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('2026-04-21');
  });

  it('uses fact_resolution_v1 as the rendered-LC unresolved source of truth without surfacing clause debt', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 LC still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 LC still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-lc',
              document_type: 'letter_of_credit',
              filename: 'LC.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: '1 field still needs confirmation before document validation input is treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-lc',
                  document_type: 'letter_of_credit',
                  filename: 'LC.pdf',
                  field_name: 'lc_number',
                  label: 'LC Number',
                  priority: 'high',
                  candidate_value: 'EXP2026BD001',
                  normalized_value: 'EXP2026BD001',
                  evidence_snippet: '20: EXP2026BD001',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-lc',
              document_type: 'letter_of_credit',
              filename: 'LC.pdf',
              extraction_status: 'partial',
              extraction_lane: 'document_ai',
              extracted_fields: {
                lc_number: 'EXP2026BD001',
                additional_conditions: ['Documents must not be dated earlier than LC issue date.'],
              },
              field_details: {
                lc_number: {
                  verification: 'model_suggested',
                },
                additional_conditions: {
                  verification: 'not_found',
                },
              },
              extraction_resolution: {
                required: true,
                unresolved_count: 2,
                summary: 'Legacy LC extraction state should not drive rendered-LC resolution.',
                fields: [
                  {
                    field_name: 'lc_number',
                    label: 'LC Number',
                    verification: 'model_suggested',
                  },
                  {
                    field_name: 'additional_conditions',
                    label: 'Additional Conditions (47A)',
                    verification: 'not_found',
                  },
                ],
              },
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields.map((field) => field.fieldName)).toEqual([
      'lc_number',
    ]);
  });

  it('uses fact_resolution_v1 as the packing-list unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-packing',
              document_type: 'packing_list',
              filename: 'Packing_List.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: '1 field still needs confirmation before document validation input is treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-packing',
                  document_type: 'packing_list',
                  filename: 'Packing_List.pdf',
                  field_name: 'document_date',
                  label: 'Document Date',
                  priority: 'high',
                  candidate_value: '2026-04-20',
                  normalized_value: '2026-04-20',
                  evidence_snippet: 'Packing List Date: 20 Apr 2026',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-packing',
              document_type: 'packing_list',
              filename: 'Packing_List.pdf',
              extraction_status: 'success',
              field_details: {
                gross_weight: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['gross_weight'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.fieldName).toBe('document_date');
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('2026-04-20');
  });

  it('uses fact_resolution_v1 as the COO unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-coo',
              document_type: 'certificate_of_origin',
              filename: 'Certificate_of_Origin.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: '1 field still needs confirmation before document validation input is treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-coo',
                  document_type: 'certificate_of_origin',
                  filename: 'Certificate_of_Origin.pdf',
                  field_name: 'country_of_origin',
                  label: 'Country Of Origin',
                  priority: 'high',
                  candidate_value: 'Bangladesh',
                  normalized_value: 'Bangladesh',
                  evidence_snippet: 'Country of Origin: Bangladesh',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-coo',
              document_type: 'certificate_of_origin',
              filename: 'Certificate_of_Origin.pdf',
              extraction_status: 'success',
              field_details: {
                exporter_name: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['exporter_name'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.fieldName).toBe('country_of_origin');
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('Bangladesh');
  });

  it('uses fact_resolution_v1 as the insurance unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-insurance',
              document_type: 'insurance_certificate',
              filename: 'Insurance_Certificate.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: 'Insurance facts still need confirmation before validation should be treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-insurance',
                  document_type: 'insurance_certificate',
                  filename: 'Insurance_Certificate.pdf',
                  field_name: 'policy_number',
                  label: 'Policy Number',
                  priority: 'high',
                  candidate_value: 'POL-2026-001',
                  normalized_value: 'POL-2026-001',
                  evidence_snippet: 'Policy No: POL-2026-001',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-insurance',
              document_type: 'insurance_certificate',
              filename: 'Insurance_Certificate.pdf',
              extraction_status: 'partial',
              field_details: {
                policy_number: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['policy_number'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields.map((field) => field.fieldName)).toEqual([
      'policy_number',
    ]);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('POL-2026-001');
  });

  it('uses fact_resolution_v1 as the inspection unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 1,
            unresolved_fields: 1,
            summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-inspection',
              document_type: 'inspection_certificate',
              filename: 'Inspection_Certificate.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: 'Inspection facts still need confirmation before validation should be treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-inspection',
                  document_type: 'inspection_certificate',
                  filename: 'Inspection_Certificate.pdf',
                  field_name: 'inspection_result',
                  label: 'Inspection Result',
                  priority: 'high',
                  candidate_value: 'PASSED',
                  normalized_value: 'PASSED',
                  evidence_snippet: 'Inspection Result: PASSED',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 1,
            unresolved_documents: 1,
            total_items: 1,
            user_resolvable_items: 1,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-inspection',
              document_type: 'inspection_certificate',
              filename: 'Inspection_Certificate.pdf',
              extraction_status: 'partial',
              field_details: {
                inspection_result: {
                  verification: 'not_found',
                },
              },
              missing_required_fields: ['inspection_result'],
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.resolutionItems).toHaveLength(1);
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(true);
    expect(mapped.documents[0]?.extractionResolution?.fields.map((field) => field.fieldName)).toEqual([
      'inspection_result',
    ]);
    expect(mapped.documents[0]?.extractionResolution?.fields[0]?.candidateValue).toBe('PASSED');
  });

  it('uses fact_resolution_v1 as the payment and courier unresolved source of truth', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 2,
          unresolved_fields: 2,
          summary: '2 documents still need 2 fields confirmed before validation should be treated as final.',
        },
        fact_resolution_v1: {
          version: 'fact_resolution_v1',
          workflow_stage: {
            stage: 'extraction_resolution',
            provisional_validation: true,
            ready_for_final_validation: false,
            unresolved_documents: 2,
            unresolved_fields: 2,
            summary: '2 documents still need 2 fields confirmed before validation should be treated as final.',
          },
          documents: [
            {
              document_id: 'doc-receipt',
              document_type: 'payment_receipt',
              filename: 'Payment_Receipt.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: 'Payment receipt facts still need confirmation before validation should be treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-receipt',
                  document_type: 'payment_receipt',
                  filename: 'Payment_Receipt.pdf',
                  field_name: 'receipt_number',
                  label: 'Receipt Number',
                  priority: 'high',
                  candidate_value: 'RCPT-26-009',
                  normalized_value: 'RCPT-26-009',
                  evidence_snippet: 'Receipt No: RCPT-26-009',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
            {
              document_id: 'doc-courier',
              document_type: 'courier_or_post_receipt_or_certificate_of_posting',
              filename: 'Courier_Receipt.pdf',
              resolution_required: true,
              ready_for_validation: false,
              unresolved_count: 1,
              summary: 'Courier receipt facts still need confirmation before validation should be treated as final.',
              resolution_items: [
                {
                  document_id: 'doc-courier',
                  document_type: 'courier_or_post_receipt_or_certificate_of_posting',
                  filename: 'Courier_Receipt.pdf',
                  field_name: 'consignment_reference',
                  label: 'Consignment Reference',
                  priority: 'high',
                  candidate_value: 'CR-2026-22',
                  normalized_value: 'CR-2026-22',
                  evidence_snippet: 'Courier Receipt No: CR-2026-22',
                  evidence_source: 'native_text',
                  page: 1,
                  reason: 'system_could_not_confirm',
                  verification_state: 'candidate',
                  resolvable_by_user: true,
                  origin: 'document_ai',
                },
              ],
            },
          ],
          summary: {
            total_documents: 2,
            unresolved_documents: 2,
            total_items: 2,
            user_resolvable_items: 2,
            ready_for_validation: false,
          },
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-receipt',
              document_type: 'payment_receipt',
              filename: 'Payment_Receipt.pdf',
              extraction_status: 'partial',
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
            {
              document_id: 'doc-courier',
              document_type: 'courier_or_post_receipt_or_certificate_of_posting',
              filename: 'Courier_Receipt.pdf',
              extraction_status: 'partial',
              review_required: true,
              review_reasons: ['FIELD_NOT_FOUND'],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);

    expect(mapped.documents[0]?.typeKey).toBe('payment_receipt');
    expect(mapped.documents[0]?.resolutionItems?.[0]?.fieldName).toBe('receipt_number');
    expect(mapped.documents[1]?.typeKey).toBe('courier_or_post_receipt_or_certificate_of_posting');
    expect(mapped.documents[1]?.extractionResolution?.fields[0]?.fieldName).toBe('consignment_reference');
  });

  it('preserves extraction lanes from canonical document payloads', () => {
    const seeded = buildValidationResults();
    const documents = [
      {
        document_id: 'doc-iso-lc',
        document_type: 'letter_of_credit',
        filename: 'LC.xml',
        extraction_status: 'success',
        extraction_lane: 'structured_iso',
        extracted_fields: {
          lc_number: 'LC-ISO-022',
        },
        field_details: {},
        review_reasons: [],
      },
      {
        document_id: 'doc-invoice',
        document_type: 'commercial_invoice',
        filename: 'Invoice.pdf',
        extraction_status: 'partial',
        extractionLane: 'document_ai',
        extracted_fields: {
          invoice_number: 'INV-022',
        },
        field_details: {},
        review_reasons: [],
      },
    ];
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        document_extraction_v1: {
          documents,
        },
        documents_structured: documents,
        workflow_stage: {
          stage: 'extraction_resolution',
          provisional_validation: true,
          ready_for_final_validation: false,
          unresolved_documents: 1,
          unresolved_fields: 1,
          summary: '1 document still needs 1 field confirmed before validation should be treated as final.',
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0]?.extractionLane).toBe('structured_iso');
    expect(mapped.documents[1]?.extractionLane).toBe('document_ai');
    expect(mapped.workflowStage?.stage).toBe('extraction_resolution');
    expect(mapped.workflowStage?.provisional_validation).toBe(true);
  });

  it('mirrors top-level contract surfaces from structured_result', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      job_id: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        validation_contract_v1: {
          final_verdict: 'review',
          ruleset_verdict: 'review',
        },
        submission_eligibility: {
          can_submit: false,
          reasons: ['validation_contract_review'],
        },
        raw_submission_eligibility: {
          can_submit: true,
          reasons: [],
        },
        effective_submission_eligibility: {
          can_submit: false,
          reasons: ['validation_contract_review'],
        },
        bank_verdict: {
          verdict: 'CAUTION',
          can_submit: false,
        },
      },
    };

    const mapped = buildValidationResponse(payload);

    expect(mapped.validation_contract_v1?.final_verdict).toBe('review');
    expect(mapped.final_verdict).toBe('review');
    expect(mapped.ruleset_verdict).toBe('review');
    expect(mapped.submission_can_submit).toBe(false);
    expect(mapped.submission_reasons).toEqual(['validation_contract_review']);
    expect(mapped.bank_verdict?.verdict).toBe('CAUTION');
    expect(mapped.effective_submission_eligibility?.can_submit).toBe(false);
    expect(mapped.raw_submission_eligibility?.can_submit).toBe(true);
  });

  it('clears derived extraction-resolution debt when backend workflow stage is validation_results', () => {
    const seeded = buildValidationResults();
    const payload = {
      jobId: seeded.jobId,
      structured_result: {
        ...seeded.structured_result,
        workflow_stage: {
          stage: 'validation_results',
          provisional_validation: false,
          ready_for_final_validation: true,
          unresolved_documents: 0,
          unresolved_fields: 0,
          summary: 'Extraction is sufficiently resolved. Validation findings reflect the current confirmed document set.',
        },
        document_extraction_v1: {
          documents: [
            {
              document_id: 'doc-bl',
              document_type: 'bill_of_lading',
              filename: 'Bill_of_Lading.pdf',
              extraction_status: 'success',
              extracted_fields: {
                issue_date: '2026-03-24',
              },
              field_details: {
                issue_date: {
                  verification: 'operator_confirmed',
                },
                gross_weight: {
                  verification: 'model_suggested',
                },
              },
              review_required: false,
              review_reasons: [],
            },
          ],
        },
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.workflowStage?.stage).toBe('validation_results');
    expect(mapped.documents[0]?.extractionResolution?.required).toBe(false);
    expect(mapped.documents[0]?.extractionResolution?.unresolvedCount).toBe(0);
  });
});

