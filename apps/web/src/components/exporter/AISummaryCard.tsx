import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, ShieldCheck, AlertTriangle } from 'lucide-react';

type RiskLevel = 'low' | 'medium' | 'high';

type AISummaryCardProps = {
  summaryText: string;
  findings: string[];
  totalIssues: number;
  riskLevel: RiskLevel;
  documentQuality: string;
  isFallback: boolean;
  aiAvailable: boolean;
};

const riskStyles: Record<RiskLevel, { label: string; badge: string }> = {
  low: { label: 'Low Risk', badge: 'bg-success/10 text-success border-success/30' },
  medium: { label: 'Moderate Risk', badge: 'bg-warning/10 text-warning border-warning/30' },
  high: { label: 'High Risk', badge: 'bg-destructive/10 text-destructive border-destructive/30' },
};

export function AISummaryCard({
  summaryText,
  findings,
  totalIssues,
  riskLevel,
  documentQuality,
  isFallback,
  aiAvailable,
}: AISummaryCardProps) {
  const risk = riskStyles[riskLevel];

  return (
    <Card className="shadow-soft border border-border/60 bg-background">
      <CardHeader className="space-y-2 pb-3">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-primary" />
          AI Summary
        </CardTitle>
        <CardDescription className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Validation assistant overview
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={`text-xs font-medium ${risk.badge}`}>{risk.label}</Badge>
          <Badge variant="outline" className="text-xs border-dashed">
            {totalIssues} {totalIssues === 1 ? 'issue' : 'issues'}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {documentQuality} docs verified
          </Badge>
          {!aiAvailable && (
            <Badge variant="outline" className="text-xs gap-1 text-muted-foreground border-muted">
              <AlertTriangle className="w-3 h-3" />
              AI disabled
            </Badge>
          )}
          {isFallback && aiAvailable && (
            <Badge variant="outline" className="text-xs gap-1 border-primary/30 text-primary">
              <ShieldCheck className="w-3 h-3" />
              Derived summary
            </Badge>
          )}
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">{summaryText}</p>
        {findings.length > 0 && (
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Top Findings</p>
            <ul className="text-sm text-foreground space-y-1 list-disc list-inside">
              {findings.slice(0, 3).map((finding, idx) => (
                <li key={`${finding}-${idx}`}>{finding}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
