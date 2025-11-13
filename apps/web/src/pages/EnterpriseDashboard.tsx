import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/hooks/use-auth'
import {
  Users,
  Building,
  ShieldCheck,
  GitBranch,
  ArrowRight,
  Activity,
  Layers,
  Clock,
  TrendingUp,
  FolderGit2,
} from 'lucide-react'

const workspaceMetrics = [
  { label: 'Active team members', value: '28', helper: 'Across 3 workspaces', icon: <Users className="h-5 w-5 text-primary" /> },
  { label: 'Workspaces', value: '3', helper: 'Export • Import • Finance', icon: <Layers className="h-5 w-5 text-info" /> },
  { label: 'Strict bank profiles', value: '8', helper: 'Auto applied to sessions', icon: <ShieldCheck className="h-5 w-5 text-success" /> },
  { label: 'Average processing time', value: '1.8 days', helper: 'Last 30 days', icon: <Clock className="h-5 w-5 text-muted-foreground" /> },
]

const workspaces = [
  {
    name: 'Export Operations',
    description: 'Handles pre-shipment compliance, advising and negotiation.',
    members: 12,
    openTasks: 3,
    link: '/lcopilot/exporter-dashboard',
  },
  {
    name: 'Import Compliance',
    description: 'Supplier document vetting and bank discrepancy responses.',
    members: 9,
    openTasks: 2,
    link: '/lcopilot/importer-dashboard',
  },
  {
    name: 'Finance & Treasury',
    description: 'Collections, URR 725 reimbursements and FX settlements.',
    members: 7,
    openTasks: 1,
    link: '/lcopilot/analytics',
  },
]

const teamActivity = [
  {
    id: 'ACT-232',
    role: 'Export Ops',
    description: 'Reviewed amendment request for LC #EXP-991',
    timestamp: '18 minutes ago',
  },
  {
    id: 'ACT-231',
    role: 'Treasury',
    description: 'Uploaded reimbursement authorization to BRAC Bank',
    timestamp: '2 hours ago',
  },
  {
    id: 'ACT-230',
    role: 'Import Ops',
    description: 'Flagged missing packing list for LC #IMP-776',
    timestamp: 'Yesterday',
  },
]

const strategicInsights = [
  {
    title: 'Discrepancy heat map',
    detail: 'Forwarder address mismatches are trending up for EU shipments.',
  },
  {
    title: 'Bank escalation risk',
    detail: 'Two pending Sonali Bank sessions nearing SLA breach in 24 hours.',
  },
  {
    title: 'Team workload',
    detail: 'Import workspace running at 120% capacity. Rebalance tasks.',
  },
]

