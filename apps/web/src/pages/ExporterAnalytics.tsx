import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
import { 
  ArrowLeft, 
  BarChart3, 
  TrendingUp, 
  TrendingDown,
  Calendar,
  FileText,
  Clock,
  DollarSign,
  Package,
  Truck,
  Activity,
  PieChart,
  LineChart
} from "lucide-react";

type ExporterAnalyticsProps = {
  embedded?: boolean;
};

// Calculate analytics from real session data
function calculateAnalytics(sessions: ValidationSession[]) {
  const now = new Date();
  const sixMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 5, 1);
  
  // Filter sessions from last 6 months
  const recentSessions = sessions.filter(s => new Date(s.created_at) >= sixMonthsAgo);
  const completedSessions = recentSessions.filter(s => s.status === 'completed');
  
  // Calculate overview stats
  const totalExports = completedSessions.length;
  const successfulSessions = completedSessions.filter(s => (s.discrepancies?.length || 0) === 0);
  const complianceRate = completedSessions.length > 0 
    ? Math.round((successfulSessions.length / completedSessions.length) * 1000) / 10
    : 0;
  
  // Calculate average processing time
  const sessionsWithTime = completedSessions.filter(s => s.processing_started_at && s.processing_completed_at);
  const avgProcessingMs = sessionsWithTime.length > 0
    ? sessionsWithTime.reduce((sum, s) => {
        const start = new Date(s.processing_started_at!).getTime();
        const end = new Date(s.processing_completed_at!).getTime();
        return sum + (end - start);
      }, 0) / sessionsWithTime.length
    : 0;
  const avgProcessingTime = avgProcessingMs > 0 
    ? `${(avgProcessingMs / 60000).toFixed(1)} minutes`
    : "N/A";
  
  // Calculate monthly growth
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const prevMonthStart = new Date(now.getFullYear(), now.getMonth() - 2, 1);
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth() - 1, 0);
  
  const lastMonthSessions = completedSessions.filter(s => {
    const date = new Date(s.created_at);
    return date >= lastMonthStart && date <= lastMonthEnd;
  });
  const prevMonthSessions = completedSessions.filter(s => {
    const date = new Date(s.created_at);
    return date >= prevMonthStart && date <= prevMonthEnd;
  });
  
  const monthlyGrowth = prevMonthSessions.length > 0 
    ? Math.round(((lastMonthSessions.length - prevMonthSessions.length) / prevMonthSessions.length) * 1000) / 10
    : lastMonthSessions.length > 0 ? 100 : 0;
  
  // Calculate monthly breakdown
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthly = [];
  for (let i = 5; i >= 0; i--) {
    const monthStart = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const monthEnd = new Date(now.getFullYear(), now.getMonth() - i + 1, 0);
    const monthSessions = completedSessions.filter(s => {
      const date = new Date(s.created_at);
      return date >= monthStart && date <= monthEnd;
    });
    const monthSuccessful = monthSessions.filter(s => (s.discrepancies?.length || 0) === 0);
    const monthSessionsWithTime = monthSessions.filter(s => s.processing_started_at && s.processing_completed_at);
    const monthAvgMs = monthSessionsWithTime.length > 0
      ? monthSessionsWithTime.reduce((sum, s) => {
          const start = new Date(s.processing_started_at!).getTime();
          const end = new Date(s.processing_completed_at!).getTime();
          return sum + (end - start);
        }, 0) / monthSessionsWithTime.length
      : 0;
    
    monthly.push({
      month: months[monthStart.getMonth()],
      exports: monthSessions.length,
      compliance: monthSessions.length > 0 ? Math.round((monthSuccessful.length / monthSessions.length) * 100) : 0,
      avgTime: monthAvgMs > 0 ? Math.round((monthAvgMs / 60000) * 10) / 10 : 0,
      packs: monthSessions.length // Assuming each session can generate a customs pack
    });
  }
  
  // Calculate document types from sessions
  const docTypeCounts: Record<string, { count: number; compliant: number }> = {};
  completedSessions.forEach(s => {
    (s.documents || []).forEach((doc: any) => {
      const type = doc.type || doc.documentType || 'Other';
      if (!docTypeCounts[type]) {
        docTypeCounts[type] = { count: 0, compliant: 0 };
      }
      docTypeCounts[type].count++;
      if (doc.status === 'success' || !doc.issuesCount) {
        docTypeCounts[type].compliant++;
      }
    });
  });
  
  const documentTypes = Object.entries(docTypeCounts)
    .map(([type, { count, compliant }]) => ({
      type,
      count,
      complianceRate: count > 0 ? Math.round((compliant / count) * 100) : 0,
      trend: 'stable' as const
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
  
  // If no document types, use defaults
  if (documentTypes.length === 0) {
    documentTypes.push(
      { type: "Commercial Invoice", count: 0, complianceRate: 0, trend: 'stable' as const },
      { type: "Packing List", count: 0, complianceRate: 0, trend: 'stable' as const },
      { type: "Bill of Lading", count: 0, complianceRate: 0, trend: 'stable' as const }
    );
  }
  
  return {
    overview: {
      totalExports,
      monthlyGrowth,
      complianceRate,
      avgProcessingTime,
      customsPacks: totalExports,
      timeToMarket: avgProcessingMs > 0 ? Math.round((avgProcessingMs / 86400000) * 10) / 10 : 0
    },
    monthly,
    documentTypes,
    exportDestinations: [] // Would need LC data to populate this
  };
}

export default function ExporterAnalytics({ embedded = false }: ExporterAnalyticsProps = {}) {
  const [activeTab, setActiveTab] = useState("overview");
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Load real session data
  useEffect(() => {
    const loadSessions = async () => {
      setIsLoading(true);
      try {
        const data = await getUserSessions();
        setSessions(data || []);
      } catch (error) {
        console.error('Failed to load sessions for analytics:', error);
        setSessions([]);
      } finally {
        setIsLoading(false);
      }
    };
    loadSessions();
  }, []);
  
  // Calculate analytics from real data
  const analytics = useMemo(() => calculateAnalytics(sessions), [sessions]);

  const containerClasses = embedded
    ? "mx-auto w-full max-w-6xl py-4"
    : "container mx-auto px-4 py-8 max-w-6xl";

  return (
    <div className={embedded ? "bg-transparent" : "bg-background min-h-screen"}>
      {/* Header */}
      {!embedded && (
        <header className="bg-card border-b border-gray-200">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link to="/exporter-dashboard">
                  <Button variant="outline" size="sm">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                  </Button>
                </Link>
                <div className="flex items-center gap-3">
                  <div className="bg-gradient-primary p-2 rounded-lg">
                    <BarChart3 className="w-6 h-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-foreground">Exporter Analytics</h1>
                    <p className="text-sm text-muted-foreground">Export performance and compliance insights</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>
      )}

      <div className={containerClasses}>
        {/* Key Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Exports</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.totalExports}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingUp className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">+{analytics.overview.monthlyGrowth}% this month</span>
                  </div>
                </div>
                <div className="bg-exporter/10 p-3 rounded-lg">
                  <Package className="w-6 h-6 text-exporter" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Compliance Rate</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.complianceRate}%</p>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingUp className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">Industry leading</span>
                  </div>
                </div>
                <div className="bg-success/10 p-3 rounded-lg">
                  <FileText className="w-6 h-6 text-success" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Customs Packs</p>
                  <p className="text-2xl font-bold text-foreground">{analytics.overview.customsPacks}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <Truck className="w-4 h-4 text-primary" />
                    <span className="text-sm text-primary">Ready for shipment</span>
                  </div>
                </div>
                <div className="bg-primary/10 p-3 rounded-lg">
                  <Truck className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analytics Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="destinations">Destinations</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Processing Efficiency */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Processing Efficiency
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-exporter mb-2">
                      {analytics.overview.avgProcessingTime}
                    </div>
                    <p className="text-sm text-muted-foreground">Average processing time</p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Document extraction</span>
                      <span className="font-medium">0.8 min</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>LC compliance check</span>
                      <span className="font-medium">0.6 min</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Customs pack generation</span>
                      <span className="font-medium">0.5 min</span>
                    </div>
                  </div>
                  
                  <div className="p-3 bg-success/5 border border-success/20 rounded-lg">
                    <p className="text-sm font-medium text-success">🚀 25% faster than industry average</p>
                  </div>
                </CardContent>
              </Card>

              {/* Financial Impact */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5" />
                    Export Value & Savings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-success mb-2">
                      $813K
                    </div>
                    <p className="text-sm text-muted-foreground">Total export value this year</p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Time savings value</span>
                      <span className="font-medium text-success">$32,000</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Reduced rejections</span>
                      <span className="font-medium text-success">$18,500</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Faster customs clearance</span>
                      <span className="font-medium text-success">$24,800</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Monthly Trends */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <LineChart className="w-5 h-5" />
                    Monthly Export Trends
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.monthly.map((month, index) => (
                      <div key={index} className="grid grid-cols-4 gap-2 p-2 rounded bg-muted/30 text-sm">
                        <div className="text-center font-medium">{month.month}</div>
                        <div className="text-center text-exporter">{month.exports}</div>
                        <div className="text-center text-success">{month.compliance}%</div>
                        <div className="text-center">{month.avgTime}m</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Document Performance */}
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Document Type Performance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.documentTypes.map((doc, index) => (
                      <div key={index} className="flex items-center justify-between p-2 rounded border border-gray-200">
                        <div className="flex-1">
                          <div className="font-medium text-sm">{doc.type}</div>
                          <div className="text-xs text-muted-foreground">{doc.count} processed</div>
                        </div>
                        <div className="text-center">
                          <div className="text-sm font-medium">{doc.complianceRate}%</div>
                          <div className="flex items-center gap-1">
                            {doc.trend === "up" ? (
                              <TrendingUp className="w-3 h-3 text-success" />
                            ) : doc.trend === "down" ? (
                              <TrendingDown className="w-3 h-3 text-destructive" />
                            ) : (
                              <div className="w-3 h-3 rounded-full bg-muted"></div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="destinations" className="space-y-6">
            <Card className="shadow-soft border-0">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Export Destinations Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analytics.exportDestinations.map((dest, index) => (
                    <div key={index} className="p-4 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <div className="font-medium">{dest.country}</div>
                          <div className="text-sm text-muted-foreground">{dest.orders} orders • ${dest.value.toLocaleString()}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-sm text-muted-foreground">Compliance</div>
                          <div className="font-medium text-success">{dest.compliance}%</div>
                        </div>
                      </div>
                      <Progress value={dest.compliance} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Performance Insights</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-3 bg-success/5 border border-success/20 rounded-lg">
                    <p className="text-sm font-medium text-success mb-1">🎯 Excellent Compliance</p>
                    <p className="text-xs text-muted-foreground">
                      Your 96.8% compliance rate is significantly above the 89% industry average. This excellence reduces delays and builds strong relationships with importers.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-exporter/5 border border-exporter/20 rounded-lg">
                    <p className="text-sm font-medium text-exporter mb-1">📈 Growing Market Share</p>
                    <p className="text-xs text-muted-foreground">
                      Your European exports have grown 42% this quarter, with Germany and UK leading. Consider expanding capacity to meet increasing demand.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg">
                    <p className="text-sm font-medium text-primary mb-1">⚡ Speed Advantage</p>
                    <p className="text-xs text-muted-foreground">
                      Processing 25% faster than competitors gives you a significant competitive edge in time-sensitive export markets.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-soft border-0">
                <CardHeader>
                  <CardTitle>Strategic Recommendations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">Expand Premium Services</p>
                      <p className="text-xs text-muted-foreground">
                        Your exceptional compliance rate positions you well to offer premium, guaranteed-clearance services at higher margins.
                      </p>
                    </div>
                    
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">GSP Certificate Optimization</p>
                      <p className="text-xs text-muted-foreground">
                        Focus on improving GSP certificate processing (94% vs 99% for COO) to unlock additional duty savings for customers.
                      </p>
                    </div>
                    
                    <div className="p-3 rounded-lg border border-gray-200">
                      <p className="text-sm font-medium mb-1">New Market Opportunities</p>
                      <p className="text-xs text-muted-foreground">
                        Strong performance in current markets suggests readiness to explore additional European destinations or premium product lines.
                      </p>
                    </div>
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