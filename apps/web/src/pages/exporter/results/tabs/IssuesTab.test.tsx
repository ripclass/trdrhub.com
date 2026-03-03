import { vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IssuesTab } from './IssuesTab';
import type { IssueCard } from '@/types/lcopilot';

describe('IssuesTab', () => {
  it('uses totalIssueCount from canonical source for tab and summary chips', () => {
    const cards: IssueCard[] = [
      {
        id: 'issue-1',
        rule: 'r1',
        title: 'Issue 1',
        description: 'desc',
        severity: 'critical',
        source: 'lc',
        field: 'f1',
        value: 'v1',
      },
      {
        id: 'issue-2',
        rule: 'r2',
        title: 'Issue 2',
        description: 'desc',
        severity: 'major',
        source: 'lc',
        field: 'f2',
        value: 'v2',
      },
    ];

    render(
      <IssuesTab
        hasIssueCards
        issueCards={cards}
        filteredIssueCards={cards}
        totalIssueCount={9}
        issueFilter="all"
        setIssueFilter={vi.fn()}
        severityCounts={{ critical: 1, major: 1, minor: 0 }}
        documentStatusMap={new Map()}
        renderAIInsightsCard={() => null}
        renderReferenceIssuesCard={() => null}
      />,
    );

    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('All (9)')).toBeInTheDocument();
    expect(screen.queryByText('All (2)')).not.toBeInTheDocument();
  });
});
