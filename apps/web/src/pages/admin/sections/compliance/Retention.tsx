import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { DatabaseZap } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { RetentionSchedule } from "@/lib/admin/types";

const service = getAdminService();

export function ComplianceRetention() {
  const enabled = isAdminFeatureEnabled("compliance");
  const { toast } = useToast();
  const [schedules, setSchedules] = React.useState<RetentionSchedule[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!enabled) return;
    service
      .listRetentionSchedules()
      .then((data) => setSchedules(data))
      .finally(() => setLoading(false));
  }, [enabled]);

  const runSchedule = async (id: string, dryRun = false) => {
    setActionId(id);
    const result = await service.runRetentionSchedule(id, dryRun);
    setActionId(null);
    toast({
      title: result.success ? (dryRun ? "Dry run complete" : "Purge initiated") : "Retention run failed",
      description: result.data?.summary ?? result.message,
      variant: result.success ? "default" : "destructive",
    });
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-sky-500/40 bg-sky-500/5 p-6 text-sm text-sky-600">
        Enable the <strong>compliance</strong> flag to manage retention schedules.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Retention schedules"
        description="Automated purging of customer and system data."
      />

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DatabaseZap className="h-5 w-5 text-primary" />
            Active schedules
          </CardTitle>
          <CardDescription>Review cadence and data targets</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : schedules.length === 0 ? (
            <AdminEmptyState
              title="No retention policies"
              description="Define schedules to keep storage compliant."
            />
          ) : (
            schedules.map((schedule) => (
              <div
                key={schedule.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1 text-sm">
                  <p className="font-medium text-foreground">{schedule.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Applies to: {schedule.appliesTo.join(", ")} • Retain for {schedule.retentionDays} days
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Last run {new Date(schedule.lastRunAt).toLocaleString()} • Next run {new Date(schedule.nextRunAt).toLocaleString()}
                  </p>
                  {schedule.dryRunSummary && <p className="text-xs text-amber-600">Dry run: {schedule.dryRunSummary}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={actionId === schedule.id}
                    onClick={() => runSchedule(schedule.id, true)}
                  >
                    Dry run
                  </Button>
                  <Button
                    size="sm"
                    disabled={actionId === schedule.id}
                    onClick={() => runSchedule(schedule.id, false)}
                  >
                    Purge now
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default ComplianceRetention;
