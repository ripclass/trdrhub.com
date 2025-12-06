/**
 * HS Code Finder Dashboard
 * 
 * AI-powered tariff classification with duty rates and FTA eligibility.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Calculator,
  Globe,
  FileText,
  History,
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertTriangle,
  DollarSign,
  Percent,
  Package,
  Info,
  Copy,
  Download,
  Star,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface ClassificationResult {
  hs_code: string;
  description: string;
  confidence: number;
  chapter: string;
  heading: string;
  subheading: string;
  alternatives: Array<{
    code: string;
    description: string;
    score: number;
  }>;
  duty_rates: Record<string, number>;
  fta_options: Array<{
    code: string;
    name: string;
    preferential_rate: number;
    savings_percent: number;
  }>;
  restrictions: string[];
  ai_reasoning: string;
}

interface DutyCalculation {
  hs_code: string;
  product_value: number;
  duty_calculation: {
    rate_type: string;
    rate_percent: number;
    duty_amount: number;
  };
  mfn_comparison: {
    mfn_rate: number;
    mfn_duty: number;
    savings: number;
  };
  landed_cost_estimate: {
    product_value: number;
    duty: number;
    estimated_freight: number;
    total: number;
  };
}

const COUNTRIES = [
  { code: "US", name: "United States", flag: "🇺🇸" },
  { code: "EU", name: "European Union", flag: "🇪🇺" },
  { code: "UK", name: "United Kingdom", flag: "🇬🇧" },
  { code: "CN", name: "China", flag: "🇨🇳" },
  { code: "JP", name: "Japan", flag: "🇯🇵" },
  { code: "IN", name: "India", flag: "🇮🇳" },
  { code: "AU", name: "Australia", flag: "🇦🇺" },
  { code: "SG", name: "Singapore", flag: "🇸🇬" },
  { code: "CA", name: "Canada", flag: "🇨🇦" },
  { code: "MX", name: "Mexico", flag: "🇲🇽" },
  { code: "BD", name: "Bangladesh", flag: "🇧🇩" },
  { code: "PK", name: "Pakistan", flag: "🇵🇰" },
  { code: "VN", name: "Vietnam", flag: "🇻🇳" },
  { code: "KR", name: "South Korea", flag: "🇰🇷" },
];

const POPULAR_SEARCHES = [
  "Cotton t-shirts",
  "Laptops",
  "Mobile phones",
  "Coffee beans",
  "Auto parts",
  "Steel pipes",
];

export default function HSCodeDashboard() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { session } = useAuth();

  // Search state
  const [productDescription, setProductDescription] = useState("");
  const [importCountry, setImportCountry] = useState("US");
  const [exportCountry, setExportCountry] = useState("");
  const [productValue, setProductValue] = useState<number | undefined>();
  
  // Results state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [dutyCalc, setDutyCalc] = useState<DutyCalculation | null>(null);
  
  // History state
  const [history, setHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (session?.access_token) {
      fetchHistory();
    }
  }, [session?.access_token]);

  const fetchHistory = async () => {
    if (!session?.access_token) return;
    
    setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/hs-code/history?limit=10`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.classifications || []);
      }
    } catch (error) {
      console.error("Error fetching history:", error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleClassify = async () => {
    if (!productDescription.trim()) {
      toast({
        title: "Required",
        description: "Please enter a product description",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setResult(null);
    setDutyCalc(null);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${API_BASE}/hs-code/classify`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          description: productDescription,
          import_country: importCountry,
          export_country: exportCountry || undefined,
          product_value: productValue,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
        
        // Auto-calculate duty if value provided
        if (productValue) {
          calculateDuty(data.hs_code);
        }
      } else {
        throw new Error("Classification failed");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to classify product",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const calculateDuty = async (hsCode: string) => {
    if (!productValue) return;

    try {
      const res = await fetch(`${API_BASE}/hs-code/calculate-duty`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hs_code: hsCode,
          import_country: importCountry,
          export_country: exportCountry || undefined,
          product_value: productValue,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setDutyCalc(data);
      }
    } catch (error) {
      console.error("Error calculating duty:", error);
    }
  };

  const handleSave = async () => {
    if (!result || !session?.access_token) {
      toast({
        title: "Login Required",
        description: "Please login to save classifications",
        variant: "destructive",
      });
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/hs-code/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          product_description: productDescription,
          hs_code: result.hs_code,
          import_country: importCountry,
          export_country: exportCountry || undefined,
          product_value: productValue,
        }),
      });

      if (res.ok) {
        toast({
          title: "Saved",
          description: "Classification saved to history",
        });
        fetchHistory();
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save classification",
        variant: "destructive",
      });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied", description: "HS code copied to clipboard" });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600">
                <Calculator className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">HS Code Finder</h1>
                <p className="text-sm text-slate-400">AI-Powered Tariff Classification</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="border-emerald-500 text-emerald-400">
                <Sparkles className="h-3 w-3 mr-1" />
                AI Powered
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Search Panel */}
          <div className="lg:col-span-2 space-y-6">
            {/* Main Search Card */}
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Search className="h-5 w-5 text-emerald-400" />
                  Classify Your Product
                </CardTitle>
                <CardDescription>
                  Describe your product in plain language and we'll find the correct HS code
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Product Description</Label>
                  <Textarea
                    placeholder="e.g., Cotton t-shirts for men, knitted, with short sleeves..."
                    value={productDescription}
                    onChange={(e) => setProductDescription(e.target.value)}
                    className="min-h-[100px] bg-slate-900 border-slate-700"
                  />
                  <div className="flex flex-wrap gap-2">
                    {POPULAR_SEARCHES.map((search) => (
                      <Badge
                        key={search}
                        variant="outline"
                        className="cursor-pointer hover:bg-slate-700"
                        onClick={() => setProductDescription(search)}
                      >
                        {search}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Import To</Label>
                    <Select value={importCountry} onValueChange={setImportCountry}>
                      <SelectTrigger className="bg-slate-900 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRIES.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.flag} {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Export From (Optional)</Label>
                    <Select value={exportCountry} onValueChange={setExportCountry}>
                      <SelectTrigger className="bg-slate-900 border-slate-700">
                        <SelectValue placeholder="Select origin" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Not specified</SelectItem>
                        {COUNTRIES.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.flag} {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Product Value (USD)</Label>
                    <Input
                      type="number"
                      placeholder="10000"
                      value={productValue || ""}
                      onChange={(e) => setProductValue(e.target.value ? Number(e.target.value) : undefined)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>
                </div>

                <Button
                  className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700"
                  onClick={handleClassify}
                  disabled={loading}
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  Classify Product
                </Button>
              </CardContent>
            </Card>

            {/* Results */}
            {result && (
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-emerald-400" />
                      Classification Result
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge
                        className={cn(
                          "text-white",
                          result.confidence >= 0.8
                            ? "bg-emerald-500"
                            : result.confidence >= 0.6
                            ? "bg-amber-500"
                            : "bg-red-500"
                        )}
                      >
                        {Math.round(result.confidence * 100)}% Confidence
                      </Badge>
                      <Button size="sm" variant="outline" onClick={() => copyToClipboard(result.hs_code)}>
                        <Copy className="h-4 w-4" />
                      </Button>
                      {session?.access_token && (
                        <Button size="sm" variant="outline" onClick={handleSave}>
                          <Star className="h-4 w-4 mr-1" />
                          Save
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Main Result */}
                  <div className="p-4 rounded-lg bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/30">
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-mono font-bold text-emerald-400">
                        {result.hs_code}
                      </div>
                      <div className="flex-1">
                        <p className="text-white font-medium">{result.description}</p>
                        <p className="text-sm text-slate-400">{result.chapter}</p>
                      </div>
                    </div>
                  </div>

                  {/* AI Reasoning */}
                  <div className="p-4 rounded-lg bg-slate-900 border border-slate-700">
                    <div className="flex items-start gap-2">
                      <Info className="h-5 w-5 text-blue-400 mt-0.5" />
                      <div>
                        <p className="text-sm text-slate-300">{result.ai_reasoning}</p>
                      </div>
                    </div>
                  </div>

                  {/* Tabs for Details */}
                  <Tabs defaultValue="duty" className="w-full">
                    <TabsList className="bg-slate-900">
                      <TabsTrigger value="duty">Duty Rates</TabsTrigger>
                      <TabsTrigger value="fta">FTA Options</TabsTrigger>
                      <TabsTrigger value="alternatives">Alternatives</TabsTrigger>
                    </TabsList>

                    <TabsContent value="duty" className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 rounded-lg bg-slate-900 border border-slate-700">
                          <p className="text-sm text-slate-400">MFN Rate</p>
                          <p className="text-2xl font-bold text-white">
                            {result.duty_rates.mfn || 0}%
                          </p>
                        </div>
                        {result.duty_rates.gsp !== undefined && (
                          <div className="p-4 rounded-lg bg-slate-900 border border-slate-700">
                            <p className="text-sm text-slate-400">GSP Rate</p>
                            <p className="text-2xl font-bold text-emerald-400">
                              {result.duty_rates.gsp}%
                            </p>
                          </div>
                        )}
                      </div>

                      {dutyCalc && (
                        <div className="p-4 rounded-lg bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30">
                          <h4 className="text-white font-medium mb-3">
                            <DollarSign className="h-4 w-4 inline mr-1" />
                            Duty Calculation
                          </h4>
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-slate-400">Product Value</p>
                              <p className="text-white font-medium">
                                ${dutyCalc.landed_cost_estimate.product_value.toLocaleString()}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-400">Duty ({dutyCalc.duty_calculation.rate_type})</p>
                              <p className="text-amber-400 font-medium">
                                ${dutyCalc.duty_calculation.duty_amount.toLocaleString()}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-400">Landed Cost Est.</p>
                              <p className="text-emerald-400 font-bold">
                                ${dutyCalc.landed_cost_estimate.total.toLocaleString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="fta" className="space-y-4">
                      {result.fta_options.length > 0 ? (
                        result.fta_options.map((fta) => (
                          <div
                            key={fta.code}
                            className="p-4 rounded-lg bg-slate-900 border border-slate-700"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-white font-medium">{fta.name}</p>
                                <p className="text-sm text-slate-400">{fta.code}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-emerald-400 font-bold">
                                  {fta.preferential_rate}% Rate
                                </p>
                                <p className="text-sm text-slate-400">
                                  Save {fta.savings_percent}%
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-slate-400">
                          <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
                          <p>Select an export country to see FTA options</p>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="alternatives" className="space-y-4">
                      {result.alternatives.length > 0 ? (
                        result.alternatives.map((alt, idx) => (
                          <div
                            key={alt.code}
                            className="p-4 rounded-lg bg-slate-900 border border-slate-700 cursor-pointer hover:border-emerald-500/50"
                            onClick={() => {
                              setResult({
                                ...result,
                                hs_code: alt.code,
                                description: alt.description,
                              });
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-mono text-emerald-400">{alt.code}</p>
                                <p className="text-sm text-slate-300">{alt.description}</p>
                              </div>
                              <Badge variant="outline">#{idx + 2}</Badge>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-slate-400 text-center py-4">
                          No alternative codes found
                        </p>
                      )}
                    </TabsContent>
                  </Tabs>

                  {/* Restrictions */}
                  {result.restrictions.length > 0 && (
                    <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                      <h4 className="text-amber-400 font-medium mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        Import Restrictions
                      </h4>
                      <ul className="list-disc list-inside text-sm text-slate-300">
                        {result.restrictions.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Recent History */}
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2 text-base">
                  <History className="h-4 w-4 text-emerald-400" />
                  Recent Classifications
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!session?.access_token ? (
                  <div className="text-center py-4 text-slate-400">
                    <p className="text-sm">Login to save your classifications</p>
                  </div>
                ) : loadingHistory ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
                  </div>
                ) : history.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-4">
                    No classifications yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {history.map((h) => (
                      <div
                        key={h.id}
                        className="p-3 rounded-lg bg-slate-900 border border-slate-700 cursor-pointer hover:border-emerald-500/50"
                        onClick={() => {
                          setProductDescription(h.product_description);
                          setImportCountry(h.import_country);
                          if (h.export_country) setExportCountry(h.export_country);
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-emerald-400 text-sm">{h.hs_code}</span>
                          <span className="text-xs text-slate-500">
                            {new Date(h.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 truncate mt-1">
                          {h.product_description}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white text-base">Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Countries</span>
                  <Badge variant="outline">100+</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">FTAs Covered</span>
                  <Badge variant="outline">50+</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Accuracy</span>
                  <Badge className="bg-emerald-500">98%</Badge>
                </div>
              </CardContent>
            </Card>

            {/* Help */}
            <Card className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/30">
              <CardContent className="pt-6">
                <h3 className="text-white font-medium mb-2">Tips for Better Results</h3>
                <ul className="text-sm text-slate-300 space-y-2">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    Be specific about materials (cotton, steel, plastic)
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    Include the product's function or use
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    Mention if it's a part or accessory
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    Specify size/weight if relevant
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

