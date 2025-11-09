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
      </div>
    </DashboardLayout>
  );
}

