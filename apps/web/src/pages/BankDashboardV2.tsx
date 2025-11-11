import { useSearchParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { BankSidebar } from "@/components/bank/BankSidebar";
import { BankQuickStats } from "@/components/bank/BankQuickStats";
import { BulkLCUpload } from "@/components/bank/BulkLCUpload";
import { ProcessingQueue } from "@/components/bank/ProcessingQueue";
import { ResultsTable } from "@/components/bank/ResultsTable";
import { ClientManagement } from "@/components/bank/ClientManagement";
import { ClientDashboardView } from "@/components/bank/ClientDashboardView";
import { NotificationPreferences } from "@/components/bank/NotificationPreferences";
import { BankAnalytics } from "@/components/bank/BankAnalytics";
import { ApprovalsView } from "./bank/Approvals";
import { DiscrepanciesView } from "./bank/Discrepancies";
import { PolicySurface } from "./bank/PolicySurface";
import { BankNotificationsView } from "./bank/BankNotifications";
import { QueueOperationsView } from "./bank/QueueOperations";
import { SLADashboardsView } from "./bank/SLADashboards";
import { EvidencePacksView } from "./bank/EvidencePacks";
import { HealthLatencyBanner } from "@/components/bank/HealthLatencyBanner";
import { SupportTicketForm } from "@/components/shared/SupportTicketForm";
import { AIAssistance } from "@/components/bank/AIAssistance";
import { BillingOverviewPage } from "./BillingOverviewPage";
import { BillingUsagePage } from "./BillingUsagePage";
import { BillingInvoicesPage } from "./BillingInvoicesPage";
import { BillingAllocationsPage } from "./BillingAllocationsPage";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useToast } from "@/hooks/use-toast";
import { useBankAuth } from "@/lib/bank/auth";
import { CompanyProfileView } from "./settings/CompanyProfile";
import { DataRetentionView } from "./settings/DataRetention";
import { FileText, CheckCircle, AlertTriangle, Clock, Bell, ArrowLeft } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { NotificationList } from "@/components/notifications/NotificationItem";
import { BulkJobsView } from "./bank/BulkJobs";
import { IntegrationsPage } from "@/components/bank/integrations/IntegrationsPage";
import { OrgProvider } from "@/contexts/OrgContext";

export default function BankDashboardV2() {
  const { user: bankUser, isAuthenticated, isLoading: authLoading } = useBankAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => searchParams.get("tab") || "dashboard");
  const [billingTab, setBillingTab] = useState<string>("overview");
  const isBankAdmin = bankUser?.role === 'bank_admin';

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/lcopilot/bank-dashboard/login");
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Sync activeTab with URL changes
  useEffect(() => {
    const tabFromUrl = searchParams.get("tab") || "dashboard";
    setActiveTab(tabFromUrl);
  }, [searchParams]);

  // Redirect non-admins away from users tab
  useEffect(() => {
    if (activeTab === "users" && !isBankAdmin) {
      setActiveTab("dashboard");
      navigate("/lcopilot/bank-dashboard?tab=dashboard", { replace: true });
    }
  }, [activeTab, isBankAdmin, navigate]);

  // Redirect non-admins away from policy tab (optional hardening)
  useEffect(() => {
    if (activeTab === "policy" && !isBankAdmin) {
      setActiveTab("dashboard");
      navigate("/lcopilot/bank-dashboard?tab=dashboard", { replace: true });
    }
  }, [activeTab, isBankAdmin, navigate]);

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render dashboard if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    const newParams = new URLSearchParams(searchParams);
    newParams.set("tab", newTab);
    // Remove client filter if not navigating to results
    if (newTab !== "results") {
      newParams.delete("client");
    }
    setSearchParams(newParams);
  };

  const handleBillingTabChange = (tab: string) => {
    setBillingTab(tab);
    const tabMap: Record<string, string> = {
      overview: "billing",
      usage: "billing-usage",
      invoices: "billing", // Stay in billing tab, but track subtab
      allocations: "billing-allocations",
    };
    const newTab = tabMap[tab] || "billing";
    handleTabChange(newTab);
  };

  return (
    <OrgProvider>
      <DashboardLayout
        sidebar={<BankSidebar />}
        breadcrumbs={[
          { label: "LCopilot", href: "/lcopilot" },
          { label: "Bank Dashboard" },
        ]}
      >
      <div className="flex flex-col gap-6 p-6 lg:p-8">
        {/* Health/Latency Banner - Only show on dashboard tab */}
        {activeTab === "dashboard" && <HealthLatencyBanner />}
        
        {/* Dashboard Tab - Shows Welcome, Stats, Recent Validations, Notifications */}
        {activeTab === "dashboard" && <DashboardOverview />}

        {/* Dynamic Content Based on Tab */}
        {activeTab === "upload" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Upload LC Documents</h2>
              <p className="text-sm text-muted-foreground">
                Upload single or bulk LC documents for validation
              </p>
            </div>
            <BulkLCUpload onUploadSuccess={() => handleTabChange("queue")} />
          </div>
        )}

        {activeTab === "queue" && (
          <QueueOperationsView embedded />
        )}

        {activeTab === "results" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Validation Results</h2>
              <p className="text-sm text-muted-foreground">
                View and filter completed LC validations
              </p>
            </div>
            <ResultsTable />
          </div>
        )}

        {activeTab === "clients" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Client Management</h2>
              <p className="text-sm text-muted-foreground">
                View client statistics and performance metrics
              </p>
            </div>
            <ClientManagement />
          </div>
        )}

        {activeTab === "client-dashboard" && (() => {
          const clientName = searchParams.get("client");
          if (!clientName) {
            return (
              <Card>
                <CardContent className="pt-6">
                  <p className="text-destructive">Client name is required</p>
                  <Button onClick={() => handleTabChange("clients")} className="mt-4">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Clients
                  </Button>
                </CardContent>
              </Card>
            );
          }
          return (
            <ClientDashboardView
              clientName={decodeURIComponent(clientName)}
              embedded
              onBack={() => handleTabChange("clients")}
            />
          );
        })()}

        {activeTab === "analytics" && (
          <div className="space-y-4">
            <BankAnalytics />
          </div>
        )}

        {activeTab === "sla" && <SLADashboardsView embedded />}

        {activeTab === "approvals" && <ApprovalsView embedded />}

        {activeTab === "discrepancies" && <DiscrepanciesView embedded />}

        {activeTab === "policy" && <PolicySurface embedded />}

        {activeTab === "evidence-packs" && <EvidencePacksView embedded />}

        {activeTab === "bulk-jobs" && <BulkJobsView embedded />}

        {activeTab === "notifications" && <BankNotificationsView embedded />}

        {activeTab === "billing" && (
          billingTab === "invoices" ? (
            <BillingInvoicesPage onTabChange={handleBillingTabChange} mode="bank" />
          ) : (
            <BillingOverviewPage onTabChange={handleBillingTabChange} mode="bank" />
          )
        )}

        {activeTab === "billing-usage" && <BillingUsagePage onTabChange={handleBillingTabChange} mode="bank" />}

        {activeTab === "billing-allocations" && <BillingAllocationsPage onTabChange={handleBillingTabChange} />}

        {activeTab === "users" && isBankAdmin && <BankUsersPage />}

        {activeTab === "settings" && <SettingsPanel />}

        {activeTab === "ai-assistance" && <AIAssistance embedded />}

        {activeTab === "integrations" && <IntegrationsPage embedded />}

        {activeTab === "help" && <HelpPanel />}
      </div>
    </DashboardLayout>
    </OrgProvider>
  );
}

