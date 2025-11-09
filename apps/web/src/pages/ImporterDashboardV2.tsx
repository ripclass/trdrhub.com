// ImporterDashboardV2 - section-based importer dashboard with embedded workflows
import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useDrafts, type Draft } from "@/hooks/use-drafts";
import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ImporterSidebar } from "@/components/importer/ImporterSidebar";
import ImportLCUpload from "./ImportLCUpload";
import ImporterAnalytics from "./ImporterAnalytics";
import ImportResults from "./ImportResults";
import { LCWorkspaceView } from "./sme/LCWorkspace";
import { DataRetentionView } from "./settings/DataRetention";
import { TemplatesView } from "./sme/Templates";
import { CompanyProfileView } from "./settings/CompanyProfile";
import {
  FileText,
  CheckCircle,
  AlertTriangle,
  Bell,
  TrendingUp,
  Clock,
  Edit3,
  Trash2,
  ArrowRight,
  GitBranch,
} from "lucide-react";
import { NotificationList, type Notification } from "@/components/notifications/NotificationItem";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

const SECTION_OPTIONS = ["dashboard", "workspace", "templates", "upload", "reviews", "analytics", "notifications", "settings", "help"] as const;
type Section = (typeof SECTION_OPTIONS)[number];

const dashboardStats = {
  thisMonth: 6,
  successRate: 91.7,
  avgProcessingTime: "2.8 minutes",
  risksIdentified: 3,
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
    title: "Import Regulations Update",
    message: "New customs requirements effective Feb 1st. Review upcoming shipments.",
    type: "info",
    timestamp: "2 hours ago",
    read: false,
    link: "/lcopilot/importer-dashboard?section=settings",
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
    link: "/lcopilot/importer-dashboard?section=reviews",
    action: {
      label: "View Results",
      action: () => {},
    },
  },
  {
    id: 3,
    title: "Risk Alert",
    message: "Unrealistic shipment date detected in LC-IMP-2024-003.",
    type: "warning",
    timestamp: "1 day ago",
    read: false,
    link: "/lcopilot/importer-dashboard?section=reviews&lc=LC-IMP-2024-003",
    badge: "High",
    action: {
      label: "Review LC",
      action: () => {},
      variant: "destructive",
    },
  },
];

const parseSectionParam = (sectionParam: string | null, legacyTabParam: string | null): Section => {
  if (sectionParam && SECTION_OPTIONS.includes(sectionParam as Section)) {
    return sectionParam as Section;
  }

  if (legacyTabParam) {
    switch (legacyTabParam) {
      case "results":
        return "reviews";
      case "notifications":
        return "notifications";
      case "analytics":
        return "analytics";
      case "upload":
        return "upload";
    }
  }

  return "dashboard";
};

