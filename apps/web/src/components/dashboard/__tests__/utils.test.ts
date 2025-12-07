import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  formatTimeAgo,
  formatDuration,
  calculateDashboardStats,
  sessionsToHistory,
  isValidSection,
} from '../utils';
import type { ValidationSession } from '@/api/sessions';

describe('formatTimeAgo', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "Just now" for times less than 1 hour ago', () => {
    const thirtyMinsAgo = new Date('2024-01-15T11:30:00Z').toISOString();
    expect(formatTimeAgo(thirtyMinsAgo)).toBe('Just now');
  });

  it('returns hours for times less than 24 hours ago', () => {
    const fiveHoursAgo = new Date('2024-01-15T07:00:00Z').toISOString();
    expect(formatTimeAgo(fiveHoursAgo)).toBe('5h ago');
  });

  it('returns days for times less than 7 days ago', () => {
    const threeDaysAgo = new Date('2024-01-12T12:00:00Z').toISOString();
    expect(formatTimeAgo(threeDaysAgo)).toBe('3d ago');
  });

  it('returns formatted date for times more than 7 days ago', () => {
    const twoWeeksAgo = new Date('2024-01-01T12:00:00Z').toISOString();
    // Should return locale date string
    expect(formatTimeAgo(twoWeeksAgo)).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
  });
});

describe('formatDuration', () => {
  it('returns "N/A" for zero or negative values', () => {
    expect(formatDuration(0)).toBe('N/A');
    expect(formatDuration(-1000)).toBe('N/A');
  });

  it('returns seconds for durations under 1 minute', () => {
    expect(formatDuration(30000)).toBe('30.0s');
    expect(formatDuration(45500)).toBe('45.5s');
  });

  it('returns minutes for durations under 1 hour', () => {
    expect(formatDuration(120000)).toBe('2.0 min');
    expect(formatDuration(3000000)).toBe('50.0 min'); // 50 minutes
  });

  it('returns hours for durations at 1 hour or more', () => {
    expect(formatDuration(3600000)).toBe('1.0h'); // 1 hour
    expect(formatDuration(5400000)).toBe('1.5h'); // 90 minutes = 1.5 hours
    expect(formatDuration(7200000)).toBe('2.0h'); // 2 hours
  });
});

describe('calculateDashboardStats', () => {
  const mockSessions: ValidationSession[] = [
    {
      id: '1',
      user_id: 'user1',
      lc_number: 'LC001',
      status: 'completed',
      created_at: new Date().toISOString(),
      processing_started_at: new Date(Date.now() - 60000).toISOString(),
      processing_completed_at: new Date().toISOString(),
      discrepancies: [],
      documents: [{ id: 'd1' }, { id: 'd2' }] as any,
    },
    {
      id: '2',
      user_id: 'user1',
      lc_number: 'LC002',
      status: 'completed',
      created_at: new Date().toISOString(),
      processing_started_at: new Date(Date.now() - 120000).toISOString(),
      processing_completed_at: new Date().toISOString(),
      discrepancies: [
        { severity: 'major', title: 'Issue 1' },
        { severity: 'critical', title: 'Issue 2' },
      ] as any,
      documents: [{ id: 'd3' }] as any,
    },
  ];

  it('calculates total reviews correctly', () => {
    const stats = calculateDashboardStats(mockSessions);
    expect(stats.totalReviews).toBe(2);
  });

  it('calculates documents processed correctly', () => {
    const stats = calculateDashboardStats(mockSessions);
    expect(stats.documentsProcessed).toBe(3);
  });

  it('calculates risks identified correctly', () => {
    const stats = calculateDashboardStats(mockSessions);
    expect(stats.risksIdentified).toBe(2);
  });

  it('calculates success rate for exporter mode (any discrepancy = failure)', () => {
    const stats = calculateDashboardStats(mockSessions, { criticalOnly: false });
    // 1 out of 2 sessions has no discrepancies = 50%
    expect(stats.successRate).toBe(50);
  });

  it('calculates success rate for importer mode (critical only = failure)', () => {
    const stats = calculateDashboardStats(mockSessions, { criticalOnly: true });
    // 1 out of 2 sessions has no critical discrepancies = 50%
    expect(stats.successRate).toBe(50);
  });

  it('returns 0 success rate when no completed sessions', () => {
    const stats = calculateDashboardStats([]);
    expect(stats.successRate).toBe(0);
  });
});

describe('sessionsToHistory', () => {
  const mockSessions: ValidationSession[] = [
    {
      id: '1',
      user_id: 'user1',
      lc_number: 'LC001',
      status: 'completed',
      created_at: '2024-01-15T12:00:00Z',
      extracted_data: { beneficiary_name: 'Acme Corp', applicant: 'Global Trade' },
      discrepancies: [],
    } as any,
    {
      id: '2',
      user_id: 'user1',
      lc_number: 'LC002',
      status: 'completed',
      created_at: '2024-01-14T12:00:00Z',
      extracted_data: { beneficiary_name: 'Test Inc', applicant: 'Trade Co' },
      discrepancies: [{ severity: 'critical', title: 'Issue' }],
    } as any,
    {
      id: '3',
      user_id: 'user1',
      lc_number: 'LC003',
      status: 'pending',
      created_at: '2024-01-13T12:00:00Z',
      discrepancies: [],
    } as any,
  ];

  it('limits results to specified count', () => {
    const history = sessionsToHistory(mockSessions, { limit: 1 });
    expect(history).toHaveLength(1);
  });

  it('filters out non-completed sessions', () => {
    const history = sessionsToHistory(mockSessions);
    expect(history).toHaveLength(2);
    expect(history.find(h => h.id === '3')).toBeUndefined();
  });

  it('sorts by created_at descending', () => {
    const history = sessionsToHistory(mockSessions);
    expect(history[0].id).toBe('1');
    expect(history[1].id).toBe('2');
  });

  it('uses beneficiary field for importer mode', () => {
    const history = sessionsToHistory(mockSessions, { partyField: 'beneficiary' });
    expect(history[0].party).toBe('Acme Corp');
  });

  it('uses applicant field for exporter mode', () => {
    const history = sessionsToHistory(mockSessions, { partyField: 'applicant' });
    expect(history[0].party).toBe('Global Trade');
  });

  it('marks sessions with discrepancies as flagged', () => {
    const history = sessionsToHistory(mockSessions, { criticalOnly: false });
    expect(history[0].status).toBe('approved');
    expect(history[1].status).toBe('flagged');
  });
});

describe('isValidSection', () => {
  it('returns true for valid sections', () => {
    expect(isValidSection('dashboard')).toBe(true);
    expect(isValidSection('upload')).toBe(true);
    expect(isValidSection('reviews')).toBe(true);
    expect(isValidSection('analytics')).toBe(true);
  });

  it('returns false for invalid sections', () => {
    expect(isValidSection('invalid')).toBe(false);
    expect(isValidSection('')).toBe(false);
    expect(isValidSection(null)).toBe(false);
  });
});