export default function EnterpriseDashboard() {
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login')
    }
  }, [authLoading, user, navigate])

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Don't render dashboard if not authenticated
  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-secondary/10 p-6">
      <div className="mx-auto w-full max-w-7xl space-y-10">
        <header className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-primary">
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              Enterprise Tenant Admin
            </Badge>
            <span className="text-muted-foreground">Medium & Large Enterprises</span>
          </div>
          <h1 className="text-3xl font-semibold text-foreground">Enterprise Trade Operations</h1>
          <p className="text-sm text-muted-foreground">
            Monitor LC validation across export, import, and finance teams. Configure workspaces, assign roles, and stay
            ahead of bank escalations from a single command center.
          </p>
        </header>

        <section>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {workspaceMetrics.map((metric) => (
              <Card key={metric.label} className="border-border/40 shadow-soft">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardDescription className="text-xs uppercase tracking-wide text-muted-foreground">
                    {metric.label}
                  </CardDescription>
                  {metric.icon}
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="text-2xl font-semibold text-foreground">{metric.value}</div>
                  <p className="text-xs text-muted-foreground">{metric.helper}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 border-border/40 shadow-strong backdrop-blur">
            <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle className="text-xl text-foreground">Team Workspaces</CardTitle>
                <CardDescription className="text-sm text-muted-foreground">
                  Assign roles, monitor activity, and open workspace dashboards.
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" className="text-sm">
                Manage teams <Users className="ml-2 h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {workspaces.map((workspace) => (
                <div
                  key={workspace.name}
                  className="flex flex-col gap-4 rounded-xl border border-border/40 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p className="text-base font-semibold text-foreground">{workspace.name}</p>
                    <p>{workspace.description}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1 text-primary"><Users className="h-3.5 w-3.5" /> {workspace.members} members</span>
                      <span className="inline-flex items-center gap-1 text-amber-500"><GitBranch className="h-3.5 w-3.5" /> {workspace.openTasks} open tasks</span>
                    </div>
                  </div>
                  <Button asChild variant="secondary" className="w-full text-sm md:w-auto">
                    <Link to={workspace.link} className="flex items-center justify-center gap-2">
                      Open workspace <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-border/40 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Bank Relationship Snapshot</CardTitle>
              <CardDescription className="text-sm text-muted-foreground">
                Track LC distribution and risk across partner banks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="rounded-lg border border-border/40 bg-muted/30 p-4">
                <div className="flex items-center justify-between text-foreground">
                  <span>Sonali Bank</span>
                  <span className="font-semibold">6 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-amber-500">2 escalations approaching SLA</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4">
                <div className="flex items-center justify-between text-foreground">
                  <span>BRAC Bank</span>
                  <span className="font-semibold">4 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-success">All compliant</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4">
                <div className="flex items-center justify-between text-foreground">
                  <span>Standard Chartered</span>
                  <span className="font-semibold">3 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Awaiting document review</p>
              </div>
              <Button asChild variant="outline" className="w-full text-sm">
                <Link to="/lcopilot/analytics/bank">Open bank analytics <TrendingUp className="ml-2 h-4 w-4" /></Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        <Separator className="opacity-20" />

        <section className="grid gap-6 lg:grid-cols-3">
          <Card className="border-border/40 shadow-sm lg:col-span-2">
            <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle className="text-base text-foreground">Cross-Team Activity</CardTitle>
                <CardDescription className="text-sm text-muted-foreground">
                  Most recent updates across export, import, and finance teams.
                </CardDescription>
              </div>
              <Tabs defaultValue="activity" className="md:w-auto">
                <TabsList>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                  <TabsTrigger value="strategic">Insights</TabsTrigger>
                </TabsList>
                <TabsContent value="activity" className="pt-4">
                  <div className="space-y-3 text-sm text-muted-foreground">
                    {teamActivity.map((item) => (
                      <div key={item.id} className="flex items-center justify-between rounded-lg border border-border/40 bg-muted/30 p-4">
                        <div>
                          <p className="text-sm font-medium text-foreground">{item.description}</p>
                          <p className="text-xs text-muted-foreground">{item.role}</p>
                        </div>
                        <span className="text-xs text-muted-foreground">{item.timestamp}</span>
                      </div>
                    ))}
                  </div>
                </TabsContent>
                <TabsContent value="strategic" className="pt-4">
                  <div className="space-y-3 text-sm text-muted-foreground">
                    {strategicInsights.map((insight) => (
                      <div key={insight.title} className="rounded-lg border border-border/40 bg-muted/30 p-4">
                        <p className="text-sm font-medium text-foreground">{insight.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{insight.detail}</p>
                      </div>
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
            </CardHeader>
            <CardContent className="pt-0" />
          </Card>

          <Card className="border-border/40 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Governance & Controls</CardTitle>
              <CardDescription className="text-sm text-muted-foreground">
                Configure approval layers, retention rules, and evidence archives.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="rounded-lg border border-border/40 bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-foreground">
                  <Building className="h-4 w-4" /> Approval chains
                </div>
                <p className="mt-1 text-xs">Finance approval required above USD 200K.</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4">
                <div className="flex items-center gap-2 text-foreground">
                  <FolderGit2 className="h-4 w-4" /> Retention policies
                </div>
                <p className="mt-1 text-xs">LC evidence stored for 7 years (URC 522 compliance).</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4">
                <div className="flex items-center gap-2 text-foreground">
                  <Activity className="h-4 w-4" /> Audit log
                </div>
                <p className="mt-1 text-xs">14 key events recorded this week.</p>
              </div>
              <Button asChild variant="secondary" className="w-full text-sm">
                <Link to="/lcopilot/exporter-analytics">Review governance settings</Link>
              </Button>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  )
}
