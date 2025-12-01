import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  TrendingUp, 
  TrendingDown, 
  Target,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3,
  PieChart,
  Activity,
  Info,
  Loader2,
  RefreshCw,
  Calendar,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPie,
  Pie,
  Cell,
  Legend,
  AreaChart,
  Area,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface AnalyticsData {
  total_verifications: number;
  pass_rate: number;
  warning_rate: number;
  fail_rate: number;
  avg_variance: number;
  tbml_flags: number;
  verdict_distribution: { pass: number; warning: number; fail: number };
  risk_breakdown: { low: number; medium: number; high: number; critical: number };
  top_commodities: Array<{ name: string; code: string; count: number; pass_rate: number }>;
}

interface MonthlyData {
  monthly_trend: Array<{ month: string; year: number; count: number }>;
}

// Chart colors
const COLORS = {
  pass: "#22c55e",
  warning: "#eab308",
  fail: "#ef4444",
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#dc2626",
  primary: "#3b82f6",
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState<AnalyticsData | null>(null);
  const [monthlyTrend, setMonthlyTrend] = useState<MonthlyData["monthly_trend"]>([]);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(30);
  
  useEffect(() => {
    fetchAnalytics();
  }, [periodDays]);
  
  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Fetch analytics and monthly trend in parallel
      const [analyticsRes, monthlyRes] = await Promise.all([
        fetch(`${API_BASE}/price-verify/analytics?period_days=${periodDays}`),
        fetch(`${API_BASE}/price-verify/analytics/monthly?months=6`)
      ]);
      
      if (analyticsRes.ok) {
        const data = await analyticsRes.json();
        setStats(data);
      }
      
      if (monthlyRes.ok) {
        const data = await monthlyRes.json();
        setMonthlyTrend(data.monthly_trend || []);
      }
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
    } finally {
      setLoading(false);
    }
  };
  
  // Default stats when no data
  const displayStats = stats || {
    total_verifications: 0,
    pass_rate: 0,
    warning_rate: 0,
    fail_rate: 0,
    avg_variance: 0,
    tbml_flags: 0,
    verdict_distribution: { pass: 0, warning: 0, fail: 0 },
    risk_breakdown: { low: 0, medium: 0, high: 0, critical: 0 },
    top_commodities: [],
  };

  // Prepare chart data
  const verdictPieData = [
    { name: "Passed", value: displayStats.verdict_distribution.pass, color: COLORS.pass },
    { name: "Warnings", value: displayStats.verdict_distribution.warning, color: COLORS.warning },
    { name: "Failed", value: displayStats.verdict_distribution.fail, color: COLORS.fail },
  ].filter(d => d.value > 0);

  const riskPieData = [
    { name: "Low", value: displayStats.risk_breakdown.low, color: COLORS.low },
    { name: "Medium", value: displayStats.risk_breakdown.medium, color: COLORS.medium },
    { name: "High", value: displayStats.risk_breakdown.high, color: COLORS.high },
    { name: "Critical", value: displayStats.risk_breakdown.critical, color: COLORS.critical },
  ].filter(d => d.value > 0);

  const commodityBarData = displayStats.top_commodities.map(c => ({
    name: c.name.length > 15 ? c.name.substring(0, 15) + "..." : c.name,
    fullName: c.name,
    count: c.count,
    passRate: c.pass_rate,
  }));

  const trendLineData = monthlyTrend.map(m => ({
    name: m.month,
    verifications: m.count,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-medium">{label || payload[0]?.payload?.fullName || payload[0]?.name}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color || entry.fill }}>
              {entry.name}: {entry.value}
              {entry.name === "passRate" || entry.dataKey === "passRate" ? "%" : ""}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
            {loading ? (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                Loading...
              </Badge>
            ) : displayStats.total_verifications === 0 ? (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                <Info className="w-3 h-3 mr-1" />
                No Data Yet
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                Live Data
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Insights and trends from your price verifications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={periodDays.toString()} onValueChange={(v) => setPeriodDays(parseInt(v))}>
            <SelectTrigger className="w-36">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={fetchAnalytics} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Verifications</p>
                <p className="text-3xl font-bold">{displayStats.total_verifications}</p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-full">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-2 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>Last {periodDays} days</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pass Rate</p>
                <p className="text-3xl font-bold text-green-600">{displayStats.pass_rate}%</p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-full">
                <Target className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-2 text-sm">
              {displayStats.pass_rate >= 80 ? (
                <>
                  <TrendingUp className="w-4 h-4 text-green-600" />
                  <span className="text-green-600">Healthy</span>
                </>
              ) : (
                <>
                  <TrendingDown className="w-4 h-4 text-yellow-600" />
                  <span className="text-yellow-600">Needs attention</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Variance</p>
                <p className="text-3xl font-bold">{displayStats.avg_variance}%</p>
              </div>
              <div className="p-3 bg-yellow-500/10 rounded-full">
                <Activity className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-2 text-sm">
              {displayStats.avg_variance <= 15 ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span className="text-green-600">Within normal range</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  <span className="text-yellow-600">Above average</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">TBML Flags</p>
                <p className="text-3xl font-bold text-red-600">{displayStats.tbml_flags}</p>
              </div>
              <div className="p-3 bg-red-500/10 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {displayStats.total_verifications > 0 
                ? `${((displayStats.tbml_flags / displayStats.total_verifications) * 100).toFixed(1)}% of total`
                : "0% of total"
              }
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Verdict Distribution Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Verdict Distribution
            </CardTitle>
            <CardDescription>Breakdown of verification outcomes</CardDescription>
          </CardHeader>
          <CardContent>
            {verdictPieData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <RechartsPie>
                  <Pie
                    data={verdictPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {verdictPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                </RechartsPie>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Risk Heatmap */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Risk Level Heatmap
            </CardTitle>
            <CardDescription>Distribution by risk severity</CardDescription>
          </CardHeader>
          <CardContent>
            {riskPieData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            ) : (
              <div className="space-y-4">
                {/* Risk Bars */}
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: "Low", value: displayStats.risk_breakdown.low, color: "bg-green-500", desc: "≤10%" },
                    { label: "Medium", value: displayStats.risk_breakdown.medium, color: "bg-yellow-500", desc: "10-25%" },
                    { label: "High", value: displayStats.risk_breakdown.high, color: "bg-orange-500", desc: "25-50%" },
                    { label: "Critical", value: displayStats.risk_breakdown.critical, color: "bg-red-500", desc: ">50%" },
                  ].map((risk, i) => (
                    <div 
                      key={risk.label}
                      className="text-center p-4 rounded-lg bg-muted/50 relative overflow-hidden"
                    >
                      <div 
                        className={`absolute bottom-0 left-0 right-0 ${risk.color} opacity-20 transition-all duration-500`}
                        style={{ 
                          height: `${displayStats.total_verifications > 0 
                            ? (risk.value / displayStats.total_verifications) * 100 
                            : 0}%` 
                        }}
                      />
                      <p className="text-3xl font-bold relative z-10">{risk.value}</p>
                      <p className="text-sm font-medium relative z-10">{risk.label}</p>
                      <p className="text-xs text-muted-foreground relative z-10">{risk.desc}</p>
                    </div>
                  ))}
                </div>
                {/* Risk Pie */}
                <ResponsiveContainer width="100%" height={150}>
                  <RechartsPie>
                    <Pie
                      data={riskPieData}
                      cx="50%"
                      cy="50%"
                      outerRadius={60}
                      dataKey="value"
                    >
                      {riskPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Monthly Trend Line Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Verification Trend</CardTitle>
          <CardDescription>Number of verifications over time</CardDescription>
        </CardHeader>
        <CardContent>
          {trendLineData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No trend data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={trendLineData}>
                <defs>
                  <linearGradient id="colorVerifications" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="verifications" 
                  stroke={COLORS.primary} 
                  strokeWidth={2}
                  fill="url(#colorVerifications)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Top Commodities Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Top Verified Commodities</CardTitle>
          <CardDescription>Most frequently verified commodities and their pass rates</CardDescription>
        </CardHeader>
        <CardContent>
          {commodityBarData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No commodity data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={commodityBarData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={120} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar dataKey="count" name="Verifications" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
                <Bar dataKey="passRate" name="Pass Rate %" fill={COLORS.pass} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Detailed Stats Grid */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Passed</p>
                <p className="text-xl font-bold">{displayStats.verdict_distribution.pass}</p>
                <p className="text-xs text-green-600">
                  {displayStats.total_verifications > 0 
                    ? `${((displayStats.verdict_distribution.pass / displayStats.total_verifications) * 100).toFixed(1)}%`
                    : "0%"
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Warnings</p>
                <p className="text-xl font-bold">{displayStats.verdict_distribution.warning}</p>
                <p className="text-xs text-yellow-600">
                  {displayStats.total_verifications > 0 
                    ? `${((displayStats.verdict_distribution.warning / displayStats.total_verifications) * 100).toFixed(1)}%`
                    : "0%"
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500/10 rounded-lg">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Failed</p>
                <p className="text-xl font-bold">{displayStats.verdict_distribution.fail}</p>
                <p className="text-xs text-red-600">
                  {displayStats.total_verifications > 0 
                    ? `${((displayStats.verdict_distribution.fail / displayStats.total_verifications) * 100).toFixed(1)}%`
                    : "0%"
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
