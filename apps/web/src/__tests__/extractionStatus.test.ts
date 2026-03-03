import {
  confidenceBand,
  formatConfidence,
  isFailedDocumentGuardrailCompliant,
  normalizeExtractionReason,
} from '@/lib/exporter/extractionStatus';

describe('extractionStatus helpers', () => {
  it('maps reasons to normalized taxonomy', () => {
    expect(normalizeExtractionReason('OCR timed out after 30s')).toBe('OCR timeout');
    expect(normalizeExtractionReason('poor scan quality')).toBe('Low text quality');
    expect(normalizeExtractionReason('missing required fields in invoice')).toBe('Missing required fields');
    expect(normalizeExtractionReason('ambiguous mapping for consignee')).toBe('Ambiguous field mapping');
    expect(normalizeExtractionReason('random unexpected reason')).toBe('Low extraction confidence');
  });

  it('maps confidence scores to required bands', () => {
    expect(confidenceBand(0.8)).toBe('High');
    expect(confidenceBand(0.79)).toBe('Medium');
    expect(confidenceBand(0.6)).toBe('Medium');
    expect(confidenceBand(0.59)).toBe('Low');
    expect(formatConfidence(0.83)).toBe('0.83 (High)');
  });

  it('enforces failed-doc guardrails', () => {
    expect(
      isFailedDocumentGuardrailCompliant({
        id: 'd1',
        documentId: 'd1',
        name: 'Invoice.pdf',
        filename: 'Invoice.pdf',
        type: 'Commercial Invoice',
        typeKey: 'commercial_invoice',
        extractionStatus: 'failed',
        status: 'error',
        issuesCount: 0,
        extractedFields: {},
        failedReason: null,
      } as any),
    ).toBe(false);

    expect(
      isFailedDocumentGuardrailCompliant({
        id: 'd2',
        documentId: 'd2',
        name: 'Invoice.pdf',
        filename: 'Invoice.pdf',
        type: 'Commercial Invoice',
        typeKey: 'commercial_invoice',
        extractionStatus: 'failed',
        status: 'error',
        issuesCount: 0,
        extractedFields: { invoice_no: 'INV-1', _extraction_confidence: 0.9 },
        failedReason: 'OCR timeout',
      } as any),
    ).toBe(false);
  });
});
