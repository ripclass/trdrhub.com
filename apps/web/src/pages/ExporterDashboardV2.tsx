import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import { useToast } from "@/hooks/use-toast";
import { useDrafts, type DraftData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { useExporterAuth } from "@/lib/exporter/auth";
import ExportLCUpload from "./ExportLCUpload";
import ExporterAnalytics from "./ExporterAnalytics";
import ExporterResults from "./ExporterResults";
import { LCWorkspaceView } from "./sme/LCWorkspace";
import { TemplatesView } from "./sme/Templates";
import { DataRetentionView } from "./settings/DataRetention";
import { CompanyProfileView } from "./settings/CompanyProfile";
import { AIAssistance } from "@/components/sme/AIAssistance";
import { ContentLibrary } from "@/components/sme/ContentLibrary";
import { ShipmentTimeline } from "@/components/sme/ShipmentTimeline";
import { BillingOverviewPage } from "./BillingOverviewPage";
import { BillingUsagePage } from "./BillingUsagePage";
import { BillingInvoicesPage } from "./BillingInvoicesPage";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  Bell,
  BarChart3,
  TrendingUp,
  Clock,
  Edit3,
  Trash2,
  ArrowRight,
  GitBranch,
} from "lucide-react";
import { NotificationList, type Notification } from "@/components/notifications/NotificationItem";
import { useUsageStats, useInvoices } from "@/hooks/useBilling";
import { InvoiceStatus } from "@/types/billing";
import { CreditCard } from "lucide-react";

type Section =
  | "dashboard"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "billing"
  | "billing-usage"
  | "ai-assistance"
  | "content-library"
  | "shipment-timeline"
  | "settings"
  | "help";

const dashboardStats = {
  thisMonth: 6,
  successRate: 91.7,
  avgProcessingTime: "2.8 minutes",
  discrepanciesFound: 3,
  totalReviews: 18,
  documentsProcessed: 54,
};

const mockHistory = [
  {
    id: "1",
    date: "2024-01-18",
    type: "LC Review",
    supplier: "ABC Exports Ltd.",
    status: "approved" as const,
    risks: 2,
  },
  {
    id: "2",
    date: "2024-01-12",
    type: "Document Check",
    supplier: "XYZ Trading Co.",
    status: "flagged" as const,
    risks: 4,
  },
  {
    id: "3",
    date: "2024-01-08",
    type: "LC Review",
    supplier: "Global Textiles Inc.",
    status: "approved" as const,
    risks: 1,
  },
];

const notifications: Notification[] = [
  {
    id: 1,
    title: "Export Regulations Update",
    message: "New customs requirements effective Feb 1st. Review your upcoming shipments.",
    type: "info",
    timestamp: "2 hours ago",
    read: false,
    link: "/lcopilot/exporter-dashboard?section=settings",
    action: {
      label: "Review Settings",
      action: () => {},
    },
  },
  {
    id: 2,
    title: "LC Review Complete",
    message: "Your draft LC has been reviewed with no critical risks identified.",
    type: "success",
    timestamp: "5 hours ago",
    read: false,
    link: "/lcopilot/exporter-dashboard?section=reviews",
    action: {
      label: "View Results",
      action: () => {},
    },
  },
  {
    id: 3,
    title: "Discrepancy Found",
    message: "Bank identified discrepancies in LC-EXP-2024-005. Action required.",
    type: "discrepancy",
    timestamp: "1 day ago",
    read: false,
    link: "/lcopilot/exporter-dashboard?section=reviews&lc=LC-EXP-2024-005",
    badge: "Urgent",
    action: {
      label: "Review Discrepancy",
      action: () => {},
      variant: "destructive",
    },
  },
];

