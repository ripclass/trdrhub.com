import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  Loader2
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface Commodity {
  code: string;
  name: string;
  category: string;
  unit: string;
  hs_codes?: string[];
  aliases?: string[];
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
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{commodity.name}</span>
                            <Badge variant="outline" className="font-mono text-xs">
                              {commodity.code}
                            </Badge>
                          </div>
                          <div className="flex gap-2 mt-1 flex-wrap">
                            <span className="text-xs text-muted-foreground">
                              Unit: {commodity.unit}
                            </span>
                            {commodity.hs_codes && commodity.hs_codes.length > 0 && (
                              <span className="text-xs text-muted-foreground">
                                HS: {commodity.hs_codes.slice(0, 2).join(", ")}
                              </span>
                            )}
                            {commodity.aliases && commodity.aliases.length > 0 && (
                              <span className="text-xs text-muted-foreground">
                                Also: {commodity.aliases.slice(0, 2).join(", ")}
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
    </div>
  );
}

