/**
 * Price History Chart Component
 * 
 * Displays historical commodity prices with Recharts.
 * Includes trend indicators and source attribution.
 */

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface PriceDataPoint {
  date: string;
  price: number;
  low?: number;
  high?: number;
  source?: string;
}

interface PriceHistoryChartProps {
  commodityCode: string;
  commodityName: string;
  currentPrice?: number;
  unit?: string;
  currency?: string;
  className?: string;
}

// Generate realistic demo historical data
function generateDemoHistory(basePrice: number, months: number = 12): PriceDataPoint[] {
  const history: PriceDataPoint[] = [];
  let price = basePrice * 0.9; // Start lower
  
  for (let i = months; i >= 0; i--) {
    const date = new Date();
    date.setMonth(date.getMonth() - i);
    
    // Add realistic variance
    const trend = (months - i) / months * 0.1; // Slight upward trend
    const noise = (Math.random() - 0.5) * 0.1; // ±5% noise
    price = basePrice * (0.9 + trend + noise);
    
    history.push({
      date: date.toISOString().slice(0, 7), // YYYY-MM format
      price: Math.round(price * 100) / 100,
      low: Math.round(price * 0.95 * 100) / 100,
      high: Math.round(price * 1.05 * 100) / 100,
      source: "historical",
    });
  }
  
  return history;
}

export default function PriceHistoryChart({
  commodityCode,
  commodityName,
  currentPrice = 100,
  unit = "mt",
  currency = "USD",
  className,
}: PriceHistoryChartProps) {
  const [loading, setLoading] = useState(true);
  const [historyData, setHistoryData] = useState<PriceDataPoint[]>([]);
  const [timeRange, setTimeRange] = useState<"6m" | "1y" | "2y">("1y");
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>("Simulated Data"); // Track actual source

  useEffect(() => {
    fetchHistory();
  }, [commodityCode, timeRange]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const months = timeRange === "6m" ? 6 : timeRange === "1y" ? 12 : 24;
      const response = await fetch(
        `${API_BASE}/price-verify/market-price/${commodityCode}/history?months=${months}`
      );
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.history?.length > 0) {
          setHistoryData(data.history);
          // Set the actual source from API response
          setDataSource(data.source || "World Bank");
        } else {
          // Use demo data - be honest
          setHistoryData(generateDemoHistory(currentPrice, months));
          setDataSource("Simulated Data");
        }
      } else {
        // Fallback to demo data - be honest
        const months = timeRange === "6m" ? 6 : timeRange === "1y" ? 12 : 24;
        setHistoryData(generateDemoHistory(currentPrice, months));
        setDataSource("Simulated Data");
      }
    } catch (err) {
      // Use demo data on error - be honest
      const months = timeRange === "6m" ? 6 : timeRange === "1y" ? 12 : 24;
      setHistoryData(generateDemoHistory(currentPrice, months));
      setDataSource("Simulated Data");
    } finally {
      setLoading(false);
    }
  };

  // Calculate trend
  const calculateTrend = (): { direction: "up" | "down" | "stable"; percent: number } => {
    if (historyData.length < 2) return { direction: "stable", percent: 0 };
    
    const firstPrice = historyData[0].price;
    const lastPrice = historyData[historyData.length - 1].price;
    const percentChange = ((lastPrice - firstPrice) / firstPrice) * 100;
    
    if (Math.abs(percentChange) < 2) return { direction: "stable", percent: percentChange };
    return {
      direction: percentChange > 0 ? "up" : "down",
      percent: Math.abs(percentChange),
    };
  };

  const trend = calculateTrend();

  // Format price for display
  const formatPrice = (value: number) => {
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
    if (value >= 1) return `$${value.toFixed(2)}`;
    return `$${value.toFixed(4)}`;
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-background border rounded-lg p-3 shadow-lg">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-lg font-bold text-primary">
            {formatPrice(data.price)}/{unit}
          </p>
          {data.low && data.high && (
            <p className="text-xs text-muted-foreground">
              Range: {formatPrice(data.low)} - {formatPrice(data.high)}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[200px] w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{commodityName} Price History</CardTitle>
            <CardDescription className="flex items-center gap-2">
              <Calendar className="h-3 w-3" />
              {timeRange === "6m" ? "Last 6 months" : timeRange === "1y" ? "Last 12 months" : "Last 24 months"}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {/* Trend Badge */}
            <Badge
              variant="outline"
              className={
                trend.direction === "up"
                  ? "text-green-600 border-green-600/30 bg-green-500/10"
                  : trend.direction === "down"
                  ? "text-red-600 border-red-600/30 bg-red-500/10"
                  : "text-muted-foreground"
              }
            >
              {trend.direction === "up" ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : trend.direction === "down" ? (
                <TrendingDown className="h-3 w-3 mr-1" />
              ) : (
                <Minus className="h-3 w-3 mr-1" />
              )}
              {trend.percent.toFixed(1)}%
            </Badge>
          </div>
        </div>
        
        {/* Time Range Selector */}
        <div className="flex gap-1 pt-2">
          {(["6m", "1y", "2y"] as const).map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? "secondary" : "ghost"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setTimeRange(range)}
            >
              {range}
            </Button>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs ml-auto"
            onClick={fetchHistory}
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={historyData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} />
              
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground"
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString("en-US", { month: "short" });
                }}
              />
              
              <YAxis
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground"
                tickFormatter={(value) => formatPrice(value)}
                domain={["auto", "auto"]}
                width={50}
              />
              
              <Tooltip content={<CustomTooltip />} />
              
              {/* Current price reference line */}
              {currentPrice && (
                <ReferenceLine
                  y={currentPrice}
                  stroke="hsl(var(--primary))"
                  strokeDasharray="5 5"
                  opacity={0.5}
                />
              )}
              
              {/* Price range area */}
              {historyData[0]?.low && (
                <Area
                  type="monotone"
                  dataKey="high"
                  stroke="none"
                  fill="url(#priceGradient)"
                  opacity={0.3}
                />
              )}
              
              {/* Main price line */}
              <Line
                type="monotone"
                dataKey="price"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        
        {/* Source Attribution - be honest about data source */}
        <div className="flex items-center justify-between text-xs text-muted-foreground mt-3 pt-3 border-t">
          <span>
            Data: {dataSource}
            {dataSource === "Simulated Data" && (
              <span className="ml-1 text-yellow-600">(for demonstration)</span>
            )}
          </span>
          {dataSource !== "Simulated Data" && (
            <a
              href={dataSource === "FRED" 
                ? "https://fred.stlouisfed.org/" 
                : "https://www.worldbank.org/en/research/commodity-markets"
              }
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-primary transition-colors"
            >
              View source
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

