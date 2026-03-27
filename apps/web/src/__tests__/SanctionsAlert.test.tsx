import { render, screen } from '@testing-library/react';
import { SanctionsAlert, SanctionsBadge } from '@/components/sanctions/SanctionsAlert';
import { renderWithProviders } from './testUtils';

const sanctionsScreening = {
  screened: true,
  screened_at: '2026-03-27T10:00:00Z',
  parties_screened: 4,
  matches: 1,
  potential_matches: 0,
  issues: [
    {
      party: 'SBERBANK',
      type: 'issuing_bank',
      status: 'match',
      score: 0.98,
    },
  ],
};

describe('SanctionsAlert', () => {
  it('renders confirmed matches as a compliance overlay when not blocked', () => {
    render(
      renderWithProviders(
        <SanctionsAlert
          sanctionsScreening={sanctionsScreening}
          sanctionsBlocked={false}
          sanctionsBlockReason={null}
        />,
      ),
    );

    expect(screen.getByText('Sanctions Match Detected')).toBeInTheDocument();
    expect(screen.queryByText(/Processing Blocked/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Documentary submit readiness is governed separately by the validation contract/i)).toBeInTheDocument();
    expect(screen.getByText(/Compliance escalation recommended/i)).toBeInTheDocument();
  });

  it('shows a compliance review badge for confirmed matches when not blocked', () => {
    render(<SanctionsBadge sanctionsScreening={sanctionsScreening} sanctionsBlocked={false} />);

    expect(screen.getByText('Compliance Review')).toBeInTheDocument();
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument();
  });
});
