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
};

const formatNumber = (value?: number | null) => (typeof value === 'number' && !Number.isNaN(value) ? value : 0);

export function SummaryStrip({ data, lcTypeLabel, lcTypeConfidence, packGenerated, overallStatus }: Props) {
  const structured = data?.structured_result;
  const summary = structured?.processing_summary;
  const analytics = structured?.analytics;

  if (!structured || !summary) {
    return null;
  }

  const documentsProcessed =
    analytics?.documents_processed ?? summary.total_documents ?? data?.documents?.length ?? 0;
  const statusDistribution = analytics?.document_status_distribution ?? {};
  const processingTime =
    summary.processing_time_display ?? analytics?.processing_time_display ?? 'N/A';
  
  const verified = formatNumber(statusDistribution.success);
  const warnings = formatNumber(statusDistribution.warning);
  const errors = formatNumber(statusDistribution.error);
  const hasIssues = warnings > 0 || errors > 0;
  
  // Calculate confidence rate
  const confidenceRate = summary.compliance_rate ?? 
    (documentsProcessed > 0 ? Math.round((verified / documentsProcessed) * 100) : 0);
  const progressValue = documentsProcessed > 0 
    ? Math.round(((verified + warnings) / documentsProcessed) * 100) 
    : 0;

  // Status icon and color
  const statusIcon = overallStatus === 'success' ? (
    <CheckCircle className="w-12 h-12 text-emerald-500" />
  ) : overallStatus === 'error' ? (
    <AlertTriangle className="w-12 h-12 text-rose-500" />
  ) : (
    <AlertTriangle className="w-12 h-12 text-amber-500" />
  );

  return (
    <Card className="shadow-soft border border-border/60">
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row gap-6 md:items-start">
          {/* Status Icon + Badges */}
          <div className="flex flex-col items-center gap-3 md:min-w-[140px]">
            {statusIcon}
            {packGenerated && (
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-700">
                <CheckCircle className="w-3 h-3 mr-1" />
                Customs Pack Ready
              </Badge>
            )}
            {lcTypeLabel && (
              <div className="text-center">
                <p className="text-[10px] uppercase text-muted-foreground tracking-wide">LC TYPE</p>
                <div className="flex items-center gap-1.5 justify-center">
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
          <div className="flex-1 space-y-2">
            <h3 className="font-semibold text-foreground text-sm">Processing Summary</h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Documents:</span>
                <span className="font-medium">{documentsProcessed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence:</span>
                <span className={`font-medium ${confidenceRate >= 80 ? 'text-emerald-600' : confidenceRate >= 50 ? 'text-amber-600' : 'text-rose-600'}`}>
                  {confidenceRate}%
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

          {/* Document Status */}
          <div className="flex-1 space-y-2">
            <h3 className="font-semibold text-foreground text-sm">Document Status</h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>{verified} documents verified</span>
              </div>
              {warnings > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>{warnings} with warnings</span>
                </div>
              )}
              {errors > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span>{errors} with errors</span>
                </div>
              )}
            </div>
            <Progress value={progressValue} className="h-2" />
          </div>

          {/* Divider */}
          <div className="hidden md:block w-px bg-border self-stretch" />

          {/* Next Steps */}
          <div className="flex-1 space-y-2">
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

