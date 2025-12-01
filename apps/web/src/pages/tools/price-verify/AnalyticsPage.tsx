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
  Info
} from "lucide-react";

export default function AnalyticsPage() {
  // Sample analytics data
  const stats = {
    totalVerifications: 247,
    passRate: 78.5,
    avgVariance: 8.3,
    tbmlFlags: 12,
    topCommodities: [
      { name: "Cotton", count: 45, passRate: 91 },
      { name: "Rice", count: 38, passRate: 84 },
      { name: "Crude Oil", count: 32, passRate: 62 },
      { name: "Steel", count: 28, passRate: 75 },
      { name: "Sugar", count: 24, passRate: 88 },
    ],
    verdictDistribution: {
      pass: 194,
      warning: 41,
      fail: 12,
    },
    monthlyTrend: [
      { month: "Jul", count: 28 },
      { month: "Aug", count: 35 },
      { month: "Sep", count: 42 },
      { month: "Oct", count: 58 },
      { month: "Nov", count: 84 },
    ],
    riskBreakdown: {
      low: 165,
      medium: 52,
      high: 18,
      critical: 12,
    },
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
          <Badge variant="outline" className="text-xs text-muted-foreground">
            <Info className="w-3 h-3 mr-1" />
            Sample Data
          </Badge>
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
                <p className="text-3xl font-bold">{stats.totalVerifications}</p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-full">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-2 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              <span>+23% this month</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pass Rate</p>
                <p className="text-3xl font-bold">{stats.passRate}%</p>
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
                <p className="text-3xl font-bold">{stats.avgVariance}%</p>
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
                <p className="text-3xl font-bold text-red-600">{stats.tbmlFlags}</p>
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
                  <span className="font-bold">{stats.verdictDistribution.pass}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-600 rounded-full" 
                      style={{ width: `${(stats.verdictDistribution.pass / stats.totalVerifications) * 100}%` }}
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
                  <span className="font-bold">{stats.verdictDistribution.warning}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-yellow-600 rounded-full" 
                      style={{ width: `${(stats.verdictDistribution.warning / stats.totalVerifications) * 100}%` }}
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
                  <span className="font-bold">{stats.verdictDistribution.fail}</span>
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-red-600 rounded-full" 
                      style={{ width: `${(stats.verdictDistribution.fail / stats.totalVerifications) * 100}%` }}
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
                <p className="text-2xl font-bold text-green-600">{stats.riskBreakdown.low}</p>
                <p className="text-sm text-muted-foreground">Low Risk</p>
                <p className="text-xs text-green-600">≤10% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-2xl font-bold text-yellow-600">{stats.riskBreakdown.medium}</p>
                <p className="text-sm text-muted-foreground">Medium Risk</p>
                <p className="text-xs text-yellow-600">10-25% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
                <p className="text-2xl font-bold text-orange-600">{stats.riskBreakdown.high}</p>
                <p className="text-sm text-muted-foreground">High Risk</p>
                <p className="text-xs text-orange-600">25-50% variance</p>
              </div>
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-2xl font-bold text-red-600">{stats.riskBreakdown.critical}</p>
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
            {stats.topCommodities.map((commodity, idx) => (
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
                    commodity.passRate >= 85 ? "text-green-600 border-green-600/30" :
                    commodity.passRate >= 70 ? "text-yellow-600 border-yellow-600/30" :
                    "text-red-600 border-red-600/30"
                  }
                >
                  {commodity.passRate}% pass rate
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
            {stats.monthlyTrend.map((month) => {
              const maxCount = Math.max(...stats.monthlyTrend.map(m => m.count));
              const height = (month.count / maxCount) * 100;
              return (
                <div key={month.month} className="flex-1 flex flex-col items-center gap-2">
                  <span className="text-sm font-medium">{month.count}</span>
                  <div 
                    className="w-full bg-primary rounded-t-md transition-all"
                    style={{ height: `${height}%` }}
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

