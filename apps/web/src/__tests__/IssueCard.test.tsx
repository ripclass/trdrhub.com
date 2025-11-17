import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { DiscrepancyGuidance } from '@/components/discrepancy/DiscrepancyGuidance';

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe('Issue card rendering', () => {
  it('shows expected/found/suggestion fields', () => {
    render(
      <DiscrepancyGuidance
        discrepancy={{
          id: 'ISSUE-1',
          title: 'Amount mismatch',
          description: 'Invoice has lower amount',
          severity: 'major',
          documentName: 'Invoice.pdf',
          rule: 'AMOUNT_CHECK',
          expected: '50000 USD',
          actual: '49000 USD',
          suggestion: 'Update invoice to match LC',
          documentType: 'Commercial Invoice',
        }}
      />,
    );

    expect(screen.getByText(/Amount mismatch/i)).toBeInTheDocument();
    expect(screen.getByText(/Expected/i)).toBeInTheDocument();
    expect(screen.getByText(/50000 USD/i)).toBeInTheDocument();
    expect(screen.getByText(/49000 USD/i)).toBeInTheDocument();
    expect(screen.getByText(/Update invoice to match LC/i)).toBeInTheDocument();
  });
});
