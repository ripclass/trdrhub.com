import { render, screen } from '@testing-library/react';
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
    expect(screen.getByText(/1 partial extraction/i)).toBeInTheDocument();
    expect(screen.getByText(/1 extraction failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Compliance Outcome \(Issue-Based\)/i)).toBeInTheDocument();
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