export default function ExporterDashboardV2() {
  const { toast } = useToast();
  const { user: exporterUser, isAuthenticated, isLoading: authLoading } = useExporterAuth();
  const navigate = useNavigate();
  const { getAllDrafts, removeDraft } = useDrafts();
  const { getAllAmendedLCs } = useVersions();
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();
  const [searchParams, setSearchParams] = useSearchParams();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/lcopilot/exporter-dashboard/login");
    }
  }, [isAuthenticated, authLoading, navigate]);

  const [drafts, setDrafts] = useState<DraftData[]>([]);
  const [isLoadingDrafts, setIsLoadingDrafts] = useState(false);
  const [amendedLCs, setAmendedLCs] = useState<
    Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>
  >([]);
  const [isLoadingAmendments, setIsLoadingAmendments] = useState(false);
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
      "billing-usage",
      "settings",
      "help",
    ];
    return allowed.includes(value as Section) ? (value as Section) : "dashboard";
  };

  const [activeSection, setActiveSection] = useState<Section>(() => parseSection(searchParams.get("section")));
  const [workspaceTab, setWorkspaceTab] = useState("drafts");
  const [billingTab, setBillingTab] = useState<string>("overview");

  useEffect(() => {
    const loadDrafts = () => {
      setIsLoadingDrafts(true);
      try {
        const exporterDrafts = getAllDrafts();
        setDrafts(exporterDrafts.filter((draft) => draft.type === "export"));
      } catch (error) {
        console.error("Failed to load drafts:", error);
      } finally {
        setIsLoadingDrafts(false);
      }
    };

    loadDrafts();
  }, [getAllDrafts]);

  useEffect(() => {
    const loadAmendedLCs = async () => {
      setIsLoadingAmendments(true);
      try {
        const amended = await getAllAmendedLCs();
        setAmendedLCs(amended);
      } catch (error) {
        console.error("Failed to load amended LCs:", error);
      } finally {
        setIsLoadingAmendments(false);
      }
    };

    loadAmendedLCs();
  }, [getAllAmendedLCs]);

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

  const handleSectionChange = (section: Section, extras: Record<string, string | undefined> = {}) => {
    setActiveSection(section);

    const next = new URLSearchParams(searchParams);

    if (section === "dashboard") {
      next.delete("section");
    } else {
      next.set("section", section);
    }

    if (section !== "upload") {
      next.delete("draftId");
    }

    if (section !== "reviews") {
      next.delete("jobId");
      next.delete("lc");
    }

    Object.entries(extras).forEach(([key, value]) => {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    });

    setSearchParams(next, { replace: true });
  };

  const handleBillingTabChange = (tab: string) => {
    setBillingTab(tab);
    const sectionMap: Record<string, Section> = {
      overview: "billing",
      usage: "billing-usage",
      invoices: "billing", // Stay in billing section, but track tab
    };
    const section = sectionMap[tab] || "billing";
    handleSectionChange(section);
  };

  const handleResumeDraft = (draft: DraftData) => {
    setWorkspaceTab("drafts");
    handleSectionChange("upload", { draftId: draft.id });
  };

  const handleDeleteDraft = (draftId: string) => {
    try {
      removeDraft(draftId);
      setDrafts((prev) => prev.filter((draft) => draft.id !== draftId));
      toast({
        title: "Draft deleted",
        description: "The saved draft has been removed successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Failed to delete draft",
        description: error?.message || "Please try again.",
        variant: "destructive",
      });
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) return "Just now";
    if (diffInHours < 24) return `${diffInHours}h ago`;

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;

    return date.toLocaleDateString();
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated (handled by useEffect, but show nothing while redirecting)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <DashboardLayout
        sidebar={<ExporterSidebar activeSection={activeSection} onSectionChange={handleSectionChange} />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Exporter Dashboard" },
        ]}
      >
        <div className="flex flex-1 flex-col gap-6 p-6 lg:p-8">
          {activeSection === "dashboard" && (
            <DashboardOverview
              stats={dashboardStats}
              drafts={drafts}
              amendedLCs={amendedLCs}
              isLoadingDrafts={isLoadingDrafts}
              isLoadingAmendments={isLoadingAmendments}
              onResumeDraft={handleResumeDraft}
              onDeleteDraft={handleDeleteDraft}
              formatTimeAgo={formatTimeAgo}
              recentHistory={mockHistory}
              workspaceTab={workspaceTab}
              onWorkspaceTabChange={setWorkspaceTab}
            />
          )}

          {activeSection === "workspace" && <LCWorkspaceView embedded />}

          {activeSection === "templates" && <TemplatesView embedded />}

          {activeSection === "upload" && (
            <ExportLCUpload
              embedded
              onComplete={({ jobId, lcNumber }) => {
                handleSectionChange("reviews", {
                  jobId,
                  lc: lcNumber || undefined,
                });
              }}
            />
          )}

          {activeSection === "reviews" && (
            <ExporterResults embedded />
          )}

          {activeSection === "analytics" && (
            <ExporterAnalytics embedded />
          )}

          {activeSection === "notifications" && <NotificationsCard notifications={notifications} />}

          {activeSection === "billing" && (
            billingTab === "invoices" ? (
              <BillingInvoicesPage onTabChange={handleBillingTabChange} />
            ) : (
              <BillingOverviewPage onTabChange={handleBillingTabChange} />
            )
          )}

          {activeSection === "billing-usage" && <BillingUsagePage onTabChange={handleBillingTabChange} />}

          {activeSection === "ai-assistance" && <AIAssistance embedded />}
          {activeSection === "content-library" && <ContentLibrary embedded />}
          {activeSection === "shipment-timeline" && <ShipmentTimeline embedded />}

          {activeSection === "settings" && <SettingsPanel />}

          {activeSection === "help" && <HelpPanel />}
        </div>
      </DashboardLayout>

      <OnboardingWizard
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={() => {
          setShowOnboarding(false);
          toast({
            title: "Onboarding complete",
            description: "You’re all set to start validating documents.",
          });
        }}
      />
    </>
  );
}

