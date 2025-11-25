// ExporterDashboard - Section-based dashboard with embedded workflows (ImporterDashboardV2 style)
import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/ui/status-badge";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import ExporterAnalytics from "./ExporterAnalytics";
import { ResultsProvider, useResultsContext } from "@/context/ResultsContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import { useAuth } from "@/hooks/use-auth";
import { useExporterAuth } from "@/lib/exporter/auth";
import {
  type ExporterSection,
  type SidebarSection,
  parseExporterSection,
  sectionToResultsTab,
  resultsTabToSection,
  sectionToSidebar,
  sidebarToSection,
} from "@/lib/exporter/exporterSections";
import { getParam } from "@/lib/exporter/url";
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Clock,
  Upload,
  BarChart3,
} from "lucide-react";

const DASHBOARD_BASE = "/lcopilot/exporter-dashboard";

export default function ExporterDashboard() {
  return (
    <ResultsProvider>
      <DashboardContent />
    </ResultsProvider>
  );
}

function DashboardContent() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { jobId: contextJobId, setJobId } = useResultsContext();
  const { user: currentUser } = useAuth();
  const { user: exporterUser, isAuthenticated, isLoading: authLoading } = useExporterAuth();

  // Parse URL params
  const sectionParam = searchParams.get("section");
  const activeSection = parseExporterSection(sectionParam);
  const urlJobId = getParam(searchParams, "jobId");
  const urlLc = getParam(searchParams, "lc");
  const urlTab = getParam(searchParams, "tab");

  // Effective jobId (context or URL)
  const effectiveJobId = urlJobId || contextJobId;

  // Sidebar state derived from section
  const [sidebarSection, setSidebarSection] = useState<SidebarSection>(
    sectionToSidebar(activeSection)
  );

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/lcopilot/exporter-dashboard/login");
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Sync jobId from URL to context
  useEffect(() => {
    if (urlJobId && urlJobId !== contextJobId) {
      setJobId(urlJobId);
    }
  }, [urlJobId, contextJobId, setJobId]);

  // Sync sidebar section when URL section changes
  useEffect(() => {
    setSidebarSection(sectionToSidebar(activeSection));
  }, [activeSection]);

  /**
   * Navigate to a section with optional extras (jobId, lc, tab).
   */
  const handleSectionChange = useCallback(
    (
      section: ExporterSection,
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
      }

      setSearchParams(params, { replace: true });
      setSidebarSection(sectionToSidebar(section));
    },
    [effectiveJobId, urlLc, urlTab, setSearchParams]
  );

  /**
   * Handle sidebar section changes (map to ExporterSection).
   */
  const handleSidebarChange = useCallback(
    (sidebar: SidebarSection) => {
      setSidebarSection(sidebar);
      const mapped = sidebarToSection(sidebar);
      if (mapped) {
        handleSectionChange(mapped);
      }
      // For non-mapped sections, just update sidebar highlight
    },
    [handleSectionChange]
  );

  /**
   * Handle upload completion - navigate to reviews with job context.
   */
  const handleUploadComplete = useCallback(
    (payload: { jobId: string; lcNumber: string }) => {
      setJobId(payload.jobId);
      handleSectionChange("reviews", {
        jobId: payload.jobId,
        lc: payload.lcNumber,
        tab: "overview",
      });
    },
    [setJobId, handleSectionChange]
  );

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

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated (handled by useEffect)
  if (!isAuthenticated) {
    return null;
  }

  // Determine which ResultsTab to show for results sections
  const initialResultsTab =
    activeSection === "reviews" && urlTab
      ? urlTab
      : sectionToResultsTab(activeSection);

  // Check if current section should show ExporterResults
  const showResults = [
    "reviews",
    "documents",
    "issues",
    "extracted-data",
    "history",
    "analytics",
    "customs",
  ].includes(activeSection);

  return (
    <DashboardLayout
      sidebar={
        <ExporterSidebar
          activeSection={sidebarSection}
          onSectionChange={handleSidebarChange}
          user={currentUser ?? exporterUser ?? undefined}
        />
      }
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Exporter Dashboard" },
      ]}
    >
      <div className="flex flex-1 flex-col gap-6 p-6 lg:p-8">
        {/* Overview Section */}
        {activeSection === "overview" && (
          <OverviewPanel onNavigate={handleSectionChange} />
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
              <ExportLCUpload embedded onComplete={handleUploadComplete} />
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
      </div>
    </DashboardLayout>
  );
}

