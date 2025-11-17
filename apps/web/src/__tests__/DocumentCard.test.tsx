import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ExporterResults from '@/pages/ExporterResults';
import { mockValidationResults } from './fixtures/lcopilot';
import { renderWithProviders } from './testUtils';

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

describe('Document cards', () => {
  it('renders per-document metadata and issue counts', async () => {
    const user = userEvent.setup();
    render(renderWithProviders(<ExporterResults />));
    await waitFor(() =>
      expect(screen.getByText(/Export Processing Timeline/i)).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('tab', { name: /Documents \(6\)/i }));

    const invoiceCard = screen.getByText('Invoice.pdf');
    expect(invoiceCard).toBeInTheDocument();
    expect(screen.getByText(/Commercial Invoice/i)).toBeInTheDocument();
    expect(screen.getByText(/Minor Issues/i)).toBeInTheDocument();
  });
});
