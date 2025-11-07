import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AdminToolbar } from "@/components/admin/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  DollarSign,
  TrendingUp,
  AlertCircle,
  FileText,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";
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
} from "recharts";

import { getAdminService } from "@/lib/admin/services";
import type { AdminSection, BillingSummary, TimeRange } from "@/lib/admin/types";
import { getChartTheme, CHART_MARGIN, getAxisStyle, getGridStyle, getTooltipStyle } from "@/lib/chart-theme";
import { cn } from "@/lib/utils";

const RANGE_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
];

const DEFAULT_RANGE: TimeRange = "30d";

const service = getAdminService();

function formatCurrency(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function formatCompactCurrency(cents: number): string {
  const dollars = cents / 100;
  if (dollars >= 1_000_000) {
    return `$${(dollars / 1_000_000).toFixed(1)}M`;
  }
  if (dollars >= 1_000) {
    return `$${(dollars / 1_000).toFixed(1)}K`;
  }
  return formatCurrency(cents);
}

interface KpiCardProps {
  label: string;
  value: string;
  secondary?: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick?: () => void;
  emphasis?: boolean;
}

function KpiCard({ label, value, secondary, icon: Icon, onClick, emphasis }: KpiCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group h-full rounded-xl border border-border/60 bg-card p-6 text-left shadow-sm transition hover:border-primary/60 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        onClick && "cursor-pointer"
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-foreground">{value}</span>
            {secondary && (
              <Badge variant="secondary" className="text-xs">
                {secondary}
              </Badge>
            )}
          </div>
        </div>
        <div className="rounded-lg bg-muted/60 p-3 text-muted-foreground group-hover:text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {emphasis && (
        <Badge className="mt-4" variant="secondary">
          Key metric
        </Badge>
      )}
    </button>
  );
}

