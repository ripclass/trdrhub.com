/**
 * HS Code Duty Calculator
 */
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Calculator, DollarSign, TrendingDown, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

interface DutyResult {
  hs_code: string;
  product_value: number;
  duty_calculation: {
    rate_type: string;
    rate_percent: number;
    base_duty: number;
    section_301_rate?: number;
    section_301_duty?: number;
    total_duty: number;
  };
  mfn_comparison: {
    mfn_rate: number;
    mfn_duty: number;
    savings: number;
  };
  landed_cost_estimate: {
    product_value: number;
    freight: number;
    insurance: number;
    cif_value: number;
    duty: number;
    total: number;
  };
}

const COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "EU", name: "European Union" },
  { code: "UK", name: "United Kingdom" },
  { code: "CN", name: "China" },
  { code: "JP", name: "Japan" },
  { code: "IN", name: "India" },
  { code: "CA", name: "Canada" },
  { code: "MX", name: "Mexico" },
];

export default function HSCodeDuty() {
  const [searchParams] = useSearchParams();
  const { toast } = useToast();

  const [hsCode, setHsCode] = useState(searchParams.get("code") || "");
  const [productValue, setProductValue] = useState("10000");
  const [importCountry, setImportCountry] = useState("US");
  const [exportCountry, setExportCountry] = useState("");
  const [ftaCode, setFtaCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DutyResult | null>(null);

  const handleCalculate = async () => {
    if (!hsCode.trim() || !productValue) {
      toast({
        title: "Error",
        description: "Please enter HS code and product value",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/hs-code/calculate-duty`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hs_code: hsCode,
          import_country: importCountry,
          export_country: exportCountry || undefined,
          product_value: parseFloat(productValue),
          fta_code: ftaCode || undefined,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        throw new Error("Calculation failed");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to calculate duties",
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
            <Calculator className="h-5 w-5 text-emerald-400" />
            Duty Calculator
          </h1>
          <p className="text-sm text-slate-400">
            Calculate import duties and landed costs for any HS code
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Calculate Duties</CardTitle>
              <CardDescription>Enter product details to calculate import costs</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>HS Code</Label>
                <Input
                  value={hsCode}
                  onChange={(e) => setHsCode(e.target.value)}
                  placeholder="e.g., 6109.10.0004"
                  className="mt-1 bg-slate-900 border-slate-700"
                />
              </div>
              <div>
                <Label>Product Value (USD)</Label>
                <Input
                  type="number"
                  value={productValue}
                  onChange={(e) => setProductValue(e.target.value)}
                  placeholder="10000"
                  className="mt-1 bg-slate-900 border-slate-700"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
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
                      <SelectValue placeholder="Select origin" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Not specified</SelectItem>
                      {COUNTRIES.map((c) => (
                        <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleCalculate} disabled={loading} className="w-full bg-emerald-600">
                <Calculator className="h-4 w-4 mr-2" />
                Calculate Duties
              </Button>
            </CardContent>
          </Card>

          {/* Result */}
          {result ? (
            <div className="space-y-4">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Duty Calculation</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg">
                    <span className="text-slate-400">Rate Type</span>
                    <span className="font-semibold text-white">{result.duty_calculation.rate_type}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg">
                    <span className="text-slate-400">Duty Rate</span>
                    <span className="font-semibold text-white">{result.duty_calculation.rate_percent}%</span>
                  </div>
                  {result.duty_calculation.section_301_rate && result.duty_calculation.section_301_rate > 0 && (
                    <div className="flex items-center justify-between p-3 bg-red-900/30 rounded-lg border border-red-800/50">
                      <span className="text-red-400">Section 301 Rate</span>
                      <span className="font-semibold text-red-400">+{result.duty_calculation.section_301_rate}%</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between p-3 bg-emerald-900/30 rounded-lg border border-emerald-800/50">
                    <span className="text-emerald-400">Total Duty</span>
                    <span className="font-bold text-emerald-400 text-xl">
                      ${result.duty_calculation.total_duty.toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Landed Cost Estimate</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Product Value</span>
                    <span className="text-white">${result.landed_cost_estimate.product_value.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Freight (Est.)</span>
                    <span className="text-white">${result.landed_cost_estimate.freight.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Insurance (Est.)</span>
                    <span className="text-white">${result.landed_cost_estimate.insurance.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm border-t border-slate-700 pt-2">
                    <span className="text-slate-400">CIF Value</span>
                    <span className="text-white">${result.landed_cost_estimate.cif_value.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Import Duty</span>
                    <span className="text-white">${result.landed_cost_estimate.duty.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-700 pt-2">
                    <span className="text-white font-semibold">Total Landed Cost</span>
                    <span className="text-emerald-400 font-bold text-lg">
                      ${result.landed_cost_estimate.total.toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {result.mfn_comparison.savings > 0 && (
                <Card className="bg-gradient-to-r from-emerald-900/30 to-slate-800 border-emerald-800/50">
                  <CardContent className="p-4 flex items-center gap-4">
                    <TrendingDown className="h-8 w-8 text-emerald-400" />
                    <div>
                      <p className="text-sm text-slate-400">Potential Savings with FTA</p>
                      <p className="text-xl font-bold text-emerald-400">
                        ${result.mfn_comparison.savings.toLocaleString()}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <DollarSign className="h-12 w-12 mx-auto text-slate-600 mb-4" />
                <p className="text-slate-400">Enter an HS code and value to calculate duties</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

