import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/use-auth";
import { BulkLCUpload } from "@/components/bank/BulkLCUpload";
import { ProcessingQueue } from "@/components/bank/ProcessingQueue";
import { ResultsTable } from "@/components/bank/ResultsTable";
import { BankQuickStats } from "@/components/bank/BankQuickStats";
import {
  FileText,
  Upload,
  BarChart3,
  Clock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

export default function BankDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("upload");

  // Check if user is a bank user
  // Frontend maps bank_officer and bank_admin to "bank" role
  const isBankUser = user && user.role === "bank";

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
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-8">
          <TabsList className="grid w-full grid-cols-3 max-w-2xl">
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
          </TabsList>

          <TabsContent value="upload" className="mt-6">
            <BulkLCUpload onUploadSuccess={() => setActiveTab("queue")} />
          </TabsContent>

          <TabsContent value="queue" className="mt-6">
            <ProcessingQueue onJobComplete={() => setActiveTab("results")} />
          </TabsContent>

          <TabsContent value="results" className="mt-6">
            <ResultsTable />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
