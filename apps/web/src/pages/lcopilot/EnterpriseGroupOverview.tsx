/**
 * EnterpriseGroupOverview — Phase A10.
 *
 * One-page rollup of every activity the enterprise company is
 * running: validations, suppliers, buyers, services clients,
 * unbilled hours. Drill-in links into each persona dashboard.
 */

import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Briefcase,
  Building2,
  Clock,
  Globe2,
  Mailbox,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { isEnterpriseTierEnabled } from "@/lib/lcopilot/featureFlags";
import { getGroupOverview } from "@/lib/lcopilot/enterpriseApi";

function KpiCard({
  label,
  value,
  Icon,
  hint,
  to,
}: {
  label: string;
  value: number | string;
  Icon: typeof BarChart3;
  hint?: string;
  to?: string;
}) {
  const inner = (
    <Card className="hover:shadow transition-shadow">
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardDescription>{label}</CardDescription>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
        {hint && (
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        )}
      </CardContent>
    </Card>
  );
  if (to) {
    return (
      <Link to={to} className="block">
        {inner}
      </Link>
    );
  }
  return inner;
}

export default function EnterpriseGroupOverview() {
  const enabled = isEnterpriseTierEnabled();
  const { data, isLoading, error } = useQuery({
    queryKey: ["enterprise", "group-overview"],
    queryFn: getGroupOverview,
    enabled,
  });

  if (!enabled) {
    return (
      <DashboardLayout
        sidebar={null}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Group overview" },
        ]}
      >
        <div className="container mx-auto p-6 max-w-2xl">
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                Enterprise tier features are gated behind
                VITE_LCOPILOT_ENTERPRISE_TIER. Enable it in apps/web/.env.
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

  return (
    <DashboardLayout
      sidebar={null}
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Group overview" },
      ]}
    >
      <div className="container mx-auto p-6 space-y-6">
        <header>
          <h1 className="text-2xl font-bold">Group overview</h1>
          <p className="text-muted-foreground">
            Every activity your company is running, on one page.
          </p>
        </header>

        {error && (
          <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {(error as Error).message ?? "Failed to load overview"}
          </div>
        )}

        {isLoading && (
          <Card>
            <CardContent className="py-6 text-sm text-muted-foreground">
              Loading…
            </CardContent>
          </Card>
        )}

        {data && (
          <>
            <section className="grid gap-4 md:grid-cols-4">
              <KpiCard
                label="Total validations"
                value={data.total_validations}
                Icon={Activity}
              />
              <KpiCard
                label="Active LCs"
                value={data.active_lcs}
                Icon={Users}
                hint="Not paid / closed / expired"
              />
              <KpiCard
                label="Open discrepancies"
                value={data.open_discrepancies}
                Icon={AlertTriangle}
              />
              <KpiCard
                label="Open re-paper"
                value={data.open_repaper_requests}
                Icon={Mailbox}
                to="/lcopilot/agency-dashboard"
              />
            </section>

            <section>
              <h2 className="text-lg font-semibold mb-3">
                Activities ({data.activities.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-3">
                <KpiCard
                  label={data.suppliers.label}
                  value={data.suppliers.count}
                  Icon={Building2}
                  hint={data.suppliers.description ?? undefined}
                  to="/lcopilot/agency-dashboard"
                />
                <KpiCard
                  label={data.foreign_buyers.label}
                  value={data.foreign_buyers.count}
                  Icon={Globe2}
                  hint={data.foreign_buyers.description ?? undefined}
                  to="/lcopilot/agency-dashboard"
                />
                <KpiCard
                  label={data.services_clients.label}
                  value={data.services_clients.count}
                  Icon={Briefcase}
                  hint={data.services_clients.description ?? undefined}
                  to="/lcopilot/services-dashboard"
                />
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              <KpiCard
                label="Unbilled hours"
                value={Number(data.billable_unbilled_hours).toFixed(2)}
                Icon={Clock}
                hint="Billable, not yet invoiced"
                to="/lcopilot/services-dashboard"
              />
              <KpiCard
                label="Active members"
                value={data.members_active}
                Icon={Users}
                hint="With access to this company"
              />
              <KpiCard
                label="Generated"
                value={new Date(data.generated_at).toLocaleString()}
                Icon={Activity}
              />
            </section>

            <div className="flex items-center gap-2">
              <Button asChild variant="outline">
                <Link to="/lcopilot/audit-log">View audit log</Link>
              </Button>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
