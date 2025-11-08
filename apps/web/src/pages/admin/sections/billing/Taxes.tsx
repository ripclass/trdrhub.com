/**
 * Tax Summaries admin page
 * Shows tax collected by jurisdiction
 */
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminToolbar, DataTable } from "@/components/admin/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ColumnDef } from "@tanstack/react-table";

import { createBillingAggregator } from "@/lib/billing/aggregator";
import { calculateTaxSummaries, createTaxEngineConfig } from "@/lib/billing/tax";
import type { TaxSummary } from "@/lib/billing/tax";
import { getChartTheme, CHART_MARGIN, getAxisStyle, getGridStyle, getTooltipStyle } from "@/lib/chart-theme";
import { formatCurrencyAmount, type Currency } from "@/lib/billing/fx";
import { getTaxSummaries } from "@/lib/admin/services/billingIntegration";

const RANGE_OPTIONS = [
  { label: "Last 7 Days", value: "7d" },
  { label: "Last 30 Days", value: "30d" },
  { label: "Last 90 Days", value: "90d" },
  { label: "Last Year", value: "365d" },
];

export function BillingTaxes() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = searchParams.get("range") || "30d";
  const countryFilter = searchParams.get("country") || "all";

  const [taxSummaries, setTaxSummaries] = React.useState<TaxSummary[]>([]);
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

        const summaries = await getTaxSummaries(fromDate, toDate);
        if (!active) return;

        setTaxSummaries(summaries || []);
      } catch (err) {
        if (!active) return;
        console.error("Failed to load tax summaries", err);
        setError("Unable to load tax summaries");
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

  const handleCountryChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === "all") {
      next.delete("country");
    } else {
      next.set("country", value);
    }
    setSearchParams(next, { replace: true });
  };

  const filteredSummaries = React.useMemo(() => {
    if (countryFilter === "all") return taxSummaries;
    return taxSummaries.filter((s) => s.country === countryFilter);
  }, [taxSummaries, countryFilter]);

  const totalTaxCollected = React.useMemo(() => {
    return filteredSummaries.reduce((sum, s) => sum + s.taxCollected, 0);
  }, [filteredSummaries]);

  const uniqueCountries = React.useMemo(() => {
    return Array.from(new Set(taxSummaries.map((s) => s.country))).sort();
  }, [taxSummaries]);

  const chartData = React.useMemo(() => {
    return filteredSummaries.slice(0, 10).map((s) => ({
      jurisdiction: s.region ? `${s.country}-${s.region}` : s.country,
      taxCollected: s.taxCollected / 100,
    }));
  }, [filteredSummaries]);

  const columns: ColumnDef<TaxSummary>[] = React.useMemo(
    () => [
      {
        accessorKey: "jurisdiction",
        header: "Jurisdiction",
        cell: ({ row }) => (
          <div>
            <div className="font-medium">{row.original.country}</div>
            {row.original.region && (
              <div className="text-xs text-muted-foreground">{row.original.region}</div>
            )}
          </div>
        ),
      },
      {
        accessorKey: "taxCollected",
        header: "Tax Collected",
        cell: ({ row }) => formatCurrencyAmount(row.original.taxCollected, row.original.currency),
      },
      {
        accessorKey: "taxRate",
        header: "Tax Rate",
        cell: ({ row }) => `${(row.original.taxRate * 100).toFixed(2)}%`,
      },
      {
        accessorKey: "transactionCount",
        header: "Transactions",
        cell: ({ row }) => row.original.transactionCount.toLocaleString(),
      },
      {
        accessorKey: "currency",
        header: "Currency",
        cell: ({ row }) => <Badge variant="outline">{row.original.currency}</Badge>,
      },
    ],
    []
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Tax Summaries" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Tax Summaries" />
        <Card className="border-destructive/40 bg-destructive/10">
          <CardHeader>
            <CardTitle className="text-destructive">{error}</CardTitle>
            <CardDescription>Try refreshing or check the billing service.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Tax Summaries"
        description="Tax collected by jurisdiction"
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
        <Select value={countryFilter} onValueChange={handleCountryChange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select country" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Countries</SelectItem>
            {uniqueCountries.map((country) => (
              <SelectItem key={country} value={country}>
                {country}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </AdminToolbar>

      <Card>
        <CardHeader>
          <CardTitle>Total Tax Collected</CardTitle>
          <CardDescription>Across all jurisdictions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">
            {formatCurrencyAmount(totalTaxCollected, "USD")}
          </div>
        </CardContent>
      </Card>

      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Tax Collected by Jurisdiction</CardTitle>
            <CardDescription>Top 10 jurisdictions</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} margin={CHART_MARGIN}>
                <CartesianGrid vertical={false} {...gridStyle} />
                <XAxis dataKey="jurisdiction" {...axisStyle} angle={-45} textAnchor="end" height={80} />
                <YAxis
                  tickFormatter={(value) => formatCurrencyAmount(value * 100, "USD")}
                  {...axisStyle}
                />
                <Tooltip
                  cursor={{ fill: "transparent" }}
                  formatter={(value: number) => formatCurrencyAmount(value * 100, "USD")}
                  {...tooltipStyle}
                />
                <Bar dataKey="taxCollected" fill={chartTheme.colors[0]} name="Tax Collected" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Tax Summary Table</CardTitle>
          <CardDescription>Detailed breakdown by jurisdiction</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={filteredSummaries} />
        </CardContent>
      </Card>
    </div>
  );
}

export default BillingTaxes;

