import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { IssueCard } from '@/types/lcopilot';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

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

  return (
    <Card
      key={fallbackId}
      className="shadow-sm border border-border/70 bg-card transition-all duration-300 hover:shadow-lg animate-in fade-in-50"
      data-testid={`issue-card-${fallbackId}`}
    >
      <CardHeader className="space-y-2 pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg font-semibold text-foreground">{issue.title ?? 'Review Required'}</CardTitle>
          <Badge
            data-testid={`severity-${fallbackId}`}
            data-icon={normalizedSeverity}
            className={cn('gap-1 border text-xs font-semibold', severity.bg)}
          >
            <Icon className="w-3.5 h-3.5" />
            {severity.label}
          </Badge>
        </div>
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
                  {meta?.type ? `${meta.type}: ` : ''}
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
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">Suggested Fix</p>
            <p className="text-sm text-foreground">{issue.suggestion}</p>
          </div>
        )}
        {issue.ucpReference && (
          <p className="text-xs text-muted-foreground">Reference: {issue.ucpReference}</p>
        )}
      </CardContent>
    </Card>
  );
}
