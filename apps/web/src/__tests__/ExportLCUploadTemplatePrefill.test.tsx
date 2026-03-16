import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import ExportLCUpload from '@/pages/ExportLCUpload';
import { renderWithProviders } from './testUtils';

const { prefillMock, toastMock } = vi.hoisted(() => ({
  prefillMock: vi.fn(),
  toastMock: vi.fn(),
}));

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
  useLcopilotQuota: () => ({
    status: 'ready',
    plan: 'FREE',
    quota: {
      used: 0,
      limit: 5,
      remaining: 5,
    },
    isExhausted: false,
    canValidate: true,
    headline: 'Starter allowance available',
    detail: '5 starter checks remaining.',
    ctaLabel: 'Upgrade',
    ctaUrl: '/pricing',
  }),
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: toastMock,
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
    getAllDrafts: vi.fn(() => []),
    isLoading: false,
  }),
}));

vi.mock('@/hooks/use-versions', () => ({
  useVersions: () => ({
    checkLCExists: vi.fn().mockResolvedValue(null),
  }),
}));

vi.mock('@/api/sme-templates', () => ({
  smeTemplatesApi: {
    prefill: prefillMock,
  },
}));

describe('ExportLCUpload template handoff', () => {
  it('applies supported template fields from the embedded upload route', async () => {
    prefillMock.mockResolvedValueOnce({
      template_name: 'Standard LC',
      fields: {
        lc_number: 'LC-TEMPLATE-001',
        beneficiary: 'Acme Trading',
        notes: 'Review beneficiary details before validation.',
      },
    });

    render(
      renderWithProviders(
        <ExportLCUpload embedded />,
        '/lcopilot/exporter-dashboard?section=upload&templateId=template-123',
      ),
    );

    await waitFor(() => {
      expect(prefillMock).toHaveBeenCalledWith({ template_id: 'template-123' });
    });

    expect(await screen.findByText(/Template applied: Standard LC/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/LC Number/i)).toHaveValue('LC-TEMPLATE-001');
    expect(screen.getByLabelText(/Additional Notes/i)).toHaveValue(
      'Review beneficiary details before validation.\n\nTemplate context (Standard LC):\n- Beneficiary: Acme Trading',
    );
    expect(toastMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Template applied',
      }),
    );
  });
});
