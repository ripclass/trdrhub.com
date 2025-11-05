import { useSearchParams } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ImporterSidebar } from "@/components/importer/ImporterSidebar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ImporterDashboardV2() {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "upload";

  return (
    <DashboardLayout
      sidebar={<ImporterSidebar />}
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Importer Dashboard" },
      ]}
    >
      <div className="flex flex-col gap-6 p-6 lg:p-8">
        {activeTab === "upload" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Upload LC for Review</h2>
              <p className="text-sm text-muted-foreground">
                Upload Letter of Credit documents for compliance review
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Upload Coming Soon</CardTitle>
                <CardDescription>
                  Importer LC upload functionality will be available here
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  This feature is under development. You'll be able to upload LC documents
                  for review and compliance checking.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "queue" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Processing Queue</h2>
              <p className="text-sm text-muted-foreground">
                Monitor active review jobs and their status
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Queue View</CardTitle>
                <CardDescription>No active processing jobs</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Your LC review requests will appear here while being processed.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "results" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Review Results</h2>
              <p className="text-sm text-muted-foreground">
                View completed LC reviews and compliance reports
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Results</CardTitle>
                <CardDescription>No completed reviews yet</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Completed LC reviews will be listed here with detailed compliance reports.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Analytics</h2>
              <p className="text-sm text-muted-foreground">
                Review trends and compliance metrics
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Analytics Dashboard</CardTitle>
                <CardDescription>Coming soon</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Detailed analytics and trends will be available here.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "notifications" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Notifications</h2>
              <p className="text-sm text-muted-foreground">
                Manage notification preferences
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Notification Settings</CardTitle>
                <CardDescription>Configure alerts and updates</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Notification preferences will be available here.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-1">Settings</h2>
              <p className="text-sm text-muted-foreground">
                Configure dashboard preferences
              </p>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Dashboard Settings</CardTitle>
                <CardDescription>Customize your experience</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Settings options will be available here.
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

