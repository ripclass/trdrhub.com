import { mockValidationResults } from './fixtures/lcopilot';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';

describe('results mapper - option e payload', () => {
  it('maps documents, issues, and customs risk from structured_result', () => {
    const mapped = buildValidationResponse(mockValidationResults);
    expect(mapped.documents).toHaveLength(6);
    expect(mapped.structured_result.analytics?.customs_risk?.tier).toBe('med');
    expect(mapped.structured_result.customs_pack?.ready).toBe(true);
  });

  it('prefers backend canonical documents_structured.status when present', () => {
    const payload: any = {
      structured_result: {
        version: 'structured_result_v1',
        validation_contract_version: '2026-02-27.p0',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'LC.pdf',
            document_type: 'letter_of_credit',
            extraction_status: 'success',
            issues_count: 0,
            discrepancyCount: 0,
            status: 'error',
            extracted_fields: {},
          },
        ],
        issues: [],
        processing_summary: { total_documents: 1 },
        analytics: { compliance_score: 100 },
        lc_structured: null,
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0].status).toBe('error');
    expect(mapped.summary.canonical_document_status).toEqual({ success: 0, warning: 0, error: 1 });
    expect(mapped.analytics.document_status_distribution).toEqual({ success: 0, warning: 0, error: 1 });
  });

  it('derives extraction summary counters from canonical document statuses (ignores stale backend counts)', () => {
    const payload: any = {
      structured_result: {
        version: 'structured_result_v1',
        validation_contract_version: '2026-02-27.p0',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'LC.pdf',
            document_type: 'letter_of_credit',
            extraction_status: 'success',
            issues_count: 0,
            discrepancyCount: 0,
            extracted_fields: {},
          },
          {
            document_id: 'd2',
            filename: 'Invoice.pdf',
            document_type: 'commercial_invoice',
            extraction_status: 'error',
            issues_count: 0,
            discrepancyCount: 0,
            extracted_fields: {},
          },
        ],
        issues: [],
        processing_summary: {
          total_documents: 2,
          successful_extractions: 2,
          failed_extractions: 0,
        },
        analytics: { compliance_score: 50 },
        lc_structured: null,
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.summary.canonical_document_status).toEqual({ success: 1, warning: 0, error: 1 });
    expect(mapped.summary.successful_extractions).toBe(1);
    expect(mapped.summary.failed_extractions).toBe(1);
  });

  it('keeps extraction status independent from discrepancy count', () => {
    const payload: any = {
      structured_result: {
        version: 'structured_result_v1',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'Invoice.pdf',
            document_type: 'commercial_invoice',
            extraction_status: 'success',
            discrepancyCount: 4,
            extracted_fields: {},
          },
        ],
        issues: [
          { id: 'i1', title: 'Mismatch', severity: 'major' },
        ],
        processing_summary: { total_documents: 1, total_issues: 1 },
        analytics: { compliance_score: 20 },
        lc_structured: null,
      },
    };

    const mapped = buildValidationResponse(payload);
    expect(mapped.documents[0].status).toBe('success');
    expect(mapped.summary.canonical_document_status).toEqual({ success: 1, warning: 0, error: 0 });
    expect(mapped.summary.total_issues).toBe(1);
    expect(mapped.analytics.compliance_score).toBe(20);
  });
});

