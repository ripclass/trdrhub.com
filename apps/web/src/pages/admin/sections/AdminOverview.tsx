import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AdminToolbar } from "@/components/admin/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Server,
  Shield,
  Users,
} from "lucide-react";

import { useAdminAuth } from "@/lib/admin/auth";
import { getAdminService } from "@/lib/admin/services";
import type { AdminSection, KPIStat, TimeRange, AdminAuditEvent } from "@/lib/admin/types";
import { cn } from "@/lib/utils";

const RANGE_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
];

const DEFAULT_RANGE: TimeRange = "7d";

const service = getAdminService();

function KpiCard({ stat, onNavigate }: { stat: KPIStat; onNavigate: (section: AdminSection | undefined) => void }) {
  const changeColor =
    stat.changeDirection === "up" ? "text-emerald-500" : stat.changeDirection === "down" ? "text-rose-500" : "text-muted-foreground";
  const Icon = stat.icon;
  const hasLink = Boolean(stat.href);
  return (
    <button
      type="button"
      onClick={() => hasLink && onNavigate(stat.href as AdminSection | undefined)}
      className="group h-full rounded-xl border border-border/60 bg-card p-6 text-left shadow-sm transition hover:border-primary/60 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-foreground">{stat.value}</span>
            <span className={cn("flex items-center gap-1 text-xs", changeColor)}>
              {stat.changeDirection !== "flat" && <ArrowUpRight className="h-3 w-3" />}
              {stat.changeLabel}
            </span>
          </div>
        </div>
        <div className="rounded-lg bg-muted/60 p-3 text-muted-foreground group-hover:text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {stat.emphasis && <Badge className="mt-4" variant="secondary">Key metric</Badge>}
    </button>
  );
}

export function AdminOverview() {
  const { user } = useAdminAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const range = (searchParams.get("range") as TimeRange) ?? DEFAULT_RANGE;

  const [stats, setStats] = React.useState<KPIStat[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [activity, setActivity] = React.useState<AdminAuditEvent[]>([]);
  const [activityError, setActivityError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    setLoading(true);
    service
      .getDashboardStats(range)
      .then((data) => {
        if (!active) return;
        setStats(data);
        setError(null);
      })
      .catch(() => {
        if (!active) return;
        setError("Unable to load dashboard metrics");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [range]);

  React.useEffect(() => {
    service
      .listAdminAuditLog({ page: 1, pageSize: 5 })
      .then((result) => {
        setActivity(result.items);
        setActivityError(null);
      })
      .catch(() => {
        setActivity([]);
        setActivityError("Unable to load recent administrative activity");
      });
  }, []);

  const handleRangeChange = (value: TimeRange) => {
    const next = new URLSearchParams(searchParams);
    if (value === DEFAULT_RANGE) {
      next.delete("range");
    } else {
      next.set("range", value);
    }
    setSearchParams(next, { replace: true });
  };

  const handleNavigate = (section: AdminSection | undefined) => {
    if (!section) return;
    const next = new URLSearchParams(searchParams);
    if (section === "overview") {
      next.delete("section");
    } else {
      next.set("section", section);
    }
    navigate({ pathname: "/admin", search: next.toString() });
  };

  return (
    <div className="flex flex-col gap-8">
      <AdminToolbar
        title={`Welcome back, ${user?.name ?? "Admin"}`}
        description="Real-time snapshot of LCopilot operations, compliance and customer health"
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

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {loading && (
          <>
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="rounded-xl border border-border/60 bg-card p-6">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="mt-4 h-7 w-32" />
                <Skeleton className="mt-2 h-4 w-40" />
              </div>
            ))}
          </>
        )}
        {!loading && error && (
          <Card className="col-span-full border-dashed border-destructive/40 bg-destructive/5 text-destructive">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                {error}
              </CardTitle>
              <CardDescription>Retry shortly or check monitoring services.</CardDescription>
            </CardHeader>
          </Card>
        )}
        {!loading && !error && stats.map((stat) => (
          <KpiCard key={stat.id} stat={stat} onNavigate={handleNavigate} />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              System status
            </CardTitle>
            <CardDescription>Top-level signals for core platform services</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {["API Gateway", "Database", "Workflow Queue", "Storage"].map((serviceName) => (
                <div
                  key={serviceName}
                  className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/40 px-4 py-3"
                >
                  <span className="text-sm font-medium text-foreground">{serviceName}</span>
                  <span className="flex items-center gap-2 text-sm text-emerald-500">
                    <CheckCircle2 className="h-4 w-4" /> Healthy
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60">
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
            <CardDescription>Common workflows you might need today</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("security-users")}>Manage users</Button>
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("ops-jobs")}>Review jobs</Button>
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("ops-alerts")}>Open alerts</Button>
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("audit-logs")}>Audit trail</Button>
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("billing-disputes")}>Billing disputes</Button>
            <Button variant="outline" className="justify-start" onClick={() => handleNavigate("system-settings")}>System settings</Button>
          </CardContent>
        </Card>
      </section>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Recent administrative activity
          </CardTitle>
          <CardDescription>Full trail available in Audit Logs</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          {activityError && (
            <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700">
              {activityError}
            </div>
          )}
          {!activityError && activity.length === 0 && (
            <div className="rounded-lg border border-dashed border-border/60 bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
              No recent admin activity recorded.
            </div>
          )}
          {!activityError &&
            activity.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-card/60 px-4 py-3"
              >
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">
                    {entry.action}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {entry.actor}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground">
                  {entry.createdAt ? new Date(entry.createdAt).toLocaleString() : ""}
                </span>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}

