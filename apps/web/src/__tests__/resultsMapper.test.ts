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
});

