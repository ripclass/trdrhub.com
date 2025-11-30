/**
 * Price Verify Dashboard Overview
 * 
 * Main dashboard page showing key metrics, recent verifications, and quick actions.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Package,
  Clock,
  ArrowRight,
  Plus,
  BarChart3,
} from "lucide-react";

// Mock data for demo
const recentVerifications = [
  {
    id: "1",
    commodity: "Raw Cotton",
    price: 2.45,
    unit: "kg",
    variance: 11.2,
    verdict: "warning",
    timestamp: "2 hours ago",
  },
  {
    id: "2",
    commodity: "Steel HRC",
    price: 680,
    unit: "mt",
    variance: -5.3,
    verdict: "pass",
    timestamp: "4 hours ago",
  },
  {
    id: "3",
    commodity: "Crude Oil (Brent)",
    price: 95,
    unit: "bbl",
    variance: 15.8,
    verdict: "warning",
    timestamp: "Yesterday",
  },
  {
    id: "4",
    commodity: "Copper",
    price: 12500,
    unit: "mt",
    variance: 47.1,
    verdict: "fail",
    timestamp: "Yesterday",
  },
  {
    id: "5",
    commodity: "White Rice",
    price: 510,
    unit: "mt",
    variance: -2.1,
    verdict: "pass",
    timestamp: "2 days ago",
  },
];

const topCommodities = [
  { name: "Raw Cotton", verifications: 124, trend: "up" },
  { name: "Steel HRC", verifications: 98, trend: "up" },
  { name: "Crude Oil", verifications: 87, trend: "down" },
  { name: "Copper", verifications: 65, trend: "up" },
  { name: "White Rice", verifications: 52, trend: "stable" },
];

export default function DashboardOverview() {
  const [stats, setStats] = useState({
    totalVerifications: 1247,
    passRate: 68,
    warningRate: 24,
    failRate: 8,
    avgVariance: 12.4,
    commoditiesCovered: 52,
  });

  const getVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case "pass":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case "fail":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getVerdictBadge = (verdict: string) => {
    const colors: Record<string, string> = {
      pass: "bg-green-500/10 text-green-500 border-green-500/20",
      warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      fail: "bg-red-500/10 text-red-500 border-red-500/20",
    };
    return (
      <Badge variant="outline" className={colors[verdict]}>
        {verdict.toUpperCase()}
      </Badge>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Welcome Section */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome back!</h1>
          <p className="text-muted-foreground">
            Here's what's happening with your price verifications.
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild>
            <Link to="/price-verify/dashboard/verify">
              <Plus className="h-4 w-4 mr-2" />
              New Verification
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Verifications</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalVerifications.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-500">+12.5%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{stats.passRate}%</div>
            <Progress value={stats.passRate} className="mt-2 h-1" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg. Variance</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">±{stats.avgVariance}%</div>
            <p className="text-xs text-muted-foreground">
              Within acceptable range
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Commodities</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.commoditiesCovered}</div>
            <p className="text-xs text-muted-foreground">
              Across 7 categories
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-7">
        {/* Recent Verifications */}
        <Card className="lg:col-span-4">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Verifications</CardTitle>
              <CardDescription>Your latest price verification results</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/price-verify/dashboard/history">
                View all
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentVerifications.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {getVerdictIcon(item.verdict)}
                    <div>
                      <p className="font-medium">{item.commodity}</p>
                      <p className="text-sm text-muted-foreground">
                        ${item.price}/{item.unit}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className={`font-medium ${
                        item.variance > 0 ? "text-red-500" : "text-green-500"
                      }`}>
                        {item.variance > 0 ? "+" : ""}{item.variance}%
                      </p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {item.timestamp}
                      </p>
                    </div>
                    {getVerdictBadge(item.verdict)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Commodities */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Top Commodities</CardTitle>
            <CardDescription>Most verified commodities this month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topCommodities.map((commodity, index) => (
                <div key={commodity.name} className="flex items-center gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{commodity.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {commodity.verifications} verifications
                    </p>
                  </div>
                  <div>
                    {commodity.trend === "up" && (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    )}
                    {commodity.trend === "down" && (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    {commodity.trend === "stable" && (
                      <div className="h-4 w-4 rounded-full bg-muted" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Verdict Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Verdict Distribution</CardTitle>
          <CardDescription>Breakdown of verification results this month</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-8">
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="text-sm">Pass</span>
                </div>
                <span className="text-sm font-medium">{stats.passRate}%</span>
              </div>
              <Progress value={stats.passRate} className="h-2 bg-muted [&>div]:bg-green-500" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <span className="text-sm">Warning</span>
                </div>
                <span className="text-sm font-medium">{stats.warningRate}%</span>
              </div>
              <Progress value={stats.warningRate} className="h-2 bg-muted [&>div]:bg-yellow-500" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <span className="text-sm">Fail</span>
                </div>
                <span className="text-sm font-medium">{stats.failRate}%</span>
              </div>
              <Progress value={stats.failRate} className="h-2 bg-muted [&>div]:bg-red-500" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

