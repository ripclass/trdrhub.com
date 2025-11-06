import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { CompliancePolicyResult } from "@/lib/admin/types";

const service = getAdminService();

function StatusBadge({ status }: { status: CompliancePolicyResult["status"] }) {
  switch (status) {
    case "pass":
      return (
        <Badge className="bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/10">Pass</Badge>
      );
    case "warning":
      return (
        <Badge className="bg-amber-500/10 text-amber-600 hover:bg-amber-500/10">Warning</Badge>
      );
    case "fail":
      return <Badge className="bg-rose-500/10 text-rose-600 hover:bg-rose-500/10">Fail</Badge>;
    default:
      return <Badge variant="secondary">Unknown</Badge>;
  }
}

export function AuditCompliance() {
  const [policies, setPolicies] = React.useState<CompliancePolicyResult[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    service
      .getComplianceSummary()
      .then((data) => setPolicies(data))
      .finally(() => setLoading(false));
  }, []);

  const stats = React.useMemo(() => {
    return policies.reduce(
      (acc, policy) => {
        acc.total += 1;
        acc[policy.status] += 1;
        acc.exceptions += policy.exceptions;
        return acc;
      },
      { total: 0, pass: 0, warning: 0, fail: 0, exceptions: 0 },
    );
  }, [policies]);

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Compliance posture"
        description="Policy adherence across regulatory and security frameworks."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[{
          label: "Passing policies",
          value: stats.pass,
          icon: ShieldCheck,
          tone: "text-emerald-600",
        }, {
          label: "Warnings",
          value: stats.warning,
          icon: ShieldQuestion,
          tone: "text-amber-600",
        }, {
          label: "Failures",
          value: stats.fail,
          icon: ShieldAlert,
          tone: "text-rose-600",
        }].map(({ label, value, icon: Icon, tone }) => (
          <Card key={label} className="border-border/60">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className={`h-5 w-5 ${tone}`} />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold text-foreground">{loading ? "—" : value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Policy runs
          </CardTitle>
          <CardDescription>Latest evidence from automated compliance checks</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-20 w-full" />
              ))}
            </div>
          ) : policies.length === 0 ? (
            <AdminEmptyState
              title="No compliance data"
              description="Run a compliance check to populate this section."
            />
          ) : (
            policies.map((policy) => (
              <div
                key={policy.id}
                className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-foreground">{policy.name}</p>
                    <Badge variant="outline" className="text-xs capitalize">
                      {policy.category}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      Last run {policy.lastRunAt ? new Date(policy.lastRunAt).toLocaleString() : "—"}
                    </span>
                    <span className="text-xs text-muted-foreground">Owner: {policy.owner}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <StatusBadge status={policy.status} />
                    <span>{policy.exceptions} outstanding exception(s)</span>
                    {policy.reportUrl && (
                      <Button asChild variant="outline" size="sm">
                        <a href={policy.reportUrl} target="_blank" rel="noreferrer">
                          View evidence
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {policy.status === "fail"
                    ? "Immediate remediation required"
                    : policy.status === "warning"
                      ? "Review exceptions and document mitigation"
                      : "Compliant"}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default AuditCompliance;
