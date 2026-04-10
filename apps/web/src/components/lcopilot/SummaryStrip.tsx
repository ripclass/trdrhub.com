import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle, XCircle, FileText, Clock, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';
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
  bankName?: string;
};

export function SummaryStrip({
  data,
  lcTypeLabel,
  lcTypeConfidence,
  overallStatus,
  actualIssuesCount,
  complianceScore,
  bankName,
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
  const borderColor = effectiveStatus === 'success'
    ? 'border-emerald-500/50'
    : effectiveStatus === 'error'
    ? 'border-red-500/50'
    : 'border-amber-500/50';
  const statusColor = effectiveStatus === 'success' ? 'text-emerald-400' : effectiveStatus === 'error' ? 'text-red-400' : 'text-amber-400';
  const StatusIcon = effectiveStatus === 'success' ? CheckCircle : effectiveStatus === 'error' ? XCircle : AlertTriangle;
  const statusWord = effectiveStatus === 'success' ? 'COMPLIANT' : effectiveStatus === 'error' ? 'BLOCKED' : 'REVIEW';

  return (
    <Card className={cn('border-2 shadow-lg', borderColor)}>
      <CardContent className="py-5 px-8">
        <div className="flex items-center gap-6">
          {/* Status badge — prominent */}
          <div className="flex items-center gap-3 shrink-0">
            <StatusIcon className={cn('w-10 h-10', statusColor)} />
            <div>
              <p className={cn('text-lg font-bold tracking-wide', statusColor)}>{statusWord}</p>
              {lcTypeLabel && (
                <div className="flex items-center gap-1.5 mt-0.5">
                  <Badge variant="secondary" className="text-[10px]">{lcTypeLabel}</Badge>
                  {lcTypeConfidence != null && lcTypeConfidence > 0 && (
                    <span className="text-[10px] text-muted-foreground">{lcTypeConfidence}%</span>
                  )}
                  {bankName && (
                    <Badge variant="outline" className="text-[10px] ml-1">{bankName}</Badge>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="hidden sm:block w-px h-12 bg-border/50" />

          {/* 4 metrics — clean, prominent numbers */}
          <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="flex items-center gap-2.5">
              <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-2xl font-bold leading-none">{documentsProcessed}</p>
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Documents</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-2xl font-bold leading-none">{reportableIssueCount}</p>
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Issues</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="w-4 h-4 text-muted-foreground shrink-0" />
              <div>
                <p className={cn('text-2xl font-bold leading-none', complianceRate >= 80 ? 'text-emerald-400' : complianceRate >= 40 ? 'text-amber-400' : 'text-red-400')}>
                  {complianceRate}%
                </p>
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Score</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <Clock className="w-4 h-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-2xl font-bold leading-none">{processingTime}</p>
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Time</p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;
