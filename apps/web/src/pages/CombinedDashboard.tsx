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
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { useOnboarding } from "@/hooks/use-onboarding";
import { useCombined } from "@/hooks/use-combined";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { ViewModeToggle } from "@/components/combined/ViewModeToggle";
import { CombinedKPIs, type KPIData } from "@/components/combined/CombinedKPIs";
import { CombinedSessions, type Session } from "@/components/combined/CombinedSessions";
import { CombinedTasks, type Task } from "@/components/combined/CombinedTasks";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
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

// Helper to format time ago
const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

  if (diffInHours < 1) return "Just now";
  if (diffInHours < 24) return `${diffInHours}h ago`;
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays === 1) return "Yesterday";
  if (diffInDays < 7) return `${diffInDays}d ago`;
  return date.toLocaleDateString();
};

// Helper to format amount
const formatAmount = (amount: number | undefined) => {
  if (!amount) return "N/A";
  if (amount >= 1000000) return `USD ${(amount / 1000000).toFixed(1)}M`;
  if (amount >= 1000) return `USD ${(amount / 1000).toFixed(0)}K`;
  return `USD ${amount.toFixed(0)}`;
};

// Mock tasks - will be replaced with tasks API later
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
  const { user: mainUser, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  
  const currentUser = mainUser ? {
    id: mainUser.id,
    name: mainUser.full_name || mainUser.username || mainUser.email.split('@')[0],
    email: mainUser.email,
    role: 'exporter' as const,
  } : null;

  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();
  const { viewMode } = useCombined();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // Load real validation sessions
  useEffect(() => {
    const loadSessions = async () => {
      setIsLoadingSessions(true);
      try {
        const data = await getUserSessions();
        setSessions(data || []);
      } catch (error) {
        console.error("Failed to load validation sessions:", error);
        setSessions([]);
      } finally {
        setIsLoadingSessions(false);
      }
    };
    if (mainUser) {
      loadSessions();
    }
  }, [mainUser]);

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
    
    if (!authLoading && !mainUser && !demoMode) {
      navigate("/login");
    }
  }, [authLoading, mainUser, navigate]);

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

  if (authLoading) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (!mainUser) return null;

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

      // Compute KPIs from real sessions
      const completedSessions = sessions.filter(s => s.status === 'completed');
      const pendingSessions = sessions.filter(s => s.status === 'processing' || s.status === 'uploading');
      
      // For now, treat all sessions as "export" since we don't have type differentiation
      // In future, this could be based on LC type or user role
      const exportCount = sessions.length;
      const importCount = 0; // Would need importer sessions API
      
      const successfulSessions = completedSessions.filter(s => {
        const criticalCount = (s.discrepancies || []).filter(d => d.severity === 'critical').length;
        return criticalCount === 0;
      });
      
      const exportApprovalRate = completedSessions.length > 0
        ? Math.round((successfulSessions.length / completedSessions.length) * 100)
        : 0;

      // Calculate average turnaround
      const sessionsWithTime = completedSessions.filter(s => s.processing_started_at && s.processing_completed_at);
      const avgTurnaroundMs = sessionsWithTime.length > 0
        ? sessionsWithTime.reduce((sum, s) => {
            const start = new Date(s.processing_started_at!).getTime();
            const end = new Date(s.processing_completed_at!).getTime();
            return sum + (end - start);
          }, 0) / sessionsWithTime.length
        : 0;
      const avgTurnaroundDays = avgTurnaroundMs > 0 
        ? `${(avgTurnaroundMs / (1000 * 60 * 60 * 24)).toFixed(1)} days`
        : "N/A";

      const kpiData: KPIData = {
        activeLCs: {
          total: sessions.length,
          export: exportCount,
          import: importCount,
        },
        approvalRate: {
          total: exportApprovalRate,
          export: exportApprovalRate,
          import: 0, // Would need importer data
        },
        pendingActions: {
          total: pendingSessions.length,
          export: pendingSessions.length,
          import: 0,
        },
        avgTurnaround: {
          total: avgTurnaroundDays,
          export: avgTurnaroundDays,
          import: "N/A",
        },
      };

      // Transform sessions to Session[] format for CombinedSessions component
      const exportSessions: Session[] = [...sessions]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5)
        .map(s => ({
          id: s.id.slice(0, 8).toUpperCase(),
          type: 'export' as const,
          counterparty: s.extracted_data?.issuing_bank || s.extracted_data?.applicant_bank || "Bank",
          amount: formatAmount(s.extracted_data?.amount || s.extracted_data?.lc_amount),
          status: s.status === 'completed' 
            ? ((s.discrepancies?.length || 0) > 0 ? 'Discrepancy noted' : 'Ready to submit')
            : s.status === 'processing' ? 'Processing...' : 'Pending',
          updatedAt: formatTimeAgo(s.updated_at),
        }));

      // Empty for now - would need separate importer sessions API
      const importSessions: Session[] = [];

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
              data={kpiData}
              isLoading={isLoadingSessions}
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
              exportSessions={exportSessions}
              importSessions={importSessions}
              isLoading={isLoadingSessions}
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
                    <span className="font-semibold">{kpiData.approvalRate.export}%</span>
                  </div>
                  <p className="mt-1 text-xs">Based on {completedSessions.length} validations</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                  <div className="flex items-center justify-between text-foreground">
                    <span>Avg. turnaround</span>
                    <span className="font-semibold">{kpiData.avgTurnaround.export}</span>
                  </div>
                  <p className="mt-1 text-xs">Processing time per validation</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                  <div className="flex items-center justify-between text-foreground">
                    <span>Total discrepancies</span>
                    <span className="font-semibold">{sessions.reduce((sum, s) => sum + (s.discrepancies?.length || 0), 0)}</span>
                  </div>
                  <p className="mt-1 text-xs">Across all validations</p>
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
