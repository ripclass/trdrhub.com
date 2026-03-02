import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SummaryStrip from '@/components/lcopilot/SummaryStrip';
import { buildValidationResults } from './fixtures/lcopilot';

describe('SummaryStrip pipeline verification status', () => {
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
});
