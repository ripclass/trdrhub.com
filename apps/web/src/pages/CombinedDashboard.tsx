import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import { useExporterAuth } from "@/lib/exporter/auth";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { useOnboarding } from "@/hooks/use-onboarding";
import { useCombined } from "@/hooks/use-combined";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { ViewModeToggle } from "@/components/combined/ViewModeToggle";
import { CombinedKPIs, type KPIData } from "@/components/combined/CombinedKPIs";
import { CombinedSessions, type Session } from "@/components/combined/CombinedSessions";
import { CombinedTasks, type Task } from "@/components/combined/CombinedTasks";
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
  Link as LinkIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

type Section =
  | "dashboard"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "billing"
  | "settings"
  | "help";

// Mock data - will be replaced with API calls in Phase 2
const mockKPIData: KPIData = {
  activeLCs: {
    total: 12,
    export: 7,
    import: 5,
  },
  approvalRate: {
    total: 94,
    export: 96,
    import: 92,
  },
  pendingActions: {
    total: 4,
    export: 2,
    import: 2,
  },
  avgTurnaround: {
    total: '2.1 days',
    export: '1.8 days',
    import: '2.5 days',
  },
};

const mockExportSessions: Session[] = [
  {
    id: 'EXP-2391',
    type: 'export',
    counterparty: 'BRAC Bank',
    amount: 'USD 125K',
    status: 'Ready to submit',
    updatedAt: '2 hours ago',
  },
  {
    id: 'EXP-2384',
    type: 'export',
    counterparty: 'Sonali Bank',
    amount: 'USD 210K',
    status: 'Discrepancy noted',
    updatedAt: 'Yesterday',
  },
];

const mockImportSessions: Session[] = [
  {
    id: 'IMP-1178',
    type: 'import',
    counterparty: 'HSBC Dhaka',
    amount: 'USD 90K',
    status: 'Awaiting supplier docs',
    updatedAt: 'Today',
  },
  {
    id: 'IMP-1169',
    type: 'import',
    counterparty: 'UCBL',
    amount: 'USD 140K',
    status: 'Under review',
    updatedAt: '48 mins ago',
  },
];

const mockTasks: Task[] = [
  {
    id: 'task-1',
    type: 'export',
    title: 'Shipment packing list upload',
    description: 'XYZ Trading Co.',
    lcNumber: 'EXP-2384',
    dueDate: new Date().toISOString().split('T')[0], // Today
    priority: 'high',
    status: 'pending',
  },
  {
    id: 'task-2',
    type: 'export',
    title: 'Bank discrepancy resolution call',
    description: 'Sonali Bank',
    lcNumber: 'EXP-2384',
    dueDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Tomorrow
    priority: 'medium',
    status: 'pending',
  },
  {
    id: 'task-3',
    type: 'import',
    title: 'Supplier invoice verification',
    description: 'UCBL',
    lcNumber: 'IMP-1169',
    dueDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // In 3 days
    priority: 'medium',
    status: 'pending',
  },
];

const getQuickActions = (viewMode: "export" | "import" | "all") => {
  const baseActions = [
    {
      title: 'Validate Export LC',
      description: 'Upload LC draft or MT700 and run ICC checks.',
      to: '/lcopilot/exporter-dashboard?section=upload',
      variant: 'bg-gradient-exporter',
      type: 'export' as const,
    },
    {
      title: 'Validate Import LC',
      description: 'Pre-screen supplier documents before shipment.',
      to: '/lcopilot/importer-dashboard?section=upload',
      variant: 'bg-gradient-importer',
      type: 'import' as const,
    },
    {
      title: 'Request Bank Profile',
      description: 'Preview enforcement profile for partner banks.',
      to: '/lcopilot/exporter-dashboard?section=analytics',
      variant: 'bg-gradient-primary',
      type: 'both' as const,
    },
  ];

  if (viewMode === "export") {
    return baseActions.filter(a => a.type === "export" || a.type === "both");
  } else if (viewMode === "import") {
    return baseActions.filter(a => a.type === "import" || a.type === "both");
  }

  return baseActions;
};