// Mock data for dashboard
const mockRecentValidations = [
  {
    id: "LC-BNK-2024-001",
    lcNumber: "LC-BNK-2024-001",
    clientName: "Global Exports Inc.",
    date: "2024-01-15",
    status: "approved",
    discrepancies: 0,
    complianceScore: 98,
  },
  {
    id: "LC-BNK-2024-002",
    lcNumber: "LC-BNK-2024-002",
    clientName: "Dhaka Trading Co.",
    date: "2024-01-14",
    status: "flagged",
    discrepancies: 2,
    complianceScore: 85,
  },
  {
    id: "LC-BNK-2024-003",
    lcNumber: "LC-BNK-2024-003",
    clientName: "Chittagong Imports",
    date: "2024-01-14",
    status: "approved",
    discrepancies: 0,
    complianceScore: 96,
  },
];

const mockBankNotifications = [
  {
    id: 1,
    title: "Approval Required",
    message: "LC-BNK-2024-001 requires your approval at Analyst Review stage.",
    type: "approval" as const,
    timestamp: "15 minutes ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=approvals&lc=LC-BNK-2024-001",
    badge: "Pending",
    action: {
      label: "Review Approval",
      action: () => {},
    },
  },
  {
    id: 2,
    title: "Discrepancy Assigned",
    message: "You have been assigned to resolve discrepancy in LC-BNK-2024-002.",
    type: "discrepancy" as const,
    timestamp: "1 hour ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=discrepancies&lc=LC-BNK-2024-002",
    badge: "High Priority",
    action: {
      label: "View Discrepancy",
      action: () => {},
      variant: "destructive" as const,
    },
  },
  {
    id: 3,
    title: "Validation Complete",
    message: "LC-BNK-2024-003 validation completed successfully with no issues.",
    type: "success" as const,
    timestamp: "3 hours ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=results&lc=LC-BNK-2024-003",
    action: {
      label: "View Results",
      action: () => {},
    },
  },
];

