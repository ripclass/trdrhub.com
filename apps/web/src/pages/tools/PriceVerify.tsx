/**
 * Price Verification Tool
 * 
 * Verify trade document prices against real-time market data.
 * Detect over/under invoicing and TBML risks.
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import {
  DollarSign,
  Search,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ArrowRight,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Package,
  FileText,
  Plus,
  Trash2,
  Download,
  RefreshCw,
  Info,
  Loader2,
  ChevronRight,
  AlertOctagon,
} from "lucide-react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

// API base URL
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Types
interface Commodity {
  code: string;
  name: string;
  category: string;
  unit: string;
  current_estimate?: number;
}

interface VerificationResult {
  success: boolean;
  verification_id: string;
  timestamp: string;
  commodity: {
    code: string;
    name: string;
    category: string;
    matched_from: string;
  };
  document_price: {
    price: number;
    unit: string;
    currency: string;
    normalized_price: number;
    normalized_unit: string;
    quantity?: number;
    total_value?: number;
  };
  market_price: {
    price: number;
    price_low: number;
    price_high: number;
    unit: string;
    currency: string;
    source: string;
    fetched_at: string;
  };
  variance: {
    percent: number;
    absolute: number;
    direction: "over" | "under" | "match";
  };
  risk: {
    risk_level: "low" | "medium" | "high" | "critical";
    risk_flags: string[];
  };
  verdict: "pass" | "warning" | "fail";
  verdict_reason: string;
  context: {
    document_type?: string;
    document_reference?: string;
    origin_country?: string;
    destination_country?: string;
  };
  error?: string;
}

interface BatchItem {
  id: string;
  commodity: string;
  price: string;
  unit: string;
  quantity: string;
  currency: string;
}

// Categories
const CATEGORIES = [
  { value: "agriculture", label: "🌾 Agriculture" },
  { value: "energy", label: "⛽ Energy" },
  { value: "metals", label: "🔩 Metals" },
  { value: "textiles", label: "👕 Textiles" },
  { value: "chemicals", label: "🧪 Chemicals" },
  { value: "food_beverage", label: "🍖 Food & Beverage" },
  { value: "electronics", label: "💻 Electronics" },
];

// Units
const UNITS = [
  { value: "kg", label: "Kilogram (kg)" },
  { value: "mt", label: "Metric Ton (MT)" },
  { value: "lb", label: "Pound (lb)" },
  { value: "oz", label: "Ounce (oz)" },
  { value: "bbl", label: "Barrel (bbl)" },
  { value: "gal", label: "Gallon (gal)" },
  { value: "l", label: "Liter (L)" },
  { value: "m", label: "Meter (m)" },
  { value: "pcs", label: "Pieces (pcs)" },
  { value: "doz", label: "Dozen (doz)" },
];

// Risk badge colors
const RISK_COLORS: Record<string, string> = {
  low: "bg-green-500/20 text-green-400 border-green-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
};

// Verdict badge colors
const VERDICT_COLORS: Record<string, string> = {
  pass: "bg-green-500/20 text-green-400 border-green-500/30",
  warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  fail: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function PriceVerify() {
  const { toast } = useToast();
  
  // State
  const [mode, setMode] = useState<"single" | "batch">("single");
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [batchResults, setBatchResults] = useState<any>(null);
  
  // Single verification form
  const [commodity, setCommodity] = useState("");
  const [price, setPrice] = useState("");
  const [unit, setUnit] = useState("kg");
  const [currency, setCurrency] = useState("USD");
  const [quantity, setQuantity] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [documentRef, setDocumentRef] = useState("");
  
  // Batch items
  const [batchItems, setBatchItems] = useState<BatchItem[]>([
    { id: "1", commodity: "", price: "", unit: "kg", quantity: "", currency: "USD" }
  ]);
  
  // Fetch commodities on mount
  useEffect(() => {
    fetchCommodities();
  }, []);
  
  const fetchCommodities = async () => {
    try {
      const response = await fetch(`${API_BASE}/price-verify/commodities`);
      const data = await response.json();
      if (data.success) {
        setCommodities(data.commodities);
      }
    } catch (error) {
      console.error("Failed to fetch commodities:", error);
      // Use mock data for demo
      setCommodities([
        { code: "COTTON_RAW", name: "Raw Cotton", category: "agriculture", unit: "kg", current_estimate: 2.20 },
        { code: "STEEL_HRC", name: "Steel (Hot Rolled Coil)", category: "metals", unit: "mt", current_estimate: 650 },
        { code: "CRUDE_OIL_BRENT", name: "Crude Oil (Brent)", category: "energy", unit: "bbl", current_estimate: 82 },
        { code: "COPPER", name: "Copper", category: "metals", unit: "mt", current_estimate: 8500 },
        { code: "RICE_WHITE", name: "White Rice", category: "agriculture", unit: "mt", current_estimate: 520 },
        { code: "UREA", name: "Urea (Fertilizer)", category: "chemicals", unit: "mt", current_estimate: 350 },
        { code: "GARMENTS_TSHIRT", name: "T-Shirts (Basic)", category: "textiles", unit: "pcs", current_estimate: 3.50 },
        { code: "SHRIMP_FROZEN", name: "Frozen Shrimp", category: "food_beverage", unit: "kg", current_estimate: 9.00 },
      ]);
    }
  };
  
  const verifySinglePrice = async () => {
    if (!commodity || !price || !unit) {
      toast({
        title: "Missing Information",
        description: "Please enter commodity, price, and unit.",
        variant: "destructive",
      });
      return;
    }
    
    setIsLoading(true);
    setResult(null);
    
    try {
      const response = await fetch(`${API_BASE}/price-verify/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          commodity,
          price: parseFloat(price),
          unit,
          currency,
          quantity: quantity ? parseFloat(quantity) : undefined,
          document_type: documentType || undefined,
          document_reference: documentRef || undefined,
        }),
      });
      
      const data = await response.json();
      setResult(data);
      
      if (data.success) {
        toast({
          title: `Verdict: ${data.verdict.toUpperCase()}`,
          description: data.verdict_reason,
          variant: data.verdict === "pass" ? "default" : "destructive",
        });
      } else {
        toast({
          title: "Verification Failed",
          description: data.error || "Could not verify price",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Verification error:", error);
      // Demo mode - simulate a result
      const demoResult: VerificationResult = {
        success: true,
        verification_id: "demo-" + Date.now(),
        timestamp: new Date().toISOString(),
        commodity: {
          code: commodity.toUpperCase().replace(/\s+/g, "_"),
          name: commodity,
          category: "agriculture",
          matched_from: commodity,
        },
        document_price: {
          price: parseFloat(price),
          unit,
          currency,
          normalized_price: parseFloat(price),
          normalized_unit: unit,
          quantity: quantity ? parseFloat(quantity) : undefined,
          total_value: quantity ? parseFloat(price) * parseFloat(quantity) : undefined,
        },
        market_price: {
          price: parseFloat(price) * 0.9, // Simulate 10% above market
          price_low: parseFloat(price) * 0.7,
          price_high: parseFloat(price) * 1.1,
          unit,
          currency: "USD",
          source: "demo",
          fetched_at: new Date().toISOString(),
        },
        variance: {
          percent: 11.1,
          absolute: parseFloat(price) * 0.1,
          direction: "over",
        },
        risk: {
          risk_level: "medium",
          risk_flags: [],
        },
        verdict: "warning",
        verdict_reason: "Price is 11.1% above market average. Review recommended.",
        context: {
          document_type: documentType,
          document_reference: documentRef,
        },
      };
      setResult(demoResult);
      toast({
        title: "Demo Mode",
        description: "Backend not connected. Showing simulated result.",
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const verifyBatch = async () => {
    const validItems = batchItems.filter(item => item.commodity && item.price && item.unit);
    
    if (validItems.length === 0) {
      toast({
        title: "No Valid Items",
        description: "Please add at least one complete item.",
        variant: "destructive",
      });
      return;
    }
    
    setIsLoading(true);
    setBatchResults(null);
    
    try {
      const response = await fetch(`${API_BASE}/price-verify/verify/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: validItems.map(item => ({
            commodity: item.commodity,
            price: parseFloat(item.price),
            unit: item.unit,
            quantity: item.quantity ? parseFloat(item.quantity) : undefined,
            currency: item.currency,
          })),
          document_type: documentType || undefined,
          document_reference: documentRef || undefined,
        }),
      });
      
      const data = await response.json();
      setBatchResults(data);
    } catch (error) {
      console.error("Batch verification error:", error);
      toast({
        title: "Error",
        description: "Failed to verify batch. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const addBatchItem = () => {
    setBatchItems([
      ...batchItems,
      { id: Date.now().toString(), commodity: "", price: "", unit: "kg", quantity: "", currency: "USD" }
    ]);
  };
  
  const removeBatchItem = (id: string) => {
    if (batchItems.length > 1) {
      setBatchItems(batchItems.filter(item => item.id !== id));
    }
  };
  
  const updateBatchItem = (id: string, field: keyof BatchItem, value: string) => {
    setBatchItems(batchItems.map(item => 
      item.id === id ? { ...item, [field]: value } : item
    ));
  };
  
  const filteredCommodities = selectedCategory === "all"
    ? commodities
    : commodities.filter(c => c.category === selectedCategory);
  
  const renderVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case "pass":
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
      case "fail":
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return null;
    }
  };
  
  const renderVarianceIcon = (direction: string) => {
    switch (direction) {
      case "over":
        return <TrendingUp className="w-4 h-4 text-red-400" />;
      case "under":
        return <TrendingDown className="w-4 h-4 text-blue-400" />;
      default:
        return <Minus className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      {/* Hero */}
      <section className="pt-24 sm:pt-32 pb-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/5 via-transparent to-transparent" />
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-white">Price Verify</h1>
                <p className="text-slate-400 text-sm">Verify commodity prices against market data</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="pb-16">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-6xl mx-auto">
            <Tabs value={mode} onValueChange={(v) => setMode(v as "single" | "batch")} className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-slate-900/50 border border-slate-800 mb-8">
                <TabsTrigger value="single" className="data-[state=active]:bg-green-500/20 data-[state=active]:text-green-400">
                  Single Verification
                </TabsTrigger>
                <TabsTrigger value="batch" className="data-[state=active]:bg-green-500/20 data-[state=active]:text-green-400">
                  Batch Verification
                </TabsTrigger>
              </TabsList>

              {/* Single Verification */}
              <TabsContent value="single">
                <div className="grid lg:grid-cols-2 gap-8">
                  {/* Input Form */}
                  <Card className="bg-slate-900/50 border-slate-800">
                    <CardHeader>
                      <CardTitle className="text-white text-lg">Enter Price Details</CardTitle>
                      <CardDescription>
                        Search for a commodity and enter the price from your document.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Commodity Search */}
                      <div className="space-y-2">
                        <Label>Commodity *</Label>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                          <Input
                            placeholder="Search by name, code, or HS code..."
                            value={commodity}
                            onChange={(e) => setCommodity(e.target.value)}
                            className="pl-10 bg-slate-800 border-slate-700"
                          />
                        </div>
                        
                        {/* Category filter */}
                        <div className="flex flex-wrap gap-2 pt-2">
                          <Badge
                            variant="outline"
                            className={`cursor-pointer ${selectedCategory === "all" ? "bg-green-500/20 text-green-400 border-green-500/30" : "border-slate-700 text-slate-400 hover:border-slate-600"}`}
                            onClick={() => setSelectedCategory("all")}
                          >
                            All
                          </Badge>
                          {CATEGORIES.map(cat => (
                            <Badge
                              key={cat.value}
                              variant="outline"
                              className={`cursor-pointer ${selectedCategory === cat.value ? "bg-green-500/20 text-green-400 border-green-500/30" : "border-slate-700 text-slate-400 hover:border-slate-600"}`}
                              onClick={() => setSelectedCategory(cat.value)}
                            >
                              {cat.label}
                            </Badge>
                          ))}
                        </div>
                        
                        {/* Quick select commodities */}
                        {commodity.length < 2 && (
                          <div className="flex flex-wrap gap-2 pt-2">
                            {filteredCommodities.slice(0, 8).map(c => (
                              <Badge
                                key={c.code}
                                variant="outline"
                                className="cursor-pointer border-slate-700 text-slate-300 hover:border-green-500/50 hover:bg-green-500/10"
                                onClick={() => {
                                  setCommodity(c.name);
                                  setUnit(c.unit);
                                }}
                              >
                                {c.name}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {/* Price and Unit */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Price per Unit *</Label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">$</span>
                            <Input
                              type="number"
                              placeholder="0.00"
                              value={price}
                              onChange={(e) => setPrice(e.target.value)}
                              className="pl-8 bg-slate-800 border-slate-700"
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label>Unit *</Label>
                          <Select value={unit} onValueChange={setUnit}>
                            <SelectTrigger className="bg-slate-800 border-slate-700">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {UNITS.map(u => (
                                <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      
                      {/* Quantity (optional) */}
                      <div className="space-y-2">
                        <Label>Quantity (optional)</Label>
                        <Input
                          type="number"
                          placeholder="Enter quantity for total value calculation"
                          value={quantity}
                          onChange={(e) => setQuantity(e.target.value)}
                          className="bg-slate-800 border-slate-700"
                        />
                      </div>
                      
                      {/* Document context (optional) */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Document Type</Label>
                          <Select value={documentType} onValueChange={setDocumentType}>
                            <SelectTrigger className="bg-slate-800 border-slate-700">
                              <SelectValue placeholder="Select..." />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="invoice">Invoice</SelectItem>
                              <SelectItem value="lc">Letter of Credit</SelectItem>
                              <SelectItem value="contract">Contract</SelectItem>
                              <SelectItem value="proforma">Proforma Invoice</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Document Reference</Label>
                          <Input
                            placeholder="INV-001, LC-2024-001..."
                            value={documentRef}
                            onChange={(e) => setDocumentRef(e.target.value)}
                            className="bg-slate-800 border-slate-700"
                          />
                        </div>
                      </div>
                      
                      <Separator className="bg-slate-800" />
                      
                      <Button
                        className="w-full bg-green-500 hover:bg-green-600"
                        onClick={verifySinglePrice}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Verifying...
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-4 h-4 mr-2" />
                            Verify Price
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                  
                  {/* Results */}
                  <div className="space-y-6">
                    {result ? (
                      <Card className="bg-slate-900/50 border-slate-800">
                        <CardHeader className="pb-4">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-white text-lg">Verification Result</CardTitle>
                            <Badge className={VERDICT_COLORS[result.verdict]}>
                              {renderVerdictIcon(result.verdict)}
                              <span className="ml-1.5 uppercase">{result.verdict}</span>
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          {/* Commodity Info */}
                          <div className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg">
                            <Package className="w-5 h-5 text-slate-400 mt-0.5" />
                            <div>
                              <div className="font-medium text-white">{result.commodity.name}</div>
                              <div className="text-sm text-slate-400">{result.commodity.code} • {result.commodity.category}</div>
                            </div>
                          </div>
                          
                          {/* Price Comparison */}
                          <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-slate-800/50 rounded-lg">
                              <div className="text-sm text-slate-400 mb-1">Your Price</div>
                              <div className="text-2xl font-bold text-white">
                                ${result.document_price.normalized_price.toFixed(2)}
                                <span className="text-sm font-normal text-slate-400">/{result.document_price.normalized_unit}</span>
                              </div>
                            </div>
                            <div className="p-4 bg-slate-800/50 rounded-lg">
                              <div className="text-sm text-slate-400 mb-1">Market Price</div>
                              <div className="text-2xl font-bold text-white">
                                ${result.market_price.price.toFixed(2)}
                                <span className="text-sm font-normal text-slate-400">/{result.market_price.unit}</span>
                              </div>
                              <div className="text-xs text-slate-500 mt-1">
                                Range: ${result.market_price.price_low.toFixed(2)} - ${result.market_price.price_high.toFixed(2)}
                              </div>
                            </div>
                          </div>
                          
                          {/* Variance */}
                          <div className="p-4 bg-slate-800/50 rounded-lg">
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-sm text-slate-400">Variance</span>
                              <div className="flex items-center gap-2">
                                {renderVarianceIcon(result.variance.direction)}
                                <span className={`font-bold ${
                                  Math.abs(result.variance.percent) < 15 ? "text-green-400" :
                                  Math.abs(result.variance.percent) < 30 ? "text-yellow-400" : "text-red-400"
                                }`}>
                                  {result.variance.percent > 0 ? "+" : ""}{result.variance.percent.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <Progress 
                              value={Math.min(Math.abs(result.variance.percent), 100)} 
                              className="h-2"
                            />
                            <div className="flex justify-between text-xs text-slate-500 mt-1">
                              <span>0%</span>
                              <span>±15% (OK)</span>
                              <span>±30% (Warning)</span>
                              <span>50%+</span>
                            </div>
                          </div>
                          
                          {/* Risk Assessment */}
                          <div className="p-4 bg-slate-800/50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm text-slate-400">Risk Level</span>
                              <Badge className={RISK_COLORS[result.risk.risk_level]}>
                                {result.risk.risk_level.toUpperCase()}
                              </Badge>
                            </div>
                            {result.risk.risk_flags.length > 0 && (
                              <div className="flex flex-wrap gap-2 mt-2">
                                {result.risk.risk_flags.map((flag, i) => (
                                  <Badge key={i} variant="outline" className="border-red-500/30 text-red-400 text-xs">
                                    <AlertOctagon className="w-3 h-3 mr-1" />
                                    {flag.replace(/_/g, " ")}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          {/* Verdict Reason */}
                          <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                            <div className="flex items-start gap-3">
                              <Info className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                              <p className="text-sm text-slate-300">{result.verdict_reason}</p>
                            </div>
                          </div>
                          
                          {/* Source Info */}
                          <div className="text-xs text-slate-500 flex items-center justify-between">
                            <span>Source: {result.market_price.source}</span>
                            <span>ID: {result.verification_id.slice(0, 8)}...</span>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex gap-3">
                            <Button variant="outline" className="flex-1 border-slate-700">
                              <Download className="w-4 h-4 mr-2" />
                              Download PDF
                            </Button>
                            <Button 
                              variant="outline" 
                              className="border-slate-700"
                              onClick={() => setResult(null)}
                            >
                              <RefreshCw className="w-4 h-4" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ) : (
                      <Card className="bg-slate-900/50 border-slate-800">
                        <CardContent className="p-12 text-center">
                          <div className="w-16 h-16 bg-slate-800 rounded-xl flex items-center justify-center mx-auto mb-4">
                            <DollarSign className="w-8 h-8 text-slate-500" />
                          </div>
                          <h3 className="text-lg font-medium text-white mb-2">Enter Price Details</h3>
                          <p className="text-slate-400 text-sm max-w-sm mx-auto">
                            Search for a commodity and enter the price from your trade document to verify against market data.
                          </p>
                        </CardContent>
                      </Card>
                    )}
                    
                    {/* Quick Info */}
                    <Card className="bg-slate-900/50 border-slate-800">
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <Info className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                          <div className="text-sm text-slate-400">
                            <p className="font-medium text-white mb-1">How it works</p>
                            <ul className="space-y-1 text-xs">
                              <li>• Compares your price against real-time market data</li>
                              <li>• Sources: World Bank, FRED, LME, industry indices</li>
                              <li>• ±15% variance = OK, ±30% = Warning, 50%+ = TBML risk</li>
                            </ul>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </TabsContent>

              {/* Batch Verification */}
              <TabsContent value="batch">
                <Card className="bg-slate-900/50 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Batch Price Verification</CardTitle>
                    <CardDescription>
                      Verify multiple line items from an invoice or LC at once.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Batch Items */}
                    <div className="space-y-3">
                      {batchItems.map((item, index) => (
                        <div key={item.id} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                          <span className="text-slate-500 text-sm w-6">{index + 1}.</span>
                          <Input
                            placeholder="Commodity"
                            value={item.commodity}
                            onChange={(e) => updateBatchItem(item.id, "commodity", e.target.value)}
                            className="flex-1 bg-slate-700 border-slate-600"
                          />
                          <Input
                            type="number"
                            placeholder="Price"
                            value={item.price}
                            onChange={(e) => updateBatchItem(item.id, "price", e.target.value)}
                            className="w-28 bg-slate-700 border-slate-600"
                          />
                          <Select value={item.unit} onValueChange={(v) => updateBatchItem(item.id, "unit", v)}>
                            <SelectTrigger className="w-24 bg-slate-700 border-slate-600">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {UNITS.slice(0, 6).map(u => (
                                <SelectItem key={u.value} value={u.value}>{u.value}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            type="number"
                            placeholder="Qty"
                            value={item.quantity}
                            onChange={(e) => updateBatchItem(item.id, "quantity", e.target.value)}
                            className="w-20 bg-slate-700 border-slate-600"
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeBatchItem(item.id)}
                            disabled={batchItems.length === 1}
                            className="text-slate-400 hover:text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                    
                    <Button variant="outline" onClick={addBatchItem} className="border-slate-700">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Item
                    </Button>
                    
                    <Separator className="bg-slate-800" />
                    
                    {/* Document Context */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Document Type</Label>
                        <Select value={documentType} onValueChange={setDocumentType}>
                          <SelectTrigger className="bg-slate-800 border-slate-700">
                            <SelectValue placeholder="Select..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="invoice">Invoice</SelectItem>
                            <SelectItem value="lc">Letter of Credit</SelectItem>
                            <SelectItem value="contract">Contract</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Document Reference</Label>
                        <Input
                          placeholder="INV-001, LC-2024-001..."
                          value={documentRef}
                          onChange={(e) => setDocumentRef(e.target.value)}
                          className="bg-slate-800 border-slate-700"
                        />
                      </div>
                    </div>
                    
                    <Button
                      className="w-full bg-green-500 hover:bg-green-600"
                      onClick={verifyBatch}
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Verifying {batchItems.filter(i => i.commodity && i.price).length} items...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Verify All Prices
                        </>
                      )}
                    </Button>
                    
                    {/* Batch Results */}
                    {batchResults && (
                      <div className="mt-6 space-y-4">
                        <Separator className="bg-slate-800" />
                        
                        {/* Summary */}
                        <div className="grid grid-cols-4 gap-4">
                          <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                            <div className="text-2xl font-bold text-green-400">{batchResults.summary.passed}</div>
                            <div className="text-xs text-slate-400">Passed</div>
                          </div>
                          <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                            <div className="text-2xl font-bold text-yellow-400">{batchResults.summary.warnings}</div>
                            <div className="text-xs text-slate-400">Warnings</div>
                          </div>
                          <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                            <div className="text-2xl font-bold text-red-400">{batchResults.summary.failed}</div>
                            <div className="text-xs text-slate-400">Failed</div>
                          </div>
                          <div className="p-4 bg-slate-800/50 rounded-lg text-center">
                            <div className="text-2xl font-bold text-white">
                              {batchResults.summary.overall_variance_percent > 0 ? "+" : ""}
                              {batchResults.summary.overall_variance_percent.toFixed(1)}%
                            </div>
                            <div className="text-xs text-slate-400">Overall Variance</div>
                          </div>
                        </div>
                        
                        {/* Individual Results */}
                        <div className="space-y-2">
                          {batchResults.items.map((item: any, i: number) => (
                            <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                              <div className="flex items-center gap-3">
                                {renderVerdictIcon(item.verdict)}
                                <span className="text-white">{item.commodity?.name || batchItems[i]?.commodity}</span>
                              </div>
                              <div className="flex items-center gap-4">
                                <span className="text-slate-400">
                                  ${item.document_price?.price.toFixed(2)}/{item.document_price?.unit}
                                </span>
                                <span className={`font-medium ${
                                  Math.abs(item.variance?.percent || 0) < 15 ? "text-green-400" :
                                  Math.abs(item.variance?.percent || 0) < 30 ? "text-yellow-400" : "text-red-400"
                                }`}>
                                  {(item.variance?.percent || 0) > 0 ? "+" : ""}{(item.variance?.percent || 0).toFixed(1)}%
                                </span>
                                <Badge className={VERDICT_COLORS[item.verdict] || VERDICT_COLORS.warning}>
                                  {item.verdict?.toUpperCase()}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </section>

      {/* Supported Commodities */}
      <section className="py-12 bg-slate-900/30">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Package className="w-5 h-5 text-green-400" />
              50+ Supported Commodities
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {commodities.slice(0, 12).map(c => (
                <div
                  key={c.code}
                  className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-green-500/50 cursor-pointer transition-colors"
                  onClick={() => {
                    setCommodity(c.name);
                    setUnit(c.unit);
                    setMode("single");
                  }}
                >
                  <div className="text-sm font-medium text-white truncate">{c.name}</div>
                  <div className="text-xs text-slate-500">{c.category}</div>
                  {c.current_estimate && (
                    <div className="text-xs text-green-400 mt-1">${c.current_estimate}/{c.unit}</div>
                  )}
                </div>
              ))}
            </div>
            <div className="text-center mt-4">
              <Button variant="link" className="text-green-400">
                View all commodities <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      <TRDRFooter />
    </div>
  );
}

