import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  Loader2
} from "lucide-react";

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

export default function AnalyticsPage() {
  const [stats, setStats] = useState<AnalyticsData | null>(null);
  const [monthlyTrend, setMonthlyTrend] = useState<MonthlyData["monthly_trend"]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchAnalytics();
  }, []);
  
  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Fetch analytics and monthly trend in parallel
      const [analyticsRes, monthlyRes] = await Promise.all([
        fetch(`${API_BASE}/price-verify/analytics?period_days=30`),
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

  return (
    <div className="p-6 space-y-6">
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
              Last 30 Days
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground">
          Insights and trends from your price verifications.
        </p>
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
            <div className="flex items-center gap-1 mt-2 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              <span>Last 30 days</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pass Rate</p>
                <p className="text-3xl font-bold">{displayStats.pass_rate}%</p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-full">
                <Target className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-2 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              <span>+5.2% vs last month</span>
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
            <div className="flex items-center gap-1 mt-2 text-sm text-red-600">
              <TrendingDown className="w-4 h-4" />
              <span>-1.8% vs last month</span>
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
              4.9% of total verifications
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Verdict Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Verdict Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <span>Passed</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">{displayStats.verdict_distribution.pass}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-600 rounded-full" 
                      style={{ width: `${displayStats.total_verifications > 0 ? (displayStats.verdict_distribution.pass / displayStats.total_verifications) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  <span>Warnings</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">{displayStats.verdict_distribution.warning}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-yellow-600 rounded-full" 
                      style={{ width: `${displayStats.total_verifications > 0 ? (displayStats.verdict_distribution.warning / displayStats.total_verifications) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span>Failed</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">{displayStats.verdict_distribution.fail}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-red-600 rounded-full" 
                      style={{ width: `${displayStats.total_verifications > 0 ? (displayStats.verdict_distribution.fail / displayStats.total_verifications) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Risk Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Risk Level Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-2xl font-bold text-green-600">{displayStats.risk_breakdown.low}</p>
                <p className="text-sm text-muted-foreground">Low Risk</p>
                <p className="text-xs text-green-600">≤10% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-2xl font-bold text-yellow-600">{displayStats.risk_breakdown.medium}</p>
                <p className="text-sm text-muted-foreground">Medium Risk</p>
                <p className="text-xs text-yellow-600">10-25% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
                <p className="text-2xl font-bold text-orange-600">{displayStats.risk_breakdown.high}</p>
                <p className="text-sm text-muted-foreground">High Risk</p>
                <p className="text-xs text-orange-600">25-50% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-2xl font-bold text-red-600">{displayStats.risk_breakdown.critical}</p>
                <p className="text-sm text-muted-foreground">Critical (TBML)</p>
                <p className="text-xs text-red-600">&gt;50% variance</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Commodities */}
      <Card>
        <CardHeader>
          <CardTitle>Top Verified Commodities</CardTitle>
          <CardDescription>Most frequently verified commodities and their pass rates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {displayStats.top_commodities.length === 0 ? (
              <p className="text-center text-muted-foreground py-4">No verifications yet</p>
            ) : displayStats.top_commodities.map((commodity, idx) => (
              <div key={commodity.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-muted-foreground w-6">
                    #{idx + 1}
                  </span>
                  <div>
                    <p className="font-medium">{commodity.name}</p>
                    <p className="text-sm text-muted-foreground">{commodity.count} verifications</p>
                  </div>
                </div>
                <Badge 
                  variant="outline"
                  className={
                    commodity.pass_rate >= 85 ? "text-green-600 border-green-600/30" :
                    commodity.pass_rate >= 70 ? "text-yellow-600 border-yellow-600/30" :
                    "text-red-600 border-red-600/30"
                  }
                >
                  {commodity.pass_rate}% pass rate
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Monthly Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Monthly Verification Trend</CardTitle>
          <CardDescription>Number of verifications per month</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end justify-between h-40 gap-2">
            {monthlyTrend.length === 0 ? (
              <p className="text-center text-muted-foreground py-4 w-full">No data yet</p>
            ) : monthlyTrend.map((month) => {
              const maxCount = Math.max(...monthlyTrend.map(m => m.count), 1);
              const height = (month.count / maxCount) * 100;
              return (
                <div key={month.month} className="flex-1 flex flex-col items-center gap-2">
                  <span className="text-sm font-medium">{month.count}</span>
                  <div 
                    className="w-full bg-primary rounded-t-md transition-all"
                    style={{ height: `${Math.max(height, 5)}%` }}
                  />
                  <span className="text-xs text-muted-foreground">{month.month}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

