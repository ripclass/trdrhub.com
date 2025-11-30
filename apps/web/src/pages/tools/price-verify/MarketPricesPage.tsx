import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  RefreshCw,
  Loader2,
  ExternalLink,
  Clock
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface MarketPrice {
  code: string;
  name: string;
  category: string;
  price: number;
  price_low: number;
  price_high: number;
  unit: string;
  currency: string;
  source: string;
  fetched_at: string;
  change_24h?: number;
}

// Sample data for demo (will be replaced by API)
const samplePrices: MarketPrice[] = [
  { code: "COTTON", name: "Cotton", category: "agriculture", price: 0.82, price_low: 0.78, price_high: 0.88, unit: "lb", currency: "USD", source: "World Bank", fetched_at: new Date().toISOString(), change_24h: 1.2 },
  { code: "CRUDE_WTI", name: "Crude Oil (WTI)", category: "energy", price: 71.50, price_low: 68, price_high: 78, unit: "bbl", currency: "USD", source: "FRED", fetched_at: new Date().toISOString(), change_24h: -0.8 },
  { code: "GOLD", name: "Gold", category: "precious_metals", price: 2650, price_low: 2500, price_high: 2800, unit: "oz", currency: "USD", source: "World Bank", fetched_at: new Date().toISOString(), change_24h: 0.3 },
  { code: "COPPER", name: "Copper", category: "metals", price: 8500, price_low: 8000, price_high: 9200, unit: "mt", currency: "USD", source: "LME", fetched_at: new Date().toISOString(), change_24h: -1.5 },
  { code: "RICE", name: "Rice", category: "agriculture", price: 520, price_low: 480, price_high: 580, unit: "mt", currency: "USD", source: "World Bank", fetched_at: new Date().toISOString(), change_24h: 0 },
  { code: "WHEAT", name: "Wheat", category: "agriculture", price: 220, price_low: 200, price_high: 250, unit: "mt", currency: "USD", source: "World Bank", fetched_at: new Date().toISOString(), change_24h: 2.1 },
  { code: "SUGAR", name: "Sugar (Raw)", category: "agriculture", price: 0.21, price_low: 0.18, price_high: 0.24, unit: "lb", currency: "USD", source: "ICE", fetched_at: new Date().toISOString(), change_24h: -0.5 },
  { code: "COFFEE", name: "Coffee (Arabica)", category: "agriculture", price: 3.20, price_low: 2.80, price_high: 3.60, unit: "lb", currency: "USD", source: "ICE", fetched_at: new Date().toISOString(), change_24h: 1.8 },
];

export default function MarketPricesPage() {
  const [prices, setPrices] = useState<MarketPrice[]>(samplePrices);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchPrices = async () => {
    setLoading(true);
    // TODO: Fetch from actual API
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLastUpdated(new Date());
    setLoading(false);
  };

  const filteredPrices = prices.filter(p => 
    search === "" ||
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.code.toLowerCase().includes(search.toLowerCase())
  );

  const formatPrice = (price: number, unit: string) => {
    if (price >= 1000) return `$${price.toLocaleString()}`;
    if (price >= 1) return `$${price.toFixed(2)}`;
    return `$${price.toFixed(4)}`;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Market Prices</h1>
          <p className="text-muted-foreground flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <Button onClick={fetchPrices} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search commodities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Commodities Tracked</p>
            <p className="text-2xl font-bold">{prices.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Rising Today</p>
            <p className="text-2xl font-bold text-green-600">
              {prices.filter(p => (p.change_24h || 0) > 0).length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Falling Today</p>
            <p className="text-2xl font-bold text-red-600">
              {prices.filter(p => (p.change_24h || 0) < 0).length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Data Sources</p>
            <p className="text-2xl font-bold">{[...new Set(prices.map(p => p.source))].length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Prices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Live Commodity Prices</CardTitle>
          <CardDescription>Real-time and historical price data from World Bank, FRED, and exchange APIs</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-medium">Commodity</th>
                    <th className="text-right p-3 font-medium">Price</th>
                    <th className="text-right p-3 font-medium hidden md:table-cell">Range</th>
                    <th className="text-right p-3 font-medium">24h Change</th>
                    <th className="text-right p-3 font-medium hidden sm:table-cell">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPrices.map(price => (
                    <tr key={price.code} className="border-b hover:bg-muted/50">
                      <td className="p-3">
                        <div>
                          <p className="font-medium">{price.name}</p>
                          <p className="text-xs text-muted-foreground">{price.code}</p>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <p className="font-mono font-medium">
                          {formatPrice(price.price, price.unit)}
                        </p>
                        <p className="text-xs text-muted-foreground">/{price.unit}</p>
                      </td>
                      <td className="p-3 text-right hidden md:table-cell">
                        <p className="text-sm text-muted-foreground font-mono">
                          {formatPrice(price.price_low, price.unit)} - {formatPrice(price.price_high, price.unit)}
                        </p>
                      </td>
                      <td className="p-3 text-right">
                        {price.change_24h !== undefined && (
                          <Badge
                            variant="outline"
                            className={
                              price.change_24h > 0
                                ? "text-green-600 border-green-600/30"
                                : price.change_24h < 0
                                ? "text-red-600 border-red-600/30"
                                : ""
                            }
                          >
                            {price.change_24h > 0 ? (
                              <TrendingUp className="w-3 h-3 mr-1" />
                            ) : price.change_24h < 0 ? (
                              <TrendingDown className="w-3 h-3 mr-1" />
                            ) : (
                              <Minus className="w-3 h-3 mr-1" />
                            )}
                            {price.change_24h > 0 ? "+" : ""}
                            {price.change_24h.toFixed(1)}%
                          </Badge>
                        )}
                      </td>
                      <td className="p-3 text-right hidden sm:table-cell">
                        <Badge variant="secondary" className="font-normal">
                          {price.source}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Data Sources */}
      <Card>
        <CardHeader>
          <CardTitle>Data Sources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: "World Bank", desc: "Commodity Markets", url: "https://data.worldbank.org" },
              { name: "FRED", desc: "Federal Reserve Data", url: "https://fred.stlouisfed.org" },
              { name: "LME", desc: "London Metal Exchange", url: "https://lme.com" },
              { name: "ICE", desc: "Intercontinental Exchange", url: "https://ice.com" },
            ].map(source => (
              <a
                key={source.name}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-4 rounded-lg border hover:bg-muted/50 transition-colors flex items-center justify-between"
              >
                <div>
                  <p className="font-medium">{source.name}</p>
                  <p className="text-xs text-muted-foreground">{source.desc}</p>
                </div>
                <ExternalLink className="w-4 h-4 text-muted-foreground" />
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

