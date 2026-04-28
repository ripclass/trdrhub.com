// ExporterDashboard - Section-based dashboard with embedded workflows
import { useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams, Link, useLocation } from "react-router-dom";
import { FirstSessionCoachmark } from "@/components/handhold/FirstSessionCoachmark";
import { TrySampleLCButton } from "@/components/handhold/TrySampleLCButton";
import { QuotaStrip } from "@/components/entitlements/QuotaStrip";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useDrafts, type DraftData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import {
  getUserSessions,
  hydrateSessionsWithStructuredResults,
  type ValidationSession,
} from "@/api/sessions";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import { DataRetentionView } from "./settings/DataRetention";
import { CompanyProfileView } from "./settings/CompanyProfile";
import { BillingOverviewPage } from "./BillingOverviewPage";
import { BillingInvoicesPage } from "./BillingInvoicesPage";
import { ResultsProvider, useResultsContext } from "@/context/ResultsContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import { useAuth } from "@/hooks/use-auth";
import { getExporterSessionTruth } from "@/lib/exporter/dashboardTruth";
import {
  type ExporterSection,
  type SidebarSection,
  parseExporterSection,
  sectionToResultsTab,
  resultsTabToSection,
  sectionToSidebar,
  sidebarToSection,
  EXPORTER_SECTION_OPTIONS,
} from "@/lib/exporter/exporterSections";
import { getParam } from "@/lib/exporter/url";
import {
  clearPendingExporterReviewRoute,
  isPendingExporterReviewRoute,
  persistPendingExporterReviewRoute,
  readPendingExporterReviewRoute,
} from "@/lib/exporter/pendingReviewRoute";
import {
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Clock,
  Upload,
  Bell,
  Edit3,
  Trash2,
  ArrowRight,
  GitBranch,
  History,
} from "lucide-react";

const DASHBOARD_BASE = "/lcopilot/exporter-dashboard";

function formatTimeAgo(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

  if (diffInHours < 1) return "Just now";
  if (diffInHours < 24) return `${diffInHours}h ago`;
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return `${diffInDays}d ago`;
  return date.toLocaleDateString();
}

export default function ExporterDashboard() {
  return (
    <ResultsProvider>
      <DashboardContent />
      <FirstSessionCoachmark />
    </ResultsProvider>
  );
}

// Type for all sections (both ExporterSection and sidebar-only sections)
type AnySection = ExporterSection | SidebarSection;

