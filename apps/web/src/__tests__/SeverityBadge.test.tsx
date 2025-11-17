import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/ui/status-badge';

describe('StatusBadge', () => {
  it('renders icons and colors based on severity', () => {
    render(
      <div>
        <StatusBadge status="success">Verified</StatusBadge>
        <StatusBadge status="error">Critical</StatusBadge>
        <StatusBadge status="warning">Review</StatusBadge>
      </div>,
    );

    expect(screen.getByText(/Verified/i)).toBeInTheDocument();
    expect(screen.getByText(/Critical/i)).toBeInTheDocument();
    expect(screen.getByText(/Review/i)).toBeInTheDocument();
  });
});
