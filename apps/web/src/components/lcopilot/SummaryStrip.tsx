import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
  lcTypeLabel?: string;
  lcTypeConfidence?: number | null;
  packGenerated?: boolean;
  overallStatus?: 'success' | 'warning' | 'error';
  actualIssuesCount?: number;
  complianceScore?: number;
};

const formatNumber = (value?: number | null) => (typeof value === 'number' && !Number.isNaN(value) ? value : 0);

export function SummaryStrip({ data, lcTypeLabel, lcTypeConfidence, packGenerated, overallStatus, actualIssuesCount, complianceScore }: Props) {
  const structured = data?.structured_result;
  const summary = structured?.processing_summary;
  const analytics = structured?.analytics;

  if (!structured || !summary) {
    return null;
  }

  // Get document counts from multiple sources for robustness
  const documentsProcessed =
    analytics?.documents_processed ?? summary.total_documents ?? data?.documents?.length ?? 0;

  // CANONICAL SOURCE: document status counts must come from the mapper's
  // canonical_document_status field (always derived from documents array).
  // Never estimate from issue counts or compliance rate — that causes drift
  // between widgets showing different numbers for the same job.
  const canonicalStatus =
    summary?.canonical_document_status ??
    summary?.document_status ??
    analytics?.document_status_distribution ??
    null;

  // If canonical status is available, use it directly (no estimation fallback)
  const verified   = formatNumber(canonicalStatus?.success);
  const warnings   = formatNumber(canonicalStatus?.warning);
  const errors     = formatNumber(canonicalStatus?.error);

  const processingTime =
    summary.processing_time_display ?? analytics?.processing_time_display ?? 'N/A';
  
  // Get issue counts - use actual count from parent if available
  const totalIssues = actualIssuesCount ?? summary.total_issues ?? summary.discrepancies ?? 0;
  // Use passed compliance score (from analyticsData, which tracks v2 scorer output)
  const complianceRate = complianceScore ?? summary.compliance_rate ?? 0;
  
  // Has issues if compliance < 100 or there are warnings/errors
  const hasIssues = complianceRate < 100 || totalIssues > 0 || warnings > 0 || errors > 0;
  
  const progressValue = documentsProcessed > 0 
    ? Math.round(((verified + warnings) / documentsProcessed) * 100) 
    : 0;

  // Status icon based on overall status prop or calculated
  const effectiveStatus = overallStatus ?? (errors > 0 ? 'error' : hasIssues ? 'warning' : 'success');
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
        <div className="flex flex-col md:flex-row gap-8 md:items-start">
          {/* Status Icon + Badges */}
          <div className="flex flex-col items-center gap-3 md:min-w-[150px]">
            {statusIcon}
            {packGenerated && (
              <Badge className="bg-emerald-600 text-white border-0 hover:bg-emerald-700">
                <CheckCircle className="w-3 h-3 mr-1" />
                Customs Pack Ready
              </Badge>
            )}
            {lcTypeLabel && (
              <div className="text-center">
                <p className="text-[10px] uppercase text-muted-foreground tracking-wide">LC TYPE</p>
                <div className="flex items-center gap-1.5 justify-center mt-1">
                  <Badge variant="secondary" className="text-xs">{lcTypeLabel}</Badge>
                  {lcTypeConfidence != null && lcTypeConfidence > 0 && (
                    <span className="text-xs text-muted-foreground">{lcTypeConfidence}%</span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="hidden md:block w-px bg-border self-stretch" />

          {/* Processing Summary */}
          <div className="flex-1 space-y-3">
            <h3 className="font-semibold text-foreground text-sm">Processing Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Documents:</span>
                <span className="font-medium">{documentsProcessed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Compliance Rate:</span>
                <span className={`font-medium ${complianceRate >= 80 ? 'text-emerald-600' : complianceRate >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                  {complianceRate}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Processing Time:</span>
                <span className="font-medium">{processingTime}</span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="hidden md:block w-px bg-border self-stretch" />

          {/* Document Status — extraction quality, not LC compliance.
               These numbers match the Documents tab and Overview stats card.
               LC compliance is shown separately as "Compliance Rate" above. */}
          <div className="flex-1 space-y-3">
            <h3 className="font-semibold text-foreground text-sm">Extraction Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>{verified} extracted OK</span>
              </div>
              {warnings > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>{warnings} partial / issues</span>
                </div>
              )}
              {errors > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span>{errors} extraction failed</span>
                </div>
              )}
              {totalIssues > 0 && (
                <div className="flex items-center gap-2 pt-1 border-t border-border/30">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <span className="text-muted-foreground">{totalIssues} LC issue{totalIssues !== 1 ? 's' : ''} found</span>
                </div>
              )}
            </div>
            <Progress value={progressValue} className="h-2" />
          </div>

          {/* Divider */}
          <div className="hidden md:block w-px bg-border self-stretch" />

          {/* Next Steps */}
          <div className="flex-1 space-y-3">
            <h3 className="font-semibold text-foreground text-sm">Next Steps</h3>
            {hasIssues ? (
              <>
                <Link to="/lcopilot/exporter-dashboard?section=upload">
                  <Button variant="outline" size="sm" className="w-full">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Fix & Re-process
                  </Button>
                </Link>
                <p className="text-xs text-muted-foreground">
                  Review warnings before bank submission
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                All documents verified successfully
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;

