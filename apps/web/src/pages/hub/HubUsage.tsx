/**
 * Hub Usage - Detailed Usage Analytics
 * 
 * View detailed usage statistics, trends, and export data.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Download,
  FileCheck,
  DollarSign,
  Package,
  Shield,
  Ship,
  Calendar,
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
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
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart as RechartsPie,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface UsageSummary {
  period: { start: string; end: string };
  usage: Record<string, number>;
  overage: {
    lc_validations: number;
    price_checks: number;
    hs_lookups: number;
    sanctions_screens: number;
    container_tracks: number;
    total_charges: number;
  };
}

interface UsageLimits {
  plan: string;
  plan_name: string;
  limits: Record<string, { limit: number | string; used: number; remaining: number | string }>;
}

interface UsageLog {
  id: string;
  operation: string;
  tool: string;
  count: number;
  is_overage: boolean;
  overage_charge?: number;
  created_at: string;
  log_data?: Record<string, unknown>;
}

interface UsageHistory {
  month: string;
  lc_validations: number;
  price_checks: number;
  hs_lookups: number;
  total: number;
}

const TOOL_COLORS = {
  lc_validations: "#3b82f6",
  price_checks: "#10b981",
  hs_lookups: "#a855f7",
  sanctions_screens: "#ef4444",
  container_tracks: "#06b6d4",
};

const TOOL_LABELS: Record<string, string> = {
  lc_validations: "LC Validations",
  price_checks: "Price Checks",
  hs_lookups: "HS Lookups",
  sanctions_screens: "Sanctions",
  container_tracks: "Container Tracks",
};

const TOOL_ICONS: Record<string, React.ElementType> = {
  lc_validations: FileCheck,
  price_checks: DollarSign,
  hs_lookups: Package,
  sanctions_screens: Shield,
  container_tracks: Ship,
};

export default function HubUsage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [period, setPeriod] = useState("current");
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [limits, setLimits] = useState<UsageLimits | null>(null);
  const [logs, setLogs] = useState<UsageLog[]>([]);
  const [history, setHistory] = useState<UsageHistory[]>([]);

  useEffect(() => {
    fetchUsageData();
  }, [period]);

  const fetchUsageData = async () => {
    setLoading(true);
    try {
      // Fetch current usage
      const usageRes = await fetch(`${API_BASE}/usage/current`, {
        credentials: "include",
      });
      if (usageRes.ok) {
        const usageData = await usageRes.json();
        setUsage(usageData);
      }

      // Fetch limits
      const limitsRes = await fetch(`${API_BASE}/usage/limits`, {
        credentials: "include",
      });
      if (limitsRes.ok) {
        const limitsData = await limitsRes.json();
        setLimits(limitsData);
      }

      // Fetch logs
      const logsRes = await fetch(`${API_BASE}/usage/logs?limit=20`, {
        credentials: "include",
      });
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData.logs || []);
      }

      // Fetch history
      const historyRes = await fetch(`${API_BASE}/usage/history`, {
        credentials: "include",
      });
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        setHistory(historyData.history || []);
      }

    } catch (error) {
      console.error("Failed to fetch usage data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchUsageData();
    setRefreshing(false);
    toast({
      title: "Refreshed",
      description: "Usage data has been updated.",
    });
  };

  const handleExport = () => {
    // Generate CSV
    const headers = ["Date", "Operation", "Tool", "Count", "Overage", "Charge"];
    const rows = logs.map(log => [
      new Date(log.created_at).toLocaleString(),
      log.operation,
      log.tool,
      log.count,
      log.is_overage ? "Yes" : "No",
      log.overage_charge ? `$${log.overage_charge.toFixed(2)}` : "-"
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usage-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    toast({
      title: "Exported",
      description: "Usage data downloaded as CSV.",
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  // Calculate totals for pie chart
  const pieData = usage?.usage
    ? Object.entries(usage.usage)
        .filter(([_, value]) => value > 0)
        .map(([key, value]) => ({
          name: TOOL_LABELS[key] || key,
          value,
          color: TOOL_COLORS[key as keyof typeof TOOL_COLORS] || "#666",
        }))
    : [];

  // Transform history for area chart
  const chartData = history.length > 0
    ? history.slice(-6).map(h => ({
        month: h.month,
        "LC Validations": h.lc_validations || 0,
        "Price Checks": h.price_checks || 0,
        "HS Lookups": h.hs_lookups || 0,
      }))
    : [
        { month: "Jul", "LC Validations": 3, "Price Checks": 12, "HS Lookups": 5 },
        { month: "Aug", "LC Validations": 5, "Price Checks": 18, "HS Lookups": 8 },
        { month: "Sep", "LC Validations": 4, "Price Checks": 25, "HS Lookups": 12 },
        { month: "Oct", "LC Validations": 7, "Price Checks": 32, "HS Lookups": 15 },
        { month: "Nov", "LC Validations": 6, "Price Checks": 28, "HS Lookups": 20 },
        { month: "Dec", "LC Validations": usage?.usage?.lc_validations || 2, "Price Checks": usage?.usage?.price_checks || 8, "HS Lookups": usage?.usage?.hs_lookups || 3 },
      ];

  const totalUsage = usage?.usage
    ? Object.values(usage.usage).reduce((a, b) => a + b, 0)
    : 0;

  const getUsagePercent = (operation: string) => {
    if (!limits?.limits) return 0;
    const data = limits.limits[operation];
    if (!data || typeof data.limit !== "number" || data.limit === 0) return 0;
    return Math.min((data.used / data.limit) * 100, 100);
  };

  return (
    <div className="p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Usage Analytics</h1>
          <p className="text-slate-400">
            {usage?.period?.start && usage?.period?.end
              ? `${formatDate(usage.period.start)} - ${formatDate(usage.period.end)}`
              : "Current billing period"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            className="border-white/10 text-slate-300"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="border-white/10 text-slate-300"
            onClick={handleExport}
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card className="bg-slate-900/50 border-white/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <BarChart3 className="w-5 h-5 text-blue-400" />
              </div>
              <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">
                <TrendingUp className="w-3 h-3 mr-1" />
                +12%
              </Badge>
            </div>
            <p className="text-3xl font-bold text-white">{totalUsage}</p>
            <p className="text-sm text-slate-400">Total Operations</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-white/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <FileCheck className="w-5 h-5 text-emerald-400" />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{usage?.usage?.lc_validations || 0}</p>
            <p className="text-sm text-slate-400">LC Validations</p>
            <Progress value={getUsagePercent("lc_validations")} className="h-1 mt-2 bg-slate-800" />
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-white/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <DollarSign className="w-5 h-5 text-purple-400" />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{usage?.usage?.price_checks || 0}</p>
            <p className="text-sm text-slate-400">Price Checks</p>
            <Progress value={getUsagePercent("price_checks")} className="h-1 mt-2 bg-slate-800" />
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-white/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <TrendingUp className="w-5 h-5 text-amber-400" />
              </div>
              {(usage?.overage?.total_charges || 0) > 0 && (
                <Badge variant="outline" className="border-amber-500/30 text-amber-400">
                  Overage
                </Badge>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {formatCurrency(usage?.overage?.total_charges || 0)}
            </p>
            <p className="text-sm text-slate-400">Overage Charges</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Usage Trend Chart */}
        <Card className="lg:col-span-2 bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white">Usage Trend</CardTitle>
            <CardDescription className="text-slate-400">
              Operations over the last 6 months
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="lcGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="hsGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                    labelStyle={{ color: "#fff" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="LC Validations"
                    stroke="#3b82f6"
                    fill="url(#lcGradient)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="Price Checks"
                    stroke="#10b981"
                    fill="url(#priceGradient)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="HS Lookups"
                    stroke="#a855f7"
                    fill="url(#hsGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Distribution Pie Chart */}
        <Card className="bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white">Distribution</CardTitle>
            <CardDescription className="text-slate-400">
              Usage by tool this month
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend
                      wrapperStyle={{ color: "#94a3b8", fontSize: "12px" }}
                    />
                  </RechartsPie>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <PieChart className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-400">No usage data yet</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Usage by Tool */}
      <Card className="mb-8 bg-slate-900/50 border-white/5">
        <CardHeader>
          <CardTitle className="text-white">Usage by Tool</CardTitle>
          <CardDescription className="text-slate-400">
            Detailed breakdown of your plan limits
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {limits?.limits &&
              Object.entries(limits.limits).map(([key, data]) => {
                const Icon = TOOL_ICONS[key] || BarChart3;
                const color = TOOL_COLORS[key as keyof typeof TOOL_COLORS] || "#666";
                const percent = typeof data.limit === "number" && data.limit > 0
                  ? Math.min((data.used / data.limit) * 100, 100)
                  : 0;
                const isOverLimit = percent >= 100;

                return (
                  <div key={key} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className="p-2 rounded-lg"
                          style={{ backgroundColor: `${color}20` }}
                        >
                          <Icon className="w-4 h-4" style={{ color }} />
                        </div>
                        <span className="text-white font-medium">
                          {TOOL_LABELS[key] || key}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-slate-400">
                          <span className="text-white font-medium">{data.used}</span>
                          {" / "}
                          {data.limit === "unlimited" ? "∞" : data.limit}
                        </span>
                        {isOverLimit && (
                          <Badge variant="outline" className="border-red-500/30 text-red-400">
                            Over Limit
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Progress
                      value={percent}
                      className="h-2 bg-slate-800"
                      style={
                        {
                          "--progress-background": isOverLimit ? "#ef4444" : color,
                        } as React.CSSProperties
                      }
                    />
                  </div>
                );
              })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity Log */}
      <Card className="bg-slate-900/50 border-white/5">
        <CardHeader>
          <CardTitle className="text-white">Activity Log</CardTitle>
          <CardDescription className="text-slate-400">
            Recent operations and charges
          </CardDescription>
        </CardHeader>
        <CardContent>
          {logs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-white/5">
                  <TableHead className="text-slate-400">Time</TableHead>
                  <TableHead className="text-slate-400">Operation</TableHead>
                  <TableHead className="text-slate-400">Tool</TableHead>
                  <TableHead className="text-slate-400 text-right">Count</TableHead>
                  <TableHead className="text-slate-400 text-right">Charge</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => {
                  const Icon = TOOL_ICONS[`${log.operation}s`] || BarChart3;
                  return (
                    <TableRow key={log.id} className="border-white/5">
                      <TableCell className="text-slate-300">
                        {formatDateTime(log.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-slate-400" />
                          <span className="text-white">
                            {log.operation.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-400">{log.tool}</TableCell>
                      <TableCell className="text-right text-white">{log.count}</TableCell>
                      <TableCell className="text-right">
                        {log.is_overage ? (
                          <span className="text-amber-400">
                            {formatCurrency(log.overage_charge || 0)}
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <BarChart3 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No activity yet</h3>
              <p className="text-slate-400 text-sm">
                Start using tools to see your activity here.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

