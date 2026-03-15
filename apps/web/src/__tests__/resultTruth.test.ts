import { getCanonicalResultTruth } from '@/lib/lcopilot/resultTruth';
import { buildValidationResults } from './fixtures/lcopilot';

describe('resultTruth', () => {
  it('prioritizes validation contract reject and effective submission eligibility over UI heuristics', () => {
    const results = buildValidationResults();
    results.issues = [];
    results.structured_result = {
      ...results.structured_result,
      issues: [],
      validation_contract_v1: {
        final_verdict: 'reject',
      },
      effective_submission_eligibility: {
        can_submit: false,
        reasons: ['rules_veto'],
      },
      bank_verdict: {
        verdict: 'REJECT',
        can_submit: false,
      },
    } as typeof results.structured_result;

    const truth = getCanonicalResultTruth(results);
    expect(truth.overallStatus).toBe('error');
    expect(truth.readinessLabel).toBe('Blocked');
    expect(truth.canSubmitFromValidation).toBe(false);
    expect(truth.finalVerdict).toBe('reject');
  });

  it('uses review state when submission is blocked without a final reject', () => {
    const results = buildValidationResults();
    results.issues = [];
    results.structured_result = {
      ...results.structured_result,
      issues: [],
      validation_contract_v1: {
        final_verdict: 'review',
      },
      effective_submission_eligibility: {
        can_submit: false,
        reasons: ['issues'],
      },
      bank_verdict: {
        verdict: 'CAUTION',
        can_submit: false,
      },
    } as typeof results.structured_result;

    const truth = getCanonicalResultTruth(results);
    expect(truth.overallStatus).toBe('warning');
    expect(truth.readinessLabel).toBe('Review needed');
    expect(truth.canSubmitFromValidation).toBe(false);
  });
});
