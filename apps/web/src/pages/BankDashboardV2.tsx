import { useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { BankSidebar } from "@/components/bank/BankSidebar";
import { BankQuickStats } from "@/components/bank/BankQuickStats";
import { BulkLCUpload } from "@/components/bank/BulkLCUpload";
import { ProcessingQueue } from "@/components/bank/ProcessingQueue";
import { ResultsTable } from "@/components/bank/ResultsTable";
import { ClientManagement } from "@/components/bank/ClientManagement";
import { NotificationPreferences } from "@/components/bank/NotificationPreferences";
import { BankAnalytics } from "@/components/bank/BankAnalytics";
import { ApprovalsView } from "./bank/Approvals";
import { DiscrepanciesView } from "./bank/Discrepancies";
import { PolicySurface } from "./bank/PolicySurface";
import { BankNotificationsView } from "./bank/BankNotifications";
import { QueueOperationsView } from "./bank/QueueOperations";
import { SLADashboardsView } from "./bank/SLADashboards";
import { EvidencePacksView } from "./bank/EvidencePacks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useToast } from "@/hooks/use-toast";
import { CompanyProfileView } from "./settings/CompanyProfile";
import { DataRetentionView } from "./settings/DataRetention";

export default function BankDashboardV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => searchParams.get("tab") || "upload");

  // Sync activeTab with URL changes
  useEffect(() => {
    const tabFromUrl = searchParams.get("tab") || "upload";
    setActiveTab(tabFromUrl);
  }, [searchParams]);

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

  return (
    <DashboardLayout
      sidebar={<BankSidebar />}
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Bank Dashboard" },
      ]}
    >
      <div className="flex flex-col gap-6 p-6 lg:p-8">
        {/* Quick Stats */}
        <BankQuickStats />

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

        {activeTab === "notifications" && <BankNotificationsView embedded />}

        {activeTab === "settings" && <SettingsPanel />}

        {activeTab === "help" && <HelpPanel />}
      </div>
    </DashboardLayout>
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
        <CardTitle>Need Help?</CardTitle>
        <CardDescription>Browse bank resources, walkthroughs, and contact options.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <div className="flex flex-wrap gap-3">
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

