/**
 * Classification Comparison Tool
 * Phase 2: Compare two products side-by-side
 */
import { useState } from "react";
import { 
  GitCompare, ArrowRight, CheckCircle2, XCircle, 
  Info, Loader2, Equal, AlertTriangle 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

interface ProductResult {
  description: string;
  hs_code: string;
  hs_description: string;
  confidence: number;
  chapter: string;
  mfn_rate: number;
  reasoning: string;
}

interface ComparisonResult {
  same_chapter: boolean;
  same_heading: boolean;
  same_subheading: boolean;
  same_code: boolean;
  rate_difference_percent: number;
  can_consolidate: boolean;
  consolidation_note: string;
}

interface CompareResponse {
  product_a: ProductResult;
  product_b: ProductResult;
  comparison: ComparisonResult;
  import_country: string;
  export_country?: string;
}

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CN", name: "China" },
  { code: "DE", name: "Germany" },
  { code: "JP", name: "Japan" },
  { code: "KR", name: "South Korea" },
  { code: "TW", name: "Taiwan" },
  { code: "VN", name: "Vietnam" },
  { code: "MX", name: "Mexico" },
  { code: "CA", name: "Canada" },
  { code: "GB", name: "United Kingdom" },
];

export default function HSCodeCompare() {
  const { toast } = useToast();
  
  const [productA, setProductA] = useState("");
  const [productB, setProductB] = useState("");
  const [importCountry, setImportCountry] = useState("US");
  const [exportCountry, setExportCountry] = useState("");
  const [isComparing, setIsComparing] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);

  const handleCompare = async () => {
    if (!productA.trim() || !productB.trim()) {
      toast({
        title: "Missing products",
        description: "Please enter descriptions for both products",
        variant: "destructive"
      });
      return;
    }

    setIsComparing(true);
    setResult(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/compare`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            product_a: productA,
            product_b: productB,
            import_country: importCountry,
            export_country: exportCountry || undefined
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Comparison failed');
      }

      const data: CompareResponse = await response.json();
      setResult(data);
    } catch (error) {
      toast({
        title: "Comparison failed",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    } finally {
      setIsComparing(false);
    }
  };

  const getSimilarityColor = (comparison: ComparisonResult) => {
    if (comparison.same_code) return "text-emerald-400";
    if (comparison.same_subheading) return "text-green-400";
    if (comparison.same_heading) return "text-yellow-400";
    if (comparison.same_chapter) return "text-orange-400";
    return "text-red-400";
  };

  const getSimilarityBadge = (comparison: ComparisonResult) => {
    if (comparison.same_code) return { label: "Same Code", color: "bg-emerald-500" };
    if (comparison.same_subheading) return { label: "Same Subheading", color: "bg-green-500" };
    if (comparison.same_heading) return { label: "Same Heading", color: "bg-yellow-500" };
    if (comparison.same_chapter) return { label: "Same Chapter", color: "bg-orange-500" };
    return { label: "Different Chapters", color: "bg-red-500" };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <GitCompare className="h-5 w-5 text-emerald-400" />
            Classification Comparison
          </h1>
          <p className="text-sm text-slate-400">
            Compare two products to see if they share the same HS code classification
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Input Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-base flex items-center gap-2">
                <span className="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded">A</span>
                Product A
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="e.g., Cotton t-shirts for men, short sleeves, knitted"
                value={productA}
                onChange={(e) => setProductA(e.target.value)}
                className="min-h-[100px] bg-slate-900 border-slate-700"
              />
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-base flex items-center gap-2">
                <span className="bg-purple-500 text-white text-xs font-bold px-2 py-0.5 rounded">B</span>
                Product B
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="e.g., Cotton polo shirts for men, short sleeves, knitted"
                value={productB}
                onChange={(e) => setProductB(e.target.value)}
                className="min-h-[100px] bg-slate-900 border-slate-700"
              />
            </CardContent>
          </Card>
        </div>

        {/* Options */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Import Country</label>
            <Select value={importCountry} onValueChange={setImportCountry}>
              <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COUNTRIES.map(c => (
                  <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm text-slate-400 mb-1 block">Export Country (Optional)</label>
            <Select value={exportCountry || "none"} onValueChange={(val) => setExportCountry(val === "none" ? "" : val)}>
              <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700">
                <SelectValue placeholder="Select origin" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Not specified</SelectItem>
                {COUNTRIES.map(c => (
                  <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button 
              onClick={handleCompare}
              disabled={isComparing || !productA.trim() || !productB.trim()}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {isComparing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Comparing...
                </>
              ) : (
                <>
                  <GitCompare className="h-4 w-4 mr-2" />
                  Compare Products
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Similarity Summary */}
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">Comparison Result</h3>
                    <p className={getSimilarityColor(result.comparison)}>
                      {result.comparison.consolidation_note}
                    </p>
                  </div>
                  <div className="text-right">
                    <Badge className={`${getSimilarityBadge(result.comparison).color} text-white`}>
                      {getSimilarityBadge(result.comparison).label}
                    </Badge>
                    {result.comparison.can_consolidate && (
                      <div className="flex items-center gap-1 mt-2 text-emerald-400 text-sm">
                        <CheckCircle2 className="h-4 w-4" />
                        Can consolidate shipments
                      </div>
                    )}
                  </div>
                </div>

                {/* Similarity Indicators */}
                <div className="grid grid-cols-4 gap-4 mt-6">
                  <div className={`p-3 rounded-lg text-center ${result.comparison.same_chapter ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-slate-900'}`}>
                    <div className="text-sm text-slate-400">Chapter</div>
                    <div className="flex justify-center mt-1">
                      {result.comparison.same_chapter ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-slate-600" />
                      )}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg text-center ${result.comparison.same_heading ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-slate-900'}`}>
                    <div className="text-sm text-slate-400">Heading</div>
                    <div className="flex justify-center mt-1">
                      {result.comparison.same_heading ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-slate-600" />
                      )}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg text-center ${result.comparison.same_subheading ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-slate-900'}`}>
                    <div className="text-sm text-slate-400">Subheading</div>
                    <div className="flex justify-center mt-1">
                      {result.comparison.same_subheading ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-slate-600" />
                      )}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg text-center ${result.comparison.same_code ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-slate-900'}`}>
                    <div className="text-sm text-slate-400">Full Code</div>
                    <div className="flex justify-center mt-1">
                      {result.comparison.same_code ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-slate-600" />
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Side by Side Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Product A Result */}
              <Card className="bg-slate-800 border-slate-700 border-l-4 border-l-blue-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-base flex items-center gap-2">
                    <span className="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded">A</span>
                    {result.product_a.description.substring(0, 50)}...
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="text-sm text-slate-400 mb-1">HS Code</div>
                    <Badge variant="outline" className="font-mono text-lg px-3 py-1">
                      {result.product_a.hs_code}
                    </Badge>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Description</div>
                    <div className="text-white text-sm">{result.product_a.hs_description}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Chapter</div>
                    <div className="text-white text-sm">{result.product_a.chapter}</div>
                  </div>
                  <div className="flex justify-between">
                    <div>
                      <div className="text-sm text-slate-400">Confidence</div>
                      <div className={result.product_a.confidence >= 0.8 ? 'text-emerald-400' : 'text-yellow-400'}>
                        {(result.product_a.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">MFN Rate</div>
                      <div className="text-white">{result.product_a.mfn_rate}%</div>
                    </div>
                  </div>
                  {result.product_a.reasoning && (
                    <div className="bg-slate-900 p-3 rounded text-xs text-slate-400">
                      <Info className="h-3 w-3 inline mr-1" />
                      {result.product_a.reasoning.substring(0, 200)}...
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Product B Result */}
              <Card className="bg-slate-800 border-slate-700 border-l-4 border-l-purple-500">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-base flex items-center gap-2">
                    <span className="bg-purple-500 text-white text-xs font-bold px-2 py-0.5 rounded">B</span>
                    {result.product_b.description.substring(0, 50)}...
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="text-sm text-slate-400 mb-1">HS Code</div>
                    <Badge variant="outline" className="font-mono text-lg px-3 py-1">
                      {result.product_b.hs_code}
                    </Badge>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Description</div>
                    <div className="text-white text-sm">{result.product_b.hs_description}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Chapter</div>
                    <div className="text-white text-sm">{result.product_b.chapter}</div>
                  </div>
                  <div className="flex justify-between">
                    <div>
                      <div className="text-sm text-slate-400">Confidence</div>
                      <div className={result.product_b.confidence >= 0.8 ? 'text-emerald-400' : 'text-yellow-400'}>
                        {(result.product_b.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">MFN Rate</div>
                      <div className="text-white">{result.product_b.mfn_rate}%</div>
                    </div>
                  </div>
                  {result.product_b.reasoning && (
                    <div className="bg-slate-900 p-3 rounded text-xs text-slate-400">
                      <Info className="h-3 w-3 inline mr-1" />
                      {result.product_b.reasoning.substring(0, 200)}...
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Rate Difference Alert */}
            {result.comparison.rate_difference_percent > 0 && (
              <Card className="bg-yellow-900/20 border-yellow-800/50">
                <CardContent className="p-4 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-yellow-400">Duty Rate Difference</p>
                    <p className="text-sm text-slate-400">
                      These products have a {result.comparison.rate_difference_percent}% difference in MFN duty rates.
                      Ensure correct classification to avoid overpaying duties or customs penalties.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Use Cases */}
        {!result && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-base">When to Use This Tool</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900 p-4 rounded-lg">
                  <Equal className="h-8 w-8 text-emerald-400 mb-2" />
                  <h4 className="font-medium text-white mb-1">Consolidate Shipments</h4>
                  <p className="text-sm text-slate-400">
                    Check if products can be shipped under the same HS code to simplify customs
                  </p>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg">
                  <AlertTriangle className="h-8 w-8 text-yellow-400 mb-2" />
                  <h4 className="font-medium text-white mb-1">Verify Classification</h4>
                  <p className="text-sm text-slate-400">
                    Ensure similar products are classified consistently
                  </p>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg">
                  <Info className="h-8 w-8 text-blue-400 mb-2" />
                  <h4 className="font-medium text-white mb-1">Duty Analysis</h4>
                  <p className="text-sm text-slate-400">
                    Compare duty rates between product variations
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

