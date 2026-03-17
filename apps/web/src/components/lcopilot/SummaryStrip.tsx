import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle } from 'lucide-react';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
  lcTypeLabel?: string;
  lcTypeConfidence?: number | null;
  lcTypeCaption?: string;
  packGenerated?: boolean;
  overallStatus?: 'success' | 'warning' | 'error';
  actualIssuesCount?: number;
  complianceScore?: number;
  readinessLabel?: string;
  readinessSummary?: string;
};

export function SummaryStrip({
  data,
  lcTypeLabel,
  lcTypeConfidence,
  lcTypeCaption,
  packGenerated,
  overallStatus,
  actualIssuesCount,
  complianceScore,
  readinessLabel,
  readinessSummary,
}: Props) {
  const structured = data?.structured_result;
  const summary =
    data?.summary ??
    (structured as any)?.processing_summary_v2 ??
    structured?.processing_summary;
  const analytics = data?.analytics ?? structured?.analytics;

  if (!summary) {
    return null;
  }

  // Canonical metrics from backend
  const documentsProcessed = summary.total_documents ?? 0;
  const statusDistribution =
    summary?.document_status ?? summary?.status_counts ?? {
      success: 0,
      warning: 0,
      error: 0,
    };
  const processingTime =
    summary.processing_time_display ?? (analytics as any)?.processing_time_display ?? 'N/A';

  const totalIssues = actualIssuesCount ?? summary.total_issues ?? summary.discrepancies ?? 0;
  const complianceRate = complianceScore ?? summary.compliance_rate ?? 0;

  const warnings = typeof (summary.warnings ?? statusDistribution.warning) === 'number'
    ? Number(summary.warnings ?? statusDistribution.warning)
    : 0;
  const errors = typeof (summary.errors ?? statusDistribution.error) === 'number'
    ? Number(summary.errors ?? statusDistribution.error)
    : 0;

  const hasIssues = complianceRate < 100 || totalIssues > 0 || warnings > 0 || errors > 0;

  // Status icon based on overall status prop or calculated
  const effectiveStatus = overallStatus ?? (errors > 0 ? 'error' : hasIssues ? 'warning' : 'success');
  const effectiveReadinessLabel = readinessLabel ?? (effectiveStatus === 'error' ? 'Blocked' : hasIssues ? 'Review needed' : 'Ready');
  const statusIcon = effectiveStatus === 'success' ? (
    <CheckCircle className="w-12 h-12 text-emerald-500" />
  ) : effectiveStatus === 'error' ? (
    <AlertTriangle className="w-12 h-12 text-rose-500" />
  ) : (
    <AlertTriangle className="w-12 h-12 text-amber-500" />
  );

  return (
    <Card className="shadow-soft border border-border/60">
      <CardContent className="p-8">
        <div className="flex flex-col lg:flex-row gap-8 lg:items-start">
          <div className="flex flex-col sm:flex-row gap-6 sm:items-center lg:min-w-[320px]">
            <div className="flex flex-col items-center gap-3 sm:min-w-[120px]">
              {statusIcon}
              {packGenerated && (
                <Badge className="bg-emerald-600 text-white border-0 hover:bg-emerald-700">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Customs Pack Ready
                </Badge>
              )}
            </div>
            {lcTypeLabel && (
              <div className="space-y-2">
                <p className="text-[10px] uppercase text-muted-foreground tracking-wide">
                  {lcTypeCaption || 'LC TYPE'}
                </p>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Badge variant="secondary" className="text-xs">{lcTypeLabel}</Badge>
                  {lcTypeConfidence != null && lcTypeConfidence > 0 && (
                    <span className="text-xs text-muted-foreground">{lcTypeConfidence}% confidence</span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  Case status: <span className="font-medium text-foreground">{effectiveReadinessLabel}</span>
                </p>
                {readinessSummary && (
                  <p className="text-xs text-muted-foreground max-w-md">{readinessSummary}</p>
                )}
              </div>
            )}
          </div>

          <div className="hidden lg:block w-px bg-border self-stretch" />

          <div className="flex-1 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Documents</p>
              <p className="text-2xl font-semibold">{documentsProcessed}</p>
              <p className="text-xs text-muted-foreground mt-1">Processed in this validation set</p>
            </div>
            <div className="rounded-lg border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Issues</p>
              <p className="text-2xl font-semibold">{totalIssues}</p>
              <p className="text-xs text-muted-foreground mt-1">Detected discrepancies or review items</p>
            </div>
            <div className="rounded-lg border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">LC Compliance</p>
              <p className={`text-2xl font-semibold ${complianceRate >= 80 ? 'text-emerald-600' : complianceRate >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                {complianceRate}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">Canonical validation score</p>
            </div>
            <div className="rounded-lg border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Processing Time</p>
              <p className="text-2xl font-semibold">{processingTime}</p>
              <p className="text-xs text-muted-foreground mt-1">Backend processing duration</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;

