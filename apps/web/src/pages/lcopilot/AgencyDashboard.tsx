/**
 * AgencyDashboard — placeholder shell for sourcing / buying agents.
 *
 * Empty state + portfolio table scaffold. Real build (bulk per-supplier
 * validation, re-papering workflow, agent-of-N factories view) deferred
 * until AI credits return and an explicit full-spec sign-off.
 *
 * See memory/project_lcopilot_onboarding_redesign.md for the product
 * framing. For now this satisfies the Day 4 deliverable so onboarding
 * activity=agent users land on a real page instead of a 404, and the
 * backend stub at GET /api/agency/suppliers returns [] so the empty state
 * is driven by real data rather than hardcoded.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Users } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { WorkspaceSwitcher } from '@/components/lcopilot/WorkspaceSwitcher'
import { api } from '@/api/client'

interface Supplier {
  id: string
  name: string
  country?: string
  active_lcs?: number
  open_discrepancies?: number
}

async function fetchSuppliers(): Promise<Supplier[]> {
  const res = await api.get<Supplier[]>('/agency/suppliers')
  return res.data
}

function AgencyEmptyState() {
  return (
    <Card className="border-dashed">
      <CardHeader className="items-center text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Users className="h-6 w-6 text-muted-foreground" />
        </div>
        <CardTitle>No suppliers yet</CardTitle>
        <CardDescription className="max-w-md">
          Add the factories and suppliers whose LC paperwork you manage. Each
          supplier gets its own mini-workspace — validation history, open
          discrepancies, bank submissions.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex justify-center">
        <Button disabled title="Coming soon — agency build is gated on full spec sign-off">
          <Plus className="mr-2 h-4 w-4" />
          Add supplier
        </Button>
      </CardContent>
    </Card>
  )
}

function SupplierPortfolioTable({ suppliers }: { suppliers: Supplier[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Supplier portfolio</CardTitle>
        <CardDescription>
          {suppliers.length} supplier{suppliers.length === 1 ? '' : 's'} under
          management
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">Supplier</th>
                <th className="pb-2 pr-4 font-medium">Country</th>
                <th className="pb-2 pr-4 font-medium">Active LCs</th>
                <th className="pb-2 font-medium">Open discrepancies</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id} className="border-b last:border-0">
                  <td className="py-3 pr-4 font-medium">{s.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{s.country ?? '—'}</td>
                  <td className="py-3 pr-4">{s.active_lcs ?? 0}</td>
                  <td className="py-3">{s.open_discrepancies ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default function AgencyDashboard() {
  const { data: suppliers, isLoading, error } = useQuery({
    queryKey: ['agency', 'suppliers'],
    queryFn: fetchSuppliers,
    staleTime: 5 * 60_000,
  })

  return (
    <DashboardLayout
      sidebar={null}
      breadcrumbs={[
        { label: 'LCopilot', href: '/lcopilot' },
        { label: 'Agency' },
      ]}
      title="Agency workspace"
      workspaceSwitcher={<WorkspaceSwitcher />}
      actions={
        <Button asChild size="sm" variant="outline">
          <Link to="/lcopilot/exporter-dashboard">Go to export workspace</Link>
        </Button>
      }
    >
      <div className="container mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Agency workspace</h1>
          <p className="text-sm text-muted-foreground max-w-2xl pt-1">
            Manage LC paperwork on behalf of the factories and suppliers you
            source for. This workspace is an early placeholder — full supplier
            portfolio, bulk validation, and agent re-papering land in a later
            release.
          </p>
        </div>

        {isLoading && (
          <div className="text-sm text-muted-foreground">Loading suppliers…</div>
        )}
        {error && (
          <div className="text-sm text-destructive">
            Couldn't load suppliers. Please try again.
          </div>
        )}
        {!isLoading && !error && (
          suppliers && suppliers.length > 0 ? (
            <SupplierPortfolioTable suppliers={suppliers} />
          ) : (
            <AgencyEmptyState />
          )
        )}
      </div>
    </DashboardLayout>
  )
}
