import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
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
import { 
  Upload, 
  FileText, 
  Download, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Eye,
  Bell,
  Settings,
  User,
  Plus,
  BarChart3,
  TrendingUp,
  Clock,
  Shield,
  FileCheck,
  Edit3,
  Trash2,
  ArrowRight
} from "lucide-react";

// Dashboard stats for importers
const dashboardStats = {
  thisMonth: 6,
  successRate: 91.7,
  avgProcessingTime: "2.8 minutes",
  risksIdentified: 3,
  totalReviews: 18,
  documentsProcessed: 54
};

const mockHistory = [
  { id: "1", date: "2024-01-18", type: "LC Review", supplier: "ABC Exports Ltd.", status: "approved", risks: 2 },
  { id: "2", date: "2024-01-12", type: "Document Check", supplier: "XYZ Trading Co.", status: "flagged", risks: 4 },
  { id: "3", date: "2024-01-08", type: "LC Review", supplier: "Global Textiles Inc.", status: "approved", risks: 1 },
];

const notifications = [
  {
    id: 1,
    title: "Import Regulations Update",
    message: "New customs requirements effective Feb 1st. Review your upcoming shipments.",
    type: "info" as const,
    timestamp: "2 hours ago"
  },
  {
    id: 2,
    title: "LC Review Complete",
    message: "Your draft LC has been reviewed with no critical risks identified.",
    type: "success" as const,
    timestamp: "5 hours ago"
  },
  {
    id: 3,
    title: "Risk Alert",
    message: "Unrealistic shipment date detected in LC-IMP-2024-003.",
    type: "warning" as const,
    timestamp: "1 day ago"
  }
];

