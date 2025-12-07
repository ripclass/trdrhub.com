import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { IssueCard } from '@/types/lcopilot';
import { AlertCircle, AlertTriangle, Info, Ban, FileWarning, Lightbulb, Sparkles, CheckCircle, Scale, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

// NOTE: UCP600 and ISBP745 descriptions are now provided by the backend
// via issue.ucpDescription and issue.isbpDescription fields.
// See: apps/api/app/constants/compliance_references.py

// Tolerance source explanations
const TOLERANCE_SOURCE_EXPLANATIONS: Record<string, { title: string; description: string; reference?: string }> = {
  'LC_SPECIFIED': {
    title: 'LC-Specified Tolerance',
    description: 'This tolerance was explicitly stated in your Letter of Credit. It takes precedence over UCP600 defaults.',
    reference: 'As per LC terms',
  },
  'UCP_DEFAULT': {
    title: 'UCP600 Article 30 Tolerance',
    description: 'Standard ±5% tolerance applies to quantity/unit price when LC uses "about" or "approximately", or when no tolerance is specified for goods sold in bulk.',
    reference: 'UCP600 Article 30(a)',
  },
  'BANK_POLICY': {
    title: 'Issuing Bank Policy',
    description: 'The issuing bank has specific tolerance policies that differ from standard UCP600. These are applied based on the bank\'s historical practices.',
    reference: 'Bank-specific',
  },
  'USER_OVERRIDE': {
    title: 'Manual Override',
    description: 'You have manually specified this tolerance. Please ensure it aligns with your LC terms.',
    reference: 'User-defined',
  },
  'INCOTERM_ADJUSTMENT': {
    title: 'Incoterms Adjustment',
    description: 'Tolerance adjusted based on the Incoterm used (CIF, FOB, etc.) which affects insurance and freight calculations.',
    reference: 'Trade practice',
  },
};

// ToleranceExplanationBadge component with hover tooltip
function ToleranceExplanationBadge({ tolerance }: { tolerance: { tolerance_percent: number; source: string; explicit?: boolean } }) {
  const sourceInfo = TOLERANCE_SOURCE_EXPLANATIONS[tolerance.source] || {
    title: 'Applied Tolerance',
    description: `A ${tolerance.tolerance_percent}% tolerance was applied to this check.`,
  };
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            variant="outline" 
            className="gap-1 text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 cursor-help"
          >
            <Scale className="w-3 h-3" />
            ±{tolerance.tolerance_percent}% tolerance
            {tolerance.explicit && <CheckCircle className="w-3 h-3 ml-0.5" />}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm p-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-emerald-500" />
              <p className="font-semibold text-sm">{sourceInfo.title}</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {sourceInfo.description}
            </p>
            {sourceInfo.reference && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                <BookOpen className="w-3 h-3" />
                {sourceInfo.reference}
              </p>
            )}
            {tolerance.explicit && (
              <p className="text-xs text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 px-2 py-1 rounded">
                ✓ Explicitly stated in LC
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Business impact mapping - what will the bank do?
const BUSINESS_IMPACT = {
  critical: {
    label: 'Will Cause Rejection',
    description: 'Bank will refuse documents',
    color: 'bg-rose-600 text-white',
    Icon: Ban,
  },
  major: {
    label: 'Likely Discrepancy',
    description: 'Bank will issue discrepancy notice',
    color: 'bg-amber-500 text-white',
    Icon: FileWarning,
  },
  medium: {
    label: 'May Cause Query',
    description: 'Bank may request clarification',
    color: 'bg-amber-400 text-amber-900',
    Icon: AlertTriangle,
  },
  minor: {
    label: 'Bank Discretion',
    description: 'Usually accepted, depends on bank',
    color: 'bg-slate-200 text-slate-700',
    Icon: Lightbulb,
  },
} as const;

const severityTokens = {
  critical: {
    label: 'Critical',
    color: '#E24A4A',
    bg: 'bg-[#E24A4A]/10 border-[#E24A4A]/30 text-[#E24A4A]',
    Icon: AlertCircle,
  },
  major: {
    label: 'Major',
    color: '#E24A4A',
    bg: 'bg-[#E24A4A]/10 border-[#E24A4A]/30 text-[#E24A4A]',
    Icon: AlertCircle,
  },
  medium: {
    label: 'Medium',
    color: '#F0A500',
    bg: 'bg-[#F0A500]/10 border-[#F0A500]/30 text-[#F0A500]',
    Icon: AlertTriangle,
  },
  minor: {
    label: 'Minor',
    color: '#6BBF59',
    bg: 'bg-[#6BBF59]/10 border-[#6BBF59]/30 text-[#2F7E2F]',
    Icon: Info,
  },
} as const;

type ExporterIssueCardProps = {
  issue: IssueCard;
  normalizedSeverity: 'critical' | 'major' | 'minor';
  documentStatusMap: Map<string, { status?: string; type?: string }>;
  fallbackId: string;
};

const formatValue = (value?: string) => {
  if (!value || value === '—') {
    return '—';
  }
  return value;
};

// Safely convert any value to string to prevent React Error #31
const safeString = (value: any): string => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'object') {
    if ('types' in value && Array.isArray(value.types)) {
      return value.types.join(', ');
    }
    return JSON.stringify(value);
  }
  return String(value);
};

export function ExporterIssueCard({
  issue,
  normalizedSeverity,
  documentStatusMap,
  fallbackId,
}: ExporterIssueCardProps) {
  const severity = severityTokens[normalizedSeverity] ?? severityTokens.minor;
  const Icon = severity.Icon;
  const documentNames = (issue.documents ?? []).filter(Boolean);

  const buildDocumentBadgeClass = (status?: string) => {
    if (status === 'success') return 'bg-success/10 text-success border-success/30';
    if (status === 'error') return 'bg-destructive/10 text-destructive border-destructive/30';
    return 'bg-warning/10 text-warning border-warning/30';
  };

  // Get business impact for this severity
  const impact = BUSINESS_IMPACT[normalizedSeverity] ?? BUSINESS_IMPACT.minor;
  const ImpactIcon = impact.Icon;
  
  // Check if this is an AI-detected issue
  const isAIDetected = 
    (issue as any).ruleset_domain === 'icc.lcopilot.ai_validation' || 
    (issue as any).auto_generated === true ||
    (issue.rule?.startsWith('AI-') ?? false);

  return (
    <Card
      key={fallbackId}
      className="shadow-sm border border-border/70 bg-card transition-all duration-300 hover:shadow-lg animate-in fade-in-50"
      data-testid={`issue-card-${fallbackId}`}
    >
      <CardHeader className="space-y-2 pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg font-semibold text-foreground">{issue.title ?? 'Review Required'}</CardTitle>
          <div className="flex items-center gap-2">
            {/* AI Detection Badge */}
            {isAIDetected && (
              <Badge
                className="gap-1 text-xs font-semibold bg-gradient-to-r from-violet-500 to-purple-600 text-white"
                title="Detected by AI Validation Engine"
              >
                <Sparkles className="w-3 h-3" />
                AI Detected
              </Badge>
            )}
            {/* Business Impact Badge - What will the bank do? */}
            <Badge
              className={cn('gap-1 text-xs font-semibold', impact.color)}
              title={impact.description}
            >
              <ImpactIcon className="w-3 h-3" />
              {impact.label}
            </Badge>
            <Badge
              data-testid={`severity-${fallbackId}`}
              data-icon={normalizedSeverity}
              className={cn('gap-1 border text-xs font-semibold', severity.bg)}
            >
              <Icon className="w-3.5 h-3.5" />
              {severity.label}
            </Badge>
          </div>
        </div>
        {issue.priority && (
          <p className="text-xs font-medium text-muted-foreground">
            Priority: {issue.priority.charAt(0).toUpperCase() + issue.priority.slice(1)}
          </p>
        )}
        {issue.description ? (
          <CardDescription className="text-sm text-muted-foreground">{issue.description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Bank Examiner Message - Professional format for banks (from V2) */}
        {(issue.ucpReference || issue.isbpReference) && (
          <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Bank Examiner Message:
            </p>
            <p className="text-sm text-slate-900 dark:text-slate-100 mt-1 font-mono">
              {issue.title}. Per {issue.ucpReference ? `UCP600 ${issue.ucpReference.replace('UCP600 Article ', 'Art. ').replace('UCP600 ', '')}` : ''}{issue.ucpReference && issue.isbpReference ? '; ' : ''}{issue.isbpReference ? `ISBP745 ${issue.isbpReference.replace('ISBP745 ', '¶')}` : ''}.
            </p>
          </div>
        )}
        
        {/* Citation Badges with Tooltips (from V2) */}
        {(issue.ucpReference || issue.isbpReference) && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <BookOpen className="h-4 w-4" />
              Regulatory Citations
            </p>
            <div className="flex flex-wrap gap-2">
              <TooltipProvider>
                {issue.ucpReference && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Badge 
                        variant="secondary" 
                        className="cursor-help bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200"
                      >
                        UCP600 {issue.ucpReference.replace('UCP600 Article ', 'Art. ').replace('UCP600 ', '')}
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="font-medium">{issue.ucpReference}</p>
                      <p className="text-xs text-slate-400">
                        {issue.ucpDescription || 'ICC Uniform Customs and Practice for Documentary Credits'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                )}
                {issue.isbpReference && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Badge 
                        variant="secondary"
                        className="cursor-help bg-purple-100 text-purple-800 hover:bg-purple-200 dark:bg-purple-900 dark:text-purple-200"
                      >
                        ISBP745 {issue.isbpReference.replace('ISBP745 ', '¶')}
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="font-medium">{issue.isbpReference}</p>
                      <p className="text-xs text-slate-400">
                        {issue.isbpDescription || 'ICC International Standard Banking Practice'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </TooltipProvider>
            </div>
          </div>
        )}
        
        {documentNames.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {documentNames.map((name) => {
              const meta = documentStatusMap.get(name);
              return (
                <Badge key={name} variant="outline" className={cn('text-xs', buildDocumentBadgeClass(meta?.status))}>
                  {meta?.type ? `${safeString(meta.type)}: ` : ''}
                  {name}
                </Badge>
              );
            })}
          </div>
        )}
        
        {/* Color-coded Expected/Found (from V2) */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
            <p className="text-xs font-medium text-green-700 dark:text-green-300 uppercase tracking-wide">Expected</p>
            <pre className="mt-1 font-mono text-sm leading-relaxed whitespace-pre-wrap text-green-900 dark:text-green-100">
              {formatValue(issue.expected)}
            </pre>
          </div>
          <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-xs font-medium text-red-700 dark:text-red-300 uppercase tracking-wide">Found</p>
            <pre className="mt-1 font-mono text-sm leading-relaxed whitespace-pre-wrap text-red-900 dark:text-red-100">
              {formatValue(issue.actual)}
            </pre>
          </div>
        </div>
        
        {/* Tolerance & Confidence Metadata */}
        {(issue.tolerance_applied || issue.extraction_confidence !== undefined) && (
          <div className="flex flex-wrap gap-2 mt-2">
            {issue.tolerance_applied && (
              <ToleranceExplanationBadge tolerance={issue.tolerance_applied} />
            )}
            {issue.extraction_confidence !== undefined && issue.extraction_confidence < 0.7 && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "gap-1 text-xs cursor-help",
                        issue.extraction_confidence < 0.5 
                          ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                          : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/30"
                      )}
                    >
                      <AlertTriangle className="w-3 h-3" />
                      OCR: {(issue.extraction_confidence * 100).toFixed(0)}%
                      {issue.extraction_confidence < 0.5 && " - Verify manually"}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="font-medium mb-1">Extraction Confidence: {(issue.extraction_confidence * 100).toFixed(0)}%</p>
                    <p className="text-xs text-muted-foreground">
                      {issue.extraction_confidence < 0.5 
                        ? "Low confidence extraction. The OCR may have misread this field. Please verify the value manually against your original document."
                        : "Medium confidence extraction. The value is likely correct but may need verification for critical fields."}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        )}
        {issue.suggestion && issue.suggestion !== '—' && (
          <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Lightbulb className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300 mb-1">
                  Suggested Solution
                </p>
                <p className="text-sm text-blue-800 dark:text-blue-200">{issue.suggestion}</p>
              </div>
            </div>
          </div>
        )}
        {/* Rule ID - shows the specific rule that triggered this issue */}
        {issue.rule && (
          <div className="text-xs text-muted-foreground pt-2 border-t border-border/50">
            <span className="font-medium">Rule:</span> {issue.rule}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
