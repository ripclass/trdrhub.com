import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  TrendingDown,
  FileText,
  Clock,
  Package,
  Truck,
  Activity,
  PieChart,
  LineChart,
} from "lucide-react";

type ExporterAnalyticsProps = {
  embedded?: boolean;
};

function calculateAnalytics(sessions: ValidationSession[]) {
  const now = new Date();
  const sixMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 5, 1);
  const recentSessions = sessions.filter((s) => new Date(s.created_at) >= sixMonthsAgo);
  const completedSessions = recentSessions.filter((s) => s.status === "completed");
  const successfulSessions = completedSessions.filter((s) => (s.discrepancies?.length || 0) === 0);
  const totalDiscrepancies = completedSessions.reduce((sum, s) => sum + (s.discrepancies?.length || 0), 0);
  const totalDocumentsProcessed = completedSessions.reduce((sum, s) => sum + ((s.documents || []).length), 0);

  const sessionsWithTime = completedSessions.filter((s) => s.processing_started_at && s.processing_completed_at);
  const avgProcessingMs =
    sessionsWithTime.length > 0
      ? sessionsWithTime.reduce((sum, s) => {
          const start = new Date(s.processing_started_at!).getTime();
          const end = new Date(s.processing_completed_at!).getTime();
          return sum + (end - start);
        }, 0) / sessionsWithTime.length
      : 0;

  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const prevMonthStart = new Date(now.getFullYear(), now.getMonth() - 2, 1);
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth() - 1, 0);

  const lastMonthSessions = completedSessions.filter((s) => {
    const date = new Date(s.created_at);
    return date >= lastMonthStart && date <= lastMonthEnd;
  });
  const prevMonthSessions = completedSessions.filter((s) => {
    const date = new Date(s.created_at);
    return date >= prevMonthStart && date <= prevMonthEnd;
  });

  const monthlyGrowth =
    prevMonthSessions.length > 0
      ? Math.round(((lastMonthSessions.length - prevMonthSessions.length) / prevMonthSessions.length) * 1000) / 10
      : lastMonthSessions.length > 0
        ? 100
        : 0;

  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const monthly = [];
  for (let i = 5; i >= 0; i -= 1) {
    const monthStart = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const monthEnd = new Date(now.getFullYear(), now.getMonth() - i + 1, 0);
    const monthSessions = completedSessions.filter((s) => {
      const date = new Date(s.created_at);
      return date >= monthStart && date <= monthEnd;
    });
    const monthSuccessful = monthSessions.filter((s) => (s.discrepancies?.length || 0) === 0);
    const monthSessionsWithTime = monthSessions.filter((s) => s.processing_started_at && s.processing_completed_at);
    const monthAvgMs =
      monthSessionsWithTime.length > 0
        ? monthSessionsWithTime.reduce((sum, s) => {
            const start = new Date(s.processing_started_at!).getTime();
            const end = new Date(s.processing_completed_at!).getTime();
            return sum + (end - start);
          }, 0) / monthSessionsWithTime.length
        : 0;

    monthly.push({
      month: monthNames[monthStart.getMonth()],
      exports: monthSessions.length,
      compliance: monthSessions.length > 0 ? Math.round((monthSuccessful.length / monthSessions.length) * 100) : 0,
      avgTime: monthAvgMs > 0 ? Math.round((monthAvgMs / 60000) * 10) / 10 : 0,
    });
  }

  const docTypeCounts: Record<string, { count: number; compliant: number }> = {};
  completedSessions.forEach((session) => {
    (session.documents || []).forEach((doc: any) => {
      const type = doc.type || doc.documentType || "Other";
      if (!docTypeCounts[type]) {
        docTypeCounts[type] = { count: 0, compliant: 0 };
      }
      docTypeCounts[type].count += 1;
      if (doc.status === "success" || !doc.issuesCount) {
        docTypeCounts[type].compliant += 1;
      }
    });
  });

  const documentTypes = Object.entries(docTypeCounts)
    .map(([type, counts]) => ({
      type,
      count: counts.count,
      complianceRate: counts.count > 0 ? Math.round((counts.compliant / counts.count) * 100) : 0,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  return {
    overview: {
      totalExports: completedSessions.length,
      monthlyGrowth,
      complianceRate:
        completedSessions.length > 0 ? Math.round((successfulSessions.length / completedSessions.length) * 1000) / 10 : 0,
      avgProcessingTime: avgProcessingMs > 0 ? `${(avgProcessingMs / 60000).toFixed(1)} minutes` : "N/A",
      customsPacks: completedSessions.length,
      totalDocumentsProcessed,
      totalDiscrepancies,
      completedSessions: completedSessions.length,
    },
    monthly,
    documentTypes,
  };
}

export default function ExporterAnalytics({ embedded = false }: ExporterAnalyticsProps = {}) {
  const [activeTab, setActiveTab] = useState("overview");
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSessions = async () => {
      setIsLoading(true);
      try {
        const data = await getUserSessions();
        setSessions(data || []);
      } catch (error) {
        console.error("Failed to load sessions for analytics:", error);
        setSessions([]);
      } finally {
        setIsLoading(false);
      }
    };

    void loadSessions();
  }, []);

  const analytics = useMemo(() => calculateAnalytics(sessions), [sessions]);
  const growthPositive = analytics.overview.monthlyGrowth >= 0;

  const containerClasses = embedded
    ? "mx-auto w-full max-w-6xl py-4"
    : "container mx-auto px-4 py-8 max-w-6xl";

  return (
    <div className={embedded ? "bg-transparent" : "bg-background min-h-screen"}>
      {!embedded && (
        <header className="border-b border-gray-200 bg-card">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link to="/lcopilot/exporter-dashboard">
                  <Button variant="outline" size="sm">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Dashboard
                  </Button>
                </Link>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-gradient-primary p-2">
                    <BarChart3 className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-foreground">Exporter Analytics</h1>
                    <p className="text-sm text-muted-foreground">
                      Real session-backed validation and processing metrics for the exporter workflow.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      <div className={containerClasses}>
        <div className="mb-8 rounded-lg border border-dashed border-border/70 bg-muted/30 p-4 text-sm text-muted-foreground">
          Beta note: this page only shows metrics that can be derived from real exporter validation history. TRDR Hub will not invent destination analytics, export value, savings, or market benchmarks here.
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card className="border-0 shadow-soft">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Completed Validations</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.totalExports}</p>
                  <div className="mt-1 flex items-center gap-1">
                    {growthPositive ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    )}
                    <span className={`text-sm ${growthPositive ? "text-success" : "text-destructive"}`}>
                      {analytics.overview.monthlyGrowth}% vs previous month
                    </span>
                  </div>
                </div>
                <div className="rounded-lg bg-exporter/10 p-3">
                  <Package className="h-6 w-6 text-exporter" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-soft">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Compliance Rate</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.complianceRate}%</p>
                  <div className="mt-1 flex items-center gap-1">
                    <FileText className="h-4 w-4 text-success" />
                    <span className="text-sm text-success">From completed validations only</span>
                  </div>
                </div>
                <div className="rounded-lg bg-success/10 p-3">
                  <FileText className="h-6 w-6 text-success" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-soft">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Documents Processed</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.totalDocumentsProcessed}</p>
                  <div className="mt-1 flex items-center gap-1">
                    <Truck className="h-4 w-4 text-primary" />
                    <span className="text-sm text-primary">Across completed validation sessions</span>
                  </div>
                </div>
                <div className="rounded-lg bg-primary/10 p-3">
                  <Truck className="h-6 w-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="destinations">Destinations</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Processing Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="mb-2 text-3xl font-bold text-exporter">{analytics.overview.avgProcessingTime}</div>
                    <p className="text-sm text-muted-foreground">Average end-to-end processing time</p>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Completed validations tracked</span>
                      <span className="font-medium">{analytics.overview.completedSessions}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Documents processed</span>
                      <span className="font-medium">{analytics.overview.totalDocumentsProcessed}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Discrepancies flagged</span>
                      <span className="font-medium">{analytics.overview.totalDiscrepancies}</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-3 text-sm text-muted-foreground">
                    Per-stage timings and market benchmarking are not modeled yet.
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Validation Workload
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="mb-2 text-3xl font-bold text-success">{analytics.overview.customsPacks}</div>
                    <p className="text-sm text-muted-foreground">Completed validation sessions</p>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Compliance rate</span>
                      <span className="font-medium text-success">{analytics.overview.complianceRate}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Documents processed</span>
                      <span className="font-medium text-success">{analytics.overview.totalDocumentsProcessed}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Discrepancies flagged</span>
                      <span className="font-medium text-success">{analytics.overview.totalDiscrepancies}</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-3 text-sm text-muted-foreground">
                    Export value, savings, and financial impact are intentionally omitted until they are connected to real data.
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <LineChart className="h-5 w-5" />
                    Monthly Validation Trends
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading validation history...</p>
                  ) : analytics.monthly.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-4 text-sm text-muted-foreground">
                      No completed validation history is available yet for monthly analytics.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {analytics.monthly.map((month) => (
                        <div key={month.month} className="grid grid-cols-4 gap-2 rounded bg-muted/30 p-2 text-sm">
                          <div className="text-center font-medium">{month.month}</div>
                          <div className="text-center text-exporter">{month.exports}</div>
                          <div className="text-center text-success">{month.compliance}%</div>
                          <div className="text-center">{month.avgTime}m</div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5" />
                    Document Type Performance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {analytics.documentTypes.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-4 text-sm text-muted-foreground">
                      Document-type performance appears here once completed validations include document summaries.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {analytics.documentTypes.map((doc) => (
                        <div key={doc.type} className="rounded border border-gray-200 p-3">
                          <div className="mb-2 flex items-center justify-between">
                            <div>
                              <div className="font-medium text-sm">{doc.type}</div>
                              <div className="text-xs text-muted-foreground">{doc.count} processed</div>
                            </div>
                            <div className="text-sm font-medium">{doc.complianceRate}%</div>
                          </div>
                          <Progress value={doc.complianceRate} className="h-2" />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="destinations" className="space-y-6">
            <Card className="border-0 shadow-soft">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Export Destinations Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-6 text-sm text-muted-foreground">
                  Destination analytics are not connected to extracted trade geography yet. This tab stays visible, but TRDR Hub will not invent country, order, or export-value data.
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle>What This Page Measures Today</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">Completed validation volume</p>
                    <p className="text-xs text-muted-foreground">
                      This page is fed by completed exporter validation sessions and their associated document summaries.
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">Compliance summary</p>
                    <p className="text-xs text-muted-foreground">
                      Compliance rate is calculated from sessions with zero recorded discrepancies.
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">Processing time summary</p>
                    <p className="text-xs text-muted-foreground">
                      Average processing time is calculated only for sessions that recorded both processing start and completion timestamps.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-soft">
                <CardHeader>
                  <CardTitle>Not Modeled Yet</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">No fake market benchmarking</p>
                    <p className="text-xs text-muted-foreground">
                      This page does not compare you against an industry average because that benchmark is not wired to live data.
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">No fake export value or savings</p>
                    <p className="text-xs text-muted-foreground">
                      Export value, duty savings, and clearance savings are intentionally omitted until they are backed by real extracted or billing data.
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="mb-1 text-sm font-medium">Destination intelligence pending</p>
                    <p className="text-xs text-muted-foreground">
                      Destination analytics will stay empty until extracted trade geography and shipping destination fields are connected.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
