import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ExporterResults from '@/pages/ExporterResults';
import { buildValidationResponse } from '@/lib/exporter/resultsMapper';
import { renderWithProviders } from './testUtils';
import { buildValidationResults, mockValidationResults } from './fixtures/lcopilot';

let activeResults = buildValidationResults();
const totalDocuments = mockValidationResults.documents.length;
const totalDiscrepancies = mockValidationResults.issues.length;
const successCount = mockValidationResults.documents.filter((doc) => doc.status === 'success').length;
const expectedSeverityCounts = mockValidationResults.issues.reduce(
  (acc, issue) => {
    const severity = (issue.severity ?? '').toLowerCase();
    if (['critical', 'fail', 'error', 'high'].includes(severity)) {
      acc.critical += 1;
    } else if (['warning', 'warn', 'major', 'medium'].includes(severity)) {
      acc.major += 1;
    } else {
      acc.minor += 1;
    }
    return acc;
  },
  { critical: 0, major: 0, minor: 0 },
);

const findCardByTitle = (title: RegExp | string): HTMLElement => {
  const heading = screen.getByText(title);
  let current: HTMLElement | null = heading as HTMLElement;
  while (current && !current.className.toString().includes('shadow-soft')) {
    current = current.parentElement as HTMLElement | null;
  }
  return current ?? (heading as HTMLElement);
};

vi.mock('@/hooks/use-lcopilot', () => {
  return {
    useJob: () => ({
      jobStatus: { status: 'completed' },
      isPolling: false,
      error: null,
      startPolling: vi.fn(),
      clearError: vi.fn(),
    }),
    useResults: () => ({
      getResults: vi.fn().mockResolvedValue(activeResults),
      results: activeResults,
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    }),
  };
});

