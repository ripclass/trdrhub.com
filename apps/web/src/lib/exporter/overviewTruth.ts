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
}

export interface ExporterOverviewTruth {
  readinessLabel: CanonicalResultTruth['readinessLabel'];
  readinessSummary: string;
  overallStatus: CanonicalResultTruth['overallStatus'];
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

export const getExporterOverviewTruth = (
  input: ExporterOverviewTruthInput,
): ExporterOverviewTruth => {
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
          : input.canonicalResultTruth.readinessLabel === 'Blocked'
          ? 'destructive'
          : 'warning',
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

  const readinessSummary =
    input.canonicalResultTruth.readinessLabel === 'Blocked'
      ? 'Submission readiness is currently blocked by canonical validation truth; treat this as a state, not a percentage score.'
      : input.canonicalResultTruth.readinessLabel === 'Review needed'
      ? 'Submission readiness currently requires review; do not compress this state into a fake numeric readiness score.'
      : 'Submission readiness is currently clear based on canonical validation eligibility.';

  return {
    readinessLabel: input.canonicalResultTruth.readinessLabel,
    readinessSummary,
    overallStatus: input.canonicalResultTruth.overallStatus,
    summaryMetrics,
    supportMetrics,
    progressMetrics,
    performanceInsights: input.performanceInsights.slice(0, 3),
    packGenerated: input.packGenerated,
  };
};
