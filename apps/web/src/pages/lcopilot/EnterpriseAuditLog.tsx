/**
 * EnterpriseAuditLog — Phase A10.
 *
 * Paged audit log with filters. Permission-gated server-side
 * (VIEW_AUDIT_LOG); the UI just hides itself for non-enterprise
 * users via the feature flag.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Filter } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { isEnterpriseTierEnabled } from "@/lib/lcopilot/featureFlags";
import { getAuditLog } from "@/lib/lcopilot/enterpriseApi";

export default function EnterpriseAuditLog() {
  const enabled = isEnterpriseTierEnabled();
  const [daysBack, setDaysBack] = useState(30);
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, error } = useQuery({
    queryKey: ["enterprise", "audit-log", daysBack, actionFilter, page, pageSize],
    queryFn: () =>
      getAuditLog({
        daysBack,
        action: actionFilter || undefined,
        page,
        pageSize,
      }),
    enabled,
  });

  if (!enabled) {
    return (
      <DashboardLayout
        sidebar={null}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Audit log" },
        ]}
      >
        <div className="container mx-auto p-6 max-w-2xl">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <p className="text-sm">
                Enterprise tier feature. Enable
                VITE_LCOPILOT_ENTERPRISE_TIER in apps/web/.env.
              </p>
              <Button asChild className="mt-4">
                <Link to="/lcopilot">Back to LCopilot</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / pageSize)) : 1;

  return (
    <DashboardLayout
      sidebar={null}
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Audit log" },
      ]}
    >
      <div className="container mx-auto p-6 space-y-4">
        <header>
          <h1 className="text-2xl font-bold">Audit log</h1>
          <p className="text-muted-foreground">
            Compliance-grade record of every action taken on your account.
          </p>
        </header>

        <Card>
          <CardContent className="grid gap-3 sm:grid-cols-4 sm:items-end py-4">
            <div className="space-y-1">
              <Label htmlFor="audit-days">Days back</Label>
              <Input
                id="audit-days"
                type="number"
                min={1}
                max={365}
                value={daysBack}
                onChange={(e) => {
                  setDaysBack(Math.max(1, Math.min(365, Number(e.target.value) || 30)));
                  setPage(1);
                }}
              />
            </div>
            <div className="space-y-1 sm:col-span-2">
              <Label htmlFor="audit-action">Action filter</Label>
              <Input
                id="audit-action"
                placeholder="e.g. validate, role_change"
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <Filter className="w-4 h-4 inline mr-1" />
              {data ? `${data.total_count} entries` : "—"}
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {(error as Error).message ?? "Failed to load audit log"}
          </div>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="py-6 text-sm text-muted-foreground">
              Loading…
            </CardContent>
          </Card>
        ) : data && data.entries.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <p className="text-sm">No audit entries match.</p>
            </CardContent>
          </Card>
        ) : (
          data && (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-muted-foreground border-b">
                    <tr>
                      <th className="px-4 py-3 font-medium">Timestamp</th>
                      <th className="px-4 py-3 font-medium">User</th>
                      <th className="px-4 py-3 font-medium">Action</th>
                      <th className="px-4 py-3 font-medium">Resource</th>
                      <th className="px-4 py-3 font-medium">IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.entries.map((e) => (
                      <tr key={e.id} className="border-t border-border">
                        <td className="px-4 py-2 text-muted-foreground tabular-nums">
                          {new Date(e.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2">
                          {e.user_email ?? (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs">
                          {e.action}
                        </td>
                        <td className="px-4 py-2 text-muted-foreground line-clamp-1 max-w-[40ch]">
                          {e.resource_type}
                          {e.resource_id ? ` · ${e.resource_id}` : ""}
                        </td>
                        <td className="px-4 py-2 text-muted-foreground tabular-nums">
                          {e.ip_address ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )
        )}

        {data && data.total_count > pageSize && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
