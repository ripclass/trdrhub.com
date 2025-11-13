import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import {
  Upload,
  FileText,
  ShieldCheck,
  ArrowRight,
  CheckCircle,
  AlertTriangle,
  ArrowUpRight,
  Truck,
  Navigation,
} from 'lucide-react'

const dashboardStats = [
  {
    label: 'Active LCs',
    value: '12',
    helper: 'Export 7 • Import 5',
    icon: <FileText className="h-5 w-5 text-primary" />,
  },
  {
    label: 'Approval Rate',
    value: '94%',
    helper: 'Last 30 days',
    icon: <ShieldCheck className="h-5 w-5 text-success" />,
  },
  {
    label: 'Pending Actions',
    value: '4',
    helper: 'Needs review today',
    icon: <AlertTriangle className="h-5 w-5 text-amber-500" />,
  },
  {
    label: 'Average Turnaround',
    value: '2.1 days',
    helper: 'Across all banks',
    icon: <Navigation className="h-5 w-5 text-info" />,
  },
]

const exportSessions = [
  {
    id: 'EXP-2391',
    counterparty: 'BRAC Bank',
    amount: 'USD 125K',
    status: 'Ready to submit',
    updatedAt: '2 hours ago',
  },
  {
    id: 'EXP-2384',
    counterparty: 'Sonali Bank',
    amount: 'USD 210K',
    status: 'Discrepancy noted',
    updatedAt: 'Yesterday',
  },
]

const importSessions = [
  {
    id: 'IMP-1178',
    counterparty: 'HSBC Dhaka',
    amount: 'USD 90K',
    status: 'Awaiting supplier docs',
    updatedAt: 'Today',
  },
  {
    id: 'IMP-1169',
    counterparty: 'UCBL',
    amount: 'USD 140K',
    status: 'Under review',
    updatedAt: '48 mins ago',
  },
]

const quickActions = [
  {
    title: 'Validate Export LC',
    description: 'Upload LC draft or MT700 and run ICC checks.',
    to: '/export-lc-upload',
    variant: 'bg-gradient-exporter',
  },
  {
    title: 'Validate Import LC',
    description: 'Pre-screen supplier documents before shipment.',
    to: '/lcopilot/import-upload',
    variant: 'bg-gradient-importer',
  },
  {
    title: 'Request Bank Profile',
    description: 'Preview enforcement profile for partner banks.',
    to: '/lcopilot/analytics/bank',
    variant: 'bg-gradient-primary',
  },
]

