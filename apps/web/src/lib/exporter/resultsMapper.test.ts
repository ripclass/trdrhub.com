import { describe, expect, it, vi } from 'vitest';
import { buildValidationResponse } from './resultsMapper';

vi.mock('@shared/types', () => ({
  mapExtractionToUiStatus: (status: string) =>
    status === 'success' ? 'success' : status === 'failed' ? 'error' : 'warning',
  CanonicalSemanticsSchema: {
    parse: () => ({}),
  },
}));

describe('resultsMapper', () => {
  it('uses backend document discrepancyCount as single source for document rows', () => {
    const response = buildValidationResponse({
      structured_result: {
        version: 'structured_result_v1',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'invoice.pdf',
            document_type: 'Commercial Invoice',
            extraction_status: 'success',
            discrepancyCount: 5,
            failed_reason: null,
            extracted_fields: {},
          },
          {
            document_id: 'd2',
            filename: 'packing.pdf',
            document_type: 'Packing List',
            extraction_status: 'success',
            discrepancyCount: 0,
            failed_reason: null,
            extracted_fields: {},
          },
        ],
        issues: [
          {
            id: 'i1',
            title: 'Issue tied to doc',
            severity: 'critical',
            documents: ['Invoice.pdf'],
            expected: 'abc',
            found: 'xyz',
          },
          {
            id: 'i2',
            title: 'Issue tied to doc',
            severity: 'major',
            documents: ['Invoice.pdf'],
            expected: '123',
            found: '456',
          },
        ],
        processing_summary: {
          total_documents: 2,
          successful_extractions: 2,
          partial_extractions: 0,
          failed_extractions: 0,
          total_issues: 9,
          severity_breakdown: {
            critical: 1,
            major: 1,
            medium: 0,
            minor: 0,
          },
        },
        analytics: {
          document_risk: [],
          compliance_score: 12,
        },
      },
    } as any);

    expect(response.documents[0].issuesCount).toBe(5);
    expect(response.summary.total_issues).toBe(9);
  });

  it('uses canonical processing_summary total_issues as issue count even when issue list is longer', () => {
    const response = buildValidationResponse({
      structured_result: {
        version: 'structured_result_v1',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'invoice.pdf',
            document_type: 'Commercial Invoice',
            extraction_status: 'success',
            discrepancyCount: 2,
            failed_reason: null,
            extracted_fields: {},
          },
          {
            document_id: 'd2',
            filename: 'packing.pdf',
            document_type: 'Packing List',
            extraction_status: 'success',
            discrepancyCount: 1,
            failed_reason: null,
            extracted_fields: {},
          },
        ],
        issues: [
          { id: 'i1', title: 'Issue', severity: 'critical', expected: 'a', found: 'b' },
          { id: 'i2', title: 'Issue', severity: 'major', expected: 'c', found: 'd' },
          { id: 'i3', title: 'Issue', severity: 'minor', expected: 'e', found: 'f' },
        ],
        processing_summary: {
          total_documents: 2,
          successful_extractions: 2,
          partial_extractions: 0,
          failed_extractions: 0,
          total_issues: 3,
          severity_breakdown: { critical: 1, major: 1, medium: 0, minor: 1 },
        },
        analytics: {
          document_risk: [],
          compliance_score: 40,
        },
      },
    } as any);

    expect(response.summary.total_issues).toBe(3);
    expect(response.summary.total_issues).toBe(
      response.documents.reduce((sum, doc) => sum + doc.issuesCount, 0),
    );
  });

  it('matches issue doc names flexibly using normalized filenames', () => {
    const response = buildValidationResponse({
      structured_result: {
        version: 'structured_result_v1',
        documents_structured: [
          {
            document_id: 'd1',
            filename: 'Invoice 01.pdf',
            document_type: 'Commercial Invoice',
            extraction_status: 'success',
            discrepancyCount: 0,
            failed_reason: null,
            extracted_fields: {},
          },
        ],
        issues: [
          {
            id: 'i1',
            title: 'Invoice issue',
            severity: 'major',
            documents: ['invoice-01'],
            expected: 'abc',
            found: 'xyz',
          },
        ],
        processing_summary: {
          total_documents: 1,
          successful_extractions: 1,
          partial_extractions: 0,
          failed_extractions: 0,
          total_issues: 1,
          severity_breakdown: { critical: 0, major: 1, medium: 0, minor: 0 },
        },
        analytics: { document_risk: [], compliance_score: 40 },
      },
    } as any);

    expect(response.issues[0].documentName).toBe('Invoice 01.pdf');
  });
});
