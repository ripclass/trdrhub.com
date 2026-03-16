import {
  getExporterSessionTruth,
  type ExporterSessionTruth,
} from '@/lib/exporter/dashboardTruth';
import type { ValidationSession } from '@/api/sessions';
import { describe, expect, it } from 'vitest';

const buildSession = (
  overrides: Partial<ValidationSession> = {},
): ValidationSession => ({
  id: 'session-1',
  status: 'completed',
  created_at: '2026-03-16T10:00:00Z',
  updated_at: '2026-03-16T10:05:00Z',
  documents: [],
  discrepancies: [],
  ...overrides,
});

describe('dashboardTruth', () => {
  it('uses canonical readiness for submit-ready sessions', () => {
    const truth = getExporterSessionTruth(
      buildSession({
        validation_results: {
          structured_result: {
            version: 'structured_result_v1',
            lc_number: 'LC-READY',
            validation_status: 'pass',
            submission_eligibility: { can_submit: true, reasons: [] },
            effective_submission_eligibility: { can_submit: true, reasons: [] },
            bank_verdict: { verdict: 'PASS', can_submit: true },
            issues: [],
          },
        },
      }),
    );

    expect(truth.canonical).toBe(true);
    expect(truth.state).toBe('ready');
    expect(truth.statusLabel).toBe('Ready');
    expect(truth.canSubmit).toBe(true);
  });

  it('keeps caution verdicts submit-ready without downgrading can-submit', () => {
    const truth = getExporterSessionTruth(
      buildSession({
        validation_results: {
          structured_result: {
            version: 'structured_result_v1',
            lc_number: 'LC-CAUTION',
            validation_status: 'pass',
            submission_eligibility: { can_submit: true, reasons: [] },
            effective_submission_eligibility: { can_submit: true, reasons: [] },
            bank_verdict: { verdict: 'CAUTION', can_submit: true },
            issues: [{ severity: 'warning' }],
          },
        },
      }),
    );

    expect(truth.state).toBe('ready');
    expect(truth.statusLabel).toBe('Ready with cautions');
    expect(truth.canSubmit).toBe(true);
  });

  it('falls back to honest completed state when canonical payload is unavailable', () => {
    const truth = getExporterSessionTruth(
      buildSession({
        discrepancies: [],
      }),
    );

    expect(truth.canonical).toBe(false);
    expect(truth.state).toBe('completed');
    expect(truth.statusLabel).toBe('Completed');
    expect(truth.canSubmit).toBe(false);
  });
});
