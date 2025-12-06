/**
 * HS Code Search Page
 */
import { useState } from "react";
import { Search, Package, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface SearchResult {
  code: string;
  description: string;
  chapter: string;
  heading?: string;
  unit?: string;
  mfn_rate?: number;
}

export default function HSCodeSearch() {
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("US");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE}/hs-code/search?q=${encodeURIComponent(query)}&country=${country}&limit=50`
      );
      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to search HS codes",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Search className="h-5 w-5 text-emerald-400" />
            Search HS Codes
          </h1>
          <p className="text-sm text-slate-400">
            Browse and search the tariff schedule by code or description
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Enter HS code or description (e.g., 8471 or laptop)"
                  className="bg-slate-900 border-slate-700"
                />
              </div>
              <Select value={country} onValueChange={setCountry}>
                <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="US">United States</SelectItem>
                  <SelectItem value="EU">European Union</SelectItem>
                  <SelectItem value="UK">United Kingdom</SelectItem>
                  <SelectItem value="CN">China</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={handleSearch} disabled={loading} className="bg-emerald-600">
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
            </div>
          </CardContent>
        </Card>

        {results.length > 0 ? (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                Found {results.length} results
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-700">
                {results.map((item) => (
                  <div key={item.code} className="p-4 hover:bg-slate-700/50 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <Badge className="bg-emerald-500/20 text-emerald-400">{item.code}</Badge>
                        {item.mfn_rate !== undefined && (
                          <Badge variant="outline" className="border-slate-600 text-slate-400">
                            MFN: {item.mfn_rate}%
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-white mt-2">{item.description}</p>
                      <p className="text-xs text-slate-500 mt-1">{item.chapter}</p>
                    </div>
                    <Link to={`/hs-code/dashboard/duty?code=${item.code}`}>
                      <Button variant="ghost" size="sm">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="text-center py-12">
            <Package className="h-12 w-12 mx-auto text-slate-600 mb-4" />
            <p className="text-slate-400">Search for HS codes by entering a code number or product description</p>
          </div>
        )}
      </div>
    </div>
  );
}

