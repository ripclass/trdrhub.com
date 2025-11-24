import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ValidationResults } from '@/types/lcopilot';

type Props = {
  data: ValidationResults | null;
};

const tierStyles: Record<string, string> = {
  low: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  med: 'bg-amber-100 text-amber-700 border border-amber-200',
  high: 'bg-rose-100 text-rose-700 border border-rose-200',
};

export function RiskPanel({ data }: Props) {
  const risk = data?.structured_result?.analytics?.customs_risk;

  if (!risk) {
    return null;
  }

  const tierClass = tierStyles[risk.tier] ?? tierStyles.low;

  return (
    <Card className="shadow-soft border border-border/60">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold flex items-center justify-between">
          <span>Customs Risk Assessment</span>
          <Badge className={tierClass}>{risk.tier?.toUpperCase() ?? 'LOW'}</Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Heuristic readiness score based on Option-E LC & document coverage
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <span className="text-2xl font-bold">{risk.score ?? 0}</span>
            </div>
            <div>
              <p className="text-sm text-muted-foreground uppercase tracking-wide">Risk Score</p>
              <p className="text-base text-foreground">
                {risk.score ?? 0} / 100 &middot; {risk.tier?.toUpperCase() ?? 'LOW'}
              </p>
            </div>
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-semibold text-foreground">Flagged items</p>
          {risk.flags?.length ? (
            <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
              {risk.flags.map((flag, idx) => (
                <li key={`${flag}-${idx}`}>{flag.replace(/_/g, ' ')}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No blocking customs issues detected.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default RiskPanel;