export default function ImporterDashboardV2() {
  const { toast } = useToast();
  const { listDrafts, deleteDraft } = useDrafts();
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();
  const [searchParams, setSearchParams] = useSearchParams();

  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [workspaceTab, setWorkspaceTab] = useState<"drafts" | "amendments">("drafts");

  const [activeSection, setActiveSection] = useState<Section>(() =>
    parseSectionParam(searchParams.get("section"), searchParams.get("tab"))
  );

  useEffect(() => {
    if (!isLoadingOnboarding && needsOnboarding) {
      setShowOnboarding(true);
    }
  }, [needsOnboarding, isLoadingOnboarding]);

  useEffect(() => {
    const fetchDrafts = async () => {
      try {
        setLoadingDrafts(true);
        const allDrafts = await listDrafts();
        const importerDrafts = allDrafts.filter(
          (d) => d.draft_type === "importer_draft" || d.draft_type === "importer_supplier"
        );
        setDrafts(importerDrafts);
      } catch (error) {
        console.error("Failed to load drafts:", error);
        toast({
          title: "Error",
          description: "Failed to load drafts. Please try again.",
          variant: "destructive",
        });
      } finally {
        setLoadingDrafts(false);
      }
    };

    fetchDrafts();
  }, [listDrafts, toast]);

  useEffect(() => {
    const nextSection = parseSectionParam(searchParams.get("section"), searchParams.get("tab"));
    if (nextSection !== activeSection) {
      setActiveSection(nextSection);
    }

    const type = searchParams.get("type");
    if (type === "supplier") {
      setWorkspaceTab("amendments");
    } else if (type === "draft") {
      setWorkspaceTab("drafts");
    }
  }, [searchParams, activeSection]);

  const handleSectionChange = (section: Section, extras: Record<string, string | undefined> = {}) => {
    setActiveSection(section);

    const next = new URLSearchParams(searchParams);
    next.delete("tab");

    if (section === "dashboard") {
      next.delete("section");
    } else {
      next.set("section", section);
    }

    if (section !== "upload") {
      next.delete("draft_id");
      next.delete("type");
    }

    if (section !== "reviews") {
      next.delete("jobId");
      next.delete("lc");
      next.delete("mode");
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

  const handleDeleteDraft = async (draftId: string) => {
    try {
      await deleteDraft(draftId);
      setDrafts((prev) => prev.filter((draft) => draft.draft_id !== draftId));
      toast({
        title: "Success",
        description: "Draft deleted successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete draft. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleResumeDraft = (draft: Draft) => {
    const draftType = draft.draft_type === "importer_draft" ? "draft" : "supplier";
    setWorkspaceTab(draftType === "draft" ? "drafts" : "amendments");
    handleSectionChange("upload", {
      draft_id: draft.draft_id,
      type: draftType,
    });
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

  return (
    <>
      <DashboardLayout
        sidebar={<ImporterSidebar activeSection={activeSection} onSectionChange={handleSectionChange} />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Importer Dashboard" },
        ]}
      >
        <div className="flex flex-1 flex-col gap-6 p-6 lg:p-8">
          {activeSection === "dashboard" && (
            <DashboardOverview
              stats={dashboardStats}
              drafts={drafts}
              loadingDrafts={loadingDrafts}
              onResumeDraft={handleResumeDraft}
              onDeleteDraft={handleDeleteDraft}
              formatTimeAgo={formatTimeAgo}
              workspaceTab={workspaceTab}
              onWorkspaceTabChange={setWorkspaceTab}
              recentHistory={mockHistory}
              notifications={notifications}
            />
          )}

          {activeSection === "workspace" && <LCWorkspaceView embedded />}

          {activeSection === "templates" && <TemplatesView embedded />}

          {activeSection === "upload" && (
            <ImportLCUpload
              embedded
              onComplete={({ jobId, lcNumber, mode }) => {
                handleSectionChange("reviews", {
                  jobId,
                  lc: lcNumber,
                  mode,
                });
              }}
            />
          )}

          {activeSection === "reviews" && (
            <ImportResults
              embedded
              jobId={searchParams.get("jobId") ?? undefined}
              lcNumber={searchParams.get("lc") ?? undefined}
              mode={(searchParams.get("mode") as "draft" | "supplier") || undefined}
            />
          )}

          {activeSection === "analytics" && <ImporterAnalytics embedded />}

          {activeSection === "notifications" && (
            <NotificationsCard notifications={notifications} />
          )}

          {activeSection === "settings" && <SettingsPanel />}

          {activeSection === "help" && <HelpPanel />}
        </div>
      </DashboardLayout>

      <OnboardingWizard
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={async () => {
          setShowOnboarding(false);
          toast({
            title: "Onboarding Complete",
            description: "Welcome to LCopilot! You're all set to start reviewing supplier documents.",
          });
        }}
      />
    </>
  );
}

type WorkspaceDraft = Draft;

interface DashboardOverviewProps {
  stats: typeof dashboardStats;
  drafts: WorkspaceDraft[];
  loadingDrafts: boolean;
  onResumeDraft: (draft: WorkspaceDraft) => void;
  onDeleteDraft: (draftId: string) => void;
  formatTimeAgo: (date: string) => string;
  workspaceTab: "drafts" | "amendments";
  onWorkspaceTabChange: (value: "drafts" | "amendments") => void;
  recentHistory: typeof mockHistory;
  notifications: typeof notifications;
}

function DashboardOverview({
  stats,
  drafts,
  loadingDrafts,
  onResumeDraft,
  onDeleteDraft,
  formatTimeAgo,
  workspaceTab,
  onWorkspaceTabChange,
  recentHistory,
  notifications,
}: DashboardOverviewProps) {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Welcome back, Bangladesh Exports Ltd</h2>
        <p className="text-muted-foreground">Here's what's happening with your LC validations today.</p>
      </div>

      <StatGrid stats={stats} />

      <WorkspaceCard
        drafts={drafts}
        loadingDrafts={loadingDrafts}
        onResumeDraft={onResumeDraft}
        onDeleteDraft={onDeleteDraft}
        formatTimeAgo={formatTimeAgo}
        workspaceTab={workspaceTab}
        onWorkspaceTabChange={onWorkspaceTabChange}
      />

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentValidationsCard history={recentHistory} />
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
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">This Month</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.thisMonth}</p>
            <p className="text-xs text-success mt-1">+20% from last month</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-importer/10">
            <FileText className="h-6 w-6 text-importer" />
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
            <p className="text-xs text-success mt-1">10s faster</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-info/10">
            <Clock className="h-6 w-6 text-info" />
          </div>
        </CardContent>
      </Card>
      <Card className="shadow-soft border-0">
        <CardContent className="flex h-full items-start justify-between gap-4 p-6 pt-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Risks Identified</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{stats.risksIdentified}</p>
            <p className="text-xs text-warning mt-1">Review required</p>
          </div>
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-warning/10">
            <AlertTriangle className="h-6 w-6 text-warning" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface WorkspaceCardProps {
  drafts: WorkspaceDraft[];
  loadingDrafts: boolean;
  onResumeDraft: (draft: WorkspaceDraft) => void;
  onDeleteDraft: (draftId: string) => void;
  formatTimeAgo: (date: string) => string;
  workspaceTab: "drafts" | "amendments";
  onWorkspaceTabChange: (value: "drafts" | "amendments") => void;
}

function WorkspaceCard({
  drafts,
  loadingDrafts,
  onResumeDraft,
  onDeleteDraft,
  formatTimeAgo,
  workspaceTab,
  onWorkspaceTabChange,
}: WorkspaceCardProps) {
  const importerDrafts = drafts.filter((d) => d.draft_type === "importer_draft");
  const amendmentDrafts = drafts.filter((d) => d.draft_type === "importer_supplier");

  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Edit3 className="w-5 h-5" /> Your LC Workspace
        </CardTitle>
        <CardDescription>Resume drafts or track amendments that need attention</CardDescription>
      </CardHeader>
      <CardContent>
        {loadingDrafts ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">Loading drafts...</div>
        ) : (
          <Tabs value={workspaceTab} onValueChange={(value) => onWorkspaceTabChange(value as "drafts" | "amendments")}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="drafts" className="flex items-center gap-2">
                <Edit3 className="w-4 h-4" /> Drafts ({importerDrafts.length})
              </TabsTrigger>
              <TabsTrigger value="amendments" className="flex items-center gap-2">
                <GitBranch className="w-4 h-4" /> Amendments ({amendmentDrafts.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="drafts" className="mt-6 space-y-4">
              {importerDrafts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No draft LC validations saved</p>
                  <p className="text-sm">Start a new validation to create a draft</p>
                </div>
              ) : (
                importerDrafts.map((draft) => (
                  <WorkspaceListItem
                    key={draft.draft_id}
                    draft={draft}
                    documentLabel="document"
                    onResumeDraft={onResumeDraft}
                    onDeleteDraft={onDeleteDraft}
                    formatTimeAgo={formatTimeAgo}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="amendments" className="mt-6 space-y-4">
              {amendmentDrafts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No supplier amendments recorded</p>
                  <p className="text-sm">Updates to supplier documents will appear here</p>
                </div>
              ) : (
                amendmentDrafts.map((draft) => (
                  <WorkspaceListItem
                    key={draft.draft_id}
                    draft={draft}
                    documentLabel="document"
                    onResumeDraft={onResumeDraft}
                    onDeleteDraft={onDeleteDraft}
                    formatTimeAgo={formatTimeAgo}
                  />
                ))
              )}
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

interface WorkspaceListItemProps {
  draft: WorkspaceDraft;
  documentLabel: string;
  onResumeDraft: (draft: WorkspaceDraft) => void;
  onDeleteDraft: (draftId: string) => void;
  formatTimeAgo: (date: string) => string;
}

function WorkspaceListItem({ draft, documentLabel, onResumeDraft, onDeleteDraft, formatTimeAgo }: WorkspaceListItemProps) {
  return (
    <div className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
      <div className="flex items-center gap-4">
        <div className="bg-importer/10 p-3 rounded-lg">
          <Edit3 className="w-5 h-5 text-importer" />
        </div>
        <div>
          <h4 className="font-semibold text-foreground">{draft.lc_number || "Untitled Draft"}</h4>
          <p className="text-sm text-muted-foreground">
            {draft.uploaded_docs.length} {documentLabel}
            {draft.uploaded_docs.length === 1 ? "" : "s"}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            Saved {formatTimeAgo(draft.updated_at)}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => onResumeDraft(draft)} className="flex items-center gap-2">
          <ArrowRight className="w-4 h-4" /> Resume
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onDeleteDraft(draft.draft_id)}
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

function RecentValidationsCard({ history }: { history: typeof mockHistory }) {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Recent LC Validations
        </CardTitle>
        <CardDescription>Your latest document validation results</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50"
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
                  {item.risks === 0 ? "No issues" : item.risks === 1 ? "1 issue" : `${item.risks} issues`}
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
        description: "Your importer workspace settings were saved successfully.",
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
        <CardDescription>Configure importer workspace preferences and data retention.</CardDescription>
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
                  <p className="text-sm font-medium text-foreground">Email alerts for bank discrepancies</p>
                  <p className="text-xs text-muted-foreground">Receive an email whenever the bank flags a discrepancy.</p>
                </div>
                <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} aria-label="Toggle discrepancy email alerts" />
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
                <Select value={defaultView} onValueChange={(value) => setDefaultView(value as Section)}>
                  <SelectTrigger id="default-view">
                    <SelectValue placeholder="Select default view" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dashboard">Dashboard metrics</SelectItem>
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

function HelpPanel() {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Need Help?</CardTitle>
        <CardDescription>Browse importer resources, walkthroughs, and contact options.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => window.open("/lcopilot/support", "_blank")}>
            Support Center
          </Button>
          <Button variant="outline" onClick={() => window.open("/docs/importer-runbook", "_blank")}>
            Importer Runbook
          </Button>
          <Button variant="outline" onClick={() => window.open("mailto:support@trdrhub.com")}>Email Support</Button>
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="faq-1">
            <AccordionTrigger>How do I validate a new LC package?</AccordionTrigger>
            <AccordionContent>
              Choose <span className="font-medium">Upload LC</span>, attach the draft LC and supporting files, then run
              validation. Results appear under <span className="font-medium">Review Results</span> with risk insights and
              document discrepancies.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-2">
            <AccordionTrigger>Where can I monitor supplier compliance trends?</AccordionTrigger>
            <AccordionContent>
              Use the <span className="font-medium">Analytics</span> view to track compliance rates, processing times, and
              risk reduction across your supplier base.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-3">
            <AccordionTrigger>Who receives importer notifications?</AccordionTrigger>
            <AccordionContent>
              Notification recipients are configured in <span className="font-medium">Workspace Settings</span>. Enable
              discrepancy alerts or digests to keep your compliance team informed.
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="rounded-lg border border-gray-200/60 bg-secondary/20 p-4">
          <p className="text-xs">
            Need a guided walkthrough? Schedule a 30-minute onboarding session with our success team and we&apos;ll review
            your importer workflow end-to-end.
          </p>
          <Button
            size="sm"
            className="mt-3"
            onClick={() => window.open("https://cal.com/trdrhub/importer-onboarding", "_blank")}
          >
            Book onboarding session
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
