import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { LcopilotQuotaState } from '@/lib/lcopilot/quota';
import { AlertTriangle, Clock3, Lock, Sparkles } from 'lucide-react';

interface LcopilotQuotaBannerProps {
  quotaState: LcopilotQuotaState;
  variant: 'exporter' | 'importer';
}

const variantClasses = {
  exporter: 'border-exporter/20 bg-exporter/5',
  importer: 'border-importer/20 bg-importer/5',
};

export function LcopilotQuotaBanner({ quotaState, variant }: LcopilotQuotaBannerProps) {
  const isWarning = quotaState.status === 'unavailable';
  const isBlocked = quotaState.status === 'ready' && quotaState.isExhausted;
  const Icon = isBlocked ? Lock : isWarning ? Clock3 : Sparkles;
  const containerClass = isBlocked
    ? 'border-destructive/25 bg-destructive/5'
    : isWarning
    ? 'border-amber-200 bg-amber-50'
    : variantClasses[variant];

  const iconClass = isBlocked
    ? 'text-destructive'
    : isWarning
    ? 'text-amber-700'
    : variant === 'exporter'
    ? 'text-exporter'
    : 'text-importer';

  return (
    <div
      className={cn('rounded-lg border p-4', containerClass)}
      data-testid={`lcopilot-quota-banner-${variant}`}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-background/70 p-2">
            <Icon className={cn('h-4 w-4', iconClass)} />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="font-medium text-foreground">{quotaState.headline}</p>
              {isBlocked && <Badge variant="destructive">Blocked</Badge>}
              {isWarning && <Badge variant="outline">Usage sync pending</Badge>}
            </div>
            <p className="text-sm text-muted-foreground">{quotaState.detail}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isBlocked && <AlertTriangle className="h-4 w-4 text-destructive" />}
          <Button asChild size="sm" variant={isBlocked ? 'default' : 'outline'}>
            <a href={quotaState.ctaUrl}>{quotaState.ctaLabel}</a>
          </Button>
        </div>
      </div>
    </div>
  );
}
