// ImporterDashboardV2 - Full-featured Importer Dashboard with sidebar layout  
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useDrafts, type Draft } from "@/hooks/use-drafts";
import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ImporterSidebar } from "@/components/importer/ImporterSidebar";
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

// Dashboard stats for importers
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
    status: "approved",
    risks: 2,
  },
  {
    id: "2",
    date: "2024-01-12",
    type: "Document Check",
    supplier: "XYZ Trading Co.",
    status: "flagged",
    risks: 4,
  },
  {
    id: "3",
    date: "2024-01-08",
    type: "LC Review",
    supplier: "Global Textiles Inc.",
    status: "approved",
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

export default function ImporterDashboardV2() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "dashboard";
  const { toast } = useToast();
  const navigate = useNavigate();
  const { listDrafts, deleteDraft } = useDrafts();
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const { needsOnboarding, isLoading: isLoadingOnboarding } = useOnboarding();

  // Check onboarding status on mount
  useEffect(() => {
    if (!isLoadingOnboarding && needsOnboarding) {
      setShowOnboarding(true);
    }
  }, [needsOnboarding, isLoadingOnboarding]);

  useEffect(() => {
    loadDrafts();
  }, []);

  const loadDrafts = async () => {
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

  const handleDeleteDraft = async (draftId: string) => {
    try {
      await deleteDraft(draftId);
      setDrafts(drafts.filter((d) => d.draft_id !== draftId));
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
    if (draft.draft_type === "importer_draft") {
      navigate(`/lcopilot/import-upload?draft_id=${draft.draft_id}&type=draft`);
    } else {
      navigate(`/lcopilot/import-upload?draft_id=${draft.draft_id}&type=supplier`);
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

  const importerDrafts = drafts.filter((d) => d.draft_type === "importer_draft");
  const amendmentDrafts = drafts.filter((d) => d.draft_type === "importer_supplier");

  return (
    <>
      <DashboardLayout
        sidebar={<ImporterSidebar />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Importer Dashboard" },
        ]}
      >
        <div className="flex flex-col gap-6 p-6 lg:p-8">
          {/* Welcome Section */}
          <div>
            <h2 className="text-3xl font-bold text-foreground mb-2">
              Welcome back, Bangladesh Exports Ltd
            </h2>
            <p className="text-muted-foreground">
              Here's what's happening with your LC validations today.
            </p>
          </div>

          <Card className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Edit3 className="w-5 h-5" /> Your LC Workspace
              </CardTitle>
              <CardDescription>Resume drafts or track amendments that need attention</CardDescription>
            </CardHeader>
            <CardContent>
              {loadingDrafts ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  Loading drafts...
                </div>
              ) : (
                <Tabs defaultValue="drafts" className="w-full">
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
                        <div
                          key={draft.draft_id}
                          className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50"
                        >
                          <div className="flex items-center gap-4">
                            <div className="bg-importer/10 p-3 rounded-lg">
                              <Edit3 className="w-5 h-5 text-importer" />
                            </div>
                            <div>
                              <h4 className="font-semibold text-foreground">
                                {draft.lc_number || "Untitled Draft"}
                              </h4>
                              <p className="text-sm text-muted-foreground">
                                {draft.uploaded_docs.length} document
                                {draft.uploaded_docs.length !== 1 ? "s" : ""} uploaded
                              </p>
                              <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                Saved {formatTimeAgo(draft.updated_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleResumeDraft(draft)}
                              className="flex items-center gap-2"
                            >
                              <ArrowRight className="w-4 h-4" /> Resume
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteDraft(draft.draft_id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="amendments" className="mt-6 space-y-4">
                    {amendmentDrafts.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p>No amendments captured yet</p>
                        <p className="text-sm">Updates to supplier documents will appear here</p>
                      </div>
                    ) : (
                      amendmentDrafts.map((draft) => (
                        <div
                          key={draft.draft_id}
                          className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50"
                        >
                          <div className="flex items-center gap-4">
                            <div className="bg-importer/10 p-3 rounded-lg">
                              <GitBranch className="w-5 h-5 text-importer" />
                            </div>
                            <div>
                              <h4 className="font-semibold text-foreground">
                                {draft.lc_number || "Untitled Draft"}
                              </h4>
                              <p className="text-sm text-muted-foreground">
                                {draft.uploaded_docs.length} document
                                {draft.uploaded_docs.length !== 1 ? "s" : ""} updated
                              </p>
                              <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                Saved {formatTimeAgo(draft.updated_at)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleResumeDraft(draft)}
                              className="flex items-center gap-2"
                            >
                              <ArrowRight className="w-4 h-4" /> Resume
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteDraft(draft.draft_id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main Content */}
            <div className="lg:col-span-2">
              {/* Recent LC Reviews */}
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
                      <span className="text-sm text-muted-foreground">Total Reviews</span>
                      <span className="font-medium">{dashboardStats.totalReviews}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Documents Processed</span>
                      <span className="text-foreground font-medium">{dashboardStats.documentsProcessed}</span>
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
            description: "Welcome to LCopilot! You're all set to start reviewing supplier documents.",
          });
        }}
      />
    </>
  );
}