// ---------- Overview Panel ----------

interface OverviewPanelProps {
  onNavigate: (section: ExporterSection) => void;
}

function OverviewPanel({ onNavigate }: OverviewPanelProps) {
  // Mock stats - in production these would come from API
  const stats = {
    thisMonth: 12,
    successRate: 94.2,
    avgProcessingTime: "2.4 min",
    issuesIdentified: 8,
    totalValidations: 47,
    documentsProcessed: 156,
  };

  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Exporter Dashboard
        </h2>
        <p className="text-muted-foreground">
          Monitor your LC validations, document compliance, and customs readiness.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="This Month"
          value={stats.thisMonth.toString()}
          sublabel="+25% from last month"
          icon={<FileText className="h-6 w-6 text-emerald-500" />}
          iconBg="bg-emerald-500/10"
        />
        <StatCard
          label="Success Rate"
          value={`${stats.successRate}%`}
          progress={stats.successRate}
          icon={<TrendingUp className="h-6 w-6 text-green-500" />}
          iconBg="bg-green-500/10"
        />
        <StatCard
          label="Avg Processing"
          value={stats.avgProcessingTime}
          sublabel="12s faster"
          icon={<Clock className="h-6 w-6 text-blue-500" />}
          iconBg="bg-blue-500/10"
        />
        <StatCard
          label="Issues Found"
          value={stats.issuesIdentified.toString()}
          sublabel="Review required"
          icon={<AlertTriangle className="h-6 w-6 text-amber-500" />}
          iconBg="bg-amber-500/10"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Start a new validation or review existing results
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={() => onNavigate("upload")}
              className="w-full justify-start"
              variant="outline"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload New LC Package
            </Button>
            <Button
              onClick={() => onNavigate("reviews")}
              className="w-full justify-start"
              variant="outline"
            >
              <FileText className="w-4 h-4 mr-2" />
              View Recent Results
            </Button>
            <Button
              onClick={() => onNavigate("analytics")}
              className="w-full justify-start"
              variant="outline"
            >
              <BarChart3 className="w-4 h-4 mr-2" />
              View Analytics
            </Button>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Your latest validation results</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { id: "1", lc: "LC-2024-001", status: "success", issues: 0 },
                { id: "2", lc: "LC-2024-002", status: "warning", issues: 2 },
                { id: "3", lc: "LC-2024-003", status: "success", issues: 0 },
              ].map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {item.status === "success" ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-500" />
                    )}
                    <span className="font-medium">{item.lc}</span>
                  </div>
                  <StatusBadge status={item.status as any}>
                    {item.issues === 0 ? "No issues" : `${item.issues} issues`}
                  </StatusBadge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Monthly Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="text-center p-4 bg-secondary/20 rounded-lg">
              <p className="text-3xl font-bold text-foreground">
                {stats.totalValidations}
              </p>
              <p className="text-sm text-muted-foreground">Total Validations</p>
            </div>
            <div className="text-center p-4 bg-secondary/20 rounded-lg">
              <p className="text-3xl font-bold text-foreground">
                {stats.documentsProcessed}
              </p>
              <p className="text-sm text-muted-foreground">Documents Processed</p>
            </div>
            <div className="text-center p-4 bg-secondary/20 rounded-lg">
              <p className="text-3xl font-bold text-foreground">
                {stats.successRate}%
              </p>
              <p className="text-sm text-muted-foreground">Compliance Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

// ---------- Stat Card Component ----------

interface StatCardProps {
  label: string;
  value: string;
  sublabel?: string;
  progress?: number;
  icon: React.ReactNode;
  iconBg: string;
}

function StatCard({ label, value, sublabel, progress, icon, iconBg }: StatCardProps) {
  return (
    <Card className="shadow-soft border-0">
      <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground mb-2">{label}</p>
          <p className="text-2xl font-bold text-foreground tabular-nums">{value}</p>
          {progress !== undefined && (
            <Progress value={progress} className="mt-2 h-2" />
          )}
          {sublabel && (
            <p className="text-xs text-emerald-600 mt-1">{sublabel}</p>
          )}
        </div>
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${iconBg}`}
        >
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}
