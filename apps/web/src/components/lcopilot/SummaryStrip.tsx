import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
};

const formatNumber = (value?: number | null) => (typeof value === 'number' && !Number.isNaN(value) ? value : 0);

export function SummaryStrip({ data }: Props) {
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
  
  // Calculate confidence/compliance rate
  const confidenceRate = summary.compliance_rate ?? 
    (documentsProcessed > 0 ? Math.round((verified / documentsProcessed) * 100) : 0);
  const progressValue = documentsProcessed > 0 
    ? Math.round(((verified + warnings) / documentsProcessed) * 100) 
    : 0;

  return (
    <Card className="shadow-soft border border-border/60">
      <CardContent className="p-6">
        <div className="grid gap-6 md:grid-cols-3">
          {/* Processing Summary */}
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground">Processing Summary</h3>
            <div className="space-y-2 text-sm">
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

          {/* Document Status */}
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground">Document Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                <span>{verified} documents verified</span>
              </div>
              {warnings > 0 && (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span>{warnings} with warnings</span>
                </div>
              )}
              {errors > 0 && (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-500" />
                  <span>{errors} with errors</span>
                </div>
              )}
            </div>
            <Progress value={progressValue} className="h-2" />
          </div>

          {/* Next Steps */}
          <div className="space-y-3">
            <h3 className="font-semibold text-foreground">Next Steps</h3>
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
              <>
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Ready for Submission
                </Badge>
                <p className="text-xs text-muted-foreground">
                  All documents verified successfully
                </p>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;

