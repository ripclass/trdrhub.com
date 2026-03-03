import { render, screen } from '@testing-library/react';
import { ExporterIssueCard } from '@/components/exporter/ExporterIssueCard';

describe('ExporterIssueCard citation rendering', () => {
  it('renders ISBP citation with consistent ASCII para fallback', () => {
    render(
      <ExporterIssueCard
        fallbackId="citation-1"
        normalizedSeverity="major"
        documentStatusMap={new Map()}
        issue={{
          id: 'issue-cite',
          title: 'Reference formatting check',
          severity: 'major',
          description: 'Ensure citation renders safely',
          ucpReference: 'UCP600 Article 14',
          isbpReference: 'ISBP745 ¶A14',
          documents: [],
          expected: '—',
          actual: '—',
          suggestion: '—',
        }}
      />,
    );

    expect(screen.getAllByText('ISBP745 para A14').length).toBeGreaterThan(0);
    expect(screen.queryByText(/¶/)).not.toBeInTheDocument();
  });
});
