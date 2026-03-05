import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BankVerdictCard, type BankVerdict } from '../BankVerdictCard';

describe('BankVerdictCard', () => {
  const baseVerdict: BankVerdict = {
    verdict: 'SUBMIT',
    verdict_color: 'green',
    verdict_message: 'All checks passed',
    recommendation: 'Safe to submit to bank',
    can_submit: true,
    will_be_rejected: false,
    estimated_discrepancy_fee: 0,
    issue_summary: {
      critical: 0,
      major: 0,
      minor: 0,
      total: 0,
    },
    action_items: [],
    action_items_count: 0,
  };

  it('renders SUBMIT verdict with correct styling', () => {
    render(<BankVerdictCard verdict={baseVerdict} />);
    
    expect(screen.getByText('READY TO SUBMIT')).toBeInTheDocument();
    expect(screen.getByText('All checks passed')).toBeInTheDocument();
    expect(screen.getByText('Safe to submit to bank')).toBeInTheDocument();
  });

  it('renders REJECT verdict with correct styling', () => {
    const rejectVerdict: BankVerdict = {
      ...baseVerdict,
      verdict: 'REJECT',
      verdict_color: 'red',
      verdict_message: 'Critical issues found',
      recommendation: 'Do not submit - major discrepancies',
      will_be_rejected: true,
      issue_summary: {
        critical: 2,
        major: 1,
        minor: 0,
        total: 3,
      },
    };

    render(<BankVerdictCard verdict={rejectVerdict} />);
    
    expect(screen.getByText('REJECT')).toBeInTheDocument();
    expect(screen.getByText('Critical issues found')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // Critical count
  });

  it('displays estimated discrepancy fee when > 0', () => {
    const verdictWithFee: BankVerdict = {
      ...baseVerdict,
      verdict: 'CAUTION',
      estimated_discrepancy_fee: 150,
    };

    render(<BankVerdictCard verdict={verdictWithFee} />);
    
    expect(screen.getByText(/USD 150.00/)).toBeInTheDocument();
  });

  it('does not display fee when 0', () => {
    render(<BankVerdictCard verdict={baseVerdict} />);
    
    expect(screen.queryByText(/USD/)).not.toBeInTheDocument();
  });

  it('displays action items when present', () => {
    const verdictWithActions: BankVerdict = {
      ...baseVerdict,
      verdict: 'HOLD',
      action_items: [
        { priority: 'critical', issue: 'Missing signature', action: 'Get document signed' },
        { priority: 'high', issue: 'Date mismatch', action: 'Verify dates' },
      ],
      action_items_count: 2,
    };

    render(<BankVerdictCard verdict={verdictWithActions} />);
    
    expect(screen.getByText('Required Actions (2)')).toBeInTheDocument();
    expect(screen.getByText('Missing signature')).toBeInTheDocument();
    expect(screen.getByText(/Get document signed/)).toBeInTheDocument();
  });

  it('shows "+N more" when action items exceed 3', () => {
    const verdictWithManyActions: BankVerdict = {
      ...baseVerdict,
      verdict: 'CAUTION',
      action_items: [
        { priority: 'critical', issue: 'Issue 1', action: 'Action 1' },
        { priority: 'high', issue: 'Issue 2', action: 'Action 2' },
        { priority: 'medium', issue: 'Issue 3', action: 'Action 3' },
        { priority: 'medium', issue: 'Issue 4', action: 'Action 4' },
        { priority: 'medium', issue: 'Issue 5', action: 'Action 5' },
      ],
      action_items_count: 5,
    };

    render(<BankVerdictCard verdict={verdictWithManyActions} />);
    
    expect(screen.getByText('+ 2 more action(s) in Issues tab')).toBeInTheDocument();
  });

  it('displays issue summary counts', () => {
    const verdictWithIssues: BankVerdict = {
      ...baseVerdict,
      verdict: 'CAUTION',
      issue_summary: {
        critical: 1,
        major: 3,
        minor: 5,
        total: 9,
      },
    };

    render(<BankVerdictCard verdict={verdictWithIssues} />);
    
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Major')).toBeInTheDocument();
  });
});

