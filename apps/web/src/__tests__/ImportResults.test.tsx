/**
 * Post Phase 2/7 rewrite. The legacy suite asserted against hand-crafted
 * header copy and dialog buttons that used to live inside the 2000-line
 * ImportResults. Those assertions aren't useful anymore — the rewrite is
 * a thin shared-tab-shell wrapper, so the interesting behaviors are
 * (a) we wire useCanonicalJobResult for real jobs and (b) the new
 * moment-aware header renders. Phase 3 adds real Phase-3-action tests.
 */
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import ImportResults from '@/pages/ImportResults';
import { buildValidationResults } from './fixtures/lcopilot';
import { renderWithProviders } from './testUtils';

const activeResults = buildValidationResults();

const canonicalHookState = {
  jobStatus: { status: 'completed' } as any,
  isPolling: false,
  results: activeResults as ReturnType<typeof buildValidationResults> | null,
  isLoading: false,
  resultsError: null as any,
  refreshResults: vi.fn().mockResolvedValue(activeResults),
};

vi.mock('@/hooks/use-lcopilot', () => ({
  useCanonicalJobResult: (jobId: string | null) => {
    // Preserve the test's ability to assert we only fetch for real jobs —
    // return a sentinel when jobId is null so test inspects the right
    // call path. Hook order stability is already covered by the shape.
    if (jobId === null) {
      return {
        jobStatus: null,
        isPolling: false,
        results: null,
        isLoading: false,
        resultsError: null,
        refreshResults: vi.fn(),
      };
    }
    return canonicalHookState;
  },
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } },
      })),
    },
  },
}));

describe('ImportResults (Phase 2/7 rewrite)', () => {
  beforeEach(() => {
    canonicalHookState.results = activeResults;
    canonicalHookState.jobStatus = { status: 'completed' };
    canonicalHookState.isPolling = false;
    canonicalHookState.isLoading = false;
  });

  it('uses the canonical shared result path for real importer jobs', () => {
    render(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="supplier" />,
        '/lcopilot/import-results/job-123?mode=supplier',
      ),
    );
    // The rewrite renders the moment-aware header when workflow_type
    // resolves to importer_supplier_docs (fallback from the mode prop).
    expect(
      screen.getByRole('heading', { name: /supplier document review/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /verdict/i })).toBeInTheDocument();
  });

  it('renders the Draft LC header when mode is draft', () => {
    render(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="draft" />,
        '/lcopilot/import-results/job-123?mode=draft',
      ),
    );
    expect(
      screen.getByRole('heading', { name: /draft lc risk analysis/i }),
    ).toBeInTheDocument();
  });

  it('does not leak legacy mock-data copy', () => {
    render(
      renderWithProviders(
        <ImportResults embedded jobId="job-123" mode="supplier" />,
        '/lcopilot/import-results/job-123?mode=supplier',
      ),
    );
    // The legacy surface hard-coded "Importer Review Summary" and bank
    // names sourced from mockSupplierResults. None of that should come
    // back after the rewrite.
    expect(screen.queryByText(/Importer Review Summary/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/LC-2024-MOCK/i)).not.toBeInTheDocument();
  });
});
