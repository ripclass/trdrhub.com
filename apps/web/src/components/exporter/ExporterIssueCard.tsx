import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { IssueCard } from '@/types/lcopilot';
import { AlertCircle, AlertTriangle, Info, Ban, FileWarning, Lightbulb, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

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
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Expected</p>
            <pre className="mt-1 rounded-md border border-muted bg-muted/20 p-3 font-mono text-sm leading-relaxed whitespace-pre-wrap">
              {formatValue(issue.expected)}
            </pre>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Found</p>
            <pre className="mt-1 rounded-md border border-muted bg-muted/20 p-3 font-mono text-sm leading-relaxed whitespace-pre-wrap">
              {formatValue(issue.actual)}
            </pre>
          </div>
        </div>
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
        {issue.ucpReference && (
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <span className="font-medium">UCP600 Reference:</span> {issue.ucpReference}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
