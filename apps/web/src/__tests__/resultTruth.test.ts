import { getCanonicalResultTruth, getContractDrivenBankVerdict } from '@/lib/lcopilot/resultTruth';
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

  it('keeps readiness submit-ready when canonical eligibility allows submission despite caution issues', () => {
    const results = buildValidationResults();
    results.issues = [];
    results.structured_result = {
      ...results.structured_result,
      issues: [],
      final_verdict: null,
      validation_status: 'pass',
      submission_eligibility: {
        can_submit: true,
        reasons: [],
      },
      effective_submission_eligibility: {
        can_submit: true,
        reasons: [],
      },
      bank_verdict: {
        verdict: 'CAUTION',
        can_submit: true,
      },
    } as typeof results.structured_result;

    const truth = getCanonicalResultTruth(results);
    expect(truth.finalVerdict).toBe('pass');
    expect(truth.overallStatus).toBe('warning');
    expect(truth.readinessLabel).toBe('Ready');
    expect(truth.canSubmitFromValidation).toBe(true);
  });

  it('keeps contract review authoritative even if legacy eligibility still says can submit', () => {
    const results = buildValidationResults();
    results.issues = [];
    results.structured_result = {
      ...results.structured_result,
      issues: [],
      final_verdict: 'pass',
      validation_status: 'pass',
      validation_contract_v1: {
        final_verdict: 'review',
      },
      effective_submission_eligibility: {
        can_submit: true,
        reasons: [],
      },
      bank_verdict: {
        verdict: 'SUBMIT',
        can_submit: true,
      },
    } as typeof results.structured_result;

    const truth = getCanonicalResultTruth(results);
    expect(truth.finalVerdict).toBe('review');
    expect(truth.overallStatus).toBe('warning');
    expect(truth.readinessLabel).toBe('Review needed');
    expect(truth.canSubmitFromValidation).toBe(false);
  });

  it('surfaces advisory lanes without downgrading ready documentary truth', () => {
    const results = buildValidationResults();
    results.issues = [
      {
        severity: 'critical',
        title: 'Potential Sanctions Match',
        rule: 'SANCTIONS-PARTY-1',
      } as any,
    ];
    results.structured_result = {
      ...results.structured_result,
      validation_contract_v1: {
        final_verdict: 'pass',
        rules_evidence: {
          issue_lanes: {
            documentary: { count: 0 },
            advisory: { count: 1 },
          },
          advisory_review_needed: true,
          primary_decision_lane: 'advisory',
        },
        evidence_summary: {
          primary_decision_lane: 'advisory',
          advisory_review_needed: true,
        },
      },
      effective_submission_eligibility: {
        can_submit: true,
        reasons: [],
      },
      bank_verdict: {
        verdict: 'SUBMIT',
        can_submit: true,
      },
    } as typeof results.structured_result;

    const truth = getCanonicalResultTruth(results);
    expect(truth.readinessLabel).toBe('Ready');
    expect(truth.canSubmitFromValidation).toBe(true);
    expect(truth.primaryDecisionLane).toBe('advisory');
    expect(truth.advisoryIssueCount).toBe(1);
    expect(truth.documentaryIssueCount).toBe(0);
    expect(truth.advisoryReviewNeeded).toBe(true);
  });

  it('builds display bank verdict from validation contract when legacy verdict drifts', () => {
    const results = buildValidationResults();
    results.issues = [];
    results.structured_result = {
      ...results.structured_result,
      validation_contract_v1: {
        final_verdict: 'reject',
      },
      effective_submission_eligibility: {
        can_submit: false,
        reasons: ['validation_contract_reject'],
      },
      bank_verdict: {
        verdict: 'SUBMIT',
        verdict_color: 'green',
        verdict_message: 'Legacy drift',
        recommendation: 'Legacy drift',
        can_submit: true,
        action_items: [{ priority: 'critical', issue: 'Amount mismatch', action: 'Fix invoice amount' }],
      },
    } as typeof results.structured_result;

    const verdict = getContractDrivenBankVerdict(results);
    expect(verdict?.verdict).toBe('REJECT');
    expect(verdict?.verdict_color).toBe('red');
    expect(verdict?.can_submit).toBe(false);
    expect(verdict?.action_items).toHaveLength(1);
  });

  it('returns legacy bank verdict when validation contract is missing', () => {
    const results = buildValidationResults();
    results.structured_result = {
      ...results.structured_result,
      validation_contract_v1: undefined,
      bank_verdict: {
        verdict: 'CAUTION',
        can_submit: true,
      },
    } as typeof results.structured_result;

    const verdict = getContractDrivenBankVerdict(results);
    expect(verdict?.verdict).toBe('CAUTION');
    expect(verdict?.can_submit).toBe(true);
  });
});
