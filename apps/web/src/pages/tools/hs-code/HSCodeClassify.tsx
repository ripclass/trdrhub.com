/**
 * HS Code Finder - Classify Product
 */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Search,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Info,
  Copy,
  Star,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
    certificate_types?: string[];
  }>;
  restrictions: string[];
  ai_reasoning: string;
}

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "EU", name: "European Union" },
  { code: "UK", name: "United Kingdom" },
  { code: "CN", name: "China" },
  { code: "JP", name: "Japan" },
  { code: "IN", name: "India" },
  { code: "AU", name: "Australia" },
  { code: "SG", name: "Singapore" },
  { code: "CA", name: "Canada" },
  { code: "MX", name: "Mexico" },
  { code: "BD", name: "Bangladesh" },
  { code: "VN", name: "Vietnam" },
  { code: "KR", name: "South Korea" },
];

export default function HSCodeClassify() {
  const [searchParams] = useSearchParams();
  const { session } = useAuth();
  const { toast } = useToast();

  const [description, setDescription] = useState(searchParams.get("q") || "");
  const [importCountry, setImportCountry] = useState("US");
  const [exportCountry, setExportCountry] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setDescription(q);
    }
  }, [searchParams]);

  const handleClassify = async () => {
    if (!description.trim()) {
      toast({
        title: "Error",
        description: "Please enter a product description",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setResult(null);
    setSaved(false);

    try {
      const response = await fetch(`${API_BASE}/hs-code/classify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(session?.access_token && { Authorization: `Bearer ${session.access_token}` }),
        },
        body: JSON.stringify({
          description,
          import_country: importCountry,
          export_country: exportCountry && exportCountry !== "none" ? exportCountry : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("Classification failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (error) {
      toast({
        title: "Classification Failed",
        description: "Unable to classify product. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!session?.access_token || !result) return;

    try {
      const response = await fetch(`${API_BASE}/hs-code/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          product_description: description,
          hs_code: result.hs_code,
          import_country: importCountry,
          export_country: exportCountry && exportCountry !== "none" ? exportCountry : undefined,
        }),
      });

      if (response.ok) {
        setSaved(true);
        toast({
          title: "Saved",
          description: "Classification saved to your history",
        });
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
    toast({ title: "Copied to clipboard" });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "text-emerald-400 bg-emerald-500/20";
    if (confidence >= 0.7) return "text-amber-400 bg-amber-500/20";
    return "text-red-400 bg-red-500/20";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Search className="h-5 w-5 text-emerald-400" />
            Classify Product
          </h1>
          <p className="text-sm text-slate-400">
            Describe your product in plain language and get AI-powered classification
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Form */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-emerald-400" />
                  Product Description
                </CardTitle>
                <CardDescription>
                  Describe your product in detail. Include material, use, dimensions, and characteristics.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="description">Product Description</Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g., Men's cotton t-shirts, short-sleeved, knitted, 100% cotton, for casual wear"
                    className="mt-1 h-32 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Import Country</Label>
                    <Select value={importCountry} onValueChange={setImportCountry}>
                      <SelectTrigger className="mt-1 bg-slate-900 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRIES.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Export Country (Optional)</Label>
                    <Select value={exportCountry} onValueChange={setExportCountry}>
                      <SelectTrigger className="mt-1 bg-slate-900 border-slate-700">
                        <SelectValue placeholder="Select origin" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Not specified</SelectItem>
                        {COUNTRIES.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button
                  onClick={handleClassify}
                  disabled={loading || !description.trim()}
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Classifying...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      Classify Product
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Result */}
            {result && (
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white">Classification Result</CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(result.hs_code)}
                      >
                        <Copy className="h-4 w-4 mr-1" />
                        Copy Code
                      </Button>
                      {session?.access_token && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleSave}
                          disabled={saved}
                        >
                          <Star className={cn("h-4 w-4 mr-1", saved && "fill-amber-400 text-amber-400")} />
                          {saved ? "Saved" : "Save"}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* HS Code */}
                  <div className="flex items-start justify-between p-4 bg-slate-900 rounded-lg">
                    <div>
                      <p className="text-sm text-slate-400">HS Code</p>
                      <p className="text-3xl font-bold text-emerald-400">{result.hs_code}</p>
                      <p className="text-sm text-slate-300 mt-1">{result.description}</p>
                    </div>
                    <Badge className={cn("px-3 py-1", getConfidenceColor(result.confidence))}>
                      {Math.round(result.confidence * 100)}% confidence
                    </Badge>
                  </div>

                  {/* Hierarchy */}
                  <div>
                    <p className="text-sm font-medium text-slate-400 mb-2">Classification Hierarchy</p>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-500">Chapter:</span>
                        <span className="text-white">{result.chapter}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-500">Heading:</span>
                        <span className="text-white">{result.heading}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-500">Subheading:</span>
                        <span className="text-white">{result.subheading}</span>
                      </div>
                    </div>
                  </div>

                  {/* AI Reasoning */}
                  <div>
                    <p className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1">
                      <Info className="h-4 w-4" />
                      Classification Reasoning
                    </p>
                    <p className="text-sm text-slate-300 bg-slate-900 p-3 rounded-lg">
                      {result.ai_reasoning}
                    </p>
                  </div>

                  {/* Duty Rates */}
                  {result.duty_rates && Object.keys(result.duty_rates).length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-400 mb-2">Duty Rates</p>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(result.duty_rates).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between p-2 bg-slate-900 rounded">
                            <span className="text-sm text-slate-400 uppercase">{key}</span>
                            <span className="text-sm font-medium text-white">{value}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* FTA Options */}
                  {result.fta_options && result.fta_options.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-400 mb-2">Available Trade Agreements</p>
                      <div className="space-y-2">
                        {result.fta_options.map((fta) => (
                          <div key={fta.code} className="flex items-center justify-between p-3 bg-slate-900 rounded-lg">
                            <div>
                              <p className="font-medium text-white">{fta.code}</p>
                              <p className="text-sm text-slate-400">{fta.name}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-emerald-400">{fta.preferential_rate}% rate</p>
                              {fta.savings_percent > 0 && (
                                <p className="text-xs text-slate-500">Save {fta.savings_percent}%</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Restrictions */}
                  {result.restrictions && result.restrictions.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        Import Restrictions
                      </p>
                      <ul className="space-y-1">
                        {result.restrictions.map((restriction, i) => (
                          <li key={i} className="text-sm text-amber-400 bg-amber-500/10 p-2 rounded">
                            {restriction}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Alternatives */}
                  {result.alternatives && result.alternatives.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-400 mb-2">Alternative Classifications</p>
                      <div className="space-y-2">
                        {result.alternatives.map((alt, i) => (
                          <div key={i} className="flex items-center justify-between p-2 bg-slate-900 rounded">
                            <div>
                              <span className="text-sm font-medium text-white">{alt.code}</span>
                              <span className="text-sm text-slate-400 ml-2">{alt.description}</span>
                            </div>
                            <Badge variant="outline" className="text-xs">
                              {Math.round((alt.score || 0.5) * 100)}%
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Tips Sidebar */}
          <div className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-base">Tips for Better Results</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm text-slate-400">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    <span>Include the <strong className="text-white">material composition</strong> (e.g., 100% cotton, polyester blend)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    <span>Specify the <strong className="text-white">intended use</strong> (e.g., for children, industrial use)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    <span>Mention if the product is <strong className="text-white">finished or unfinished</strong></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    <span>Include <strong className="text-white">dimensions or weight</strong> if relevant</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                    <span>Specify <strong className="text-white">brand names</strong> for known products</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-base">GRI Rules Applied</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 font-semibold">GRI 1:</span>
                    <span>Terms of headings and Chapter Notes</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 font-semibold">GRI 2:</span>
                    <span>Unfinished goods and mixtures</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 font-semibold">GRI 3:</span>
                    <span>Most specific description prevails</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 font-semibold">GRI 6:</span>
                    <span>Subheading classification</span>
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

