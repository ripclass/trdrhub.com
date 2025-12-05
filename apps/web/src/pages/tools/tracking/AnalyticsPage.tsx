/**
 * Analytics Page
 * 
 * Tracking analytics and insights.
 */

import { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  Clock,
  Ship,
  Container,
  AlertTriangle,
  CheckCircle,
  Calendar,
  ArrowUp,
  ArrowDown,
  Minus,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface PortfolioStats {
  active: number;
  delivered_30d: number;
  delayed: number;
  on_time_rate: number;
}

// Mock carrier performance data
const CARRIER_PERFORMANCE = [
  { carrier: "MSC", onTime: 94, avgDelay: 0.5, shipments: 12, trend: "up" },
  { carrier: "Maersk", onTime: 91, avgDelay: 1.2, shipments: 8, trend: "stable" },
  { carrier: "Hapag-Lloyd", onTime: 89, avgDelay: 1.8, shipments: 6, trend: "down" },
  { carrier: "OOCL", onTime: 96, avgDelay: 0.3, shipments: 4, trend: "up" },
  { carrier: "CMA CGM", onTime: 87, avgDelay: 2.1, shipments: 5, trend: "stable" },
];

const ROUTE_PERFORMANCE = [
  { route: "Shanghai → Rotterdam", avgTransit: 28, onTime: 92, shipments: 8 },
  { route: "Chittagong → Hamburg", avgTransit: 32, onTime: 85, shipments: 5 },
  { route: "Mumbai → Los Angeles", avgTransit: 35, onTime: 88, shipments: 4 },
  { route: "Singapore → New York", avgTransit: 38, onTime: 90, shipments: 3 },
];

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case "up": return <ArrowUp className="w-4 h-4 text-emerald-500" />;
    case "down": return <ArrowDown className="w-4 h-4 text-red-500" />;
    default: return <Minus className="w-4 h-4 text-slate-500" />;
  }
};

export default function AnalyticsPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<PortfolioStats>({
    active: 0,
    delivered_30d: 0,
    delayed: 0,
    on_time_rate: 0,
  });
  const [dateRange, setDateRange] = useState("30d");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          if (data.stats) {
            setStats(data.stats);
          }
        }
      } catch (error) {
        console.error("Failed to fetch stats:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchStats();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tracking Analytics</h1>
          <p className="text-muted-foreground">Performance insights and metrics for your shipments</p>
        </div>
        <Select value={dateRange} onValueChange={setDateRange}>
          <SelectTrigger className="w-[150px]">
            <Calendar className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 Days</SelectItem>
            <SelectItem value="30d">Last 30 Days</SelectItem>
            <SelectItem value="90d">Last 90 Days</SelectItem>
            <SelectItem value="365d">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">On-Time Rate</p>
                <p className="text-2xl font-bold">{stats.on_time_rate}%</p>
              </div>
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs">
              <ArrowUp className="w-3 h-3 text-emerald-500" />
              <span className="text-emerald-500">+2.3%</span>
              <span className="text-muted-foreground">vs last period</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Active Shipments</p>
                <p className="text-2xl font-bold">{stats.active}</p>
              </div>
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Ship className="w-5 h-5 text-blue-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs">
              <span className="text-muted-foreground">Currently tracking</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Delivered</p>
                <p className="text-2xl font-bold">{stats.delivered_30d}</p>
              </div>
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs">
              <span className="text-muted-foreground">Last 30 days</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Currently Delayed</p>
                <p className="text-2xl font-bold">{stats.delayed}</p>
              </div>
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs">
              {stats.delayed > 0 ? (
                <span className="text-amber-500">Needs attention</span>
              ) : (
                <span className="text-muted-foreground">All on schedule</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Carrier Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Container className="w-5 h-5" />
              Carrier Performance
            </CardTitle>
            <CardDescription>On-time delivery rates by carrier</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {CARRIER_PERFORMANCE.map((carrier) => (
                <div key={carrier.carrier} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{carrier.carrier}</span>
                      {getTrendIcon(carrier.trend)}
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-muted-foreground">{carrier.shipments} shipments</span>
                      <Badge variant={carrier.onTime >= 90 ? "default" : "secondary"}>
                        {carrier.onTime}%
                      </Badge>
                    </div>
                  </div>
                  <Progress value={carrier.onTime} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    Avg delay: {carrier.avgDelay} days
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Route Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Ship className="w-5 h-5" />
              Route Performance
            </CardTitle>
            <CardDescription>Transit times by route</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {ROUTE_PERFORMANCE.map((route) => (
                <div key={route.route} className="p-3 rounded-lg bg-muted/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm">{route.route}</span>
                    <Badge variant={route.onTime >= 90 ? "default" : "secondary"}>
                      {route.onTime}% on-time
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground text-xs">Avg Transit</p>
                      <p className="font-medium">{route.avgTransit} days</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Shipments</p>
                      <p className="font-medium">{route.shipments}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Key Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
                <span className="font-medium text-emerald-600 dark:text-emerald-400">Performance Up</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Your on-time delivery rate has improved by 2.3% compared to last month.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Container className="w-5 h-5 text-blue-500" />
                <span className="font-medium text-blue-600 dark:text-blue-400">Top Carrier</span>
              </div>
              <p className="text-sm text-muted-foreground">
                OOCL is your best performing carrier with 96% on-time delivery rate.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-5 h-5 text-amber-500" />
                <span className="font-medium text-amber-600 dark:text-amber-400">Recommendation</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Consider setting up delay alerts for Chittagong → Hamburg route which has higher variability.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