vi.mock('@/api/exporter', () => ({
  exporterApi: {
    checkGuardrails: vi.fn().mockResolvedValue({
      can_submit: true,
      blocking_issues: [],
      warnings: [],
      required_docs_present: true,
      high_severity_discrepancies: 0,
      policy_checks_passed: true,
    }),
    listBankSubmissions: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    generateCustomsPack: vi.fn().mockResolvedValue({
      download_url: '',
      file_name: 'CustomsPack.zip',
      sha256: '',
      generated_at: new Date().toISOString(),
      manifest: {
        lc_number: 'LC123',
        validation_session_id: 'session',
        generated_at: new Date().toISOString(),
        documents: [],
        generator_version: 'test',
      },
    }),
    downloadCustomsPack: vi.fn().mockResolvedValue(new Blob()),
    createBankSubmission: vi.fn().mockResolvedValue({
      id: 'submission',
      company_id: 'company',
      user_id: 'user',
      validation_session_id: 'session',
      lc_number: 'LC123',
      status: 'pending',
      created_at: new Date().toISOString(),
    }),
    getSubmissionEvents: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

describe('ExporterResults', () => {
  beforeEach(() => {
    activeResults = buildValidationResults();
  });

  it('renders overview metrics from processing summary', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Letter of Credit Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/Customs Risk Assessment/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Processing Summary/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Documents \\(${totalDocuments}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(`Issues \\(${totalDiscrepancies}\\)`, 'i')),
    ).toBeInTheDocument();
    expect(screen.getByText(/LC Compliance/i)).toBeInTheDocument();

    const statsCard = findCardByTitle(/Export Document Statistics/i);
    const verifiedLabel = within(statsCard).getByText(/^Verified$/i);
    const verifiedValue = verifiedLabel.previousElementSibling;
    expect(verifiedValue?.textContent).toBe(String(successCount));

    const warningsLabel = within(statsCard).getByText(/^Warnings$/i);
    const warningsValue = warningsLabel.previousElementSibling;
    expect(warningsValue?.textContent).toBe(String(totalDiscrepancies));

    const complianceRow = screen.getByText(/LC Compliance:/i).parentElement as HTMLElement;
    const expectedCompliance = `${Math.round((successCount / totalDocuments) * 100)}%`;
    expect(within(complianceRow).getByText(expectedCompliance)).toBeInTheDocument();
  });

  it('renders documents tab with all trade documents', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Documents \(6\)/i }));
    for (const doc of mockValidationResults.documents) {
      expect(screen.getByText(doc.name)).toBeInTheDocument();
    }
  });

  it('renders issues tab with expected/found values', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));
    expect(screen.getByText(/Amount mismatch/i)).toBeInTheDocument();
    const primaryIssue = screen.getByTestId('issue-card-issue-1');
    expect(
      within(primaryIssue)
        .getAllByText(/^Expected$/i)[0],
    ).toBeInTheDocument();
    const expectedValueNodes = within(primaryIssue).getAllByText((_, node) =>
      (node?.textContent ?? '').includes('50000 USD'),
    );
    const actualValueNodes = within(primaryIssue).getAllByText((_, node) =>
      (node?.textContent ?? '').includes('49000 USD'),
    );
    expect(expectedValueNodes[0]).toBeInTheDocument();
    expect(actualValueNodes[0]).toBeInTheDocument();

    const criticalCard = screen.getAllByText(/^Critical$/i)[0]?.closest('div') as HTMLElement;
    const majorCard = screen.getAllByText(/^Major$/i)[0]?.closest('div') as HTMLElement;
    const minorCard = screen.getAllByText(/^Minor$/i)[0]?.closest('div') as HTMLElement;

    const getCountText = (element?: HTMLElement | null) =>
      element?.querySelector('.text-2xl')?.textContent ?? '';
    expect(getCountText(criticalCard)).toBe(expectedSeverityCounts.critical.toString());
    expect(getCountText(majorCard)).toBe(expectedSeverityCounts.major.toString());
    expect(getCountText(minorCard)).toBe(expectedSeverityCounts.minor.toString());

    const severityBadge = screen.getByTestId('severity-issue-1');
    expect(severityBadge.dataset.icon).toBe('critical');
    expect(severityBadge.className).toContain('bg-[#E24A4A]/10');
  });

  it('renders analytics tab with compliance score', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Analytics/i }));
    expect(screen.getByText(/Processing Performance/i)).toBeInTheDocument();
    expect(screen.getByText(`${mockValidationResults.analytics.compliance_score}%`)).toBeInTheDocument();
    expect(screen.getByText(/Document Status Distribution/i)).toBeInTheDocument();
  });

  it('renders UI when only structured_result payload is provided', async () => {
    const user = userEvent.setup();
    const structuredOnly = buildValidationResponse({
      structured_result: mockValidationResults.structured_result,
    });
    activeResults = structuredOnly;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(structuredOnly.documents[0]?.name ?? 'Letter of Credit'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Issues/i }));
    expect(screen.getByText(structuredOnly.issues[0]?.title ?? 'Review Required')).toBeInTheDocument();
  });

  it('shows success state when there are no issues', async () => {
    const withoutIssues = buildValidationResults();
    withoutIssues.issues = [];
    withoutIssues.structured_result!.issues = [];
    withoutIssues.summary = {
      ...withoutIssues.summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    withoutIssues.structured_result!.processing_summary = {
      ...withoutIssues.structured_result!.processing_summary,
      total_issues: 0,
      severity_breakdown: { critical: 0, major: 0, medium: 0, minor: 0 },
    };
    activeResults = withoutIssues;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Issues/i }));
    expect(screen.getByText(/All documents comply with LC terms/i)).toBeInTheDocument();
  });

  it('indicates analytics unavailability when structured_result analytics are missing', async () => {
    const withoutAnalytics = buildValidationResults();
    (withoutAnalytics.structured_result as any).analytics = undefined;
    activeResults = withoutAnalytics;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Analytics/i }));
    expect(screen.getByText(/Analytics unavailable/i)).toBeInTheDocument();
  });

  it('hides the timeline when no events are provided', async () => {
    const noTimeline = buildValidationResults();
    noTimeline.timeline = [];
    if (noTimeline.structured_result) {
      noTimeline.structured_result.timeline = [];
    }
    activeResults = noTimeline;

    render(renderWithProviders(<ExporterResults />));
    await waitFor(() => expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument());
    expect(screen.queryByText(/Export Processing Timeline/i)).not.toBeInTheDocument();
  });

  it('shows document parsing warning when extracted fields are empty', async () => {
    const docWithNoFields = buildValidationResults();
    docWithNoFields.documents[0].extractedFields = {};
    if (docWithNoFields.structured_result) {
      docWithNoFields.structured_result.documents[0].extracted_fields = {};
    }
    activeResults = docWithNoFields;

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await user.click(screen.getByRole('tab', { name: /Documents/i }));
    expect(
      screen.getByText(/This document could not be fully parsed/i),
    ).toBeInTheDocument();
  });
});
