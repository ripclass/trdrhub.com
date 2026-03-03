import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AmendmentCard, type AmendmentsAvailable } from '../AmendmentCard';

describe('AmendmentCard', () => {
  const amendments: AmendmentsAvailable = {
    count: 2,
    total_estimated_fee_usd: 200,
    total_processing_days: 4,
    amendments: [
      {
        issue_id: 'a-1',
        field: {
          tag: '45A',
          name: 'Description of Goods',
          current: 'Current A',
          proposed: 'Proposed A',
        },
        narrative: 'Amend goods description',
        mt707_text: 'mt707-a',
        iso20022_xml: '<xml>a</xml>',
        bank_processing_days: 2,
        estimated_fee_usd: 100,
      },
      {
        issue_id: 'a-2',
        field: {
          tag: '46A',
          name: 'Documents Required',
          current: 'Current B',
          proposed: 'Proposed B',
        },
        narrative: 'Amend docs requirement',
        mt707_text: 'mt707-b',
        iso20022_xml: '<xml>b</xml>',
        bank_processing_days: 2,
        estimated_fee_usd: 100,
      },
    ],
  };

  it('shows per-card selected format and keeps selection isolated', () => {
    const onDownloadMT707 = vi.fn();
    const onDownloadISO20022 = vi.fn();

    render(
      <AmendmentCard
        amendments={amendments}
        onDownloadMT707={onDownloadMT707}
        onDownloadISO20022={onDownloadISO20022}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /view amendments/i }));

    // Defaults are MT707 for both cards.
    expect(screen.getAllByText(/Selected format for this amendment:/i)).toHaveLength(2);
    expect(screen.getAllByText('MT707').length).toBeGreaterThanOrEqual(2);

    // Switch first card to ISO20022.
    const isoButtons = screen.getAllByRole('button', { name: /ISO20022/i });
    fireEvent.click(isoButtons[0]);

    expect(onDownloadISO20022).toHaveBeenCalledTimes(1);

    const selectedLines = screen.getAllByText(/Selected format for this amendment:/i).map((el) => el.parentElement?.textContent || '');
    expect(selectedLines[0]).toContain('ISO20022');
    expect(selectedLines[1]).toContain('MT707');
  });
});
