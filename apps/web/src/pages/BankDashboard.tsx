import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/use-auth";
import { useQuery } from "@tanstack/react-query";
import { getStubStatus } from "@/api/sessions";
import { BulkLCUpload } from "@/components/bank/BulkLCUpload";
import { ProcessingQueue } from "@/components/bank/ProcessingQueue";
import { ResultsTable } from "@/components/bank/ResultsTable";
import { BankQuickStats } from "@/components/bank/BankQuickStats";
import { ClientManagement } from "@/components/bank/ClientManagement";
import {
  FileText,
  Upload,
  BarChart3,
  Clock,
  CheckCircle,
  AlertTriangle,
  Users,
} from "lucide-react";

export default function BankDashboard() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get("tab") || "upload";
  const [activeTab, setActiveTab] = useState(tabFromUrl);

  // Check if stub mode is enabled
  const { data: stubStatus } = useQuery({
    queryKey: ['stub-status'],
    queryFn: getStubStatus,
    retry: false,
  });

  const isStubMode = stubStatus?.stub_mode_enabled || false;

  // Check if user is a bank user
  // Frontend maps bank_officer and bank_admin to "bank" role
  // In stub mode, allow access regardless of role
  const isBankUser = isStubMode || (user && user.role === "bank");

  // Update tab when URL changes
  useEffect(() => {
    const tabFromUrl = searchParams.get("tab") || "upload";
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams, activeTab]);

  // Update URL when tab changes
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

  if (!isBankUser) {
    return (
      <div className="container mx-auto py-6">
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>Access Restricted</CardTitle>
            <CardDescription>
              This dashboard is only available for bank users.
              {user && (
                <span className="block mt-2 text-xs">
                  Your role: {user.role}
                </span>
              )}
              {!isStubMode && (
                <span className="block mt-2 text-xs text-muted-foreground">
                  Stub mode is disabled. Enable stub mode to bypass authentication.
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/lcopilot">Go to LCopilot</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b sticky top-0 z-50 backdrop-blur-sm bg-card/95">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <FileText className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">Bank LC Validation</h1>
                  <p className="text-sm text-muted-foreground">Bulk validation dashboard</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" asChild>
                <Link to="/lcopilot/analytics/bank">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  System Analytics
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Quick Stats */}
        <BankQuickStats />

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-8">
          <TabsList className="grid w-full grid-cols-4 max-w-3xl">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload LC
            </TabsTrigger>
            <TabsTrigger value="queue" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Processing Queue
            </TabsTrigger>
            <TabsTrigger value="results" className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Results
            </TabsTrigger>
            <TabsTrigger value="clients" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Clients
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="mt-6">
            <BulkLCUpload onUploadSuccess={() => handleTabChange("queue")} />
          </TabsContent>

          <TabsContent value="queue" className="mt-6">
            <ProcessingQueue onJobComplete={() => handleTabChange("results")} />
          </TabsContent>

          <TabsContent value="results" className="mt-6">
            <ResultsTable />
          </TabsContent>

          <TabsContent value="clients" className="mt-6">
            <ClientManagement />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
