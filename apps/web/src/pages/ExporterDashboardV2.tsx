import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useDrafts, type DraftData } from "@/hooks/use-drafts";
import { useVersions } from "@/hooks/use-versions";
import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  Bell,
  Plus,
  BarChart3,
  TrendingUp,
  Clock,
  Edit3,
  Trash2,
  ArrowRight,
  GitBranch,
} from "lucide-react";

// Dashboard stats for exporters
const dashboardStats = {
  thisMonth: 12,
  successRate: 94.2,
  avgProcessingTime: "2.3 minutes",
  discrepanciesFound: 8,
  totalChecks: 24,
  documentsProcessed: 96,
};

const mockHistory = [
  {
    id: "BD-2024-001",
    date: "2024-01-15",
    company: "Dhaka Exports Ltd",
    documents: 5,
    status: "approved",
    discrepancies: 0,
  },
  {
    id: "BD-2024-002",
    date: "2024-01-14",
    company: "Bengal Trade Co",
    documents: 7,
    status: "rejected",
    discrepancies: 3,
  },
  {
    id: "BD-2024-003",
    date: "2024-01-14",
    company: "Chittagong Imports",
    documents: 4,
    status: "flagged",
    discrepancies: 1,
  },
];

const notifications = [
  {
    id: 1,
    title: "New ICC Update Available",
    message: "UCP 600 guidelines have been updated. Review new discrepancy rules.",
    type: "info" as const,
    timestamp: "2 hours ago",
  },
  {
    id: 2,
    title: "LC Processing Complete",
    message: "BD-2024-005 has been processed successfully with no discrepancies.",
    type: "success" as const,
    timestamp: "4 hours ago",
  },
  {
    id: 3,
    title: "Discrepancy Alert",
    message: "BD-2024-006 has 2 discrepancies that need attention.",
    type: "warning" as const,
    timestamp: "1 day ago",
  },
];

