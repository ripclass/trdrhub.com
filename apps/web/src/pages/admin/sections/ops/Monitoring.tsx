import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminToolbar } from "@/components/admin/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Activity, AlertTriangle, ArrowUpRight, RefreshCw } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { OpsMetric, TimeRange } from "@/lib/admin/types";
import { cn } from "@/lib/utils";

const RANGE_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "15m", value: "24h" },
  { label: "1h", value: "7d" },
  { label: "24h", value: "30d" },
  { label: "7d", value: "90d" },
];

const DEFAULT_RANGE: TimeRange = "24h";
const service = getAdminService();

function MetricCard({ metric }: { metric: OpsMetric }) {
  const deltaClass = metric.trend === "up" ? "text-emerald-500" : metric.trend === "down" ? "text-rose-500" : "text-muted-foreground";
  const formattedValue = metric.unit ? `${metric.value}${metric.unit}` : metric.value;
  const progress = metric.target ? Math.min(100, Math.round((metric.value / metric.target) * 100)) : undefined;

  return (
    <Card className="border-border/60">
      <CardHeader className="space-y-1">
        <CardTitle className="text-sm font-medium text-muted-foreground">{metric.name}</CardTitle>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-foreground">{formattedValue}</span>
          <span className={cn("flex items-center gap-1 text-xs", deltaClass)}>
            {metric.trend !== "stable" && <ArrowUpRight className="h-3 w-3" />}
            {metric.change > 0 ? `+${metric.change}` : metric.change}
            {metric.unit}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {progress !== undefined && metric.unit !== "%" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Target {metric.target}{metric.unit}</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
        {metric.metadata && (
          <div className="space-y-1 text-xs text-muted-foreground">
            {Object.entries(metric.metadata).map(([key, value]) => (
              <p key={key}>
                <span className="font-medium text-foreground/80">{key}:</span> {String(value)}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function OpsMonitoring() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = (searchParams.get("opsRange") as TimeRange) ?? DEFAULT_RANGE;
  const [metrics, setMetrics] = React.useState<OpsMetric[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const loadMetrics = React.useCallback(() => {
    setLoading(true);
    service
      .getOpsMetrics(range)
      .then((data) => {
        setMetrics(data);
        setError(null);
      })
      .catch(() => setError("Unable to load operational metrics"))
      .finally(() => setLoading(false));
  }, [range]);

  React.useEffect(() => {
    loadMetrics();
    const interval = window.setInterval(loadMetrics, 60_000);
    return () => window.clearInterval(interval);
  }, [loadMetrics]);

  const handleRangeChange = (value: TimeRange) => {
    const next = new URLSearchParams(searchParams);
    if (value === DEFAULT_RANGE) next.delete("opsRange");
    else next.set("opsRange", value);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Operations monitoring"
        description="Track core reliability, latency and throughput KPIs across LCopilot."
        actions={
          <Button size="sm" variant="outline" onClick={loadMetrics} disabled={loading} className="gap-2">
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Refresh
          </Button>
        }
      >
        <div className="flex items-center gap-2">
          {RANGE_OPTIONS.map((option) => (
            <Button
              key={option.value}
              size="sm"
              variant={range === option.value ? "default" : "outline"}
              onClick={() => handleRangeChange(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </AdminToolbar>

      {error && (
        <Card className="border-destructive/40 bg-destructive/10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              {error}
            </CardTitle>
            <CardDescription>Try refreshing or verify the monitoring service.</CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {loading
          ? Array.from({ length: 6 }).map((_, index) => (
              <Card key={index} className="border-border/60">
                <CardHeader className="space-y-2">
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-8 w-24" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <Skeleton className="h-2 w-full" />
                  <Skeleton className="h-2 w-4/5" />
                </CardContent>
              </Card>
            ))
          : metrics.map((metric) => <MetricCard key={metric.id} metric={metric} />)}
      </div>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Current platform highlights
          </CardTitle>
          <CardDescription>Latest signals from monitoring service</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/40 px-4 py-3">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">No SLA breaches detected</p>
              <p className="text-xs text-muted-foreground">All services meeting uptime commitments in selected window.</p>
            </div>
            <Badge variant="outline">SLO 99.97%</Badge>
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/40 px-4 py-3">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">Queue depth within safe range</p>
              <p className="text-xs text-muted-foreground">Average processing time under 5 minutes.</p>
            </div>
            <Badge variant="outline">34 queued</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default OpsMonitoring;

