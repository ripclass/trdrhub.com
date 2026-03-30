import type { CanonicalResultTruth } from '@/lib/lcopilot/resultTruth';

export interface OverviewSupportMetric {
  label: string;
  value: string | number;
  tone?: 'default' | 'success' | 'warning' | 'destructive' | 'primary';
}

export interface OverviewProgressMetric {
  label: string;
  value: number;
}

export interface ExporterChecklistTruthInput {
  missingRequirements: number;
  partialRequirements: number;
  blockedReviews: number;
  reviewRequired: number;
  awaitingDocuments: number;
}

export interface ExporterOverviewTruthInput {
  totalDocuments: number;
  totalIssues: number;
  complianceScore: number;
  extractionAccuracy: number;
  processingTime: string;
  successCount: number;
  warningCount: number;
  packGenerated: boolean;
  performanceInsights: string[];
  canonicalResultTruth: CanonicalResultTruth;
  checklistTruth: ExporterChecklistTruthInput;
}

export interface ExporterOverviewTruth {
  readinessLabel: CanonicalResultTruth['readinessLabel'];
  readinessSummary: string;
  overallStatus: CanonicalResultTruth['overallStatus'];
  presentationStatus: 'ready' | 'review_required' | 'not_ready';
  presentationSummary: string;
  summaryMetrics: OverviewSupportMetric[];
  supportMetrics: OverviewSupportMetric[];
  progressMetrics: OverviewProgressMetric[];
  performanceInsights: string[];
  packGenerated: boolean;
}

const toMetricTone = (
  value: number,
  thresholds: { success: number; warning: number },
): OverviewSupportMetric['tone'] => {
  if (value >= thresholds.success) return 'success';
  if (value >= thresholds.warning) return 'warning';
  return 'destructive';
};

export const getExporterPresentationTruth = (
  input: Pick<ExporterOverviewTruthInput, 'canonicalResultTruth' | 'checklistTruth' | 'totalIssues'>,
): Pick<ExporterOverviewTruth, 'readinessLabel' | 'readinessSummary' | 'overallStatus' | 'presentationStatus' | 'presentationSummary'> => {
  const hasBlockingChecklistState =
    input.checklistTruth.missingRequirements > 0 ||
    input.checklistTruth.blockedReviews > 0 ||
    input.checklistTruth.awaitingDocuments > 0;
  const hasReviewChecklistState =
    input.checklistTruth.partialRequirements > 0 ||
    input.checklistTruth.reviewRequired > 0;

  if (
    input.canonicalResultTruth.readinessLabel === 'Blocked' ||
    hasBlockingChecklistState
  ) {
    return {
      readinessLabel: 'Blocked',
      readinessSummary:
        hasBlockingChecklistState
          ? 'Clean presentation is blocked because required documents or blocked checklist items are still unresolved.'
          : 'Clean presentation is blocked by canonical validation truth and should stay blocked until the blocking items are cleared.',
      overallStatus: 'error',
      presentationStatus: 'not_ready',
      presentationSummary:
        'Not ready for clean presentation. Clear the missing required documents and blocked review items first.',
    };
  }

  if (
    input.canonicalResultTruth.readinessLabel === 'Review needed' ||
    hasReviewChecklistState
  ) {
    const requirementAction = input.canonicalResultTruth.requirementActionTitles[0];
    const requirementSummary =
      requirementAction && input.canonicalResultTruth.requirementReviewNeeded
        ? `Clean presentation still needs review because one or more LC-required statements or documentary requirements are unresolved, starting with ${requirementAction}.`
        : null;
    const requirementPresentationSummary = input.canonicalResultTruth.requirementReviewNeeded
      ? 'Resolve the remaining LC-required statements or seek an LC amendment before treating this presentation as clean.'
      : null;
    const documentarySummary =
      input.canonicalResultTruth.primaryDecisionLane === 'documentary' &&
      input.canonicalResultTruth.documentaryIssueCount > 0
        ? 'Clean presentation still needs review because documentary findings remain unresolved.'
        : null;
    return {
      readinessLabel: 'Review needed',
      readinessSummary:
        requirementSummary ??
        documentarySummary ??
        (hasReviewChecklistState
          ? 'Clean presentation still needs review because checklist items are unresolved.'
          : 'Clean presentation still needs review; keep this as a workflow state, not a fake numeric score.'),
      overallStatus: 'warning',
      presentationStatus: 'review_required',
      presentationSummary:
        requirementPresentationSummary ??
        'Review or remediate the open items before treating this presentation as clean.',
    };
  }

  if (input.canonicalResultTruth.advisoryReviewNeeded) {
    return {
      readinessLabel: 'Ready',
      readinessSummary:
        'Documentary checks are clear for presentation. Advisory or compliance alerts remain visible separately and do not block submission on their own.',
      overallStatus: 'success',
      presentationStatus: 'ready',
      presentationSummary:
        'Ready for clean presentation on documentary checks. Review advisory signals separately as non-blocking overlays.',
    };
  }

  return {
    readinessLabel: 'Ready',
    readinessSummary: 'Current documentary checks are clear for presentation based on the checklist and canonical validation truth.',
    overallStatus: 'success',
    presentationStatus: 'ready',
    presentationSummary: 'Document set appears ready for clean presentation on the current review.',
  };
};

export const getExporterOverviewTruth = (
  input: ExporterOverviewTruthInput,
): ExporterOverviewTruth => {
  const presentationTruth = getExporterPresentationTruth({
    canonicalResultTruth: input.canonicalResultTruth,
    checklistTruth: input.checklistTruth,
    totalIssues: input.totalIssues,
  });

  const summaryMetrics: OverviewSupportMetric[] = [
    {
      label: 'Documents',
      value: input.totalDocuments,
      tone: 'default',
    },
    {
      label: 'Issues',
      value: input.totalIssues,
      tone:
        input.totalIssues === 0
          ? 'success'
          : presentationTruth.readinessLabel === 'Blocked'
          ? 'destructive'
          : 'warning',
    },
  ];

  const supportMetrics: OverviewSupportMetric[] = [
    {
      label: 'Verified',
      value: input.successCount,
      tone: input.successCount > 0 ? 'success' : 'default',
    },
    {
      label: 'Warnings',
      value: input.warningCount,
      tone: input.warningCount > 0 ? 'warning' : 'default',
    },
    {
      label: 'Validation Score',
      value: `${input.complianceScore}%`,
      tone: toMetricTone(input.complianceScore, { success: 80, warning: 50 }),
    },
    {
      label: 'Processing Time',
      value: input.processingTime,
      tone: 'primary',
    },
  ];

  const progressMetrics: OverviewProgressMetric[] = [
    {
      label: 'Document Fields Confirmed',
      value: input.extractionAccuracy,
    },
    {
      label: 'Validation Score',
      value: input.complianceScore,
    },
  ];

  return {
    readinessLabel: presentationTruth.readinessLabel,
    readinessSummary: presentationTruth.readinessSummary,
    overallStatus: presentationTruth.overallStatus,
    presentationStatus: presentationTruth.presentationStatus,
    presentationSummary: presentationTruth.presentationSummary,
    summaryMetrics,
    supportMetrics,
    progressMetrics,
    performanceInsights: input.performanceInsights.slice(0, 3),
    packGenerated: input.packGenerated,
  };
};
