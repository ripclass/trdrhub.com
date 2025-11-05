import { useSearchParams } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { BankSidebar } from "@/components/bank/BankSidebar";
import { BankQuickStats } from "@/components/bank/BankQuickStats";
import { BulkLCUpload } from "@/components/bank/BulkLCUpload";
import { ProcessingQueue } from "@/components/bank/ProcessingQueue";
import { ResultsTable } from "@/components/bank/ResultsTable";
import { ClientManagement } from "@/components/bank/ClientManagement";
import { NotificationPreferences } from "@/components/bank/NotificationPreferences";
import { BankAnalytics } from "@/components/bank/BankAnalytics";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export default function BankDashboardV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "upload";

  const handleTabChange = (newTab: string) => {
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
        { label: "Bank Dashboard V2" },
      ]}
      actions={
        <>
          <Badge variant="outline" className="text-xs">
            New Layout
          </Badge>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/lcopilot/bank-dashboard">
              <ArrowLeft className="w-4 h-4 mr-1" />
              Old Layout
            </Link>
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-6 p-4 lg:p-6">
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
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Processing Queue</h2>
              <p className="text-sm text-muted-foreground">
                Monitor active validation jobs and their status
              </p>
            </div>
            <ProcessingQueue onJobComplete={() => handleTabChange("results")} />
          </div>
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

        {activeTab === "notifications" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Notification Preferences</h2>
              <p className="text-sm text-muted-foreground">
                Configure email and SMS alerts for validations
              </p>
            </div>
            <NotificationPreferences />
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

