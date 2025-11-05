import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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

  const [drafts, setDrafts] = useState<DraftData[]>([]);
  const [isLoadingDrafts, setIsLoadingDrafts] = useState(false);
  const [amendedLCs, setAmendedLCs] = useState<
    Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>
  >([]);
  const [isLoadingAmendments, setIsLoadingAmendments] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [activeTab, setActiveTab] = useState("drafts");

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
        sidebar={<ExporterSidebar />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Exporter Dashboard" },
        ]}
      >
        <div className="flex flex-col gap-6 p-6 lg:p-8">
          <div>
            <h2 className="text-3xl font-bold text-foreground mb-2">Welcome back, Global Exports Inc.</h2>
            <p className="text-muted-foreground">
              Here’s everything that’s happening with your export LC validations today.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">This Month</p>
                    <p className="text-2xl font-bold text-foreground">{dashboardStats.thisMonth}</p>
                    <p className="text-xs text-success">+18% vs last month</p>
                  </div>
                  <div className="bg-exporter/10 p-3 rounded-lg">
                    <FileText className="w-6 h-6 text-exporter" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Success Rate</p>
                    <p className="text-2xl font-bold text-foreground">{dashboardStats.successRate}%</p>
                    <Progress value={dashboardStats.successRate} className="mt-2 h-2" />
                  </div>
                  <div className="bg-success/10 p-3 rounded-lg">
                    <TrendingUp className="w-6 h-6 text-success" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Avg Processing</p>
                    <p className="text-2xl font-bold text-foreground">{dashboardStats.avgProcessingTime}</p>
                    <p className="text-xs text-success">12s faster</p>
                  </div>
                  <div className="bg-info/10 p-3 rounded-lg">
                    <Clock className="w-6 h-6 text-info" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden shadow-soft border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Discrepancies Found</p>
                    <p className="text-2xl font-bold text-foreground">{dashboardStats.discrepanciesFound}</p>
                    <p className="text-xs text-warning">Needs review</p>
                  </div>
                  <div className="bg-warning/10 p-3 rounded-lg">
                    <AlertTriangle className="w-6 h-6 text-warning" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {(isLoadingDrafts || isLoadingAmendments || drafts.length > 0 || amendedLCs.length > 0) && (
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Edit3 className="w-5 h-5" />
                  Your LC Workspace
                </CardTitle>
                <CardDescription>Resume drafts or track amendments that need attention</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="drafts" className="flex items-center gap-2">
                      <Edit3 className="w-4 h-4" /> Drafts ({drafts.length})
                    </TabsTrigger>
                    <TabsTrigger value="amendments" className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4" /> Amendments ({amendedLCs.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="drafts" className="mt-6">
                    {isLoadingDrafts ? (
                      <div className="flex items-center justify-center gap-3 py-8 text-muted-foreground">
                        <div className="w-5 h-5 rounded-full border-2 border-exporter border-t-transparent animate-spin" />
                        Loading drafts...
                      </div>
                    ) : drafts.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <Edit3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p>No drafts saved</p>
                        <p className="text-sm">Save a draft while uploading to resume later.</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {drafts.map((draft) => {
                          const fileCount = draft.filesMeta?.length ?? 0;
                          return (
                            <div
                              key={draft.id}
                              className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
                            >
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <h4 className="font-semibold text-foreground truncate">
                                    {draft.lcNumber || "Untitled Draft"}
                                  </h4>
                                  <Badge variant="outline" className="text-xs">
                                    Incomplete
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                                  <span>{fileCount} file{fileCount === 1 ? "" : "s"}</span>
                                  <span>•</span>
                                  <span>Updated {formatTimeAgo(draft.updatedAt)}</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button variant="outline" size="sm" className="flex items-center gap-2">
                                  <ArrowRight className="w-4 h-4" /> Resume
                                </Button>
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
                          );
                        })}
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="amendments" className="mt-6">
                    {isLoadingAmendments ? (
                      <div className="flex items-center justify-center gap-3 py-8 text-muted-foreground">
                        <div className="w-5 h-5 rounded-full border-2 border-exporter border-t-transparent animate-spin" />
                        Loading amended LCs...
                      </div>
                    ) : amendedLCs.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p>No amended LCs yet</p>
                        <p className="text-sm">When an LC gets a new version it will appear here.</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {amendedLCs.map((lc) => (
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
                                <div className="text-xs text-muted-foreground mt-1">
                                  Updated {formatTimeAgo(lc.last_updated)}
                                </div>
                              </div>
                            </div>
                            <Button variant="outline" size="sm" className="flex items-center gap-2">
                              <Clock className="w-4 h-4" /> View
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}

          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
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
                    {mockHistory.map((item) => (
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
            </div>

            <div className="space-y-6">
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

              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="text-lg">Quick Stats</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4 text-sm">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Total Reviews</span>
                      <span className="text-foreground font-medium">{dashboardStats.totalReviews}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Documents Processed</span>
                      <span className="text-foreground font-medium">{dashboardStats.documentsProcessed}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Average Processing</span>
                      <span className="text-foreground font-medium">{dashboardStats.avgProcessingTime}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
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
