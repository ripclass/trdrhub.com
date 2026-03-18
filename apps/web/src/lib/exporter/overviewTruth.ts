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
          ? 'Submission readiness is blocked because required documents or blocked review states are still unresolved on the exporter checklist.'
          : 'Submission readiness is currently blocked by canonical validation truth; treat this as a state, not a percentage score.',
      overallStatus: 'error',
      presentationStatus: 'not_ready',
      presentationSummary:
        'Not ready for clean presentation until missing required documents and blocked review items are cleared.',
    };
  }

  if (
    input.canonicalResultTruth.readinessLabel === 'Review needed' ||
    hasReviewChecklistState ||
    input.totalIssues > 0
  ) {
    return {
      readinessLabel: 'Review needed',
      readinessSummary:
        hasReviewChecklistState || input.totalIssues > 0
          ? 'Submission readiness requires review because checklist items or issue findings are still unresolved.'
          : 'Submission readiness currently requires review; do not compress this state into a fake numeric readiness score.',
      overallStatus: 'warning',
      presentationStatus: 'review_required',
      presentationSummary:
        'Presentation requires review or remediation before it should be treated as clean.',
    };
  }

  return {
    readinessLabel: 'Ready',
    readinessSummary: 'Submission readiness is currently clear based on exporter checklist and canonical validation eligibility.',
    overallStatus: 'success',
    presentationStatus: 'ready',
    presentationSummary: 'Document set appears ready for clean presentation on current review.',
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
      label: 'LC Compliance',
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
      label: 'Structured Extraction',
      value: input.extractionAccuracy,
    },
    {
      label: 'LC Compliance',
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
