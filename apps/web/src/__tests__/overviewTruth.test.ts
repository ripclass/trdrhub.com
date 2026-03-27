import { getExporterPresentationTruth } from '@/lib/exporter/overviewTruth';
import type { CanonicalResultTruth } from '@/lib/lcopilot/resultTruth';

describe('overviewTruth', () => {
  it('keeps advisory-only issue sets submit-ready when canonical truth is pass', () => {
    const canonicalResultTruth: CanonicalResultTruth = {
      validationContract: {
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
      } as any,
      finalVerdict: 'pass',
      submissionEligibility: {
        can_submit: true,
        reasons: [],
      } as any,
      bankVerdict: {
        verdict: 'SUBMIT',
        can_submit: true,
      } as any,
      overallStatus: 'warning',
      readinessLabel: 'Ready',
      readinessClass: 'text-success',
      canSubmitFromValidation: true,
      requirementReviewNeeded: false,
      requirementReasonCodes: [],
      requirementActionTitles: [],
      requirementReadinessItems: [],
      primaryDecisionLane: 'advisory',
      documentaryIssueCount: 0,
      advisoryIssueCount: 1,
      advisoryReviewNeeded: true,
    };

    const truth = getExporterPresentationTruth({
      canonicalResultTruth,
      checklistTruth: {
        missingRequirements: 0,
        partialRequirements: 0,
        blockedReviews: 0,
        reviewRequired: 0,
        awaitingDocuments: 0,
      },
      totalIssues: 1,
    });

    expect(truth.readinessLabel).toBe('Ready');
    expect(truth.presentationStatus).toBe('ready');
    expect(truth.readinessSummary).toMatch(/non-blocking overlays/i);
  });
});
