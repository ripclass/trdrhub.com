import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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

const notifications = [
  {
    id: 1,
    title: "Import Regulations Update",
    message: "New customs requirements effective Feb 1st. Review your upcoming shipments.",
    type: "info" as const,
    timestamp: "2 hours ago",
  },
  {
    id: 2,
    title: "LC Review Complete",
    message: "Your draft LC has been reviewed with no critical risks identified.",
    type: "success" as const,
    timestamp: "5 hours ago",
  },
  {
    id: 3,
    title: "Risk Alert",
    message: "Unrealistic shipment date detected in LC-IMP-2024-003.",
    type: "warning" as const,
    timestamp: "1 day ago",
  },
];

export default function ExporterDashboardV2() {
  const { toast } = useToast();
  const { getAllDrafts, removeDraft } = useDrafts();
  const { getAllAmendedLCs } = useVersions();
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [drafts, setDrafts] = useState<DraftData[]>([]);
  const [isLoadingDrafts, setIsLoadingDrafts] = useState(false);
  const [amendedLCs, setAmendedLCs] = useState<
    Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>
  >([]);
  const [isLoadingAmendments, setIsLoadingAmendments] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  type Section =
    | "dashboard"
    | "upload"
    | "reviews"
    | "analytics"
    | "notifications"
    | "settings"
    | "help";

  const parseSection = (value: string | null): Section => {
    const allowed: Section[] = [
      "dashboard",
      "upload",
      "reviews",
      "analytics",
      "notifications",
      "settings",
      "help",
    ];
    return allowed.includes(value as Section) ? (value as Section) : "dashboard";
  };

  const [activeSection, setActiveSection] = useState<Section>(() => parseSection(searchParams.get("section")));
  const [workspaceTab, setWorkspaceTab] = useState("drafts");

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

  const handleSectionChange = (section: Section) => {
    setActiveSection(section);
    if (section === "dashboard") {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ section }, { replace: true });
    }
  };

  const handleResumeDraft = (draft: DraftData) => {
    navigate(`/export-lc-upload?draftId=${draft.id}`);
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

          {activeSection === "upload" && (
            <UploadPanel
              onOpenUpload={() => navigate("/export-lc-upload")}
              drafts={drafts}
              isLoadingDrafts={isLoadingDrafts}
              onResumeDraft={handleResumeDraft}
            />
          )}

          {activeSection === "reviews" && (
            <RecentValidationsCard
              title="Review Results"
              description="Validate your recent LC checks"
              history={mockHistory}
            />
          )}

          {activeSection === "analytics" && (
            <AnalyticsPanel stats={dashboardStats} />
          )}

          {activeSection === "notifications" && <NotificationsCard notifications={notifications} />}

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

type WorkspaceDraft = DraftData;

interface DashboardOverviewProps {
  stats: typeof dashboardStats;
  drafts: WorkspaceDraft[];
  amendedLCs: Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>;
  isLoadingDrafts: boolean;
  isLoadingAmendments: boolean;
  onResumeDraft: (draft: WorkspaceDraft) => void;
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
  return (
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
  );
}

interface WorkspaceCardProps {
  drafts: WorkspaceDraft[];
  amendedLCs: Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>;
  isLoadingDrafts: boolean;
  isLoadingAmendments: boolean;
  onResumeDraft: (draft: WorkspaceDraft) => void;
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

function NotificationsCard({ notifications }: { notifications: typeof notifications }) {
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
        <div className="space-y-4">
          {notifications.map((notification) => (
            <div key={notification.id} className="p-3 rounded-lg border border-gray-200/50">
              <div className="flex items-start gap-3">
                <div
                  className={`p-1 rounded-full ${
                    notification.type === "success"
                      ? "bg-success/10"
                      : notification.type === "warning"
                      ? "bg-warning/10"
                      : "bg-info/10"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      notification.type === "success"
                        ? "bg-success"
                        : notification.type === "warning"
                        ? "bg-warning"
                        : "bg-info"
                    }`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm text-foreground">{notification.title}</h4>
                  <p className="text-xs text-muted-foreground mt-1">{notification.message}</p>
                  <p className="text-xs text-muted-foreground mt-2">{notification.timestamp}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
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

function UploadPanel({
  onOpenUpload,
  drafts,
  isLoadingDrafts,
  onResumeDraft,
}: {
  onOpenUpload: () => void;
  drafts: WorkspaceDraft[];
  isLoadingDrafts: boolean;
  onResumeDraft: (draft: WorkspaceDraft) => void;
}) {
  return (
    <div className="space-y-6">
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
          <CardDescription>
            Prepare and submit export documents for validation directly from your workspace.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Use the document uploader to validate LC packages, invoices, packing lists, and other trade
            documentation. You can save drafts to resume later or submit for validation when ready.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Button className="bg-gradient-exporter hover:opacity-90" onClick={onOpenUpload}>
              Open Upload Workspace
            </Button>
            <Button variant="outline" onClick={() => window.open("/export-lc-upload", "_blank")}>Learn about document requirements</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Recent Drafts</CardTitle>
          <CardDescription>Resume an existing draft to continue uploading files.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingDrafts ? (
            <div className="flex items-center justify-center gap-3 py-6 text-muted-foreground">
              <div className="w-5 h-5 rounded-full border-2 border-exporter border-t-transparent animate-spin" />
              Loading drafts...
            </div>
          ) : drafts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Edit3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No drafts saved</p>
              <p className="text-sm">Upload documents to save a draft and resume later.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {drafts.slice(0, 5).map((draft) => (
                <div
                  key={draft.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
                >
                  <div>
                    <h4 className="font-semibold text-foreground">{draft.lcNumber || "Untitled Draft"}</h4>
                    <p className="text-xs text-muted-foreground">Updated {new Date(draft.updatedAt).toLocaleDateString()}</p>
                  </div>
                  <Button variant="outline" size="sm" className="flex items-center gap-2" onClick={() => onResumeDraft(draft)}>
                    <ArrowRight className="w-4 h-4" /> Resume
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AnalyticsPanel({ stats }: { stats: typeof dashboardStats }) {
  return (
    <div className="space-y-6">
      <StatGrid stats={stats} />
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Performance Overview</CardTitle>
          <CardDescription>
            Summary of exporter validation performance and discrepancy trends.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Success rate remains strong at <strong>{stats.successRate}%</strong>. Average processing time is
            currently <strong>{stats.avgProcessingTime}</strong>, which is <strong>10 seconds faster</strong> than
            last month. Discrepancies remain low with <strong>{stats.discrepanciesFound}</strong> items flagged for
            review.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="rounded-lg border border-gray-200/50 bg-secondary/20 p-4">
              <h4 className="font-semibold text-foreground mb-2">Validation Mix</h4>
              <p>LC reviews account for 62% of activity, document checks 28%, and ancillary validations 10%.</p>
            </div>
            <div className="rounded-lg border border-gray-200/50 bg-secondary/20 p-4">
              <h4 className="font-semibold text-foreground mb-2">Discrepancy Drivers</h4>
              <p>Most discrepancies relate to shipment dates and invoice mismatches. Track amendments to stay ahead.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SettingsPanel() {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Workspace Settings</CardTitle>
        <CardDescription>Adjust preferences for notifications, drafts, and validation defaults.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>Settings management is coming soon. In the meantime, contact support to configure workspace preferences.</p>
        <Button variant="outline" className="w-fit" onClick={() => window.open("mailto:support@trdrhub.com")}>Contact Support</Button>
      </CardContent>
    </Card>
  );
}

function HelpPanel() {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Need Help?</CardTitle>
        <CardDescription>Access guidance and resources for exporter workflows.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>
          Browse our knowledge base for common exporter workflows, or reach out to our team for personalised
          assistance.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => window.open("/lcopilot/support", "_blank")}>Support Center</Button>
          <Button variant="outline" onClick={() => window.open("mailto:support@trdrhub.com")}>Email Support</Button>
        </div>
      </CardContent>
    </Card>
  );
}
