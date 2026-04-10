import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
  lcTypeLabel?: string;
  lcTypeConfidence?: number | null;
  lcTypeCaption?: string;
  packGenerated?: boolean;
  overallStatus?: 'success' | 'warning' | 'error';
  actualIssuesCount?: number;
  advisoryIssuesCount?: number;
  complianceScore?: number;
  readinessLabel?: string;
  readinessSummary?: string;
};

export function SummaryStrip({
  data,
  lcTypeLabel,
  lcTypeConfidence,
  overallStatus,
  actualIssuesCount,
  complianceScore,
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

  const documentsProcessed = summary.total_documents ?? 0;
  const processingTime =
    summary.processing_time_display ?? (analytics as any)?.processing_time_display ?? 'N/A';
  const reportableIssueCount =
    actualIssuesCount ??
    Number((summary as any)?.reportable_issue_count ?? summary.total_issues ?? summary.discrepancies ?? 0);
  const complianceRate = complianceScore ?? summary.compliance_rate ?? 0;

  const effectiveStatus = overallStatus ?? (complianceRate >= 80 ? 'success' : complianceRate >= 40 ? 'warning' : 'error');
  const StatusIcon = effectiveStatus === 'success' ? CheckCircle : effectiveStatus === 'error' ? XCircle : AlertTriangle;
  const statusColor = effectiveStatus === 'success' ? 'text-emerald-500' : effectiveStatus === 'error' ? 'text-red-500' : 'text-amber-500';

  return (
    <Card className="shadow-soft border border-border/60">
      <CardContent className="py-4 px-6">
        <div className="flex items-center gap-6">
          {/* Status icon + LC type — compact left section */}
          <div className="flex items-center gap-3 shrink-0">
            <StatusIcon className={`w-8 h-8 ${statusColor}`} />
            {lcTypeLabel && (
              <div>
                <Badge variant="secondary" className="text-xs">{lcTypeLabel}</Badge>
                {lcTypeConfidence != null && lcTypeConfidence > 0 && (
                  <p className="text-[10px] text-muted-foreground mt-0.5">{lcTypeConfidence}% confidence</p>
                )}
              </div>
            )}
          </div>

          <div className="hidden sm:block w-px h-10 bg-border" />

          {/* 4 metric cards — even grid, no squeeze */}
          <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="text-center sm:text-left">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Documents</p>
              <p className="text-xl font-bold">{documentsProcessed}</p>
            </div>
            <div className="text-center sm:text-left">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Issues</p>
              <p className="text-xl font-bold">{reportableIssueCount}</p>
            </div>
            <div className="text-center sm:text-left">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Score</p>
              <p className={`text-xl font-bold ${complianceRate >= 80 ? 'text-emerald-500' : complianceRate >= 40 ? 'text-amber-500' : 'text-red-500'}`}>
                {complianceRate}%
              </p>
            </div>
            <div className="text-center sm:text-left">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Time</p>
              <p className="text-xl font-bold">{processingTime}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;