export default function ImporterDashboard() {
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
      const importerDrafts = allDrafts.filter(d =>
        d.draft_type === 'importer_draft' || d.draft_type === 'importer_supplier'
      );
      setDrafts(importerDrafts);
    } catch (error) {
      console.error('Failed to load drafts:', error);
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
      setDrafts(drafts.filter(d => d.draft_id !== draftId));
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
    if (draft.draft_type === 'importer_draft') {
      navigate(`/lcopilot/import-upload?draft_id=${draft.draft_id}&type=draft`);
    } else {
      navigate(`/lcopilot/import-upload?draft_id=${draft.draft_id}&type=supplier`);
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;

    return date.toLocaleDateString();
  };

  const draftLCRisks = drafts.filter(d => d.draft_type === 'importer_draft');
  const supplierDrafts = drafts.filter(d => d.draft_type === 'importer_supplier');

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-gray-200 sticky top-0 z-50 backdrop-blur-sm bg-card/95">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="bg-gradient-importer p-2 rounded-lg">
                  <FileText className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">LCopilot</h1>
                  <p className="text-sm text-muted-foreground">Dashboard</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm">
                <Bell className="w-4 h-4 mr-2" />
                Notifications
                <Badge variant="destructive" className="ml-2 h-5 w-5 p-0 text-xs">3</Badge>
              </Button>
              <Button variant="outline" size="sm">
                <User className="w-4 h-4 mr-2" />
                Profile
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            Welcome back, Bangladesh Exports Ltd
          </h2>
          <p className="text-muted-foreground">
            Here's what's happening with your LC validations today.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <Link to="/lcopilot/import-upload" className="flex-1">
            <Button className="w-full h-16 bg-gradient-importer hover:opacity-90 text-left justify-start shadow-medium group">
              <div className="flex items-center gap-4">
                <div className="bg-white/20 p-3 rounded-lg group-hover:scale-110 transition-transform">
                  <Plus className="w-6 h-6" />
                </div>
                <div>
                  <div className="font-semibold">Upload LC</div>
                  <div className="text-sm opacity-90">Start validation process</div>
                </div>
              </div>
            </Button>
          </Link>
          <Link to="/lcopilot/importer-analytics" className="flex-1">
            <Button variant="outline" className="w-full h-16 text-left justify-start">
              <div className="flex items-center gap-4">
                <div className="bg-importer/10 p-3 rounded-lg">
                  <BarChart3 className="w-6 h-6 text-importer" />
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">This Month</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.thisMonth}</p>
                  <p className="text-xs text-success">+20% from last month</p>
                </div>
                <div className="bg-importer/10 p-3 rounded-lg">
                  <FileText className="w-6 h-6 text-importer" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
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

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Processing</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.avgProcessingTime}</p>
                  <p className="text-xs text-success">10s faster</p>
                </div>
                <div className="bg-info/10 p-3 rounded-lg">
                  <Clock className="w-6 h-6 text-info" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Risks Identified</p>
                  <p className="text-2xl font-bold text-foreground">{dashboardStats.risksIdentified}</p>
                  <p className="text-xs text-warning">Review required</p>
                </div>
                <div className="bg-warning/10 p-3 rounded-lg">
                  <AlertTriangle className="w-6 h-6 text-warning" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Your Drafts Section */}
        {(loadingDrafts || drafts.length > 0) && (
          <Card className="shadow-soft border-0 mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Edit3 className="w-5 h-5" />
                Your Drafts
              </CardTitle>
              <CardDescription>
                Resume your saved LC validations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingDrafts ? (
                <div className="flex items-center justify-center py-8">
                  <div className="text-muted-foreground">Loading drafts...</div>
                </div>
              ) : (
                <Tabs defaultValue="draft-lc" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="draft-lc" className="flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Draft LC Risk ({draftLCRisks.length})
                    </TabsTrigger>
                    <TabsTrigger value="supplier-docs" className="flex items-center gap-2">
                      <FileCheck className="w-4 h-4" />
                      Supplier Documents ({supplierDrafts.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="draft-lc" className="mt-6">
                    {draftLCRisks.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p>No draft LC validations saved</p>
                        <p className="text-sm">Start a new validation to create a draft</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {draftLCRisks.map((draft) => (
                          <div key={draft.draft_id} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                            <div className="flex items-center gap-4">
                              <div className="bg-importer/10 p-3 rounded-lg">
                                <FileText className="w-5 h-5 text-importer" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-foreground">
                                  {draft.lc_number || 'Untitled Draft'}
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                  {draft.uploaded_docs.length} document{draft.uploaded_docs.length !== 1 ? 's' : ''} uploaded
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-xs text-muted-foreground">
                                    Saved {formatTimeAgo(draft.updated_at)}
                                  </span>
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
                                <ArrowRight className="w-4 h-4" />
                                Resume
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
                        ))}
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="supplier-docs" className="mt-6">
                    {supplierDrafts.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <FileCheck className="w-12 h-12 mx-auto mb-4 opacity-20" />
                        <p>No supplier document drafts saved</p>
                        <p className="text-sm">Start a new validation to create a draft</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {supplierDrafts.map((draft) => (
                          <div key={draft.draft_id} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
                            <div className="flex items-center gap-4">
                              <div className="bg-importer/10 p-3 rounded-lg">
                                <FileCheck className="w-5 h-5 text-importer" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-foreground">
                                  {draft.lc_number || 'Untitled Draft'}
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                  {draft.uploaded_docs.length} document{draft.uploaded_docs.length !== 1 ? 's' : ''} uploaded
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-xs text-muted-foreground">
                                    Saved {formatTimeAgo(draft.updated_at)}
                                  </span>
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
                                <ArrowRight className="w-4 h-4" />
                                Resume
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
                        ))}
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {/* Recent LC Reviews */}
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Recent LC Validations
                </CardTitle>
                <CardDescription>
                  Your latest document validation results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {mockHistory.map((item) => (
                    <div key={item.id} className="flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
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
                          <h4 className="font-semibold text-foreground">{item.type} #{item.id}</h4>
                          <p className="text-sm text-muted-foreground">Supplier: {item.supplier}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-muted-foreground">{item.date}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <StatusBadge status={item.status === "approved" ? "success" : "warning"}>
                            {item.risks === 0 ? "No issues" : 
                             item.risks === 1 ? "1 issue" : `${item.risks} issues`}
                          </StatusBadge>
                        </div>
                        <Button variant="outline" size="sm">
                          <Eye className="w-4 h-4 mr-2" />
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
                <CardDescription>
                  Updates and alerts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {notifications.map((notification) => (
                    <div key={notification.id} className="p-3 rounded-lg border border-gray-200/50">
                      <div className="flex items-start gap-3">
                        <div className={`p-1 rounded-full ${
                          notification.type === "success" ? "bg-success/10" :
                          notification.type === "warning" ? "bg-warning/10" : "bg-info/10"
                        }`}>
                          <div className={`w-2 h-2 rounded-full ${
                            notification.type === "success" ? "bg-success" :
                            notification.type === "warning" ? "bg-warning" : "bg-info"
                          }`} />
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
    </div>
  );
}