import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SummaryStrip from '@/components/lcopilot/SummaryStrip';
import { buildValidationResults } from './fixtures/lcopilot';

describe('SummaryStrip top block behavior', () => {
  it('renders VERIFIED badge in green state', () => {
    const data = buildValidationResults();
    (data.structured_result as any).pipeline_verification_status = 'VERIFIED';
    (data.structured_result as any).pipeline_verification_fail_reasons = [];
    (data.structured_result as any).pipeline_verification_checks = [{ name: 'sig', passed: true }];

    render(
      <MemoryRouter>
        <SummaryStrip data={data} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/^Trust Status$/i)).toBeInTheDocument();
    expect(screen.getByText(/^VERIFIED$/i)).toBeInTheDocument();
    expect(screen.queryByText(/not bank-ready/i)).not.toBeInTheDocument();
  });

  it('renders UNVERIFIED badge with short fail reasons and not bank-ready hint', () => {
    const data = buildValidationResults();
    (data.structured_result as any).pipeline_verification_status = 'UNVERIFIED';
    (data.structured_result as any).pipeline_verification_fail_reasons = [
      'OCR confidence below threshold',
      'Signature checksum missing',
      'Rulepack version mismatch',
      'Source hash mismatch',
    ];
    (data.structured_result as any).pipeline_verification_checks = [
      { name: 'ocr_confidence', passed: false },
      { name: 'signature', passed: false },
    ];

    render(
      <MemoryRouter>
        <SummaryStrip data={data} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/^UNVERIFIED$/i)).toBeInTheDocument();
    expect(screen.getByText(/not bank-ready/i)).toBeInTheDocument();
    expect(screen.getByText(/OCR confidence below threshold/i)).toBeInTheDocument();
    expect(screen.getByText(/Signature checksum missing/i)).toBeInTheDocument();
    expect(screen.getByText(/Rulepack version mismatch/i)).toBeInTheDocument();
  });

  it('renders invariant failure reason as part of UNVERIFIED signal', () => {
    const data = buildValidationResults();
    (data.structured_result as any).pipeline_verification_status = 'UNVERIFIED';
    (data.structured_result as any).invariant_failure_reason =
      'issue_count_invariant_failed: canonical_total_issues=3 != backend_processing_summary.total_issues=12';
    (data.structured_result as any).pipeline_verification_fail_reasons = [
      'issue_count_invariant_failed: canonical_total_issues=3 != backend_processing_summary.total_issues=12',
    ];
    (data.structured_result as any).pipeline_verification_checks = [
      { name: 'issue_count_invariant', passed: false },
    ];

    render(
      <MemoryRouter>
        <SummaryStrip data={data} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/^UNVERIFIED$/i)).toBeInTheDocument();
    expect(screen.getByText(/issue_count_invariant_failed/i)).toBeInTheDocument();
    expect(screen.getByText(/canonical_total_issues=3/i)).toBeInTheDocument();
  });

  it('renders NOT PROVIDED when trust status is missing', () => {
    const data = buildValidationResults();
    (data.structured_result as any).pipeline_verification_status = null;

    render(
      <MemoryRouter>
        <SummaryStrip data={data} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/^Trust Status$/i)).toBeInTheDocument();
    expect(screen.getByText(/^NOT PROVIDED$/i)).toBeInTheDocument();
  });

  it('uses critical/reject CTA mapping for next steps', () => {
    const data = buildValidationResults();

    render(
      <MemoryRouter>
        <SummaryStrip data={data} finalVerdict="REJECT" criticalIssueCount={1} />
      </MemoryRouter>,
    );

    expect(screen.getByRole('button', { name: /Resolve Critical Issues/i })).toBeInTheDocument();
  });

  it('keeps extraction counters independent from issue totals', () => {
    const data = buildValidationResults();
    data.issues = new Array(25).fill(0).map((_, idx) => ({
      id: `issue-${idx}`,
      title: `Issue ${idx}`,
      description: 'High issue volume',
      severity: idx % 2 === 0 ? 'critical' : 'major',
      documents: ['Invoice.pdf'],
      expected: 'A',
      actual: 'B',
      suggestion: 'Fix',
    } as any));
    data.summary = {
      ...(data.summary as any),
      total_issues: 25,
      canonical_document_status: { success: 4, warning: 1, error: 1 },
    } as any;
    const errorDoc = data.documents.find((doc: any) => doc.status === 'error') as any;
    if (errorDoc) {
      errorDoc.failedReason = 'OCR timeout';
      errorDoc.extractedFields = { ...(errorDoc.extractedFields ?? {}), _extraction_confidence: 0.2 };
    }

    if (data.structured_result) {
      (data.structured_result as any).issues = data.issues as any;
      (data.structured_result as any).processing_summary = {
        ...(data.structured_result as any).processing_summary,
        total_issues: 25,
        canonical_document_status: { success: 4, warning: 1, error: 1 },
      };
    }

    render(
      <MemoryRouter>
        <SummaryStrip data={data} actualIssuesCount={25} complianceScore={10} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/4 extracted OK/i)).toBeInTheDocument();
    expect(screen.getByText(/2 partial extraction/i)).toBeInTheDocument();
    expect(screen.queryByText(/extraction failed/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Compliance Outcome \(Issue-Based\)/i)).toBeInTheDocument();
  });

  it('renders affected documents with exact counts and supports drawer navigation trigger', async () => {
    const user = userEvent.setup();
    const data = buildValidationResults();
    data.documents = [
      { ...(data.documents[0] as any), id: 'd1', documentId: 'd1', name: 'LC.pdf', status: 'success' },
      { ...(data.documents[1] as any), id: 'd2', documentId: 'd2', name: 'Insurance.pdf', status: 'warning', failedReason: 'missing required fields', extractedFields: { _extraction_confidence: 0.65 } },
      { ...(data.documents[2] as any), id: 'd3', documentId: 'd3', name: 'Invoice.pdf', status: 'error', failedReason: 'ocr timed out', extractedFields: { _extraction_confidence: 0.2 } },
    ] as any;
    data.summary = {
      ...(data.summary as any),
      canonical_document_status: { success: 1, warning: 1, error: 1 },
    } as any;

    const onOpenDocumentDetails = vi.fn();

    render(
      <MemoryRouter>
        <SummaryStrip data={data} onOpenDocumentDetails={onOpenDocumentDetails} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Failed \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Partial \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/OCR timeout/i)).toBeInTheDocument();
    expect(screen.getByText(/Missing required fields/i)).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: /View details/i })[0]);
    expect(onOpenDocumentDetails).toHaveBeenCalled();
  });

  it('uses customs wording safety text', () => {
    const data = buildValidationResults();

    render(
      <MemoryRouter>
        <SummaryStrip data={data} packGenerated />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Customs Pack File Generated/i)).toBeInTheDocument();
    expect(screen.getByText(/File generation does not confirm bank\/customs submission readiness/i)).toBeInTheDocument();
  });
});
