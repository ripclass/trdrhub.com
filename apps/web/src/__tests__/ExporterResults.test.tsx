import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ExporterResults from '@/pages/ExporterResults';
import { renderWithProviders } from './testUtils';
import { mockValidationResults } from './fixtures/lcopilot';

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
      getResults: vi.fn().mockResolvedValue(mockValidationResults),
      results: mockValidationResults,
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
  it('renders overview metrics from processing summary', async () => {
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Export Document Statistics/i)).toBeInTheDocument();
    expect(screen.getByText(/6\)/i)).toBeInTheDocument(); // Documents tab label
    expect(screen.getByText(/Issues \(3\)/i)).toBeInTheDocument();
    expect(screen.getByText(/LC Compliance/i)).toBeInTheDocument();
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
    expect(screen.getByText(/Expected/i)).toBeInTheDocument();
    expect(screen.getByText(/50000 USD/)).toBeInTheDocument();
    expect(screen.getByText(/49000 USD/)).toBeInTheDocument();
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
  });
});
