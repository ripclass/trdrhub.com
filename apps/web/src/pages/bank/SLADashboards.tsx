import * as React from "react";
import { useSearchParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart3,
  Clock,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Download,
  Calendar,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { bankApi, SLAMetric, SLABreach, SLAMetricsResponse, SLABreachesResponse } from "@/api/bank";
import { useQuery } from "@tanstack/react-query";

const COLORS = {
  met: "#22c55e",
  at_risk: "#f59e0b",
  breached: "#ef4444",
};

export function SLADashboardsView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [timeRange, setTimeRange] = React.useState<string>("week");

  // Fetch SLA metrics
  const { data: metricsData, isLoading: isLoadingMetrics, refetch: refetchMetrics } = useQuery<SLAMetricsResponse>({
    queryKey: ['sla-metrics', timeRange],
    queryFn: () => bankApi.getSLAMetrics(timeRange),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Fetch SLA breaches
  const { data: breachesData, isLoading: isLoadingBreaches, refetch: refetchBreaches } = useQuery<SLABreachesResponse>({
    queryKey: ['sla-breaches', timeRange],
    queryFn: () => bankApi.getSLABreaches(timeRange),
    staleTime: 30 * 1000,
  });

  const metrics = metricsData?.metrics || [];
  const breaches = breachesData?.breaches || [];
  const overallCompliance = metricsData?.overall_compliance || 0;
  const throughputData = metricsData?.throughput_data || [];
  const agingData = metricsData?.aging_data || [];

  const handleExportReport = async () => {
    try {
      await bankApi.exportSLAReport(timeRange, 'pdf');
      toast({
        title: "SLA Report Exported",
        description: "Your SLA report has been downloaded.",
      });
    } catch (error: any) {
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export SLA report. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">SLA Dashboards</h2>
          <p className="text-muted-foreground">
            Monitor service level agreements, throughput, aging, and breach incidents.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Time Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExportReport} className="gap-2">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Overall Compliance Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Overall SLA Compliance</CardTitle>
          <CardDescription>Current compliance across all SLA metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24">
                <svg className="w-24 h-24 transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    className="text-muted"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${(overallCompliance / 100) * 251.2} 251.2`}
                    className={
                      overallCompliance >= 90
                        ? "text-green-500"
                        : overallCompliance >= 75
                        ? "text-yellow-500"
                        : "text-red-500"
                    }
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold">{overallCompliance}%</span>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Compliance Rate</p>
                <p className="text-xs text-muted-foreground">
                  {metrics.filter((m) => m.status === "met").length} of {metrics.length} metrics met
                </p>
              </div>
            </div>
            <div className="flex-1 grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  {metrics.filter((m) => m.status === "met").length}
                </p>
                <p className="text-xs text-muted-foreground">Met</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {metrics.filter((m) => m.status === "at_risk").length}
                </p>
                <p className="text-xs text-muted-foreground">At Risk</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">
                  {metrics.filter((m) => m.status === "breached").length}
                </p>
                <p className="text-xs text-muted-foreground">Breached</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SLA Metrics Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.name}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">{metric.name}</CardTitle>
                <StatusBadge
                  status={
                    metric.status === "met"
                      ? "success"
                      : metric.status === "at_risk"
                      ? "warning"
                      : "destructive"
                  }
                >
                  {metric.status === "met" ? "Met" : metric.status === "at_risk" ? "At Risk" : "Breached"}
                </StatusBadge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-foreground">
                      {metric.current} {metric.unit}
                    </p>
                    <p className="text-xs text-muted-foreground">Target: {metric.target} {metric.unit}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {metric.trend === "up" ? (
                      <TrendingUp className="h-4 w-4 text-red-500" />
                    ) : metric.trend === "down" ? (
                      <TrendingDown className="h-4 w-4 text-green-500" />
                    ) : (
                      <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span
                      className={`text-xs font-medium ${
                        metric.trend === "up" ? "text-red-500" : metric.trend === "down" ? "text-green-500" : "text-muted-foreground"
                      }`}
                    >
                      {metric.trendPercentage > 0 ? "+" : ""}
                      {metric.trendPercentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <Progress
                  value={(metric.current / metric.target) * 100}
                  className="h-2"
                />
                <p className="text-xs text-muted-foreground">
                  {metric.current < metric.target
                    ? `${((metric.target - metric.current) / metric.target * 100).toFixed(1)}% below target`
                    : `${((metric.current - metric.target) / metric.target * 100).toFixed(1)}% above target`}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <Tabs defaultValue="throughput" className="w-full">
        <TabsList>
          <TabsTrigger value="throughput">Throughput</TabsTrigger>
          <TabsTrigger value="aging">Aging Distribution</TabsTrigger>
          <TabsTrigger value="breaches">Breaches</TabsTrigger>
        </TabsList>

        <TabsContent value="throughput" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">LC Processing Throughput</CardTitle>
              <CardDescription>Number of LCs processed per hour</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={throughputData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="lcs" fill="#3b82f6" name="LCs Processed" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="aging" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Queue Aging Distribution</CardTitle>
              <CardDescription>Distribution of LCs by queue time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={agingData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time_range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#8b5cf6" name="LC Count">
                      {agingData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            index === 0
                              ? COLORS.met
                              : index === 1
                              ? COLORS.at_risk
                              : COLORS.breached
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-4 gap-2 text-sm">
                  {agingData.map((item) => (
                    <div key={item.time_range} className="text-center">
                      <p className="font-semibold">{item.count}</p>
                      <p className="text-xs text-muted-foreground">{item.time_range}</p>
                      <p className="text-xs text-muted-foreground">({item.percentage}%)</p>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="breaches" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-medium">SLA Breaches</CardTitle>
                  <CardDescription>Recent SLA breach incidents</CardDescription>
                </div>
                <Badge variant="destructive">{breaches.length} breaches</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingBreaches ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading breaches...
                </div>
              ) : breaches.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No SLA breaches in the selected time range</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>LC Number</TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead>Metric</TableHead>
                      <TableHead>Target</TableHead>
                      <TableHead>Actual</TableHead>
                      <TableHead>Breach Time</TableHead>
                      <TableHead>Severity</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {breaches.map((breach) => (
                      <TableRow key={breach.id}>
                        <TableCell className="font-medium">{breach.lc_number}</TableCell>
                        <TableCell>{breach.client_name}</TableCell>
                        <TableCell>{breach.metric}</TableCell>
                        <TableCell>{breach.target}</TableCell>
                        <TableCell className="text-destructive font-medium">{breach.actual}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(breach.breach_time).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <StatusBadge
                            status={
                              breach.severity === "critical"
                                ? "error"
                                : breach.severity === "major"
                                ? "warning"
                                : "pending"
                            }
                          >
                            {breach.severity}
                          </StatusBadge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

