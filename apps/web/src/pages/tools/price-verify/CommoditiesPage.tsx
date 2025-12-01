import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { 
  Search, 
  Wheat, 
  Fuel, 
  Gem, 
  Factory, 
  Shirt,
  Fish,
  Cpu,
  FlaskConical,
  ChevronRight,
  Loader2,
  TrendingUp,
  DollarSign,
  LineChart,
  ExternalLink,
  CheckCircle
} from "lucide-react";
import PriceHistoryChart from "@/components/price-verify/PriceHistoryChart";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface Commodity {
  code: string;
  name: string;
  category: string;
  unit: string;
  hs_codes?: string[];
  aliases?: string[];
  current_estimate?: number;
  price_low?: number;
  price_high?: number;
  has_live_feed?: boolean;
  source_display?: string;
}

const categoryIcons: Record<string, any> = {
  agriculture: Wheat,
  energy: Fuel,
  metals: Gem,
  precious_metals: Gem,
  textiles: Shirt,
  food_beverage: Fish,
  electronics: Cpu,
  chemicals: FlaskConical,
  default: Factory,
};

const categoryColors: Record<string, string> = {
  agriculture: "bg-green-500/10 text-green-600 border-green-500/20",
  energy: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  metals: "bg-slate-500/10 text-slate-600 border-slate-500/20",
  precious_metals: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
  textiles: "bg-purple-500/10 text-purple-600 border-purple-500/20",
  food_beverage: "bg-cyan-500/10 text-cyan-600 border-cyan-500/20",
  electronics: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  chemicals: "bg-pink-500/10 text-pink-600 border-pink-500/20",
};