export default function CombinedDashboard() {
  const { toast } = useToast();
  const { user: mainUser } = useAuth();
  const { user: exporterUser, isAuthenticated, isLoading: authLoading } = useExporterAuth();
  const navigate = useNavigate();
  
  const currentUser = mainUser ? {
    id: mainUser.id,
    name: mainUser.full_name || mainUser.username || mainUser.email.split('@')[0],
    email: mainUser.email,
    role: 'exporter' as const,
  } : exporterUser;

  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();
  const { viewMode } = useCombined();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showOnboarding, setShowOnboarding] = useState(false);

  const parseSection = (value: string | null): Section => {
    const allowed: Section[] = [
      "dashboard",
      "workspace",
      "templates",
      "upload",
      "reviews",
      "analytics",
      "notifications",
      "billing",
      "settings",
      "help",
    ];
    return allowed.includes(value as Section) ? (value as Section) : "dashboard";
  };

  const [activeSection, setActiveSection] = useState<Section>(() => parseSection(searchParams.get("section")));

  useEffect(() => {
    const demoMode = localStorage.getItem('demo_mode') === 'true' || 
                    new URLSearchParams(window.location.search).get('demo') === 'true';
    
    const hasAuth = mainUser || (isAuthenticated && !authLoading);
    
    if (!authLoading && !hasAuth && !demoMode) {
      navigate("/login");
    }
  }, [isAuthenticated, authLoading, mainUser, navigate]);

  useEffect(() => {
    if (!isLoadingOnboarding && needsOnboarding) {
      setShowOnboarding(true);
    }
  }, [needsOnboarding, isLoadingOnboarding]);

  useEffect(() => {
    const current = parseSection(searchParams.get("section"));
    if (current !== activeSection) {
      setActiveSection(current);
    }
  }, [searchParams]);

  const handleSectionChange = (section: Section) => {
    setActiveSection(section);
    setSearchParams({ section });
  };

  if (authLoading && !mainUser) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (!mainUser && (!isAuthenticated || authLoading)) return null;

  const handleKpiClick = (kpi: string, mode?: typeof viewMode) => {
    // Telemetry: Log KPI click
    console.log("📊 KPI clicked:", { kpi, mode, viewMode });
    // Could apply filters based on KPI clicked
    // For now, just log for telemetry
  };

  const handleSessionClick = (session: Session) => {
    // Telemetry: Log session click
    console.log("📋 Session clicked:", { sessionId: session.id, type: session.type });
  };

  const handleQuickActionClick = (action: { title: string; to: string; type: string }) => {
    // Telemetry: Log quick action click
    console.log("⚡ Quick action clicked:", { action: action.title, destination: action.to });
  };

  const renderContent = () => {
    if (activeSection === "dashboard") {
      const quickActions = getQuickActions(viewMode);
      const exportTasks = mockTasks.filter(t => t.type === "export");
      const importTasks = mockTasks.filter(t => t.type === "import");

      return (
        <div className="space-y-8">
          <header className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-primary/10 text-primary">
                Unified Export & Import Workspace
              </Badge>
              <span className="text-sm text-muted-foreground">SME Tier</span>
            </div>
            <h1 className="text-3xl font-semibold text-foreground">Welcome back, {currentUser?.name || "User"}!</h1>
            <p className="text-sm text-muted-foreground">
              Track every export and import LC in one view. Upload documents, resolve discrepancies, and stay synchronized
              with your bank counterparts without switching workspaces.
            </p>
          </header>

          {/* KPI Section */}
          <section>
            <CombinedKPIs
              data={mockKPIData}
              isLoading={false}
              onKpiClick={handleKpiClick}
            />
          </section>

          {/* Quick Actions Section */}
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
                  <Button
                    asChild
                    variant="secondary"
                    className={`${action.variant} hover:opacity-90 w-full text-foreground`}
                    onClick={() => handleQuickActionClick(action)}
                  >
                    <Link to={action.to} className="flex items-center justify-center gap-2 text-sm font-medium">
                      Continue <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </section>

          {/* Sessions Section */}
          <section>
            <CombinedSessions
              exportSessions={mockExportSessions}
              importSessions={mockImportSessions}
              isLoading={false}
              onSessionClick={handleSessionClick}
            />
          </section>

          <Separator className="opacity-20" />

          {/* Tasks and Performance Section */}
          <section className="grid gap-4 md:grid-cols-3">
            <CombinedTasks
              exportTasks={exportTasks}
              importTasks={importTasks}
              isLoading={false}
              maxItems={5}
            />

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
                    <span className="font-semibold">{mockKPIData.approvalRate.export}%</span>
                  </div>
                  <p className="mt-1 text-xs">+4.2% vs previous quarter</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                  <div className="flex items-center justify-between text-foreground">
                    <span>Import approval</span>
                    <span className="font-semibold">{mockKPIData.approvalRate.import}%</span>
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
                  <Link to="/lcopilot/exporter-dashboard?section=analytics">Open analytics <ArrowUpRight className="ml-2 h-4 w-4" /></Link>
                </Button>
              </CardContent>
            </Card>
          </section>
        </div>
      );
    }

    // Placeholder for other sections
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="p-8 text-center">
          <CardTitle className="mb-4">Section: {activeSection}</CardTitle>
          <CardDescription>
            This section is under development for the Combined Dashboard.
            <br />
            Use the sidebar to navigate to Export or Import dashboards for full functionality.
          </CardDescription>
          <div className="mt-6 flex gap-4 justify-center">
            <Button asChild variant="outline">
              <Link to="/lcopilot/exporter-dashboard">Go to Export Dashboard</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/lcopilot/importer-dashboard">Go to Import Dashboard</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  };

  return (
    <>
      <DashboardLayout
        sidebar={
          <ExporterSidebar
            activeSection={activeSection}
            onSectionChange={handleSectionChange}
            user={currentUser}
          />
        }
        topbar={
          activeSection === "dashboard" ? (
            <ViewModeToggle showAll={true} />
          ) : undefined
        }
      >
        <div className="p-6">
          {renderContent()}
        </div>
      </DashboardLayout>

      <OnboardingWizard
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={() => {
          setShowOnboarding(false);
          toast({
            title: "Onboarding complete",
            description: "You're all set to start validating documents.",
          });
        }}
      />
    </>
  );
}