function DashboardContent() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { jobId: contextJobId, setJobId } = useResultsContext();
  const { user: authUser } = useAuth();
  const { toast } = useToast();
  const currentUser = authUser
    ? {
        id: authUser.id,
        name: authUser.full_name || authUser.username || authUser.email.split("@")[0],
        email: authUser.email,
        role: authUser.role,
      }
    : null;

  // Parse URL params
  const sectionParam = searchParams.get("section");
  const urlJobId = getParam(searchParams, "jobId");
  const urlLc = getParam(searchParams, "lc");
  const urlTab = getParam(searchParams, "tab");
  const urlTemplateId = getParam(searchParams, "templateId");
  const urlDraftId = getParam(searchParams, "draftId");

  // Active section - can be either ExporterSection or SidebarSection
  const [activeSection, setActiveSection] = useState<AnySection>(() => {
    if (!sectionParam) return "overview";
    const parsed = parseExporterSection(sectionParam);
    if (parsed !== "overview" || sectionParam === "overview") return parsed;
    const sidebarSections: SidebarSection[] = [
      "dashboard", "upload", "reviews", "billing", "settings"
    ];
    if (sidebarSections.includes(sectionParam as SidebarSection)) {
      return sectionParam as SidebarSection;
    }
    return "overview";
  });

  // Billing sub-tab state
  const [billingTab, setBillingTab] = useState<"overview" | "invoices">("overview");

  // Effective jobId (context or URL)
  const effectiveJobId = urlJobId || contextJobId;
  const hasResultsRouteContext = Boolean(
    sectionParam &&
      urlJobId &&
      ["reviews", "documents", "issues", "extracted-data", "history", "customs"].includes(sectionParam),
  );

  // Derive sidebar section from activeSection
  const sidebarSection: SidebarSection = EXPORTER_SECTION_OPTIONS.includes(activeSection as ExporterSection)
    ? sectionToSidebar(activeSection as ExporterSection)
    : (activeSection as SidebarSection);

  // Sync jobId from URL to context
  useEffect(() => {
    if (urlJobId && urlJobId !== contextJobId) {
      setJobId(urlJobId);
    }
  }, [urlJobId, contextJobId, setJobId]);

  // Sync activeSection when URL section changes
  useEffect(() => {
    if (!sectionParam) {
      setActiveSection("overview");
      return;
    }
    const parsed = parseExporterSection(sectionParam);
    if (parsed !== "overview" || sectionParam === "overview") {
      setActiveSection(parsed);
      return;
    }
    const sidebarSections: SidebarSection[] = [
      "dashboard", "upload", "reviews", "billing", "settings"
    ];
    if (sidebarSections.includes(sectionParam as SidebarSection)) {
      setActiveSection(sectionParam as SidebarSection);
    } else {
      setActiveSection("overview");
    }
  }, [sectionParam]);

  useEffect(() => {
    const currentRoute = `${location.pathname}${location.search}`;
    if (isPendingExporterReviewRoute(currentRoute)) {
      persistPendingExporterReviewRoute(currentRoute);
      return;
    }

    if (location.pathname !== DASHBOARD_BASE || location.search) {
      return;
    }

    const pendingRoute = readPendingExporterReviewRoute();
    if (!pendingRoute) {
      return;
    }

    const pendingUrl = new URL(pendingRoute, window.location.origin);
    setSearchParams(new URLSearchParams(pendingUrl.search), { replace: true });
  }, [location.pathname, location.search, setSearchParams]);

  /**
   * Navigate to a section with optional extras (jobId, lc, tab).
   */
  const handleSectionChange = useCallback(
    (
      section: AnySection,
      extras?: { jobId?: string; lc?: string; tab?: string }
    ) => {
      const params = new URLSearchParams();

      // Set section (omit if overview for cleaner URL)
      if (section !== "overview") {
        params.set("section", section);
      }

      // For results-related sections, keep job params
      const isResultsSection = [
        "reviews",
        "documents",
        "issues",
        "extracted-data",
        "history",
        "analytics",
        "customs",
      ].includes(section);

      if (isResultsSection) {
        const jobIdToUse = extras?.jobId ?? effectiveJobId;
        const lcToUse = extras?.lc ?? urlLc;
        const tabToUse = extras?.tab ?? (section === "reviews" ? urlTab : undefined);

        if (jobIdToUse) params.set("jobId", jobIdToUse);
        if (lcToUse) params.set("lc", lcToUse);
        if (tabToUse && section === "reviews") params.set("tab", tabToUse);

        const pendingRoute = `${DASHBOARD_BASE}?${params.toString()}`;
        if (jobIdToUse) {
          persistPendingExporterReviewRoute(pendingRoute);
        } else {
          clearPendingExporterReviewRoute();
        }
      } else {
        clearPendingExporterReviewRoute();
      }

      setSearchParams(params, { replace: true });
      setActiveSection(section);
    },
    [effectiveJobId, urlLc, urlTab, setSearchParams]
  );

  /**
   * Handle sidebar section changes.
   */
  const handleSidebarChange = useCallback(
    (sidebar: SidebarSection) => {
      const mapped = sidebarToSection(sidebar);
      handleSectionChange(mapped);
    },
    [handleSectionChange]
  );

  /**
   * Handle billing tab changes
   */
  const handleBillingTabChange = useCallback((tab: string) => {
    if (tab === "invoices") {
      setBillingTab("invoices");
    } else {
      setBillingTab("overview");
    }
    handleSectionChange("billing");
  }, [handleSectionChange]);

  /**
   * Handle upload completion - navigate to reviews with job context.
   */
  const handleUploadComplete = useCallback(
    (payload: { jobId: string; lcNumber: string }) => {
    setJobId(payload.jobId);
      handleSectionChange("reviews", {
        jobId: payload.jobId,
        lc: payload.lcNumber,
      });
    },
    [setJobId, handleSectionChange]
  );

  // Extraction review now renders inline inside the upload page — no
  // dashboard navigation needed. The ExportLCUpload component holds the
  // extraction payload in its own state and shows the review below the
  // uploads; clicking Start Validation there calls onComplete which routes
  // to the reviews section.

  /**
   * Handle tab change within ExporterResults.
   */
  const handleResultsTabChange = useCallback(
    (tab: string) => {
      const newSection = resultsTabToSection(tab);
      handleSectionChange(newSection, {
        jobId: effectiveJobId,
        lc: urlLc,
        tab: newSection === "reviews" ? tab : undefined,
      });
    },
    [effectiveJobId, urlLc, handleSectionChange]
  );

  if (!currentUser) {
    return null;
  }

  // Determine which ResultsTab to show for results sections
  const initialResultsTab =
    activeSection === "reviews" && urlTab
      ? urlTab
      : EXPORTER_SECTION_OPTIONS.includes(activeSection as ExporterSection)
        ? sectionToResultsTab(activeSection as ExporterSection)
        : "overview";

  // Check if current section should show ExporterResults
  const showResults = [
    "reviews",
    "documents",
    "issues",
    "extracted-data",
    "history",
    "customs",
  ].includes(activeSection);

  useEffect(() => {
    if (!hasResultsRouteContext) {
      return;
    }
    persistPendingExporterReviewRoute(`${location.pathname}${location.search}`);
  }, [hasResultsRouteContext, location.pathname, location.search]);

  return (
    <DashboardLayout
      sidebar={
        <ExporterSidebar
          activeSection={sidebarSection}
          onSectionChange={handleSidebarChange}
          user={currentUser}
        />
      }
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Exporter Dashboard" },
      ]}
    >
      <div className="flex flex-1 flex-col gap-6 p-6 lg:p-8">
        {/* Quota strip — Phase A4 */}
        <QuotaStrip />

        {/* Overview Section */}
        {activeSection === "overview" && (
          <OverviewPanel
            onNavigate={handleSectionChange}
            user={currentUser}
          />
        )}

        {/* Upload Section */}
        {activeSection === "upload" && (
          <Card className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload LC Documents
              </CardTitle>
              <CardDescription>
                Run extraction, rule checks, and customs readiness against your LC
                package.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ExportLCUpload
                key={`upload-${urlDraftId ?? "no-draft"}-${urlTemplateId ?? "no-template"}`}
                embedded
                draftId={urlDraftId}
                templateId={urlTemplateId}
                onComplete={handleUploadComplete}
              />
            </CardContent>
          </Card>
        )}

        {/* Results Sections (reviews, documents, issues, etc.) */}
        {showResults && (
          <ExporterResults
            embedded
            jobId={effectiveJobId ?? undefined}
            lcNumber={urlLc ?? undefined}
            initialTab={initialResultsTab as any}
            onTabChange={handleResultsTabChange}
          />
        )}

        {/* Billing Section */}
        {activeSection === "billing" && (
          billingTab === "invoices" ? (
            <BillingInvoicesPage onTabChange={handleBillingTabChange} />
          ) : (
            <BillingOverviewPage onTabChange={handleBillingTabChange} />
          )
        )}

        {/* Settings Section */}
        {activeSection === "settings" && <SettingsPanel toast={toast} />}
      </div>
    </DashboardLayout>
  );
}