export default function CombinedDashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/10 to-primary/5 p-6">
      <div className="mx-auto w-full max-w-6xl space-y-8">
        <header className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-primary">
            <Badge variant="secondary" className="bg-primary/10 text-primary">
              Unified Export & Import Workspace
            </Badge>
            <span className="text-muted-foreground">SME Tier</span>
          </div>
          <h1 className="text-3xl font-semibold text-foreground">Combined LC Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Track every export and import LC in one view. Upload documents, resolve discrepancies, and stay synchronized
            with your bank counterparts without switching workspaces.
          </p>
        </header>

        <section>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {dashboardStats.map((stat) => (
              <Card key={stat.label} className="border-border/40 shadow-soft">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardDescription className="text-xs uppercase tracking-wide text-muted-foreground">
                    {stat.label}
                  </CardDescription>
                  {stat.icon}
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="text-2xl font-semibold text-foreground">{stat.value}</div>
                  <p className="text-xs text-muted-foreground">{stat.helper}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {quickActions.map((action) => (
            <Card key={action.title} className="border-border/40 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base text-foreground">{action.title}</CardTitle>
                <CardDescription className="text-sm text-muted-foreground">
                  {action.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild variant="secondary" className={`${action.variant} hover:opacity-90 w-full text-foreground`}>
                  <Link to={action.to} className="flex items-center justify-center gap-2 text-sm font-medium">
                    Continue <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </section>

        <section className="rounded-2xl border border-border/40 bg-card/50 shadow-strong backdrop-blur">
          <Tabs defaultValue="exports" className="w-full">
            <div className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-foreground">Validation Sessions</h2>
                <p className="text-sm text-muted-foreground">
                  Export and import LC progress in one place. Filter by tab to focus faster.
                </p>
              </div>
              <TabsList className="grid w-full grid-cols-2 md:w-auto">
                <TabsTrigger value="exports">Export LCs</TabsTrigger>
                <TabsTrigger value="imports">Import LCs</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="exports" className="p-6 pt-0">
              <div className="grid gap-4 md:grid-cols-2">
                {exportSessions.map((session) => (
                  <Card key={session.id} className="border-border/40 shadow-sm transition-colors hover:border-primary/30">
                    <CardHeader className="space-y-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-semibold text-foreground">{session.id}</CardTitle>
                        <Badge variant="outline" className="text-xs text-primary">
                          Export
                        </Badge>
                      </div>
                      <CardDescription className="text-sm text-muted-foreground">
                        {session.counterparty} • {session.amount}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm text-muted-foreground">
                      <p className="flex items-center gap-2 text-foreground">
                        <CheckCircle className="h-4 w-4 text-success" /> {session.status}
                      </p>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Updated {session.updatedAt}</span>
                        <Button asChild variant="ghost" size="sm" className="h-8 px-2 text-primary">
                          <Link to={`/lcopilot/exporter-dashboard?session=${session.id}`}>Open workspace</Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="imports" className="p-6 pt-0">
              <div className="grid gap-4 md:grid-cols-2">
                {importSessions.map((session) => (
                  <Card key={session.id} className="border-border/40 shadow-sm transition-colors hover:border-primary/30">
                    <CardHeader className="space-y-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-semibold text-foreground">{session.id}</CardTitle>
                        <Badge variant="outline" className="text-xs text-info">
                          Import
                        </Badge>
                      </div>
                      <CardDescription className="text-sm text-muted-foreground">
                        {session.counterparty} • {session.amount}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm text-muted-foreground">
                      <p className="flex items-center gap-2 text-foreground">
                        <Truck className="h-4 w-4 text-info" /> {session.status}
                      </p>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Updated {session.updatedAt}</span>
                        <Button asChild variant="ghost" size="sm" className="h-8 px-2 text-primary">
                          <Link to={`/lcopilot/importer-dashboard?session=${session.id}`}>Open workspace</Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </section>

        <Separator className="opacity-20" />

        <section className="grid gap-4 md:grid-cols-3">
          <Card className="md:col-span-2 border-border/40 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Upcoming Deliverables</CardTitle>
              <CardDescription className="text-sm text-muted-foreground">
                Keep suppliers and banks aligned with a unified schedule.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="flex items-start justify-between rounded-lg border border-border/40 bg-muted/40 p-4">
                <div>
                  <p className="text-foreground font-medium">Shipment packing list upload</p>
                  <p>XYZ Trading Co. • LC EXP-2384</p>
                </div>
                <Badge variant="secondary" className="text-amber-500">
                  Due today
                </Badge>
              </div>
              <div className="flex items-start justify-between rounded-lg border border-border/40 bg-muted/20 p-4">
                <div>
                  <p className="text-foreground font-medium">Bank discrepancy resolution call</p>
                  <p>Sonali Bank • LC EXP-2384</p>
                </div>
                <Badge variant="outline">Tomorrow</Badge>
              </div>
              <div className="flex items-start justify-between rounded-lg border border-border/40 bg-muted/20 p-4">
                <div>
                  <p className="text-foreground font-medium">Supplier invoice verification</p>
                  <p>UCBL • LC IMP-1169</p>
                </div>
                <Badge variant="outline">In 3 days</Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/40 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Performance Snapshot</CardTitle>
              <CardDescription className="text-sm text-muted-foreground">
                Export vs. import comparison this quarter.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border border-border/40 bg-muted/30 p-4 text-sm text-muted-foreground">
                <div className="flex items-center justify-between text-foreground">
                  <span>Export approval</span>
                  <span className="font-semibold">96%</span>
                </div>
                <p className="mt-1 text-xs">+4.2% vs previous quarter</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                <div className="flex items-center justify-between text-foreground">
                  <span>Import approval</span>
                  <span className="font-semibold">92%</span>
                </div>
                <p className="mt-1 text-xs">+2.5% vs previous quarter</p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                <div className="flex items-center justify-between text-foreground">
                  <span>Bank escalations</span>
                  <span className="font-semibold">3</span>
                </div>
                <p className="mt-1 text-xs">Down from 7 last quarter</p>
              </div>
              <Button asChild variant="outline" className="w-full text-sm">
                <Link to="/lcopilot/analytics">Open analytics <ArrowUpRight className="ml-2 h-4 w-4" /></Link>
              </Button>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  )
}
