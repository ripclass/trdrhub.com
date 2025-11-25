// ExporterDashboard - Section-based dashboard with embedded workflows (ImporterDashboardV2 style)
import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useToast } from "@/hooks/use-toast";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import ExporterAnalytics from "./ExporterAnalytics";
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
import { NotificationList, type Notification } from "@/components/notifications/NotificationItem";
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
  EXPORTER_SECTION_OPTIONS,
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
  Bell,
} from "lucide-react";

const DASHBOARD_BASE = "/lcopilot/exporter-dashboard";

// Mock notifications for exporter dashboard
const mockNotifications: Notification[] = [
  {
    id: 1,
    title: "Export Regulations Update",
    message: "New export documentation requirements effective Feb 1st. Review your templates.",
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
    title: "LC Validation Completed",
    message: "LC-2024-042 has been validated. 2 issues require your attention.",
    type: "warning",
    timestamp: "4 hours ago",
    read: false,
    link: "/lcopilot/exporter-dashboard?section=reviews",
    action: {
      label: "View Results",
      action: () => {},
    },
  },
  {
    id: 3,
    title: "Customs Pack Ready",
    message: "Your customs documentation pack for LC-2024-041 is ready for download.",
    type: "success",
    timestamp: "Yesterday",
    read: true,
  },
];

export default function ExporterDashboard() {
  return (
    <ResultsProvider>
      <DashboardContent />
    </ResultsProvider>
  );
}

// Type for all sections (both ExporterSection and sidebar-only sections)
type AnySection = ExporterSection | SidebarSection;

function DashboardContent() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { jobId: contextJobId, setJobId } = useResultsContext();
  const { user: currentUser } = useAuth();
  const { user: exporterUser, isAuthenticated, isLoading: authLoading } = useExporterAuth();
  const { toast } = useToast();

  // Parse URL params
  const sectionParam = searchParams.get("section");
  const urlJobId = getParam(searchParams, "jobId");
  const urlLc = getParam(searchParams, "lc");
  const urlTab = getParam(searchParams, "tab");

  // Active section - can be either ExporterSection or SidebarSection
  const [activeSection, setActiveSection] = useState<AnySection>(() => {
    if (!sectionParam) return "overview";
    // Check if it's a valid ExporterSection first
    const parsed = parseExporterSection(sectionParam);
    if (parsed !== "overview" || sectionParam === "overview") return parsed;
    // Check if it's a valid SidebarSection
    const sidebarSections: SidebarSection[] = [
      "dashboard", "workspace", "templates", "upload", "reviews", "analytics",
      "notifications", "billing", "billing-usage", "ai-assistance",
      "content-library", "shipment-timeline", "settings", "help"
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

  // Derive sidebar section from activeSection
  const sidebarSection: SidebarSection = EXPORTER_SECTION_OPTIONS.includes(activeSection as ExporterSection)
    ? sectionToSidebar(activeSection as ExporterSection)
    : (activeSection as SidebarSection);

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
    // Check if it's a valid SidebarSection
    const sidebarSections: SidebarSection[] = [
      "dashboard", "workspace", "templates", "upload", "reviews", "analytics",
      "notifications", "billing", "billing-usage", "ai-assistance",
      "content-library", "shipment-timeline", "settings", "help"
    ];
    if (sidebarSections.includes(sectionParam as SidebarSection)) {
      setActiveSection(sectionParam as SidebarSection);
    } else {
      setActiveSection("overview");
    }
  }, [sectionParam]);

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
    if (tab === "usage") {
      handleSectionChange("billing-usage");
    } else if (tab === "invoices") {
      setBillingTab("invoices");
      handleSectionChange("billing");
    } else {
      setBillingTab("overview");
      handleSectionChange("billing");
    }
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

        {/* LC Workspace Section */}
        {activeSection === "workspace" && <LCWorkspaceView embedded />}

        {/* Templates Section */}
        {activeSection === "templates" && <TemplatesView embedded />}

        {/* Analytics Section (standalone, not results tab) */}
        {activeSection === "analytics" && <ExporterAnalytics embedded />}

        {/* Notifications Section */}
        {activeSection === "notifications" && (
          <NotificationsCard notifications={mockNotifications} />
        )}

        {/* Billing Section */}
        {activeSection === "billing" && (
          billingTab === "invoices" ? (
            <BillingInvoicesPage onTabChange={handleBillingTabChange} />
          ) : (
            <BillingOverviewPage onTabChange={handleBillingTabChange} />
          )
        )}

        {/* Billing Usage Section */}
        {activeSection === "billing-usage" && (
          <BillingUsagePage onTabChange={handleBillingTabChange} />
        )}

        {/* AI Assistance Section */}
        {activeSection === "ai-assistance" && <AIAssistance embedded role="exporter" />}

        {/* Content Library Section */}
        {activeSection === "content-library" && <ContentLibrary embedded />}

        {/* Shipment Timeline Section */}
        {activeSection === "shipment-timeline" && <ShipmentTimeline embedded />}

        {/* Settings Section */}
        {activeSection === "settings" && <SettingsPanel toast={toast} />}

        {/* Help Section */}
        {activeSection === "help" && <HelpPanel />}
      </div>
    </DashboardLayout>
  );
}

// ---------- Overview Panel ----------

interface OverviewPanelProps {
  onNavigate: (section: AnySection) => void;
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

// ---------- Notifications Card ----------

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
        <CardDescription>Updates and alerts for your export workflow</CardDescription>
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

// ---------- Settings Panel ----------

interface SettingsPanelProps {
  toast: ReturnType<typeof useToast>["toast"];
}

function SettingsPanel({ toast }: SettingsPanelProps) {
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [autoArchiveDrafts, setAutoArchiveDrafts] = useState(false);
  const [digestFrequency, setDigestFrequency] = useState("daily");
  const [defaultView, setDefaultView] = useState<AnySection>("overview");
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
    setDefaultView("overview");
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

// ---------- Help Panel ----------

function HelpPanel() {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Need Help?</CardTitle>
        <CardDescription>Browse exporter resources, walkthroughs, and contact options.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => window.open("/lcopilot/support", "_blank")}>
            Support Center
          </Button>
          <Button variant="outline" onClick={() => window.open("/docs/exporter-runbook", "_blank")}>
            Exporter Runbook
          </Button>
          <Button variant="outline" onClick={() => window.open("mailto:support@trdrhub.com")}>Email Support</Button>
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="faq-1">
            <AccordionTrigger>How do I validate a new LC package?</AccordionTrigger>
            <AccordionContent>
              Choose <span className="font-medium">Upload Documents</span>, attach your LC and supporting files, then run
              validation. Results appear under <span className="font-medium">Review Results</span> with compliance checks and
              customs readiness assessment.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-2">
            <AccordionTrigger>How do I generate a customs pack?</AccordionTrigger>
            <AccordionContent>
              After validation, navigate to the <span className="font-medium">Customs Pack</span> tab in Review Results.
              Your customs documentation will be automatically generated based on the validated LC data.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-3">
            <AccordionTrigger>Where can I monitor validation trends?</AccordionTrigger>
            <AccordionContent>
              Use the <span className="font-medium">Analytics</span> view to track compliance rates, processing times, and
              document quality trends across your export operations.
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
