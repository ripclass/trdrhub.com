import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { EnterpriseSidebar } from '@/components/enterprise/EnterpriseSidebar'
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
  FileText,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react'

type Section =
  | "dashboard"
  | "workspaces"
  | "teams"
  | "analytics"
  | "governance"
  | "notifications"
  | "settings"
  | "help"

const workspaceMetrics = [
  { label: 'Open Export LCs', value: '7', helper: '+2 from last week', icon: <FileText className="h-5 w-5 text-blue-500" />, trend: 'up' },
  { label: 'Open Import LCs', value: '5', helper: '1 pending review', icon: <FileText className="h-5 w-5 text-purple-500" />, trend: 'neutral' },
  { label: 'Pending Reviews', value: '3', helper: 'Requires attention', icon: <AlertTriangle className="h-5 w-5 text-amber-500" />, trend: 'down' },
  { label: 'Critical Discrepancies', value: '2', helper: 'SLA approaching', icon: <ShieldCheck className="h-5 w-5 text-red-500" />, trend: 'neutral' },
  { label: 'Team Members', value: '28', helper: 'Across 3 workspaces', icon: <Users className="h-5 w-5 text-primary" />, trend: 'up' },
  { label: 'Avg Processing Time', value: '1.8 days', helper: 'Last 30 days', icon: <Clock className="h-5 w-5 text-muted-foreground" />, trend: 'down' },
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
  const [activeSection, setActiveSection] = useState<Section>("dashboard")

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

  const currentUser = user
    ? {
        id: user.id,
        name: user.user_metadata?.full_name || user.email?.split("@")[0] || "User",
        email: user.email || "",
        role: user.user_metadata?.role || "tenant_admin",
      }
    : null

  return (
    <DashboardLayout
      sidebar={
        <EnterpriseSidebar
          activeSection={activeSection}
          onSectionChange={setActiveSection}
          user={currentUser}
        />
      }
    >
      <div className="p-6 lg:p-8">
        <div className="space-y-8">
          <header className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-primary/10 text-primary">
                Enterprise Tenant Admin
              </Badge>
              <span className="text-sm text-muted-foreground">Medium & Large Enterprises</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Enterprise Command Center</h1>
              <p className="text-muted-foreground mt-1">
                Monitor LC validation across export, import, and finance teams. Configure workspaces, assign roles, and stay
                ahead of bank escalations.
              </p>
            </div>
          </header>

          {/* KPI Metrics */}
          <section>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {workspaceMetrics.map((metric) => (
                <Card key={metric.label}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {metric.label}
                    </CardTitle>
                    {metric.icon}
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{metric.value}</div>
                    <p className="text-xs text-muted-foreground mt-1">{metric.helper}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          {/* Workspaces & Bank Relationships */}
          <section className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Team Workspaces</CardTitle>
                  <CardDescription className="mt-1">
                    Assign roles, monitor activity, and open workspace dashboards.
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <Users className="mr-2 h-4 w-4" />
                  Manage teams
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {workspaces.map((workspace) => (
                <div
                  key={workspace.name}
                  className="flex flex-col gap-3 rounded-lg border bg-card p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-1">
                    <p className="font-semibold">{workspace.name}</p>
                    <p className="text-sm text-muted-foreground">{workspace.description}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" /> {workspace.members} members
                      </span>
                      <span className="inline-flex items-center gap-1 text-amber-500">
                        <GitBranch className="h-3.5 w-3.5" /> {workspace.openTasks} open tasks
                      </span>
                    </div>
                  </div>
                  <Button asChild variant="secondary" size="sm" className="md:w-auto">
                    <Link to={workspace.link}>
                      Open workspace <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Bank Relationships</CardTitle>
              <CardDescription className="mt-1">
                Track LC distribution and risk across partner banks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-lg border bg-muted/30 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Sonali Bank</span>
                  <span className="text-sm font-semibold">6 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-amber-500">2 escalations approaching SLA</p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">BRAC Bank</span>
                  <span className="text-sm font-semibold">4 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-emerald-600">All compliant</p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Standard Chartered</span>
                  <span className="text-sm font-semibold">3 active LCs</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Awaiting document review</p>
              </div>
              <Button asChild variant="outline" size="sm" className="w-full">
                <Link to="/lcopilot/analytics/bank">
                  Open bank analytics <TrendingUp className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
          </section>

          <Separator className="opacity-20" />

          {/* Activity & Governance */}
          <section className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Cross-Team Activity</CardTitle>
              <CardDescription className="mt-1">
                Most recent updates across export, import, and finance teams.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="activity" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="activity">Activity Feed</TabsTrigger>
                  <TabsTrigger value="strategic">Strategic Insights</TabsTrigger>
                </TabsList>
                <TabsContent value="activity" className="space-y-3 mt-4">
                  {teamActivity.map((item) => (
                    <div key={item.id} className="flex items-start justify-between rounded-lg border bg-card p-3">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{item.description}</p>
                        <p className="text-xs text-muted-foreground">{item.role}</p>
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">{item.timestamp}</span>
                    </div>
                  ))}
                </TabsContent>
                <TabsContent value="strategic" className="space-y-3 mt-4">
                  {strategicInsights.map((insight) => (
                    <div key={insight.title} className="rounded-lg border bg-card p-3">
                      <p className="text-sm font-medium">{insight.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{insight.detail}</p>
                    </div>
                  ))}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Governance & Controls</CardTitle>
              <CardDescription className="mt-1">
                Configure approval layers, retention rules, and evidence archives.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-lg border bg-muted/30 p-3">
                <div className="flex items-center gap-2 font-medium">
                  <Building className="h-4 w-4" /> Approval chains
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Finance approval required above USD 200K.</p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center gap-2 font-medium">
                  <FolderGit2 className="h-4 w-4" /> Retention policies
                </div>
                <p className="mt-1 text-xs text-muted-foreground">LC evidence stored for 7 years (URC 522 compliance).</p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center gap-2 font-medium">
                  <Activity className="h-4 w-4" /> Audit log
                </div>
                <p className="mt-1 text-xs text-muted-foreground">14 key events recorded this week.</p>
              </div>
              <Button asChild variant="secondary" size="sm" className="w-full">
                <Link to="/lcopilot/exporter-analytics">Review governance settings</Link>
              </Button>
            </CardContent>
          </Card>
          </section>
        </div>
      </div>
    </DashboardLayout>
  )
}
