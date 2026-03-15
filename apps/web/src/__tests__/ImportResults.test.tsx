import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import ImportResults from '@/pages/ImportResults';
import { buildValidationResults } from './fixtures/lcopilot';
import { renderWithProviders } from './testUtils';

const activeResults = buildValidationResults({
  structured_result: {
    ...buildValidationResults().structured_result,
    validation_contract_v1: {
      final_verdict: 'review',
    },
    effective_submission_eligibility: {
      can_submit: false,
      reasons: ['issues'],
    },
    bank_profile: {
      bank_code: 'ICBC',
      bank_name: 'Industrial and Commercial Bank of China',
      strictness: 'strict',
    },
    amendments_available: {
      count: 1,
      amendments: [
        {
          issue_id: 'issue-44e',
          field: {
            tag: '44E',
            name: 'Port of Loading',
            current: 'MUMBAI',
            proposed: 'CHITTAGONG',
          },
          narrative: 'Update the nominated port before presentation.',
          swift_mt707_text: ':44E:CHITTAGONG',
          bank_processing_days: 2,
          estimated_fee_usd: 75,
        },
      ],
      total_estimated_fee_usd: 75,
      total_processing_days: 2,
    },
  } as any,
});

const canonicalHookState = {
  jobStatus: { status: 'completed' },
  isPolling: false,
  results: activeResults as ReturnType<typeof buildValidationResults> | null,
  isLoading: false,
  resultsError: null as any,
  refreshResults: vi.fn().mockResolvedValue(activeResults),
};

vi.mock('@/hooks/use-lcopilot', () => ({
  useCanonicalJobResult: () => canonicalHookState,
  usePackage: () => ({
    generatePackage: vi.fn(),
    downloadPackage: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock('@/api/importer', () => ({
  importerApi: {
    requestBankPrecheck: vi.fn(),
    downloadSupplierFixPack: vi.fn(),
    sendToSupplier: vi.fn(),
  },
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
  },
}));

describe('ImportResults', () => {
  beforeEach(() => {
    canonicalHookState.jobStatus = { status: 'completed' };
    canonicalHookState.isPolling = false;
    canonicalHookState.results = activeResults;
    canonicalHookState.isLoading = false;
    canonicalHookState.resultsError = null;
    canonicalHookState.refreshResults = vi.fn().mockResolvedValue(activeResults);
  });

  it('uses the canonical shared result path for real importer jobs', async () => {
    render(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="supplier" />,
        '/lcopilot/import-results/job-123?mode=supplier',
      ),
    );

    expect(await screen.findByText(/Importer Review Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/Industrial and Commercial Bank of China/i)).toBeInTheDocument();
    expect(screen.getByText(/1 Amendment Available/i)).toBeInTheDocument();
    expect(screen.queryByText(/Supplier Document Compliance/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Request Bank Review/i })).not.toBeInTheDocument();
  });

  it('transitions from loading to canonical results without violating hook order', async () => {
    canonicalHookState.results = null;
    canonicalHookState.isLoading = true;
    canonicalHookState.isPolling = true;
    canonicalHookState.jobStatus = { status: 'processing' };

    const view = render(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="supplier" />,
        '/lcopilot/import-results/job-123?mode=supplier',
      ),
    );

    expect(await screen.findByText(/Checking Document Compliance/i)).toBeInTheDocument();

    canonicalHookState.results = activeResults;
    canonicalHookState.isLoading = false;
    canonicalHookState.isPolling = false;
    canonicalHookState.jobStatus = { status: 'completed' };

    view.rerender(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="supplier" />,
        '/lcopilot/import-results/job-123?mode=supplier',
      ),
    );

    expect(await screen.findByText(/Importer Review Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/Industrial and Commercial Bank of China/i)).toBeInTheDocument();
  });
});
