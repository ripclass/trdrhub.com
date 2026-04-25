/**
 * GroupOverview — placeholder for the enterprise-tier cross-SBU rollup.
 *
 * Real implementation (aggregate KPIs across SBUs, per-SBU drilldown,
 * consolidated throughput view) deferred to a later sprint — see
 * memory/project_lcopilot_onboarding_redesign.md ("Enterprise tier features:
 * defer to next sprint. This refactor only wires the tier flag + one visible
 * affordance.")
 *
 * Reachable via the "Group overview" link in the dashboard header when the
 * user's Company.tier = 'enterprise'.
 */

import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { DashboardLayout } from '@/components/layout/DashboardLayout'

export default function GroupOverview() {
  return (
    <DashboardLayout
      sidebar={null}
      breadcrumbs={[
        { label: 'LCopilot', href: '/lcopilot' },
        { label: 'Group overview' },
      ]}
      title="Group overview"
      actions={
        <Button asChild size="sm" variant="outline">
          <Link to="/lcopilot/exporter-dashboard">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to workspace
          </Link>
        </Button>
      }
    >
      <div className="container mx-auto max-w-4xl p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Cross-SBU overview</CardTitle>
            <CardDescription>
              Aggregate view across all your strategic business units.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This will roll up throughput, discrepancy rate, open issues, and
              bank-level performance across every SBU your trade finance team
              oversees. We're shipping this in a follow-up release — ping us if
              you'd like early access.
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-md border border-dashed p-4">
                <div className="text-xs uppercase text-muted-foreground">LCs this month</div>
                <div className="pt-1 text-2xl font-semibold text-muted-foreground">—</div>
              </div>
              <div className="rounded-md border border-dashed p-4">
                <div className="text-xs uppercase text-muted-foreground">Open discrepancies</div>
                <div className="pt-1 text-2xl font-semibold text-muted-foreground">—</div>
              </div>
              <div className="rounded-md border border-dashed p-4">
                <div className="text-xs uppercase text-muted-foreground">Throughput</div>
                <div className="pt-1 text-2xl font-semibold text-muted-foreground">—</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