interface DashboardOverviewProps {
  stats: typeof dashboardStats;
  drafts: DraftData[];
  amendedLCs: Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>;
  isLoadingDrafts: boolean;
  isLoadingAmendments: boolean;
  onResumeDraft: (draft: DraftData) => void;
  onDeleteDraft: (draftId: string) => void;
  formatTimeAgo: (date: string) => string;
  recentHistory: typeof mockHistory;
  workspaceTab: string;
  onWorkspaceTabChange: (value: string) => void;
}

function DashboardOverview({
  stats,
  drafts,
  amendedLCs,
  isLoadingDrafts,
  isLoadingAmendments,
  onResumeDraft,
  onDeleteDraft,
  formatTimeAgo,
  recentHistory,
  workspaceTab,
  onWorkspaceTabChange,
}: DashboardOverviewProps) {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Welcome back, Global Exports Inc.</h2>
        <p className="text-muted-foreground">
          Here's what's happening with your LC validations today.
        </p>
      </div>

      <StatGrid stats={stats} />

      <WorkspaceCard
        drafts={drafts}
        amendedLCs={amendedLCs}
        isLoadingDrafts={isLoadingDrafts}
        isLoadingAmendments={isLoadingAmendments}
        onResumeDraft={onResumeDraft}
        onDeleteDraft={onDeleteDraft}
        formatTimeAgo={formatTimeAgo}
        workspaceTab={workspaceTab}
        onWorkspaceTabChange={onWorkspaceTabChange}
      />

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentValidationsCard
            title="Recent LC Validations"
            description="Your latest document validation results"
            history={recentHistory}
          />
        </div>
        <div className="space-y-6">
          <NotificationsCard notifications={notifications} />
          <QuickStatsCard stats={stats} />
        </div>
      </div>
    </>
  );
}

