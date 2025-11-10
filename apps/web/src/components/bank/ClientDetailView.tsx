/**
 * Client Detail View Component
 * 
 * Shows detailed KPIs, trends, recent issues, and duplicates heatmap for a specific client.
 * Used in expandable rows in ClientManagement.
 */

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { bankApi, BankResult } from "@/api/bank";
import { format } from "date-fns";
import { TrendingUp, TrendingDown, AlertCircle, Activity, Copy, Clock, BarChart3, FileText, CheckCircle } from "lucide-react";
import { sanitizeDisplayText } from "@/lib/sanitize";

interface ClientDetailViewProps {
  clientName: string;
  clientStats: {
    total_validations: number;
    compliance_rate: number;
    average_compliance_score: number;
    total_discrepancies: number;
    discrepancies_count: number;
    compliant_count: number;
    failed_count: number;
  };
}

export function ClientDetailView({ clientName, clientStats }: ClientDetailViewProps) {
  // Fetch detailed client dashboard data
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['client-dashboard-detail', clientName],
    queryFn: () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 90); // Last 90 days
      return bankApi.getClientDashboard(clientName, {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      });
    },
    enabled: !!clientName,
    staleTime: 60 * 1000, // Cache for 1 minute
  });

  if (isLoading) {
    return (
      <div className="p-4 border-t bg-muted/30">
        <div className="text-center py-4 text-muted-foreground">Loading client details...</div>
      </div>
    );
  }

  const trendData = dashboardData?.trend_data || [];
  const lcResults = dashboardData?.lc_results || [];

  // Calculate trends (comparing last 30 days vs previous 30 days)
  const recentTrends = trendData.slice(-30);
  const previousTrends = trendData.slice(-60, -30);
  
  const recentAvgCompliance = recentTrends.length > 0
    ? recentTrends.reduce((sum, t) => sum + t.avg_compliance_score, 0) / recentTrends.length
    : 0;
  const previousAvgCompliance = previousTrends.length > 0
    ? previousTrends.reduce((sum, t) => sum + t.avg_compliance_score, 0) / previousTrends.length
    : 0;
  
  const complianceTrend = recentAvgCompliance - previousAvgCompliance;
  const complianceTrendPercent = previousAvgCompliance > 0
    ? ((complianceTrend / previousAvgCompliance) * 100).toFixed(1)
    : "0.0";

  // Recent issues (LCs with discrepancies in last 7 days)
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const recentIssues = lcResults
    .filter(r => {
      const completedAt = r.completed_at ? new Date(r.completed_at) : null;
      return completedAt && completedAt >= sevenDaysAgo && r.discrepancy_count > 0;
    })
    .slice(0, 5);

  // Duplicates heatmap (group by LC number)
  const lcGroups: Record<string, BankResult[]> = {};
  lcResults.forEach(result => {
    const lcNum = result.lc_number || "Unknown";
    if (!lcGroups[lcNum]) {
      lcGroups[lcNum] = [];
    }
    lcGroups[lcNum].push(result);
  });

  const duplicateLCs = Object.entries(lcGroups)
    .filter(([_, results]) => results.length > 1)
    .map(([lcNum, results]) => ({
      lc_number: lcNum,
      count: results.length,
      results: results.sort((a, b) => {
        const dateA = a.completed_at ? new Date(a.completed_at).getTime() : 0;
        const dateB = b.completed_at ? new Date(b.completed_at).getTime() : 0;
        return dateB - dateA;
      }),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  return (
    <div className="p-4 border-t bg-muted/30">
      <Tabs defaultValue="kpis" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="kpis">KPIs & Trends</TabsTrigger>
          <TabsTrigger value="issues">Recent Issues</TabsTrigger>
          <TabsTrigger value="duplicates">Duplicates</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="kpis" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Compliance Trend */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Compliance Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">{clientStats.compliance_rate.toFixed(1)}%</div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                      {complianceTrend >= 0 ? (
                        <>
                          <TrendingUp className="w-3 h-3 text-green-600" />
                          <span className="text-green-600">+{complianceTrendPercent}%</span>
                        </>
                      ) : (
                        <>
                          <TrendingDown className="w-3 h-3 text-red-600" />
                          <span className="text-red-600">{complianceTrendPercent}%</span>
                        </>
                      )}
                      <span>vs previous period</span>
                    </div>
                  </div>
                  <Activity className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            {/* Average Score */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Average Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">{clientStats.average_compliance_score.toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Across {clientStats.total_validations} validations
                    </div>
                  </div>
                  <BarChart3 className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            {/* Discrepancy Rate */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Discrepancy Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">
                      {clientStats.total_validations > 0
                        ? ((clientStats.discrepancies_count / clientStats.total_validations) * 100).toFixed(1)
                        : "0.0"}%
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {clientStats.discrepancies_count} of {clientStats.total_validations} LCs
                    </div>
                  </div>
                  <AlertCircle className="w-8 h-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Trend Chart (Simple visualization) */}
          {trendData.length > 0 && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Compliance Trend (Last 90 Days)</CardTitle>
                <CardDescription>Average compliance score over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-32 flex items-end gap-1">
                  {trendData.slice(-30).map((point, idx) => {
                    const height = (point.avg_compliance_score / 100) * 100;
                    return (
                      <div
                        key={idx}
                        className="flex-1 bg-primary/20 rounded-t hover:bg-primary/40 transition-colors"
                        style={{ height: `${height}%` }}
                        title={`${format(new Date(point.date), "MMM d")}: ${point.avg_compliance_score.toFixed(1)}%`}
                      />
                    );
                  })}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>{format(new Date(trendData[Math.max(0, trendData.length - 30)].date), "MMM d")}</span>
                  <span>{format(new Date(trendData[trendData.length - 1].date), "MMM d")}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="issues" className="mt-4">
          {recentIssues.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <CheckCircle className="w-12 h-12 mx-auto text-green-600 mb-2" />
                <p className="text-muted-foreground">No recent issues in the last 7 days</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {recentIssues.map((issue) => (
                <Card key={issue.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={issue.discrepancy_count > 5 ? "destructive" : "secondary"}>
                            {issue.discrepancy_count} {issue.discrepancy_count === 1 ? "issue" : "issues"}
                          </Badge>
                          <span className="font-medium">{sanitizeDisplayText(issue.lc_number || "N/A")}</span>
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {issue.completed_at
                            ? format(new Date(issue.completed_at), "MMM d, yyyy 'at' HH:mm")
                            : "Date unknown"}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{issue.compliance_score}%</div>
                        <div className="text-xs text-muted-foreground">Compliance</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="duplicates" className="mt-4">
          {duplicateLCs.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <Copy className="w-12 h-12 mx-auto text-muted-foreground mb-2" />
                <p className="text-muted-foreground">No duplicate LCs found</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Duplicate LC Heatmap</CardTitle>
                  <CardDescription>
                    LCs validated multiple times (showing top {duplicateLCs.length})
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {duplicateLCs.map((dup) => (
                      <div key={dup.lc_number} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Copy className="w-4 h-4 text-muted-foreground" />
                            <span className="font-medium">{sanitizeDisplayText(dup.lc_number)}</span>
                            <Badge variant="outline">{dup.count}x</Badge>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                          {dup.results.map((result, idx) => (
                            <div
                              key={result.id}
                              className={`p-2 rounded border ${
                                result.discrepancy_count > 0 ? "bg-yellow-50 border-yellow-200" : "bg-green-50 border-green-200"
                              }`}
                            >
                              <div className="font-medium">
                                {result.completed_at
                                  ? format(new Date(result.completed_at), "MMM d")
                                  : "Unknown"}
                              </div>
                              <div className="text-muted-foreground">
                                {result.compliance_score}% • {result.discrepancy_count} issues
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Recent Activity</CardTitle>
              <CardDescription>Last 10 validations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {lcResults.slice(0, 10).map((result) => (
                  <div key={result.id} className="flex items-center justify-between p-2 border rounded">
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <div>
                        <div className="font-medium text-sm">{sanitizeDisplayText(result.lc_number || "N/A")}</div>
                        <div className="text-xs text-muted-foreground">
                          {result.completed_at
                            ? format(new Date(result.completed_at), "MMM d, yyyy 'at' HH:mm")
                            : "Date unknown"}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          result.status === "compliant"
                            ? "default"
                            : result.status === "discrepancies"
                            ? "secondary"
                            : "destructive"
                        }
                      >
                        {result.status}
                      </Badge>
                      <div className="text-right text-sm">
                        <div className="font-medium">{result.compliance_score}%</div>
                        <div className="text-xs text-muted-foreground">{result.discrepancy_count} issues</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

