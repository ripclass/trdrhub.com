import { render, screen } from '@testing-library/react';
import SummaryStrip from '@/components/lcopilot/SummaryStrip';
import { buildValidationResults } from './fixtures/lcopilot';

describe('SummaryStrip', () => {
  it('keeps the primary issue metric documentary-first and calls out advisory alerts separately', () => {
    const results = buildValidationResults();
    results.summary = {
      ...results.summary,
      total_issues: 0,
    } as any;
    (results.summary as any).reportable_issue_count = 0;
    (results.summary as any).advisory_issue_count = 1;
    (results.summary as any).primary_decision_lane = 'advisory';

    render(
      <SummaryStrip
        data={results}
        overallStatus="success"
        actualIssuesCount={0}
        advisoryIssuesCount={1}
        complianceScore={82}
        readinessLabel="Ready"
        readinessSummary="Documentary checks are clear for presentation."
      />,
    );

    expect(screen.getByText('Documentary Issues')).toBeInTheDocument();
    expect(screen.getByText(/No blocking documentary issues\. 1 advisory alert remains visible separately\./i)).toBeInTheDocument();
  });
});