// ---------- Exporter Dashboard Overview (Original Layout) ----------

interface OverviewPanelProps {
  onNavigate: (section: AnySection) => void;
  user?: { name?: string; email?: string; company?: string } | null;
}

function OverviewPanel({ onNavigate, user }: OverviewPanelProps) {
  const { toast } = useToast();
  const { user: authUser, isLoading: isLoadingAuth } = useAuth();
  const { getAllDrafts, removeDraft } = useDrafts();
  const { getAllAmendedLCs } = useVersions();
  
  const [drafts, setDrafts] = useState<DraftData[]>([]);
  const [isLoadingDrafts, setIsLoadingDrafts] = useState(false);
  const [amendedLCs, setAmendedLCs] = useState<Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>>([]);
  const [isLoadingAmendments, setIsLoadingAmendments] = useState(false);
  const [activeTab, setActiveTab] = useState("drafts");
  
  // Real validation sessions data
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  // Load exporter drafts
  useEffect(() => {
    const loadDrafts = () => {
      setIsLoadingDrafts(true);
      try {
        const exporterDrafts = getAllDrafts();
        setDrafts(exporterDrafts);
      } catch (error) {
        console.error('Failed to load drafts:', error);
      } finally {
        setIsLoadingDrafts(false);
      }
    };
    loadDrafts();
  }, [getAllDrafts]);

  // Load amended LCs
  useEffect(() => {
    const loadAmendedLCs = async () => {
      setIsLoadingAmendments(true);
      try {
        const amended = await getAllAmendedLCs();
        setAmendedLCs(amended);
      } catch (error) {
        console.error('Failed to load amended LCs:', error);
      } finally {
        setIsLoadingAmendments(false);
      }
    };
    loadAmendedLCs();
  }, [getAllAmendedLCs]);

  // Load real validation sessions via react-query so useValidate /
  // useResumeValidate invalidating ['user-sessions'] triggers an
  // auto-refetch (Phase 4/3).
  const sessionsQuery = useQuery({
    queryKey: ['user-sessions'],
    queryFn: async () => {
      const data = await getUserSessions();
      return hydrateSessionsWithStructuredResults(data || [], 8);
    },
    enabled: !isLoadingAuth && !!authUser,
    staleTime: 5_000,
  });

  useEffect(() => {
    if (!authUser) {
      setSessions([]);
      setSessionsError(null);
      setIsLoadingSessions(false);
      return;
    }
    setIsLoadingSessions(sessionsQuery.isLoading);
    if (sessionsQuery.error) {
      console.error('Failed to load validation sessions:', sessionsQuery.error);
      setSessions([]);
      setSessionsError('Validation history is temporarily unavailable.');
      return;
    }
    if (sessionsQuery.data) {
      setSessions(sessionsQuery.data);
      setSessionsError(null);
    }
  }, [authUser, sessionsQuery.data, sessionsQuery.error, sessionsQuery.isLoading]);

  const handleDeleteDraft = (draftId: string) => {
    try {
      removeDraft(draftId);
      setDrafts(prev => prev.filter(d => d.id !== draftId));
      toast({
        title: "Draft Deleted",
        description: "The saved draft has been removed.",
      });
    } catch (error: any) {
      toast({
        title: "Failed to Delete Draft",
        description: error.message || "Could not delete the draft. Please try again.",
        variant: "destructive",
      });
    }
  };

  const companyName = user?.company || user?.name || "Exporter";

  const sessionTruths = useMemo(
    () =>
      sessions.map((session) => ({
        session,
        truth: getExporterSessionTruth(session),
      })),
    [sessions],
  );

  // Calculate real stats from sessions
  const now = new Date();
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const thisMonthSessions = sessions.filter(s => new Date(s.created_at) >= thisMonthStart);
  const completedSessionTruths = sessionTruths.filter(({ session }) => session.status === 'completed');
  const readySessionTruths = completedSessionTruths.filter(({ truth }) => truth.canSubmit);
  const reviewSessionTruths = completedSessionTruths.filter(({ truth }) => truth.state === "review");
  const blockedSessionTruths = completedSessionTruths.filter(({ truth }) => truth.state === "blocked");
  const totalIssues = completedSessionTruths.reduce((sum, { truth }) => sum + truth.issueCount, 0);
  const totalDocuments = sessionTruths.reduce((sum, { truth }) => sum + truth.documentCount, 0);

  const submitReadyRate = completedSessionTruths.length > 0
    ? Math.round((readySessionTruths.length / completedSessionTruths.length) * 100 * 10) / 10
    : 0;

  // Calculate average processing time
  const completedSessions = completedSessionTruths.map(({ session }) => session);
  const sessionsWithTime = completedSessions.filter(s => s.processing_started_at && s.processing_completed_at);
  const avgProcessingMs = sessionsWithTime.length > 0
    ? sessionsWithTime.reduce((sum, s) => {
        const start = new Date(s.processing_started_at!).getTime();
        const end = new Date(s.processing_completed_at!).getTime();
        return sum + (end - start);
      }, 0) / sessionsWithTime.length
    : 0;
  const avgProcessingTime = avgProcessingMs > 0 
    ? `${(avgProcessingMs / 60000).toFixed(1)} min`
    : "N/A";

  // Get recent validations (last 5 completed)
  const recentValidations = [...completedSessionTruths]
    .sort((a, b) => new Date(b.session.created_at).getTime() - new Date(a.session.created_at).getTime())
    .slice(0, 5);

  return (
    <>
      {/* Welcome Section */}
      <div className="mb-4">
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Welcome back, {companyName}
        </h2>
        <p className="text-muted-foreground">
          Here's what's happening with your LC validations today.
        </p>
      </div>

      {/* Stats Grid - Right below welcome */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">This Month</p>
                <p className="text-2xl font-bold text-foreground">{sessionsError ? "—" : thisMonthSessions.length}</p>
                <p className="text-xs text-muted-foreground">
                  {sessionsError ? sessionsError : `${sessions.length} total validations`}
                </p>
              </div>
              <div className="bg-emerald-500/10 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Submit-ready Rate</p>
                <p className="text-2xl font-bold text-foreground">{sessionsError ? "—" : `${submitReadyRate}%`}</p>
                {!sessionsError && <Progress value={submitReadyRate} className="mt-2 h-2" />}
                <p className="text-xs text-muted-foreground mt-2">
                  {sessionsError ? "Retry after your validation history reconnects." : "Submit-ready validations"}
                </p>
              </div>
              <div className="bg-green-500/10 p-3 rounded-lg">
                <TrendingUp className="w-6 h-6 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Avg Processing</p>
                <p className="text-2xl font-bold text-foreground">{sessionsError ? "—" : avgProcessingTime}</p>
                <p className="text-xs text-muted-foreground">
                  {sessionsError ? "No processing summary while history is unavailable." : `${completedSessions.length} completed`}
                </p>
              </div>
              <div className="bg-blue-500/10 p-3 rounded-lg">
                <Clock className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Needs Review</p>
                <p className="text-2xl font-bold text-foreground">
                  {sessionsError ? "—" : reviewSessionTruths.length + blockedSessionTruths.length}
                </p>
                <p className="text-xs text-muted-foreground">
                  {sessionsError ? "Review counts unavailable right now." : `${totalIssues} total issues across completed validations`}
                </p>
              </div>
              <div className="bg-amber-500/10 p-3 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Drafts and Amendments Tabs */}
      <Card className="shadow-soft border-0 mb-6">
          <CardHeader>
            <CardTitle>Your LC Management</CardTitle>
            <CardDescription>
              Manage browser-saved upload drafts and track amended LCs from live version data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="drafts" className="flex items-center gap-2">
                  <Edit3 className="w-4 h-4" />
                  Browser Drafts ({drafts.length})
                </TabsTrigger>
                <TabsTrigger value="amendments" className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4" />
                  Amendments ({amendedLCs.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="drafts" className="mt-6">
                <div className="mb-4 rounded-lg border border-dashed border-border/70 bg-muted/30 p-3 text-sm text-muted-foreground">
                  Drafts are saved locally in this browser. Resume any draft to continue where you left off.
                </div>
                {isLoadingDrafts ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full mr-3"></div>
                    <span className="text-muted-foreground">Loading drafts...</span>
                  </div>
                ) : drafts.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Edit3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
                    <p>No browser drafts saved</p>
                    <p className="text-sm">Save a draft while uploading to resume later on this device</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {drafts.map((draft) => (
                      <div key={draft.id} className="flex items-center justify-between p-4 border rounded-lg bg-secondary/20">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium">
                              {draft.lcNumber || 'Untitled Draft'}
                            </h4>
                            <Badge variant="outline" className="text-xs">
                              Browser-local
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{draft.filesMeta?.length || 0} files</span>
                            <span>•</span>
                            <span>Updated {formatTimeAgo(draft.updatedAt)}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Link to={`${DASHBOARD_BASE}?section=upload&draftId=${draft.id}`}>
                            <Button variant="outline" size="sm">
                              <ArrowRight className="w-4 h-4 mr-2" />
                              Resume
                            </Button>
                          </Link>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteDraft(draft.id)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="amendments" className="mt-6">
                <div className="mb-4 rounded-lg border border-dashed border-border/70 bg-muted/30 p-3 text-sm text-muted-foreground">
                  LCs with multiple validation versions are tracked here automatically.
                </div>
                {isLoadingAmendments ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full mr-3"></div>
                    <span className="text-muted-foreground">Loading amendments...</span>
                  </div>
                ) : amendedLCs.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-20" />
                    <p>No amended LCs</p>
                    <p className="text-sm">LCs with multiple versions will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {amendedLCs.map((lc) => (
                      <div key={lc.lc_number} className="flex items-center justify-between p-4 border rounded-lg bg-secondary/20">
                        <div className="flex items-center gap-4">
                          <div className="bg-emerald-500/10 p-3 rounded-lg">
                            <GitBranch className="w-5 h-5 text-emerald-600" />
                          </div>
                          <div>
                            <h4 className="font-semibold text-foreground">
                              LC #{lc.lc_number}
                            </h4>
                            <p className="text-sm text-muted-foreground">
                              {lc.versions} versions • Latest: {lc.latest_version}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-muted-foreground">
                                Last updated {formatTimeAgo(lc.last_updated)}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onNavigate("reviews")}
                          >
                            <History className="w-4 h-4 mr-2" />
                            View History
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

      {/* Two Column Layout: Recent Validations + Sidebar */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Content - Recent LC Validations */}
        <div className="lg:col-span-2">
          <Card className="shadow-soft border-0">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Recent LC Validations
                </CardTitle>
                <CardDescription>
                  Your latest document validation results
                </CardDescription>
              </div>
              <Link
                to="/reviews"
                className="text-sm text-primary hover:underline flex-shrink-0"
              >
                View all →
              </Link>
            </CardHeader>
            <CardContent>
              {isLoadingSessions ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full mr-3"></div>
                  <span className="text-muted-foreground">Loading validations...</span>
                </div>
              ) : sessionsError ? (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>Validation history unavailable</p>
                  <p className="text-sm">{sessionsError}</p>
                </div>
              ) : recentValidations.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No validations yet</p>
                  <p className="text-sm">Upload your first LC package — or run a sample to see how validation works.</p>
                  <div className="mt-4 flex items-center justify-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => onNavigate("upload")}
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Upload LC
                    </Button>
                    <TrySampleLCButton variant="default" />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {recentValidations.map(({ session, truth }) => {
                    const docCount = truth.documentCount;
                    const lcNumber = truth.lcNumber;
                    
                    return (
                      <div key={session.id} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                        <div className="flex items-center gap-4">
                          <div className="flex-shrink-0">
                            {truth.overallStatus === "success" ? (
                              <div className="bg-green-500/10 p-2 rounded-lg">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                              </div>
                            ) : truth.overallStatus === "error" ? (
                              <div className="bg-red-500/10 p-2 rounded-lg">
                                <XCircle className="w-5 h-5 text-red-500" />
                              </div>
                            ) : (
                              <div className="bg-amber-500/10 p-2 rounded-lg">
                                <AlertTriangle className="w-5 h-5 text-amber-500" />
                              </div>
                            )}
                          </div>
                          <div>
                            <h4 className="font-semibold text-foreground">LC-{lcNumber}</h4>
                            <p className="text-sm text-muted-foreground">Session {session.id.slice(0, 8)}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-muted-foreground">{formatTimeAgo(session.created_at)}</span>
                              <span className="text-xs text-muted-foreground">• {docCount} documents</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <StatusBadge status={truth.overallStatus}>
                              {truth.statusLabel}
                            </StatusBadge>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {truth.issueCount === 0
                                ? "No issues recorded"
                                : truth.issueCount === 1
                                ? "1 issue recorded"
                                : `${truth.issueCount} issues recorded`}
                            </p>
                          </div>
                          <Link to={`/lcopilot/exporter-dashboard?section=reviews&jobId=${session.id}`}>
                            <Button variant="outline" size="sm">
                              View
                            </Button>
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Quick Stats */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="text-lg">Summary</CardTitle>
              <CardDescription>Your validation overview</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Validations</span>
                  <span className="font-medium">{sessions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Documents Processed</span>
                  <span className="font-medium">{totalDocuments}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Submit-ready</span>
                  <span className="font-medium">{readySessionTruths.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Needs review</span>
                  <span className="font-medium">{reviewSessionTruths.length + blockedSessionTruths.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Blocked</span>
                  <span className="font-medium">{blockedSessionTruths.length}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity Summary */}
          <Card className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Bell className="w-5 h-5" />
                Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              {sessionsError ? (
                <p className="text-sm text-muted-foreground text-center py-4">{sessionsError}</p>
              ) : recentValidations.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
              ) : (
                <div className="space-y-3">
                  {recentValidations.slice(0, 3).map(({ session, truth }) => {
                    const lcNumber = truth.lcNumber;
                    const activityTitle =
                      truth.state === "blocked"
                        ? "Validation blocked"
                        : truth.statusLabel === "Ready with cautions"
                        ? "Ready with cautions"
                        : truth.canSubmit
                        ? "Ready for submission"
                        : truth.statusLabel === "Completed"
                        ? "Validation completed"
                        : "Review needed";
                    return (
                      <div key={session.id} className="p-3 rounded-lg border border-gray-200/50">
                        <div className="flex items-start gap-3">
                          <div className={`p-1 rounded-full ${
                            truth.overallStatus === "success" ? "bg-green-500/10" :
                            truth.overallStatus === "error" ? "bg-red-500/10" : "bg-amber-500/10"
                          }`}>
                            <div className={`w-2 h-2 rounded-full ${
                              truth.overallStatus === "success" ? "bg-green-500" :
                              truth.overallStatus === "error" ? "bg-red-500" : "bg-amber-500"
                            }`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm text-foreground">
                              {activityTitle}
                            </h4>
                            <p className="text-xs text-muted-foreground mt-1">LC-{lcNumber}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {truth.issueCount === 0
                                ? "No issues recorded"
                                : truth.issueCount === 1
                                ? "1 issue recorded"
                                : `${truth.issueCount} issues recorded`}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">{formatTimeAgo(session.created_at)}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}


// ---------- Settings Panel ----------

interface SettingsPanelProps {
  toast: ReturnType<typeof useToast>["toast"];
}

function SettingsPanel({ toast }: SettingsPanelProps) {
  const preferencesStorageKey = "lcopilot_exporter_preferences";
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [autoArchiveDrafts, setAutoArchiveDrafts] = useState(false);
  const [digestFrequency, setDigestFrequency] = useState("daily");
  const [defaultView, setDefaultView] = useState<AnySection>("overview");
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("preferences");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(preferencesStorageKey);
      if (!stored) return;
      const parsed = JSON.parse(stored) as {
        emailAlerts?: boolean;
        autoArchiveDrafts?: boolean;
        digestFrequency?: string;
        defaultView?: AnySection;
      };
      setEmailAlerts(parsed.emailAlerts ?? true);
      setAutoArchiveDrafts(parsed.autoArchiveDrafts ?? false);
      setDigestFrequency(parsed.digestFrequency ?? "daily");
      setDefaultView(parsed.defaultView ?? "overview");
    } catch (error) {
      console.error("Failed to load exporter browser preferences:", error);
    }
  }, []);

  const handleSave = () => {
    try {
      setSaving(true);
      localStorage.setItem(
        preferencesStorageKey,
        JSON.stringify({
          emailAlerts,
          autoArchiveDrafts,
          digestFrequency,
          defaultView,
        }),
      );
      setSaving(false);
      toast({
        title: "Preferences updated",
        description: "Your exporter browser preferences were saved on this device.",
      });
    } catch (error) {
      setSaving(false);
      toast({
        title: "Save failed",
        description: "Could not save browser preferences on this device.",
        variant: "destructive",
      });
    }
  };

  const handleReset = () => {
    setEmailAlerts(true);
    setAutoArchiveDrafts(false);
    setDigestFrequency("daily");
    setDefaultView("overview");
    localStorage.removeItem(preferencesStorageKey);
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
                  <p className="text-sm font-medium text-foreground">Email alerts for validation issues</p>
                  <p className="text-xs text-muted-foreground">Receive an email whenever validation finds discrepancies.</p>
                </div>
                <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} aria-label="Toggle validation email alerts" />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Auto-archive completed validations</p>
                  <p className="text-xs text-muted-foreground">Move validations to archive 7 days after completion.</p>
                </div>
                <Switch
                  checked={autoArchiveDrafts}
                  onCheckedChange={setAutoArchiveDrafts}
                  aria-label="Toggle auto archive"
                />
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
                <Select value={defaultView} onValueChange={(value) => setDefaultView(value as AnySection)}>
                  <SelectTrigger id="default-view">
                    <SelectValue placeholder="Select default view" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="overview">Dashboard metrics</SelectItem>
                    <SelectItem value="upload">Upload LC</SelectItem>
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
            <p className="text-xs text-muted-foreground">
              Preferences are stored locally in this browser.
            </p>
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