function StatGrid({ stats }: { stats: typeof dashboardStats }) {
  const navigate = useNavigate();
  const { data: usageStats } = useUsageStats();
  const { data: invoicesData } = useInvoices({
    status: InvoiceStatus.PENDING,
    limit: 1,
  });

  const hasPendingInvoices = invoicesData?.invoices && invoicesData.invoices.length > 0;
  const quotaPercentage = usageStats && usageStats.quota_limit
    ? Math.min(100, (usageStats.quota_used / usageStats.quota_limit) * 100)
    : 0;

  return (
    <div className="space-y-4">
      {/* Billing Signals */}
      {(usageStats || hasPendingInvoices) ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-2">
          {usageStats ? (
            <Card className="shadow-soft border-0">
              <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Usage Quota</p>
                  <div className="space-y-2">
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {usageStats.quota_used.toLocaleString()} / {usageStats.quota_limit?.toLocaleString() ?? "∞"}
                    </p>
                    <Progress value={quotaPercentage} className="h-2" />
                  </div>
                </div>
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
                  <TrendingUp className="h-6 w-6 text-blue-500" />
                </div>
              </CardContent>
            </Card>
          ) : null}
          {hasPendingInvoices ? (
            <Card className="shadow-soft border-0 border-yellow-500/20">
              <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Pending Invoice</p>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {invoicesData?.invoices.length || 0}
                    </p>
                    <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                      Action Required
                    </Badge>
                  </div>
                  <button
                    onClick={() => navigate("/lcopilot/exporter-dashboard?section=billing")}
                    className="mt-3 text-sm text-primary hover:underline w-full text-left"
                  >
                    View invoices →
                  </button>
                </div>
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-yellow-500/10">
                  <CreditCard className="h-6 w-6 text-yellow-500" />
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}
      
      {/* Main Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">This Month</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.thisMonth}</p>
            <p className="text-xs text-success mt-1">+18% vs last month</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-exporter/10">
            <FileText className="h-6 w-6 text-exporter" />
          </div>
        </CardContent>
      </Card>
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Success Rate</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.successRate}%</p>
            <Progress value={stats.successRate} className="mt-2 h-2" />
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-success/10">
            <TrendingUp className="h-6 w-6 text-success" />
          </div>
        </CardContent>
      </Card>
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Avg Processing</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.avgProcessingTime}</p>
            <p className="text-xs text-success mt-1">12s faster</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-info/10">
            <Clock className="h-6 w-6 text-info" />
          </div>
        </CardContent>
      </Card>
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Discrepancies Found</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.discrepanciesFound}</p>
            <p className="text-xs text-warning mt-1">Review required</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-warning/10">
            <AlertTriangle className="h-6 w-6 text-warning" />
          </div>
        </CardContent>
      </Card>
    </div>
    </div>
  );
}

interface WorkspaceCardProps {
  drafts: DraftData[];
  amendedLCs: Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>;
  isLoadingDrafts: boolean;
  isLoadingAmendments: boolean;
  onResumeDraft: (draft: DraftData) => void;
  onDeleteDraft: (draftId: string) => void;
  formatTimeAgo: (date: string) => string;
  workspaceTab: string;
  onWorkspaceTabChange: (value: string) => void;
}

function WorkspaceCard({
  drafts,
  amendedLCs,
  isLoadingDrafts,
  isLoadingAmendments,
  onResumeDraft,
  onDeleteDraft,
  formatTimeAgo,
  workspaceTab,
  onWorkspaceTabChange,
}: WorkspaceCardProps) {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Edit3 className="w-5 h-5" /> Your LC Workspace
        </CardTitle>
        <CardDescription>Resume drafts or track amendments that need attention</CardDescription>
      </CardHeader>
      <CardContent>
        {(isLoadingDrafts || isLoadingAmendments) ? (
          <div className="flex items-center justify-center gap-3 py-8 text-muted-foreground">
            <div className="w-5 h-5 rounded-full border-2 border-exporter border-t-transparent animate-spin" />
            Loading workspace...
          </div>
        ) : (
          <Tabs value={workspaceTab} onValueChange={onWorkspaceTabChange} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="drafts" className="flex items-center gap-2">
                <Edit3 className="w-4 h-4" /> Drafts ({drafts.length})
              </TabsTrigger>
              <TabsTrigger value="amendments" className="flex items-center gap-2">
                <GitBranch className="w-4 h-4" /> Amendments ({amendedLCs.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="drafts" className="mt-6 space-y-4">
              {drafts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Edit3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No drafts saved</p>
                  <p className="text-sm">Save a draft while uploading to resume later.</p>
                </div>
              ) : (
                drafts.map((draft) => {
                  const fileCount = draft.filesMeta?.length ?? 0;
                  return (
                    <div
                      key={draft.id}
                      className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
                    >
                      <div className="flex items-center gap-4">
                        <div className="bg-exporter/10 p-3 rounded-lg">
                          <Edit3 className="w-5 h-5 text-exporter" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-foreground">
                            {draft.lcNumber || "Untitled Draft"}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {fileCount} file{fileCount === 1 ? "" : "s"}
                          </p>
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            Saved {formatTimeAgo(draft.updatedAt)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onResumeDraft(draft)}
                          className="flex items-center gap-2"
                        >
                          <ArrowRight className="w-4 h-4" /> Resume
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onDeleteDraft(draft.id)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  );
                })
              )}
            </TabsContent>

            <TabsContent value="amendments" className="mt-6 space-y-4">
              {amendedLCs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No amended LCs yet</p>
                  <p className="text-sm">When an LC gets a new version it will appear here.</p>
                </div>
              ) : (
                amendedLCs.map((lc) => (
                  <div
                    key={lc.lc_number}
                    className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
                  >
                    <div className="flex items-center gap-4">
                      <div className="bg-exporter/10 p-3 rounded-lg">
                        <GitBranch className="w-5 h-5 text-exporter" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground">LC #{lc.lc_number}</h4>
                        <p className="text-sm text-muted-foreground">
                          {lc.versions} version{lc.versions === 1 ? "" : "s"} • Latest: {lc.latest_version}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          Updated {formatTimeAgo(lc.last_updated)}
                        </div>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" className="flex items-center gap-2">
                      <Clock className="w-4 h-4" /> View
                    </Button>
                  </div>
                ))
              )}
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

interface RecentValidationsCardProps {
  title: string;
  description: string;
  history: typeof mockHistory;
}

function RecentValidationsCard({ title, description, history }: RecentValidationsCardProps) {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
            >
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0">
                  {item.status === "approved" ? (
                    <div className="bg-success/10 p-2 rounded-lg">
                      <CheckCircle className="w-5 h-5 text-success" />
                    </div>
                  ) : (
                    <div className="bg-warning/10 p-2 rounded-lg">
                      <AlertTriangle className="w-5 h-5 text-warning" />
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">
                    {item.type} #{item.id}
                  </h4>
                  <p className="text-sm text-muted-foreground">Supplier: {item.supplier}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span>{item.date}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={item.risks === 0 ? "success" : "warning"}>
                  {item.risks === 0
                    ? "No issues"
                    : item.risks === 1
                    ? "1 issue"
                    : `${item.risks} issues`}
                </StatusBadge>
                <Button variant="outline" size="sm">
                  View
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function NotificationsCard({ notifications }: { notifications: Notification[] }) {
  const [localNotifications, setLocalNotifications] = React.useState(notifications);
  const navigate = useNavigate();

  const handleMarkAsRead = (id: string | number) => {
    setLocalNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const handleDismiss = (id: string | number) => {
    setLocalNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleMarkAllAsRead = () => {
    setLocalNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="w-5 h-5" />
          Notifications
        </CardTitle>
        <CardDescription>Updates and alerts</CardDescription>
      </CardHeader>
      <CardContent>
        <NotificationList
          notifications={localNotifications}
          onMarkAsRead={handleMarkAsRead}
          onDismiss={handleDismiss}
          onMarkAllAsRead={handleMarkAllAsRead}
          showHeader={false}
        />
      </CardContent>
    </Card>
  );
}

function QuickStatsCard({ stats }: { stats: typeof dashboardStats }) {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="text-lg">Quick Stats</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 text-sm">
          <div className="flex justify-between text-muted-foreground">
            <span>Total Reviews</span>
            <span className="text-foreground font-medium">{stats.totalReviews}</span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>Documents Processed</span>
            <span className="text-foreground font-medium">{stats.documentsProcessed}</span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>Average Processing</span>
            <span className="text-foreground font-medium">{stats.avgProcessingTime}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SettingsPanel() {
  const { toast } = useToast();
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [autoArchiveDrafts, setAutoArchiveDrafts] = useState(false);
  const [digestFrequency, setDigestFrequency] = useState("daily");
  const [defaultView, setDefaultView] = useState<Section>("dashboard");
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("preferences");

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast({
        title: "Preferences updated",
        description: "Your exporter workspace settings were saved successfully.",
      });
    }, 600);
  };

  const handleReset = () => {
    setEmailAlerts(true);
    setAutoArchiveDrafts(false);
    setDigestFrequency("daily");
    setDefaultView("dashboard");
  };

  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Settings</CardTitle>
        <CardDescription>Configure exporter workspace preferences and data retention.</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="preferences">Preferences</TabsTrigger>
            <TabsTrigger value="company-profile">Company Profile</TabsTrigger>
            <TabsTrigger value="data-retention">Data & Privacy</TabsTrigger>
          </TabsList>
          <TabsContent value="preferences" className="space-y-6 mt-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Email alerts for discrepancies</p>
                  <p className="text-xs text-muted-foreground">Receive an email whenever a validation is flagged.</p>
                </div>
                <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} aria-label="Toggle discrepancy email alerts" />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Auto-archive completed drafts</p>
                  <p className="text-xs text-muted-foreground">Move drafts to archive 7 days after successful validation.</p>
                </div>
                <Switch checked={autoArchiveDrafts} onCheckedChange={setAutoArchiveDrafts} aria-label="Toggle auto archive" />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="digest-frequency">Notification digest</Label>
                <Select value={digestFrequency} onValueChange={setDigestFrequency}>
                  <SelectTrigger id="digest-frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="instant">Instant</SelectItem>
                    <SelectItem value="hourly">Hourly</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">Choose how often you receive summary notifications.</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="default-view">Default workspace view</Label>
                <Select value={defaultView} onValueChange={(value) => setDefaultView(value as Section)}>
                  <SelectTrigger id="default-view">
                    <SelectValue placeholder="Select default view" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dashboard">Dashboard metrics</SelectItem>
                    <SelectItem value="upload">Upload documents</SelectItem>
                    <SelectItem value="reviews">Review results</SelectItem>
                    <SelectItem value="analytics">Analytics</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">The section that opens first each time you visit.</p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3">
              <Button variant="outline" onClick={handleReset}>Reset</Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save preferences"}
              </Button>
            </div>
          </TabsContent>
          <TabsContent value="company-profile" className="mt-6">
            <CompanyProfileView embedded />
          </TabsContent>
          <TabsContent value="data-retention" className="mt-6">
            <DataRetentionView embedded />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function HelpPanel() {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Need Help?</CardTitle>
        <CardDescription>Browse exporter resources, walkthroughs, and contact options.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => window.open("/lcopilot/support", "_blank")}>Support Center</Button>
          <Button variant="outline" onClick={() => window.open("/docs/exporter-runbook", "_blank")}>Exporter Runbook</Button>
          <Button variant="outline" onClick={() => window.open("mailto:support@trdrhub.com")}>Email Support</Button>
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="faq-1">
            <AccordionTrigger>How do I validate a new LC package?</AccordionTrigger>
            <AccordionContent>
              Select <span className="font-medium">Upload Documents</span>, attach the LC and supporting files, then run
              validation. Results appear under <span className="font-medium">Review Results</span> with discrepancy
              details and downloadable packs.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-2">
            <AccordionTrigger>Where can I track discrepancy trends?</AccordionTrigger>
            <AccordionContent>
              Use the <span className="font-medium">Analytics</span> view to monitor month-over-month exports, common
              discrepancy drivers, and compliance rates by document type or destination market.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-3">
            <AccordionTrigger>Who receives notifications?</AccordionTrigger>
            <AccordionContent>
              Notification recipients are defined in <span className="font-medium">Workspace Settings</span>. Enable
              email alerts or set digest frequency to control how your compliance team is notified.
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="rounded-lg border border-gray-200/60 bg-secondary/20 p-4">
          <p className="text-xs">
            Need a guided walkthrough? Schedule a 30-minute onboarding session with our success team and we&apos;ll review
            your exporter workflow end-to-end.
          </p>
          <Button
            size="sm"
            className="mt-3"
            onClick={() => window.open("https://cal.com/trdrhub/exporter-onboarding", "_blank")}
          >
            Book onboarding session
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
