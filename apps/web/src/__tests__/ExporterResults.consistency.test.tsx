import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ExporterResults from '@/pages/ExporterResults';
import { buildValidationResults } from './fixtures/lcopilot';
import { exporterApi } from '@/api/exporter';
import { renderWithProviders } from './testUtils';

let activeResults = buildValidationResults();

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

const getIssuesCardCount = (label: 'Critical' | 'Major' | 'Minor' | 'Total Issues') => {
  if (label === 'Total Issues') {
    return Number(
      screen
        .getByRole('tab', { name: /Overview/i })
        .closest('div')
        ?.querySelector('[data-testid="total-issues"]')
        ?.textContent?.trim() ??
        '0',
    );
  }

  const issueCards = screen.getAllByTestId(/issue-card-/);
  const normalized = label.toLowerCase();
  const card = issueCards.find((issueCard) => {
    const severityBadge = issueCard.querySelector(`[data-icon="${normalized}"]`);
    return severityBadge?.textContent?.trim().toLowerCase() === normalized;
  });

  if (!card) {
    return 0;
  }

  return Number(card.querySelector('.text-2xl')?.textContent ?? '0');
};

describe('ExporterResults consistency guards', () => {
  beforeEach(() => {
    activeResults = buildValidationResults();
    vi.mocked(exporterApi.checkGuardrails).mockResolvedValue({
      can_submit: true,
      blocking_issues: [],
      warnings: [],
      required_docs_present: true,
      high_severity_discrepancies: 0,
      policy_checks_passed: true,
    } as any);
  });

  it('enforces Total Issues = displayed severity bucket sum', async () => {
    const staleTotal = 9;
    activeResults.summary = {
      ...(activeResults.summary as any),
      total_issues: staleTotal,
    } as any;
    (activeResults.structured_result as any).processing_summary = {
      ...((activeResults.structured_result as any).processing_summary ?? {}),
      total_issues: staleTotal,
    };

    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Issues \(3\)/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /Issues \(3\)/i }));

    const critical = getIssuesCardCount('Critical');
    const major = getIssuesCardCount('Major');
    const minor = getIssuesCardCount('Minor');
    const total = getIssuesCardCount('Total Issues');
    expect(total).toBe(critical + major + minor);
  });

  it('uses Regenerate action when customs pack is already generated and keeps readiness messaging separate', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Customs Pack/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));

    const generateButton = screen.getByRole('button', { name: /Regenerate Customs Pack/i });
    expect(generateButton).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Generate Customs Pack$/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Customs Pack State/i)).toBeInTheDocument();
    expect(screen.getByText(/Validation decision:/i)).toBeInTheDocument();
    expect(screen.getByText(/Customs Clearance Readiness/i)).toBeInTheDocument();
  });
  it('uses one canonical gate decision label across Overview and Customs Pack', async () => {
    const user = userEvent.setup();
    (activeResults.structured_result as any).validation_blocked = true;
    (activeResults.structured_result as any).block_reason = 'Critical field missing';
    (activeResults.structured_result as any).gate_result = {
      level: 'blocked',
      block_reason: 'Critical field missing',
    };

    render(renderWithProviders(<ExporterResults />));

    await waitFor(() => {
      expect(screen.getByText(/Customs Decision:/i)).toBeInTheDocument();
    });

    const overviewDecisionRow = screen.getByText(/Customs Decision:/i).parentElement as HTMLElement;
    expect(within(overviewDecisionRow).getByText(/^Blocked$/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Customs Pack/i }));

    const customsDecisionRow = screen.getByText(/Validation decision:/i).parentElement as HTMLElement;
    expect(within(customsDecisionRow).getByText(/^Blocked$/i)).toBeInTheDocument();
  });

  it('honors tab=overview deep-link deterministically on initial load', async () => {
    render(
      renderWithProviders(
        <ExporterResults initialTab="documents" />,
        '/lcopilot/exporter-results?jobId=test&tab=overview',
      ),
    );

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Overview/i })).toHaveAttribute('data-state', 'active');
    });
    expect(screen.getByRole('tab', { name: /Documents/i })).toHaveAttribute('data-state', 'inactive');
  });

  it('falls back to overview when initial/deep-link tab is not a valid ResultsTab', async () => {
    render(
      renderWithProviders(
        <ExporterResults initialTab={'not-a-tab' as any} />,
        '/lcopilot/exporter-results?jobId=test&tab=does-not-exist',
      ),
    );

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Overview/i })).toHaveAttribute('data-state', 'active');
    });
    expect(screen.getByRole('tab', { name: /Issues/i })).toHaveAttribute('data-state', 'inactive');
    expect(screen.getByRole('tab', { name: /Customs Pack/i })).toHaveAttribute('data-state', 'inactive');
  });
});
