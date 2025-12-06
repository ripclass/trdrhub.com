/**
 * FTA Eligibility Check
 */
import { useState, useEffect } from "react";
import { Globe, CheckCircle, FileText, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface FTAResult {
  fta_code: string;
  fta_name: string;
  mfn_rate: number;
  preferential_rate: number;
  savings_percent: number;
  rules_of_origin: {
    requirement: string;
    rule_type: string;
    ctc_requirement?: string;
    rvc_threshold?: string;
    certificate_required: string;
  };
  documentation: string[];
  cumulation_type?: string;
  de_minimis?: string;
}

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "MX", name: "Mexico" },
  { code: "CN", name: "China" },
  { code: "JP", name: "Japan" },
  { code: "KR", name: "South Korea" },
  { code: "VN", name: "Vietnam" },
  { code: "IN", name: "India" },
  { code: "AU", name: "Australia" },
  { code: "SG", name: "Singapore" },
  { code: "BD", name: "Bangladesh" },
  { code: "UK", name: "United Kingdom" },
];

export default function HSCodeFTA() {
  const { toast } = useToast();
  const [hsCode, setHsCode] = useState("");
  const [importCountry, setImportCountry] = useState("US");
  const [exportCountry, setExportCountry] = useState("CN");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<FTAResult[]>([]);
  const [availableFtas, setAvailableFtas] = useState<any[]>([]);

  useEffect(() => {
    fetchFtas();
  }, []);

  const fetchFtas = async () => {
    try {
      const response = await fetch(`${API_BASE}/hs-code/ftas`);
      if (response.ok) {
        const data = await response.json();
        setAvailableFtas(data.ftas || []);
      }
    } catch (error) {
      console.error("Failed to fetch FTAs:", error);
    }
  };

  const handleCheck = async () => {
    if (!hsCode.trim() || !importCountry || !exportCountry) {
      toast({
        title: "Error",
        description: "Please enter HS code and select countries",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/hs-code/fta-check?hs_code=${hsCode}&import_country=${importCountry}&export_country=${exportCountry}`
      );
      if (response.ok) {
        const data = await response.json();
        setResults(data.eligible_ftas || []);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to check FTA eligibility",
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
            <Globe className="h-5 w-5 text-emerald-400" />
            FTA Eligibility
          </h1>
          <p className="text-sm text-slate-400">
            Check Free Trade Agreement eligibility and rules of origin
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Check Eligibility</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>HS Code</Label>
                <Input
                  value={hsCode}
                  onChange={(e) => setHsCode(e.target.value)}
                  placeholder="e.g., 6109.10"
                  className="mt-1 bg-slate-900 border-slate-700"
                />
              </div>
              <div>
                <Label>Import To</Label>
                <Select value={importCountry} onValueChange={setImportCountry}>
                  <SelectTrigger className="mt-1 bg-slate-900 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COUNTRIES.map((c) => (
                      <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Export From</Label>
                <Select value={exportCountry} onValueChange={setExportCountry}>
                  <SelectTrigger className="mt-1 bg-slate-900 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COUNTRIES.map((c) => (
                      <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleCheck} disabled={loading} className="w-full bg-emerald-600">
                <Globe className="h-4 w-4 mr-2" />
                Check FTA Eligibility
              </Button>
            </CardContent>
          </Card>

          {/* Results */}
          <div className="lg:col-span-2">
            {results.length > 0 ? (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-white">
                  Found {results.length} Eligible Trade Agreement{results.length !== 1 ? "s" : ""}
                </h2>
                {results.map((fta) => (
                  <Card key={fta.fta_code} className="bg-slate-800 border-slate-700">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="text-white">{fta.fta_code}</CardTitle>
                          <CardDescription>{fta.fta_name}</CardDescription>
                        </div>
                        {fta.savings_percent > 0 && (
                          <Badge className="bg-emerald-500/20 text-emerald-400">
                            <TrendingDown className="h-3 w-3 mr-1" />
                            Save {fta.savings_percent}%
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-900 rounded-lg">
                          <p className="text-xs text-slate-400">MFN Rate</p>
                          <p className="text-lg font-semibold text-white">{fta.mfn_rate}%</p>
                        </div>
                        <div className="p-3 bg-emerald-900/30 rounded-lg border border-emerald-800/50">
                          <p className="text-xs text-emerald-400">Preferential Rate</p>
                          <p className="text-lg font-semibold text-emerald-400">{fta.preferential_rate}%</p>
                        </div>
                      </div>

                      {fta.rules_of_origin && (
                        <div>
                          <p className="text-sm font-medium text-slate-400 mb-2">Rules of Origin</p>
                          <div className="space-y-2 text-sm">
                            <div className="flex items-start gap-2">
                              <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                              <span className="text-slate-300">{fta.rules_of_origin.requirement}</span>
                            </div>
                            {fta.rules_of_origin.rvc_threshold && (
                              <div className="flex items-start gap-2">
                                <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                                <span className="text-slate-300">{fta.rules_of_origin.rvc_threshold}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {fta.documentation && (
                        <div>
                          <p className="text-sm font-medium text-slate-400 mb-2">Required Documentation</p>
                          <div className="flex flex-wrap gap-2">
                            {fta.documentation.map((doc, i) => (
                              <Badge key={i} variant="outline" className="border-slate-600 text-slate-300">
                                <FileText className="h-3 w-3 mr-1" />
                                {doc}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <Globe className="h-12 w-12 mx-auto text-slate-600 mb-4" />
                  <p className="text-slate-400">Enter an HS code and trade lane to check FTA eligibility</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

