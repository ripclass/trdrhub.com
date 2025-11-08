/**
 * Revenue Recognition admin page
 * Shows recognized vs deferred revenue with charts
 */
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminToolbar } from "@/components/admin/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
  Legend,
} from "recharts";

import { createBillingAggregator } from "@/lib/billing/aggregator";
import { calculateRecognition, getDeferredRevenueBalance } from "@/lib/billing/recognition";
import { getChartTheme, CHART_MARGIN, getAxisStyle, getGridStyle, getTooltipStyle } from "@/lib/chart-theme";
import { formatCurrencyAmount, type Currency } from "@/lib/billing/fx";
import { getRecognitionData } from "@/lib/admin/services/billingIntegration";

const RANGE_OPTIONS = [
  { label: "Last 7 Days", value: "7d" },
  { label: "Last 30 Days", value: "30d" },
  { label: "Last 90 Days", value: "90d" },
  { label: "Last Year", value: "365d" },
];

export function BillingRecognition() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = searchParams.get("range") || "30d";

  const [recognitionData, setRecognitionData] = React.useState<ReturnType<typeof calculateRecognition> | null>(null);
  const [deferredBalance, setDeferredBalance] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const chartTheme = getChartTheme();
  const axisStyle = getAxisStyle(chartTheme);
  const gridStyle = getGridStyle(chartTheme);
  const tooltipStyle = getTooltipStyle(chartTheme);

  React.useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        const now = new Date();
        let days: number;
        switch (range) {
          case "7d":
            days = 7;
            break;
          case "30d":
            days = 30;
            break;
          case "90d":
            days = 90;
            break;
          case "365d":
            days = 365;
            break;
          default:
            days = 30;
        }

        const fromDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString();
        const toDate = now.toISOString();

        const data = await getRecognitionData(fromDate, toDate);
        if (!active) return;

        if (data) {
          setRecognitionData(data);
          const balance = getDeferredRevenueBalance(
            (await createBillingAggregator("USD").listInvoices({ from: fromDate, to: toDate })).items,
            toDate
          );
          setDeferredBalance(balance);
        } else {
          setError("Unable to load recognition data");
        }
      } catch (err) {
        if (!active) return;
        console.error("Failed to load recognition data", err);
        setError("Unable to load recognition data");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      active = false;
    };
  }, [range]);

  const handleRangeChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("range", value);
    setSearchParams(next, { replace: true });
  };

  const monthlyChartData = React.useMemo(() => {
    if (!recognitionData) return [];
    return recognitionData.monthlyBreakdown.map((item) => ({
      month: item.month,
      recognized: item.recognized / 100,
      deferred: item.deferred / 100,
    }));
  }, [recognitionData]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Revenue Recognition" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !recognitionData) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Revenue Recognition" />
        <Card className="border-destructive/40 bg-destructive/10">
          <CardHeader>
            <CardTitle className="text-destructive">{error || "Unable to load recognition data"}</CardTitle>
            <CardDescription>Try refreshing or check the billing service.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Revenue Recognition"
        description="Recognized vs deferred revenue using accrual accounting"
      >
        <Select value={range} onValueChange={handleRangeChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            {RANGE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </AdminToolbar>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Recognized</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {formatCurrencyAmount(recognitionData.totalRecognized, "USD")}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Deferred</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {formatCurrencyAmount(recognitionData.totalDeferred, "USD")}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Deferred Balance (as of today)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {deferredBalance !== null ? formatCurrencyAmount(deferredBalance, "USD") : "-"}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Monthly Recognition Breakdown</CardTitle>
          <CardDescription>Recognized vs deferred revenue by month</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={monthlyChartData} margin={CHART_MARGIN}>
              <CartesianGrid vertical={false} {...gridStyle} />
              <XAxis dataKey="month" {...axisStyle} />
              <YAxis
                tickFormatter={(value) => formatCurrencyAmount(value * 100, "USD")}
                {...axisStyle}
              />
              <Tooltip
                cursor={{ fill: "transparent" }}
                formatter={(value: number) => formatCurrencyAmount(value * 100, "USD")}
                {...tooltipStyle}
              />
              <Legend />
              <Bar dataKey="recognized" fill={chartTheme.colors[0]} name="Recognized" />
              <Bar dataKey="deferred" fill={chartTheme.colors[1]} name="Deferred" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Daily Recognition Trend</CardTitle>
          <CardDescription>Daily recognized revenue over time</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart
              data={recognitionData.dailyBreakdown.slice(-30).map((item) => ({
                date: item.date,
                recognized: item.recognizedAmount / 100,
              }))}
              margin={CHART_MARGIN}
            >
              <CartesianGrid vertical={false} {...gridStyle} />
              <XAxis dataKey="date" {...axisStyle} tickFormatter={(value) => new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric" })} />
              <YAxis
                tickFormatter={(value) => formatCurrencyAmount(value * 100, "USD")}
                {...axisStyle}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(value: number) => formatCurrencyAmount(value * 100, "USD")}
                labelFormatter={(value) => new Date(value).toLocaleDateString()}
                {...tooltipStyle}
              />
              <Line
                type="monotone"
                dataKey="recognized"
                stroke={chartTheme.colors[0]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name="Recognized"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

export default BillingRecognition;