export default function CommoditiesPage() {
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedCommodity, setSelectedCommodity] = useState<Commodity | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  useEffect(() => {
    fetchCommodities();
  }, []);

  const fetchCommodities = async () => {
    try {
      const response = await fetch(`${API_BASE}/price-verify/commodities`);
      if (response.ok) {
        const data = await response.json();
        setCommodities(data.commodities || []);
      }
    } catch (err) {
      console.error("Failed to fetch commodities:", err);
    } finally {
      setLoading(false);
    }
  };

  const categories = [...new Set(commodities.map(c => c.category))];

  const filteredCommodities = commodities.filter(c => {
    const matchesSearch = search === "" || 
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.aliases?.some(a => a.toLowerCase().includes(search.toLowerCase()));
    const matchesCategory = !selectedCategory || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const groupedCommodities = filteredCommodities.reduce((acc, c) => {
    if (!acc[c.category]) acc[c.category] = [];
    acc[c.category].push(c);
    return acc;
  }, {} as Record<string, Commodity[]>);

  const handleCommodityClick = (commodity: Commodity) => {
    setSelectedCommodity(commodity);
    setShowDetailModal(true);
  };

  const formatPrice = (price?: number) => {
    if (!price) return "N/A";
    if (price >= 1000) return `$${price.toLocaleString()}`;
    if (price >= 1) return `$${price.toFixed(2)}`;
    return `$${price.toFixed(4)}`;
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commodities Database</h1>
        <p className="text-muted-foreground">
          {commodities.length} commodities with real-time market price tracking.
        </p>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search commodities by name, code, or alias..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Button>
          {categories.map(cat => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
            >
              {cat.replace(/_/g, " ")}
            </Button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {categories.slice(0, 4).map(cat => {
          const Icon = categoryIcons[cat] || categoryIcons.default;
          const count = commodities.filter(c => c.category === cat).length;
          return (
            <Card key={cat} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedCategory(cat)}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`p-2 rounded-lg ${categoryColors[cat] || "bg-muted"}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-semibold capitalize">{cat.replace(/_/g, " ")}</p>
                  <p className="text-sm text-muted-foreground">{count} items</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Commodities List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedCommodities).map(([category, items]) => {
            const Icon = categoryIcons[category] || categoryIcons.default;
            return (
              <Card key={category}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 capitalize">
                    <Icon className="w-5 h-5" />
                    {category.replace(/_/g, " ")}
                  </CardTitle>
                  <CardDescription>{items.length} commodities</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-2">
                    {items.map(commodity => (
                      <div
                        key={commodity.code}
                        onClick={() => handleCommodityClick(commodity)}
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{commodity.name}</span>
                            <Badge variant="outline" className="font-mono text-xs">
                              {commodity.code}
                            </Badge>
                            {commodity.has_live_feed && (
                              <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                                Live
                              </Badge>
                            )}
                          </div>
                          <div className="flex gap-4 mt-1 flex-wrap items-center">
                            <span className="text-xs text-muted-foreground">
                              Unit: {commodity.unit}
                            </span>
                            {commodity.current_estimate && (
                              <span className="text-xs font-medium text-primary">
                                {formatPrice(commodity.current_estimate)}/{commodity.unit}
                              </span>
                            )}
                            {commodity.source_display && (
                              <span className="text-xs text-muted-foreground">
                                via {commodity.source_display}
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {filteredCommodities.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">No commodities found matching your search.</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Commodity Detail Modal */}
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedCommodity && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <DialogTitle className="text-xl">{selectedCommodity.name}</DialogTitle>
                  <Badge variant="outline" className="font-mono">
                    {selectedCommodity.code}
                  </Badge>
                  {selectedCommodity.has_live_feed && (
                    <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                      Live Data
                    </Badge>
                  )}
                </div>
                <DialogDescription>
                  {selectedCommodity.category.replace(/_/g, " ")} • Unit: {selectedCommodity.unit}
                </DialogDescription>
              </DialogHeader>

              {/* Price Summary */}
              <div className="grid grid-cols-3 gap-4 py-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <DollarSign className="w-4 h-4" />
                      <span className="text-xs">Current Price</span>
                    </div>
                    <p className="text-2xl font-bold">
                      {formatPrice(selectedCommodity.current_estimate)}
                    </p>
                    <p className="text-xs text-muted-foreground">per {selectedCommodity.unit}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <TrendingUp className="w-4 h-4" />
                      <span className="text-xs">Price Range</span>
                    </div>
                    <p className="text-lg font-semibold">
                      {formatPrice(selectedCommodity.price_low)} - {formatPrice(selectedCommodity.price_high)}
                    </p>
                    <p className="text-xs text-muted-foreground">typical range</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                      <ExternalLink className="w-4 h-4" />
                      <span className="text-xs">Data Source</span>
                    </div>
                    <p className="text-lg font-semibold">
                      {selectedCommodity.source_display || "TRDR Database"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedCommodity.has_live_feed ? "real-time" : "curated data"}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Price History Chart */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <LineChart className="w-4 h-4" />
                    Price History
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <PriceHistoryChart 
                    commodityCode={selectedCommodity.code}
                    commodityName={selectedCommodity.name}
                  />
                </CardContent>
              </Card>

              {/* Additional Info */}
              {(selectedCommodity.hs_codes?.length || selectedCommodity.aliases?.length) && (
                <Card>
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-2 gap-4">
                      {selectedCommodity.hs_codes && selectedCommodity.hs_codes.length > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">HS Codes</p>
                          <div className="flex flex-wrap gap-1">
                            {selectedCommodity.hs_codes.map(hs => (
                              <Badge key={hs} variant="outline" className="font-mono text-xs">
                                {hs}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {selectedCommodity.aliases && selectedCommodity.aliases.length > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">Also Known As</p>
                          <div className="flex flex-wrap gap-1">
                            {selectedCommodity.aliases.map(alias => (
                              <Badge key={alias} variant="secondary" className="text-xs">
                                {alias}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <Button asChild className="flex-1">
                  <Link to={`/price-verify/dashboard/verify?commodity=${selectedCommodity.code}`}>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Verify Price for {selectedCommodity.name}
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link to="/price-verify/dashboard/prices">
                    <LineChart className="w-4 h-4 mr-2" />
                    Market Prices
                  </Link>
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