function DashboardOverview() {
  const { user: bankUser } = useBankAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState(mockBankNotifications);

  const handleMarkAsRead = (id: string | number) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const handleDismiss = (id: string | number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">
          Welcome back, {bankUser?.name || bankUser?.email?.split("@")[0] || "Bank User"}
        </h2>
        <p className="text-muted-foreground">
          Here's what's happening with your LC validations today.
        </p>
      </div>

      {/* Quick Stats */}
      <BankQuickStats />

      {/* Recent Validations and Notifications */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
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
                {mockRecentValidations.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-4 rounded-lg border bg-secondary/20"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex-shrink-0">
                        {item.status === "approved" ? (
                          <div className="bg-green-500/10 p-2 rounded-lg">
                            <CheckCircle className="w-5 h-5 text-green-500" />
                          </div>
                        ) : (
                          <div className="bg-yellow-500/10 p-2 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-yellow-500" />
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground">{item.lcNumber}</h4>
                        <p className="text-sm text-muted-foreground">Client: {item.clientName}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>{item.date}</span>
                          <span>•</span>
                          <span>Score: {item.complianceScore}%</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={item.discrepancies === 0 ? "success" : "warning"}>
                        {item.discrepancies === 0
                          ? "No issues"
                          : item.discrepancies === 1
                          ? "1 issue"
                          : `${item.discrepancies} issues`}
                      </StatusBadge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/lcopilot/bank-dashboard?tab=results&lc=${item.lcNumber}`)}
                      >
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
              <CardDescription>Recent updates and alerts</CardDescription>
            </CardHeader>
            <CardContent>
              <NotificationList
                notifications={notifications.slice(0, 3)}
                onMarkAsRead={handleMarkAsRead}
                onDismiss={handleDismiss}
                onMarkAllAsRead={handleMarkAllAsRead}
                showHeader={false}
              />
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-4"
                onClick={() => navigate("/lcopilot/bank-dashboard?tab=notifications")}
              >
                View All Notifications
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function SettingsPanel() {
  const { toast } = useToast();
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [autoArchiveResults, setAutoArchiveResults] = useState(false);
  const [digestFrequency, setDigestFrequency] = useState("daily");
  const [defaultView, setDefaultView] = useState<string>("upload");
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("preferences");

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast({
        title: "Preferences updated",
        description: "Your bank workspace settings were saved successfully.",
      });
    }, 600);
  };

  const handleReset = () => {
    setEmailAlerts(true);
    setAutoArchiveResults(false);
    setDigestFrequency("daily");
    setDefaultView("upload");
  };

  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle>Settings</CardTitle>
        <CardDescription>Configure bank workspace preferences and data retention.</CardDescription>
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
                  <p className="text-sm font-medium text-foreground">Auto-archive completed validations</p>
                  <p className="text-xs text-muted-foreground">Move completed validations to archive 30 days after completion.</p>
                </div>
                <Switch checked={autoArchiveResults} onCheckedChange={setAutoArchiveResults} aria-label="Toggle auto archive" />
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
                <Select value={defaultView} onValueChange={setDefaultView}>
                  <SelectTrigger id="default-view">
                    <SelectValue placeholder="Select default view" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="upload">Upload LC</SelectItem>
                    <SelectItem value="queue">Processing Queue</SelectItem>
                    <SelectItem value="results">Results</SelectItem>
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
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Need Help?</CardTitle>
            <CardDescription>Browse bank resources, walkthroughs, and contact options.</CardDescription>
          </div>
          <InAppTutorials dashboard="bank" />
        </div>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap gap-3">
          <SupportTicketForm />
          <Button variant="outline" onClick={() => window.open("/lcopilot/support", "_blank")}>Support Center</Button>
          <Button variant="outline" onClick={() => window.open("/docs/bank-runbook", "_blank")}>Bank Runbook</Button>
          <Button variant="outline" onClick={() => window.open("mailto:support@trdrhub.com")}>Email Support</Button>
        </div>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="faq-1">
            <AccordionTrigger>How do I upload and validate LC documents?</AccordionTrigger>
            <AccordionContent>
              Select <span className="font-medium">Upload LC</span>, attach the LC and supporting documents, then submit for validation. 
              Track progress in <span className="font-medium">Processing Queue</span> and view results under <span className="font-medium">Results</span>.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-2">
            <AccordionTrigger>How do I manage approvals and discrepancies?</AccordionTrigger>
            <AccordionContent>
              Use the <span className="font-medium">Approvals</span> tab to review and approve LC validations. 
              The <span className="font-medium">Discrepancies</span> tab shows flagged issues that need resolution.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="faq-3">
            <AccordionTrigger>Who receives notifications?</AccordionTrigger>
            <AccordionContent>
              Notification recipients are defined in <span className="font-medium">Settings</span>. Enable
              email alerts or set digest frequency to control how your team is notified of validations, approvals, and discrepancies.
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="rounded-lg border border-gray-200/60 bg-secondary/20 p-4">
          <p className="text-xs">
            Need a guided walkthrough? Schedule a 30-minute onboarding session with our success team and we&apos;ll review
            your bank workflow end-to-end.
          </p>
          <Button
            size="sm"
            className="mt-3"
            onClick={() => window.open("https://cal.com/trdrhub/bank-onboarding", "_blank")}
          >
            Book onboarding session
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

