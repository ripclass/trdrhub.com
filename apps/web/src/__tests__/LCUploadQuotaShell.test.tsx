import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import ExportLCUpload from '@/pages/ExportLCUpload';
import ImportLCUpload from '@/pages/ImportLCUpload';
import { renderWithProviders } from './testUtils';

const exhaustedQuotaState = {
  status: 'ready' as const,
  plan: 'FREE' as const,
  quota: {
    used: 5,
    limit: 5,
    remaining: 0,
  },
  isExhausted: true,
  canValidate: false,
  headline: 'Starter allowance exhausted',
  detail: 'You have used all 5 starter checks in the current cycle. Upgrade to continue validating LC documents.',
  ctaLabel: 'Upgrade to continue',
  ctaUrl: '/pricing',
};

vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}));

vi.mock('@/hooks/use-lcopilot', () => ({
  useValidate: () => ({
    validate: vi.fn(),
    isLoading: false,
    clearError: vi.fn(),
  }),
}));

vi.mock('@/hooks/use-lcopilot-quota', () => ({
  useLcopilotQuota: () => exhaustedQuotaState,
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock('@/hooks/use-drafts', () => ({
  useDrafts: () => ({
    saveDraft: vi.fn(),
    loadDraft: vi.fn(),
    removeDraft: vi.fn(),
    createDraft: vi.fn(),
    getDraft: vi.fn(),
    updateDraft: vi.fn(),
    markDraftSubmitted: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock('@/hooks/use-versions', () => ({
  useVersions: () => ({
    checkLCExists: vi.fn().mockResolvedValue(null),
  }),
}));

describe('LC upload quota shell', () => {
  it('renders the same exhausted quota banner on exporter upload', async () => {
    render(renderWithProviders(<ExportLCUpload />));

    const banner = await screen.findByTestId('lcopilot-quota-banner-exporter');
    expect(banner).toHaveTextContent(/Starter allowance exhausted/i);
    expect(screen.getByRole('link', { name: /Upgrade to continue/i })).toHaveAttribute('href', '/pricing');
  });

  it('renders the same exhausted quota banner on importer upload', async () => {
    render(renderWithProviders(<ImportLCUpload />));

    const banner = await screen.findByTestId('lcopilot-quota-banner-importer');
    expect(banner).toHaveTextContent(/Starter allowance exhausted/i);
    expect(screen.getByRole('link', { name: /Upgrade to continue/i })).toHaveAttribute('href', '/pricing');
  });
});
