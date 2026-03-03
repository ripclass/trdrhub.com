import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ValidationResults } from '@/types/lcopilot';
import {
  confidenceBand,
  formatConfidence,
  isFailedDocumentGuardrailCompliant,
  normalizeExtractionReason,
  toConfidenceScore,
} from '@/lib/exporter/extractionStatus';

type Props = {
  data: ValidationResults | null;
  lcTypeLabel?: string;
  lcTypeConfidence?: number | null;
  packGenerated?: boolean;
  overallStatus?: 'success' | 'warning' | 'error';
  actualIssuesCount?: number;
  complianceScore?: number;
  finalVerdict?: string | null;
  criticalIssueCount?: number;
  isReadyToSubmit?: boolean;
  onOpenDocumentDetails?: (documentId: string) => void;
};

const formatNumber = (value?: number | null) => (typeof value === 'number' && !Number.isNaN(value) ? value : 0);

export function SummaryStrip({
  data,
  lcTypeLabel,
  lcTypeConfidence,
  packGenerated,
  overallStatus,
  actualIssuesCount,
  complianceScore,
  finalVerdict,
  criticalIssueCount,
  isReadyToSubmit,
  onOpenDocumentDetails,
}: Props) {
  const structured = data?.structured_result;
  const summary = data?.summary ?? structured?.processing_summary;
  const analytics = data?.analytics ?? structured?.analytics;

  if (!summary) {
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

  const processingTime =
    summary.processing_time_display ?? analytics?.processing_time_display ?? 'N/A';

  const extractionDocs = data?.documents ?? [];
  const partialDocuments = extractionDocs.filter((doc) => (doc.status ?? '').toLowerCase() === 'warning');
  const failedDocuments = extractionDocs.filter(
    (doc) => (doc.status ?? '').toLowerCase() === 'error' && isFailedDocumentGuardrailCompliant(doc),
  );
  const verifiedCount = extractionDocs.filter((doc) => (doc.status ?? '').toLowerCase() === 'success').length;
  const warningsCount = partialDocuments.length;
  const errorsCount = failedDocuments.length;

  // Header counts must align to list lengths computed from the same filtered sets.
  const verified = verifiedCount || formatNumber(canonicalStatus?.success);
  const warnings = warningsCount;
  const errors = errorsCount;

  const pipelineVerificationStatusRaw =
    (structured as any)?.pipeline_verification_status ??
    (summary as any)?.pipeline_verification_status;
  const pipelineVerificationStatus =
    typeof pipelineVerificationStatusRaw === 'string'
      ? pipelineVerificationStatusRaw.toUpperCase()
      : null;
  const pipelineIsVerified = pipelineVerificationStatus === 'VERIFIED';
  const pipelineIsUnverified = pipelineVerificationStatus === 'UNVERIFIED';

  const pipelineFailReasons = (
    (structured as any)?.pipeline_verification_fail_reasons ??
    (summary as any)?.pipeline_verification_fail_reasons ??
    []
  ) as string[];
  const pipelineChecks = (
    (structured as any)?.pipeline_verification_checks ??
    (summary as any)?.pipeline_verification_checks ??
    []
  ) as Array<Record<string, unknown>>;
  const shortFailReasons = pipelineFailReasons.slice(0, 3);
  
  // Get issue counts - use actual count from parent if available
  const totalIssues = actualIssuesCount ?? summary.total_issues ?? summary.discrepancies ?? 0;
  // Use passed compliance score (from analyticsData, which tracks v2 scorer output)
  const complianceRate = complianceScore ?? summary.compliance_rate ?? 0;
  
  // Extraction is independent from compliance findings.
  const hasIssues = totalIssues > 0;
  const hasCriticalIssues = (criticalIssueCount ?? 0) > 0;
  const verdictReject = (finalVerdict ?? '').toUpperCase() === 'REJECT';
  const complianceOutcome: 'clean' | 'warning' | 'reject' =
    totalIssues === 0 && complianceRate >= 90
      ? 'clean'
      : complianceRate < 50 || verdictReject || hasCriticalIssues
      ? 'reject'
      : 'warning';

  const nextStep =
    verdictReject || hasCriticalIssues
      ? {
          cta: 'Resolve Critical Issues',
          to: '?tab=discrepancies',
          helper: 'Critical compliance issues must be resolved before submission.',
        }
      : hasIssues
      ? {
          cta: 'Fix & Re-process',
          to: '/lcopilot/exporter-dashboard?section=upload',
          helper: 'Review and resolve issues before reprocessing.',
        }
      : isReadyToSubmit
      ? {
          cta: 'Proceed to Bank Submission',
          to: '?tab=customs',
          helper: 'Validation is clean; proceed with final submission checks.',
        }
      : {
          cta: 'Review Before Submission',
          to: '?tab=overview',
          helper: 'Do a final review before initiating submission.',
        };

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
              <div className="space-y-1 text-center">
                <Badge className="bg-emerald-600 text-white border-0 hover:bg-emerald-700">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Customs Pack File Generated
                </Badge>
                <p className="text-[11px] text-muted-foreground max-w-[180px]">
                  File generation does not confirm bank/customs submission readiness.
                </p>
              </div>
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
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs uppercase tracking-wide text-muted-foreground">Trust Status</span>
                <Badge
                  className={pipelineIsVerified
                    ? 'bg-emerald-600 text-white border-0 hover:bg-emerald-700'
                    : pipelineIsUnverified
                    ? 'bg-amber-100 text-amber-800 border border-amber-300 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-700'
                    : 'bg-muted text-muted-foreground border border-border'}
                  title={
                    pipelineIsVerified
                      ? 'Backend verification passed'
                      : pipelineIsUnverified
                      ? 'Backend verification failed — not bank-ready'
                      : 'Pipeline verification status not provided'
                  }
                >
                  {pipelineIsVerified ? 'VERIFIED' : pipelineIsUnverified ? 'UNVERIFIED' : 'NOT PROVIDED'}
                </Badge>
                {pipelineIsUnverified && (
                  <span className="text-xs text-amber-700 dark:text-amber-300">not bank-ready</span>
                )}
              </div>
              {pipelineIsUnverified && shortFailReasons.length > 0 && (
                <div className="rounded-md border border-amber-300/70 bg-amber-50/60 dark:bg-amber-950/30 p-2">
                  <ul className="text-xs text-amber-900 dark:text-amber-100 space-y-1">
                    {shortFailReasons.map((reason, index) => (
                      <li key={`${reason}-${index}`}>• {reason}</li>
                    ))}
                  </ul>
                  {(pipelineFailReasons.length > shortFailReasons.length || pipelineChecks.length > 0) && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-[11px] text-amber-800 dark:text-amber-200">
                        View verification details
                      </summary>
                      <div className="mt-1 space-y-1 text-[11px] text-amber-900/90 dark:text-amber-100/90">
                        {pipelineFailReasons.slice(shortFailReasons.length).map((reason, index) => (
                          <p key={`extra-${index}`}>• {reason}</p>
                        ))}
                        {pipelineChecks.length > 0 && (
                          <p className="text-amber-700 dark:text-amber-300">Checks: {pipelineChecks.length}</p>
                        )}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
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
                  <span>{warnings} partial extraction</span>
                </div>
              )}
              {errors > 0 && (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span>{errors} extraction failed</span>
                </div>
              )}

              {(failedDocuments.length > 0 || partialDocuments.length > 0) && (
                <div className="pt-1 border-t border-border/30 space-y-2">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Affected Documents</p>

                  {failedDocuments.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium">Failed ({failedDocuments.length})</p>
                      {failedDocuments.map((doc) => {
                        const score = toConfidenceScore((doc.extractedFields as any)?._extraction_confidence);
                        const reason = normalizeExtractionReason(doc.failedReason);
                        return (
                          <div
                            key={`failed-${doc.id}`}
                            className="grid grid-cols-[1fr_auto_auto] gap-2 items-center text-xs rounded border border-border/50 p-2 cursor-pointer hover:bg-muted/50"
                            onClick={() => onOpenDocumentDetails?.(doc.documentId || doc.id)}
                          >
                            <div className="min-w-0">
                              <p className="truncate font-medium">{doc.name}</p>
                              <p className="text-muted-foreground truncate">{reason}</p>
                            </div>
                            <span className="text-muted-foreground">{formatConfidence(score)}</span>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={(event) => {
                                event.stopPropagation();
                                onOpenDocumentDetails?.(doc.documentId || doc.id);
                              }}
                            >
                              View details
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {partialDocuments.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium">Partial ({partialDocuments.length})</p>
                      {partialDocuments.map((doc) => {
                        const score = toConfidenceScore((doc.extractedFields as any)?._extraction_confidence);
                        const reason = normalizeExtractionReason(doc.failedReason || (confidenceBand(score) === 'Low' ? 'Low extraction confidence' : 'Missing required fields'));
                        return (
                          <div
                            key={`partial-${doc.id}`}
                            className="grid grid-cols-[1fr_auto_auto] gap-2 items-center text-xs rounded border border-border/50 p-2 cursor-pointer hover:bg-muted/50"
                            onClick={() => onOpenDocumentDetails?.(doc.documentId || doc.id)}
                          >
                            <div className="min-w-0">
                              <p className="truncate font-medium">{doc.name}</p>
                              <p className="text-muted-foreground truncate">{reason}</p>
                            </div>
                            <span className="text-muted-foreground">{formatConfidence(score)}</span>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={(event) => {
                                event.stopPropagation();
                                onOpenDocumentDetails?.(doc.documentId || doc.id);
                              }}
                            >
                              View details
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              <div className="pt-1 border-t border-border/30 space-y-1">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Compliance Outcome (Issue-Based)</p>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${complianceOutcome === 'clean' ? 'bg-emerald-500' : complianceOutcome === 'warning' ? 'bg-amber-500' : 'bg-rose-500'}`} />
                  <span className="text-muted-foreground">
                    {complianceOutcome === 'clean' ? 'Clean' : complianceOutcome === 'warning' ? 'Warning' : 'Reject'}
                    {totalIssues > 0 ? ` · ${totalIssues} issue${totalIssues !== 1 ? 's' : ''}` : ''}
                  </span>
                </div>
              </div>
            </div>
            <Progress value={progressValue} className="h-2" />
          </div>

          {/* Divider */}
          <div className="hidden md:block w-px bg-border self-stretch" />

          {/* Next Steps */}
          <div className="flex-1 space-y-3">
            <h3 className="font-semibold text-foreground text-sm">Next Steps</h3>
            <>
              <Link to={nextStep.to}>
                <Button variant="outline" size="sm" className="w-full">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  {nextStep.cta}
                </Button>
              </Link>
              <p className="text-xs text-muted-foreground">
                {nextStep.helper}
              </p>
            </>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SummaryStrip;