export function BillingOverview() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const range = (searchParams.get("range") as TimeRange) ?? DEFAULT_RANGE;
  const currency = searchParams.get("currency") ?? "USD";
  const environment = searchParams.get("environment") ?? "all";

  const [summary, setSummary] = React.useState<BillingSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const chartTheme = React.useMemo(() => getChartTheme(), []);

  React.useEffect(() => {
    let active = true;
    setLoading(true);
    service
      .getBillingSummary(range, currency)
      .then((data) => {
        if (!active) return;
        setSummary(data);
        setError(null);
      })
      .catch(() => {
        if (!active) return;
        setError("Unable to load billing summary");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [range, currency]);

  const handleRangeChange = (value: TimeRange) => {
    const next = new URLSearchParams(searchParams);
    if (value === DEFAULT_RANGE) {
      next.delete("range");
    } else {
      next.set("range", value);
    }
    setSearchParams(next, { replace: true });
  };

  const handleCurrencyChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === "USD") {
      next.delete("currency");
    } else {
      next.set("currency", value);
    }
    setSearchParams(next, { replace: true });
  };

  const handleEnvironmentChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === "all") {
      next.delete("environment");
    } else {
      next.set("environment", value);
    }
    setSearchParams(next, { replace: true });
  };

  const handleNavigate = (section: AdminSection) => {
    const next = new URLSearchParams();
    next.set("section", section);
    navigate({ pathname: "/admin", search: next.toString() });
  };

  // Mock chart data (would come from service in real implementation)
  const revenueData = React.useMemo(() => {
    const days = range === "7d" ? 7 : range === "30d" ? 30 : 90;
    return Array.from({ length: days }).map((_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (days - i - 1));
      return {
        date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        revenue: summary ? Math.round(summary.monthToDateCents / days) + Math.floor(Math.random() * 5000) : 0,
      };
    });
  }, [range, summary]);

  const mrrWaterfallData = React.useMemo(() => {
    if (!summary) return [];
    return [
      { category: "New", value: Math.round(summary.mrrCents * 0.15) },
      { category: "Expansion", value: Math.round(summary.mrrCents * 0.05) },
      { category: "Contraction", value: -Math.round(summary.mrrCents * 0.02) },
      { category: "Churn", value: -Math.round(summary.mrrCents * 0.03) },
    ];
  }, [summary]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Billing Overview" description="Executive KPIs and revenue analytics" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Billing Overview" description="Executive KPIs and revenue analytics" />
        <Card className="border-destructive/40 bg-destructive/10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              {error || "Unable to load billing summary"}
            </CardTitle>
            <CardDescription>Try refreshing or check the billing service.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Billing Overview"
        description="Executive KPIs and revenue analytics"
        actions={
          <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        }
      >
        <Select value={range} onValueChange={handleRangeChange}>
          <SelectTrigger className="w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={currency} onValueChange={handleCurrencyChange}>
          <SelectTrigger className="w-[100px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="USD">USD</SelectItem>
            <SelectItem value="EUR">EUR</SelectItem>
            <SelectItem value="GBP">GBP</SelectItem>
          </SelectContent>
        </Select>

        <Select value={environment} onValueChange={handleEnvironmentChange}>
          <SelectTrigger className="w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="live">Live</SelectItem>
            <SelectItem value="sandbox">Sandbox</SelectItem>
          </SelectContent>
        </Select>
      </AdminToolbar>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="MRR"
          value={formatCompactCurrency(summary.mrrCents)}
          secondary={formatCurrency(summary.mrrCents)}
          icon={DollarSign}
          onClick={() => handleNavigate("billing-plans")}
          emphasis
        />
        <KpiCard
          label="ARR"
          value={formatCompactCurrency(summary.arrCents)}
          secondary={formatCurrency(summary.arrCents)}
          icon={TrendingUp}
          onClick={() => handleNavigate("billing-plans")}
        />
        <KpiCard
          label="Month-to-Date"
          value={formatCompactCurrency(summary.monthToDateCents)}
          secondary={formatCurrency(summary.monthToDateCents)}
          icon={FileText}
          onClick={() => handleNavigate("billing-adjustments")}
        />
        <KpiCard
          label="Net Revenue"
          value={formatCompactCurrency(summary.netRevenueCents)}
          secondary={formatCurrency(summary.netRevenueCents)}
          icon={DollarSign}
          onClick={() => handleNavigate("billing-adjustments")}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Refunds</CardTitle>
            <CardDescription>Total refunds this month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-destructive">
                {formatCompactCurrency(summary.refundsCents)}
              </span>
              <Badge variant="destructive" className="text-xs">
                {formatCurrency(summary.refundsCents)}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-4 gap-2"
              onClick={() => {
                const next = new URLSearchParams();
                next.set("section", "billing-adjustments");
                next.set("filter", "refunds");
                navigate({ pathname: "/admin", search: next.toString() });
              }}
            >
              View refunds
              <ArrowUpRight className="h-3 w-3" />
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Disputes Open</CardTitle>
            <CardDescription>Active disputes requiring attention</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-foreground">{summary.disputesOpen}</span>
              <Badge variant="outline" className="text-xs">
                {summary.disputesOpen === 0 ? "None" : "Action required"}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-4 gap-2"
              onClick={() => {
                const next = new URLSearchParams();
                next.set("section", "billing-disputes");
                next.set("status", "open,under_review");
                navigate({ pathname: "/admin", search: next.toString() });
              }}
            >
              View disputes
              <ArrowUpRight className="h-3 w-3" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Revenue Over Time</CardTitle>
            <CardDescription>Daily revenue for the selected period</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={revenueData} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" {...getGridStyle(chartTheme)} />
                <XAxis dataKey="date" {...getAxisStyle(chartTheme)} />
                <YAxis
                  {...getAxisStyle(chartTheme)}
                  tickFormatter={(value) => formatCompactCurrency(value)}
                />
                <Tooltip
                  {...getTooltipStyle(chartTheme)}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke={chartTheme.colors[0]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Revenue"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>MRR Waterfall</CardTitle>
            <CardDescription>New, expansion, contraction, and churn</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mrrWaterfallData} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" {...getGridStyle(chartTheme)} />
                <XAxis dataKey="category" {...getAxisStyle(chartTheme)} />
                <YAxis
                  {...getAxisStyle(chartTheme)}
                  tickFormatter={(value) => formatCompactCurrency(value)}
                />
                <Tooltip
                  {...getTooltipStyle(chartTheme)}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Bar
                  dataKey="value"
                  fill={chartTheme.colors[0]}
                  name="MRR Change"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Lists */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Customers (MTD)</CardTitle>
            <CardDescription>By revenue this month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {["Bank of Asia", "GlobalTrade Inc.", "LatAm Exports"].map((name, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{name}</span>
                  <span className="font-medium">{formatCompactCurrency((i + 1) * 50000)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overdue Invoices</CardTitle>
            <CardDescription>Requiring follow-up</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {summary.invoicesThisMonth > 0 ? (
                <div className="text-sm text-muted-foreground">
                  {summary.invoicesThisMonth} invoices this month
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No overdue invoices</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Payouts</CardTitle>
            <CardDescription>Last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {["Payout #1234", "Payout #1233", "Payout #1232"].map((id, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{id}</span>
                  <span className="font-medium">{formatCompactCurrency((i + 1) * 30000)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default BillingOverview;

