/**
 * Performance Page
 * 
 * Carrier scorecards and delivery performance metrics.
 */

import { useState, useEffect } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Ship,
  Container,
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  Award,
  Target,
  Calendar,
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

// Carrier scorecard data
const CARRIER_SCORECARDS = [
  {
    carrier: "OOCL",
    logo: "🚢",
    onTimeRate: 96,
    avgTransit: 28,
    avgDelay: 0.3,
    shipments: 42,
    trend: "up",
    rating: "A+",
  },
  {
    carrier: "MSC",
    logo: "🚢",
    onTimeRate: 94,
    avgTransit: 30,
    avgDelay: 0.5,
    shipments: 128,
    trend: "up",
    rating: "A",
  },
  {
    carrier: "Maersk",
    logo: "🚢",
    onTimeRate: 91,
    avgTransit: 29,
    avgDelay: 1.2,
    shipments: 85,
    trend: "stable",
    rating: "A-",
  },
  {
    carrier: "CMA CGM",
    logo: "🚢",
    onTimeRate: 89,
    avgTransit: 31,
    avgDelay: 1.5,
    shipments: 56,
    trend: "down",
    rating: "B+",
  },
  {
    carrier: "Hapag-Lloyd",
    logo: "🚢",
    onTimeRate: 88,
    avgTransit: 32,
    avgDelay: 1.8,
    shipments: 34,
    trend: "stable",
    rating: "B+",
  },
  {
    carrier: "Evergreen",
    logo: "🚢",
    onTimeRate: 87,
    avgTransit: 30,
    avgDelay: 2.0,
    shipments: 28,
    trend: "up",
    rating: "B",
  },
];

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case "up":
      return <TrendingUp className="w-4 h-4 text-emerald-500" />;
    case "down":
      return <TrendingDown className="w-4 h-4 text-red-500" />;
    default:
      return <Minus className="w-4 h-4 text-slate-500" />;
  }
};

const getRatingColor = (rating: string) => {
  if (rating.startsWith("A")) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
  if (rating.startsWith("B")) return "bg-blue-500/20 text-blue-400 border-blue-500/30";
  if (rating.startsWith("C")) return "bg-amber-500/20 text-amber-400 border-amber-500/30";
  return "bg-slate-500/20 text-slate-400 border-slate-500/30";
};

export default function PerformancePage() {
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState("90d");
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    totalShipments: 0,
    onTimeRate: 92,
    avgTransitDays: 30,
    avgDelayDays: 1.2,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_BASE}/tracking/portfolio`, {
          credentials: "include",
        });
        if (response.ok) {
          const data = await response.json();
          if (data.stats) {
            setStats({
              totalShipments: data.shipments?.length || 0,
              onTimeRate: data.stats.on_time_rate || 92,
              avgTransitDays: 30,
              avgDelayDays: 1.2,
            });
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
  }, [user, dateRange]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Performance</h1>
          <p className="text-muted-foreground">
            Carrier scorecards and delivery metrics
          </p>
        </div>
        <Select value={dateRange} onValueChange={setDateRange}>
          <SelectTrigger className="w-[150px]">
            <Calendar className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30d">Last 30 Days</SelectItem>
            <SelectItem value="90d">Last 90 Days</SelectItem>
            <SelectItem value="180d">Last 6 Months</SelectItem>
            <SelectItem value="365d">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Overall KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">On-Time Delivery</p>
                <p className="text-2xl font-bold">{stats.onTimeRate}%</p>
              </div>
              <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
                <Target className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <Progress value={stats.onTimeRate} className="h-1.5 mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Avg Transit Time</p>
                <p className="text-2xl font-bold">{stats.avgTransitDays}d</p>
              </div>
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-blue-500" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Industry avg: 32 days
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Avg Delay</p>
                <p className="text-2xl font-bold">{stats.avgDelayDays}d</p>
              </div>
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              When delayed
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total Shipments</p>
                <p className="text-2xl font-bold">{stats.totalShipments || "—"}</p>
              </div>
              <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                <Container className="w-5 h-5 text-purple-500" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Last {dateRange.replace("d", " days")}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Carrier Scorecards */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="w-5 h-5" />
            Carrier Scorecards
          </CardTitle>
          <CardDescription>
            Performance rankings based on your shipment history
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {CARRIER_SCORECARDS.map((carrier, index) => (
              <div
                key={carrier.carrier}
                className="p-4 rounded-lg border bg-muted/30"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center text-xl">
                      {carrier.logo}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{carrier.carrier}</span>
                        <Badge className={getRatingColor(carrier.rating)}>
                          {carrier.rating}
                        </Badge>
                        {index === 0 && (
                          <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                            <Award className="w-3 h-3 mr-1" />
                            Top Performer
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {carrier.shipments} shipments tracked
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {getTrendIcon(carrier.trend)}
                    <span className="text-sm text-muted-foreground">
                      {carrier.trend === "up" ? "Improving" : carrier.trend === "down" ? "Declining" : "Stable"}
                    </span>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">On-Time Rate</span>
                      <span className="text-sm font-medium">{carrier.onTimeRate}%</span>
                    </div>
                    <Progress value={carrier.onTimeRate} className="h-1.5" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Avg Transit</p>
                    <p className="text-sm font-medium">{carrier.avgTransit} days</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Avg Delay</p>
                    <p className="text-sm font-medium">{carrier.avgDelay} days</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Insights & Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
                <span className="font-medium text-emerald-600 dark:text-emerald-400">
                  Best Performer
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                <strong>OOCL</strong> has the highest on-time rate (96%) with minimal delays.
                Consider prioritizing them for time-sensitive shipments.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <span className="font-medium text-amber-600 dark:text-amber-400">
                  Watch List
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                <strong>CMA CGM</strong> performance is declining. Monitor closely and
                consider alternatives for critical shipments.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-5 h-5 text-blue-500" />
                <span className="font-medium text-blue-600 dark:text-blue-400">
                  Transit Optimization
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                Your average transit time (30 days) is 2 days below industry average.
                Good carrier selection is paying off.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-5 h-5 text-purple-500" />
                <span className="font-medium text-purple-600 dark:text-purple-400">
                  Goal Progress
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                Your on-time rate of {stats.onTimeRate}% is above the 85% target.
                Keep up the excellent carrier management.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

