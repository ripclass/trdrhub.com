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

// UCP600 article descriptions for tooltips (from V2)
const UCP600_DESCRIPTIONS: Record<string, string> = {
  '6': 'Availability, Expiry Date and Place for Presentation',
  '6(d)': 'Documents must be presented within expiry date',
  '14': 'Standard for Examination of Documents',
  '14(a)': 'Banks must examine presentation to determine compliance on face',
  '14(b)': 'Bank has maximum 5 banking days for examination',
  '14(c)': 'Data in documents must not conflict',
  '14(d)': 'Data need not be identical but must not conflict',
  '16': 'Discrepant Documents, Waiver and Notice',
  '18': 'Commercial Invoice',
  '18(a)': 'Invoice must appear to be issued by beneficiary',
  '18(b)': 'Invoice must be made out in name of applicant',
  '18(c)': 'Description of goods must correspond with LC',
  '20': 'Bill of Lading',
  '20(a)': 'B/L requirements (carrier name, signature, dates)',
  '27': 'Clean Transport Document',
  '28': 'Insurance Document and Coverage',
  '28(b)': 'Insurance coverage must be at least 110% of CIF/CIP value',
  '29': 'Extension of Expiry Date or Period for Presentation',
  '30': 'Tolerance in Credit Amount, Quantity and Unit Prices',
};

// ISBP745 paragraph descriptions
const ISBP745_DESCRIPTIONS: Record<string, string> = {
  'A14': 'Documents must be presented within LC validity',
  'A27': 'Expiry date considerations',
  'C3': 'Invoice amount and currency',
  'E12': 'B/L requirements and clauses',
  '72': 'Goods description requirements',
  '73': 'Data linkage principle',
};

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
                        {(() => {
                          const artMatch = issue.ucpReference?.match(/Article\s*(\d+[a-z]?(?:\([a-z]\))?)/i);
                          const art = artMatch ? artMatch[1] : '';
                          return UCP600_DESCRIPTIONS[art] || 'ICC Uniform Customs and Practice for Documentary Credits';
                        })()}
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
                        {(() => {
                          const paraMatch = issue.isbpReference?.match(/([A-Z]?\d+)/);
                          const para = paraMatch ? paraMatch[1] : '';
                          return ISBP745_DESCRIPTIONS[para] || 'ICC International Standard Banking Practice';
                        })()}
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
              <Badge 
                variant="outline" 
                className="gap-1 text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
              >
                <Scale className="w-3 h-3" />
                ±{issue.tolerance_applied.tolerance_percent}% tolerance
                <span className="opacity-60">({issue.tolerance_applied.source.replace(/_/g, ' ')})</span>
              </Badge>
            )}
            {issue.extraction_confidence !== undefined && issue.extraction_confidence < 0.7 && (
              <Badge 
                variant="outline" 
                className={cn(
                  "gap-1 text-xs",
                  issue.extraction_confidence < 0.5 
                    ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                    : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/30"
                )}
              >
                <AlertTriangle className="w-3 h-3" />
                OCR: {(issue.extraction_confidence * 100).toFixed(0)}%
                {issue.extraction_confidence < 0.5 && " - Verify manually"}
              </Badge>
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
