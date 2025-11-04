import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Eye,
  Download,
  Users,
  BarChart3,
} from "lucide-react";
import { format } from "date-fns";
import { bankApi, BankResult } from "@/api/bank";
import { sanitizeDisplayText } from "@/lib/sanitize";
import { LCResultDetailModal } from "@/components/bank/LCResultDetailModal";
import { useToast } from "@/hooks/use-toast";

export default function ClientDashboard() {
  const { clientName } = useParams<{ clientName: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [dateRange, setDateRange] = useState("90"); // days
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedClientName, setSelectedClientName] = useState<string | undefined>();
  const [selectedLcNumber, setSelectedLcNumber] = useState<string | undefined>();

  // Calculate date range for API
  const getDateRange = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - parseInt(dateRange));
    return {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    };
  };

  // Fetch client dashboard data
  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ['client-dashboard', clientName, dateRange],
    queryFn: () => {
      if (!clientName) throw new Error("Client name is required");
      return bankApi.getClientDashboard(clientName, getDateRange());
    },
    enabled: !!clientName,
    staleTime: 30 * 1000, // Cache for 30 seconds
  });

  if (!clientName) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-destructive">Client name is required</p>
            <Button onClick={() => navigate('/lcopilot/bank-dashboard?tab=clients')} className="mt-4">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Clients
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardHeader>
            <CardTitle>Loading Client Dashboard</CardTitle>
            <CardDescription>Loading data for {sanitizeDisplayText(clientName)}...</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-12">
              <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4 animate-pulse" />
              <p className="text-muted-foreground">Loading dashboard...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !dashboardData) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardHeader>
            <CardTitle>Error Loading Dashboard</CardTitle>
            <CardDescription>Failed to load client dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 mx-auto text-destructive mb-4" />
              <p className="text-destructive mb-4">
                {error instanceof Error ? error.message : "Failed to load client dashboard"}
              </p>
              <div className="flex gap-2 justify-center">
                <Button onClick={() => navigate('/lcopilot/bank-dashboard?tab=clients')}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Clients
                </Button>
                <Button variant="outline" onClick={() => window.location.reload()}>
                  Retry
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = dashboardData.statistics;
  const lcResults = dashboardData.lc_results;
  const trendData = dashboardData.trend_data;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "compliant":
        return <Badge variant="default" className="bg-green-500">Compliant</Badge>;
      case "discrepancies":
        return <Badge variant="default" className="bg-yellow-500">Discrepancies</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const handleViewDetails = (result: BankResult) => {
    setSelectedJobId(result.jobId);
    setSelectedClientName(result.client_name);
    setSelectedLcNumber(result.lc_number);
  };

  const handleDownloadPDF = async (result: BankResult) => {
    try {
      const { getReportDownloadUrl } = await import("@/api/sessions");
      const reportData = await getReportDownloadUrl(result.jobId);
      window.open(reportData.download_url, "_blank");
    } catch (error: any) {
      console.error("Failed to download report:", error);
      toast({
        title: "Download Failed",
        description: "Failed to download report. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Calculate trend indicators
  const recentTrend = trendData.length >= 2
    ? trendData.slice(-7) // Last 7 days
    : [];
  
  const avgScoreTrend = recentTrend.length >= 2
    ? recentTrend[recentTrend.length - 1].avg_compliance_score - recentTrend[0].avg_compliance_score
    : 0;

  const complianceRateTrend = recentTrend.length >= 2
    ? (recentTrend[recentTrend.length - 1].compliant / Math.max(recentTrend[recentTrend.length - 1].validations, 1) * 100) -
      (recentTrend[0].compliant / Math.max(recentTrend[0].validations, 1) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b sticky top-0 z-50 backdrop-blur-sm bg-card/95">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/lcopilot/bank-dashboard?tab=clients')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Clients
              </Button>
              <div className="flex items-center gap-3">
                <div className="bg-gradient-primary p-2 rounded-lg">
                  <Users className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-foreground">
                    {sanitizeDisplayText(dashboardData.client_name)}
                  </h1>
                  <p className="text-sm text-muted-foreground">Client Performance Dashboard</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" asChild>
                <Link to={`/lcopilot/bank-dashboard?tab=results&client=${encodeURIComponent(clientName)}`}>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  View All Results
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Date Range Filter */}
        <div className="mb-6">
          <Label>Date Range</Label>
          <Select value={dateRange} onValueChange={setDateRange} className="w-48 mt-2">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
              <SelectItem value="180">Last 180 days</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Performance Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Validations</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_validations}</div>
              <p className="text-xs text-muted-foreground">
                {stats.first_validation_date && stats.last_validation_date
                  ? `Since ${format(new Date(stats.first_validation_date), "MMM d, yyyy")}`
                  : "All time"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Compliance Rate</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.compliance_rate.toFixed(1)}%</div>
              <div className="flex items-center gap-1 text-xs mt-1">
                {complianceRateTrend > 0 ? (
                  <>
                    <TrendingUp className="h-3 w-3 text-green-600" />
                    <span className="text-green-600">+{complianceRateTrend.toFixed(1)}%</span>
                  </>
                ) : complianceRateTrend < 0 ? (
                  <>
                    <TrendingDown className="h-3 w-3 text-red-600" />
                    <span className="text-red-600">{complianceRateTrend.toFixed(1)}%</span>
                  </>
                ) : (
                  <span className="text-muted-foreground">No change</span>
                )}
                <span className="text-muted-foreground">vs last 7 days</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Compliance Score</CardTitle>
              <BarChart3 className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.average_compliance_score.toFixed(1)}%</div>
              <div className="flex items-center gap-1 text-xs mt-1">
                {avgScoreTrend > 0 ? (
                  <>
                    <TrendingUp className="h-3 w-3 text-green-600" />
                    <span className="text-green-600">+{avgScoreTrend.toFixed(1)}%</span>
                  </>
                ) : avgScoreTrend < 0 ? (
                  <>
                    <TrendingDown className="h-3 w-3 text-red-600" />
                    <span className="text-red-600">{avgScoreTrend.toFixed(1)}%</span>
                  </>
                ) : (
                  <span className="text-muted-foreground">No change</span>
                )}
                <span className="text-muted-foreground">vs last 7 days</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
              <Clock className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.average_processing_time_seconds
                  ? `${stats.average_processing_time_seconds.toFixed(1)}s`
                  : "N/A"}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Per validation</p>
            </CardContent>
          </Card>
        </div>

        {/* Status Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                Compliant
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{stats.compliant_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {((stats.compliant_count / stats.total_validations) * 100).toFixed(1)}% of total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                With Discrepancies
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{stats.discrepancies_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {((stats.discrepancies_count / stats.total_validations) * 100).toFixed(1)}% of total
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.total_discrepancies} total discrepancies
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-600" />
                Failed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{stats.failed_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {((stats.failed_count / stats.total_validations) * 100).toFixed(1)}% of total
              </p>
            </CardContent>
          </Card>
        </div>

        {/* LC Results Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>LC Validation Results</CardTitle>
                <CardDescription>
                  {lcResults.length} validation{lcResults.length !== 1 ? 's' : ''} found
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {lcResults.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No validation results found</p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>LC Number</TableHead>
                      <TableHead>Date Received</TableHead>
                      <TableHead>Completed</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="text-right">Discrepancies</TableHead>
                      <TableHead className="text-right">Documents</TableHead>
                      <TableHead className="text-right">Processing Time</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lcResults.map((result) => {
                      const completedAt = result.completed_at ? new Date(result.completed_at) : new Date();
                      const lcNumber = sanitizeDisplayText(result.lc_number, "N/A");
                      const dateReceived = result.date_received || "";

                      return (
                        <TableRow key={result.id}>
                          <TableCell className="font-medium">{lcNumber}</TableCell>
                          <TableCell>{dateReceived || "N/A"}</TableCell>
                          <TableCell>
                            {format(completedAt, "MMM dd, yyyy HH:mm")}
                          </TableCell>
                          <TableCell>{getStatusBadge(result.status)}</TableCell>
                          <TableCell className="text-right">
                            {result.compliance_score}%
                          </TableCell>
                          <TableCell className="text-right">
                            {result.discrepancy_count}
                          </TableCell>
                          <TableCell className="text-right">
                            {result.document_count}
                          </TableCell>
                          <TableCell className="text-right">
                            {result.processing_time_seconds !== undefined && result.processing_time_seconds !== null
                              ? `${result.processing_time_seconds}s`
                              : "N/A"}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewDetails(result)}
                                title="View Details"
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDownloadPDF(result)}
                                title="Download PDF Report"
                              >
                                <Download className="w-4 h-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <LCResultDetailModal
        jobId={selectedJobId}
        open={!!selectedJobId}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedJobId(null);
            setSelectedClientName(undefined);
            setSelectedLcNumber(undefined);
          }
        }}
        clientName={selectedClientName}
        lcNumber={selectedLcNumber}
      />
    </div>
  );
}

