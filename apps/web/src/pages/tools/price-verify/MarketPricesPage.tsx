import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  RefreshCw,
  Loader2,
  ExternalLink,
  Clock,
  LineChart,
} from "lucide-react";
import PriceHistoryChart from "@/components/price-verify/PriceHistoryChart";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
  source_display?: string;
  source_url?: string;
  fetched_at: string;
  change_24h?: number;
  has_live_feed?: boolean;
}

// Demo data fallback
const DEMO_PRICES: MarketPrice[] = [
  { code: "COTTON_RAW", name: "Raw Cotton", category: "agriculture", price: 2.20, price_low: 1.90, price_high: 2.50, unit: "kg", currency: "USD", source: "world_bank", source_display: "World Bank Commodity Markets", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "CRUDE_OIL_BRENT", name: "Crude Oil (Brent)", category: "energy", price: 82.00, price_low: 75, price_high: 90, unit: "bbl", currency: "USD", source: "fred", source_display: "FRED", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "GOLD", name: "Gold", category: "metals", price: 2050, price_low: 1950, price_high: 2150, unit: "oz", currency: "USD", source: "fred", source_display: "FRED", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "COPPER", name: "Copper (Grade A)", category: "metals", price: 8500, price_low: 7800, price_high: 9200, unit: "mt", currency: "USD", source: "lme", source_display: "LME", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "RICE_WHITE", name: "White Rice (5%)", category: "agriculture", price: 520, price_low: 480, price_high: 560, unit: "mt", currency: "USD", source: "world_bank", source_display: "World Bank", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "STEEL_HRC", name: "Steel (Hot Rolled Coil)", category: "metals", price: 650, price_low: 580, price_high: 720, unit: "mt", currency: "USD", source: "curated", source_display: "CRU Index", fetched_at: new Date().toISOString(), has_live_feed: false },
  { code: "SUGAR_RAW", name: "Raw Sugar (ISA)", category: "agriculture", price: 0.48, price_low: 0.42, price_high: 0.54, unit: "kg", currency: "USD", source: "world_bank", source_display: "ISA Daily Price", fetched_at: new Date().toISOString(), has_live_feed: true },
  { code: "COFFEE_ARABICA", name: "Coffee (Arabica)", category: "agriculture", price: 4.80, price_low: 4.20, price_high: 5.40, unit: "kg", currency: "USD", source: "world_bank", source_display: "ICO Composite", fetched_at: new Date().toISOString(), has_live_feed: true },
];

export default function MarketPricesPage() {
  const [prices, setPrices] = useState<MarketPrice[]>(DEMO_PRICES);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [search, setSearch] = useState("");
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [selectedCommodity, setSelectedCommodity] = useState<MarketPrice | null>(null);
  const [showChart, setShowChart] = useState(false);

  // Fetch real commodity data on mount
  useEffect(() => {
    fetchPrices();
  }, []);

  const fetchPrices = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/price-verify/commodities`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.commodities?.length > 0) {
          // Transform API data to our format
          const transformedPrices: MarketPrice[] = data.commodities.map((c: any) => ({
            code: c.code,
            name: c.name,
            category: c.category,
            price: c.current_price || c.current_estimate || 0,
            price_low: c.price_range ? parseFloat(c.price_range.split(' - ')[0].replace('$', '')) : 0,
            price_high: c.price_range ? parseFloat(c.price_range.split(' - ')[1].replace('$', '')) : 0,
            unit: c.unit,
            currency: c.currency || 'USD',
            source: c.has_live_feed ? 'live' : 'curated',
            source_display: c.source_note || (c.has_live_feed ? 'Live Market Data' : 'TRDR Database'),
            fetched_at: new Date().toISOString(),
            has_live_feed: c.has_live_feed,
          }));
          setPrices(transformedPrices);
          setIsLive(true);
        }
      }
    } catch (error) {
      console.log("Using demo data - API not available");
    } finally {
      setLastUpdated(new Date());
      setLoading(false);
    }
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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Market Prices</h1>
            {isLive ? (
              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground">Demo Mode</Badge>
            )}
          </div>
          <p className="text-muted-foreground flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Last updated: {lastUpdated.toLocaleTimeString()}
            {isLive && <span className="text-xs">• Data from World Bank, FRED, LME</span>}
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
                    <th className="text-right p-3 font-medium w-12"></th>
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
                        <div className="flex items-center justify-end gap-2">
                          {price.has_live_feed && (
                            <span className="h-2 w-2 rounded-full bg-green-500" title="Live feed" />
                          )}
                          <Badge variant="secondary" className="font-normal">
                            {price.source_display || price.source}
                          </Badge>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedCommodity(price);
                            setShowChart(true);
                          }}
                        >
                          <LineChart className="h-4 w-4" />
                        </Button>
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

      {/* Price History Chart Modal */}
      <Dialog open={showChart} onOpenChange={setShowChart}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <LineChart className="h-5 w-5 text-primary" />
              Price History
            </DialogTitle>
          </DialogHeader>
          {selectedCommodity && (
            <div className="space-y-4">
              <PriceHistoryChart
                commodityCode={selectedCommodity.code}
                commodityName={selectedCommodity.name}
                currentPrice={selectedCommodity.price}
                unit={selectedCommodity.unit}
                currency={selectedCommodity.currency}
              />
              <div className="flex items-center justify-between text-sm text-muted-foreground pt-2 border-t">
                <span>
                  Current: <strong className="text-foreground">{formatPrice(selectedCommodity.price, selectedCommodity.unit)}/{selectedCommodity.unit}</strong>
                </span>
                <span>
                  Range: {formatPrice(selectedCommodity.price_low, selectedCommodity.unit)} - {formatPrice(selectedCommodity.price_high, selectedCommodity.unit)}
                </span>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