export default function ExporterDashboardV2() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "dashboard";
  const [drafts, setDrafts] = useState<DraftData[]>([]);
  const [isLoadingDrafts, setIsLoadingDrafts] = useState(false);
  const [amendedLCs, setAmendedLCs] = useState<
    Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>
  >([]);
  const [isLoadingAmendments, setIsLoadingAmendments] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const { toast } = useToast();
  const { getAllDrafts, removeDraft } = useDrafts();
  const { getAllAmendedLCs } = useVersions();
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();

  // Load exporter drafts from localStorage
  useEffect(() => {
    const loadDrafts = () => {
      setIsLoadingDrafts(true);
      try {
        const exporterDrafts = getAllDrafts();
        setDrafts(exporterDrafts);
      } catch (error) {
        console.error("Failed to load drafts:", error);
      } finally {
        setIsLoadingDrafts(false);
      }
    };

    loadDrafts();
  }, [getAllDrafts]);

  // Check onboarding status on mount
  useEffect(() => {
    if (!isLoadingOnboarding && needsOnboarding) {
      setShowOnboarding(true);
    }
  }, [needsOnboarding, isLoadingOnboarding]);

  // Load amended LCs
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

  const handleDeleteDraft = (draftId: string) => {
    try {
      removeDraft(draftId);
      setDrafts(drafts.filter((d) => d.id !== draftId));
      toast({
        title: "Success",
        description: "Draft deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete draft",
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
        sidebar={<ExporterSidebar />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Exporter Dashboard" },
        ]}
      >
        <div className="flex flex-col gap-6 p-6 lg:p-8">
          {/* Welcome Section */}
          <div>
            <h2 className="text-3xl font-bold text-foreground mb-2">
              Welcome back, Global Exports Inc.
            </h2>
            <p className="text-muted-foreground">
              Here's what's happening with your document validations today.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/export-lc-upload" className="flex-1">
              <Button className="w-full h-16 bg-gradient-exporter hover:opacity-90 text-left justify-start shadow-medium group">
                <div className="flex items-center gap-4">
                  <div className="bg-white/20 p-3 rounded-lg group-hover:scale-110 transition-transform">
                    <Plus className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="font-semibold">Upload Documents</div>
                    <div className="text-sm opacity-90">Start validation process</div>
                  </div>
                </div>
              </Button>
            </Link>
            <Link to="/lcopilot/exporter-analytics" className="flex-1">
              <Button variant="outline" className="w-full h-16 text-left justify-start">
                <div className="flex items-center gap-4">
                  <div className="bg-exporter/10 p-3 rounded-lg">
                    <BarChart3 className="w-6 h-6 text-exporter" />
                  </div>
                  <div>
                    <div className="font-semibold">View Analytics</div>
                    <div className="text-sm text-muted-foreground">Performance insights</div>
                  </div>
                </div>
              </Button>
            </Link>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">This Month</p>
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {dashboardStats.thisMonth}
                    </p>
                    <p className="text-xs text-success mt-1">+15% from last month</p>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-exporter/10">
                    <FileText className="h-6 w-6 text-exporter" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Success Rate</p>
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {dashboardStats.successRate}%
                    </p>
                    <Progress value={dashboardStats.successRate} className="mt-2 h-2" />
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-success/10">
                    <TrendingUp className="h-6 w-6 text-success" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">Avg Processing</p>
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {dashboardStats.avgProcessingTime}
                    </p>
                    <p className="text-xs text-success mt-1">12s faster</p>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-info/10">
                    <Clock className="h-6 w-6 text-info" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6 pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      Discrepancies Found
                    </p>
                    <p className="text-2xl font-bold text-foreground tabular-nums">
                      {dashboardStats.discrepanciesFound}
                    </p>
                    <p className="text-xs text-warning mt-1">Review required</p>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-warning/10">
                    <AlertTriangle className="h-6 w-6 text-warning" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Your Drafts and Amendments Section */}
          {(isLoadingDrafts || isLoadingAmendments || drafts.length > 0 || amendedLCs.length > 0) && (
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Edit3 className="w-5 h-5" />
                  Your Drafts & Amendments
                </CardTitle>
                <CardDescription>Resume your saved validations or manage LC amendments</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingDrafts || isLoadingAmendments ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-muted-foreground">Loading...</div>
                  </div>
                ) : (
                  <Tabs defaultValue="drafts" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="drafts" className="flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Drafts ({drafts.length})
                      </TabsTrigger>
                      <TabsTrigger value="amendments" className="flex items-center gap-2">
                        <GitBranch className="w-4 h-4" />
                        Amendments ({amendedLCs.length})
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="drafts" className="mt-6">
                      {drafts.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                          <p>No draft validations saved</p>
                          <p className="text-sm">Start a new validation to create a draft</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {drafts.map((draft) => (
                            <div
                              key={draft.id}
                              className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50"
                            >
                              <div className="flex items-center gap-4">
                                <div className="bg-exporter/10 p-3 rounded-lg">
                                  <FileText className="w-5 h-5 text-exporter" />
                                </div>
                                <div>
                                  <h4 className="font-semibold text-foreground">
                                    {draft.lcNumber || "Untitled Draft"}
                                  </h4>
                                  <p className="text-sm text-muted-foreground">
                                    {draft.documents.length} document
                                    {draft.documents.length !== 1 ? "s" : ""} uploaded
                                  </p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-muted-foreground">
                                      Saved {formatTimeAgo(draft.lastModified)}
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Link to={`/export-lc-upload?draft=${draft.id}`}>
                                  <Button variant="outline" size="sm" className="flex items-center gap-2">
                                    <ArrowRight className="w-4 h-4" />
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
                      {amendedLCs.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-20" />
                          <p>No amended LCs found</p>
                          <p className="text-sm">LC amendments will appear here</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {amendedLCs.map((lc) => (
                            <div
                              key={lc.lc_number}
                              className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50"
                            >
                              <div className="flex items-center gap-4">
                                <div className="bg-exporter/10 p-3 rounded-lg">
                                  <GitBranch className="w-5 h-5 text-exporter" />
                                </div>
                                <div>
                                  <h4 className="font-semibold text-foreground">{lc.lc_number}</h4>
                                  <p className="text-sm text-muted-foreground">
                                    {lc.versions} version{lc.versions !== 1 ? "s" : ""} • Latest:{" "}
                                    {lc.latest_version}
                                  </p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-muted-foreground">
                                      Updated {formatTimeAgo(lc.last_updated)}
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button variant="outline" size="sm">
                                  <ArrowRight className="w-4 h-4 mr-2" />
                                  View
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </TabsContent>
                  </Tabs>
                )}
              </CardContent>
            </Card>
          )}

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main Content */}
            <div className="lg:col-span-2">
              {/* Recent LC Validations */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Recent Document Validations
                  </CardTitle>
                  <CardDescription>Your latest validation results</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {mockHistory.map((item) => (
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
                            <h4 className="font-semibold text-foreground">{item.id}</h4>
                            <p className="text-sm text-muted-foreground">Company: {item.company}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-muted-foreground">
                                {item.documents} docs • {item.date}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <StatusBadge
                              status={
                                item.status === "approved"
                                  ? "success"
                                  : item.status === "rejected"
                                  ? "destructive"
                                  : "warning"
                              }
                            >
                              {item.discrepancies === 0
                                ? "No issues"
                                : item.discrepancies === 1
                                ? "1 issue"
                                : `${item.discrepancies} issues`}
                            </StatusBadge>
                          </div>
                          <Link to={`/lcopilot/exporter-results?lc=${item.id}`}>
                            <Button variant="outline" size="sm">
                              View
                            </Button>
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Notifications */}
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

              {/* Quick Stats */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="text-lg">Quick Stats</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Total Checks</span>
                      <span className="font-medium">{dashboardStats.totalChecks}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Documents Processed</span>
                      <span className="font-medium">{dashboardStats.documentsProcessed}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Average Processing</span>
                      <span className="font-medium">{dashboardStats.avgProcessingTime}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </DashboardLayout>

      {/* Onboarding Wizard */}
      <OnboardingWizard
        open={showOnboarding}
        onClose={() => setShowOnboarding(false)}
        onComplete={async () => {
          setShowOnboarding(false);
          toast({
            title: "Onboarding Complete",
            description: "Welcome to LCopilot! You're all set to start validating documents.",
          });
        }}
      />
    </>
  );
}
