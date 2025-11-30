/**
 * Price Verify - Single Verification Page
 * 
 * The main verification form within the dashboard.
 * Supports both manual input and document upload with OCR extraction.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  CheckCircle,
  AlertTriangle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Package,
  Info,
  Loader2,
  Download,
  RefreshCw,
  AlertOctagon,
  Upload,
  FileText,
  X,
  Sparkles,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
  low: "bg-green-500/10 text-green-500 border-green-500/20",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
};

// Verdict badge colors
const VERDICT_COLORS: Record<string, string> = {
  pass: "bg-green-500/10 text-green-500 border-green-500/20",
  warning: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  fail: "bg-red-500/10 text-red-500 border-red-500/20",
};

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
  };
  variance: {
    percent: number;
    absolute: number;
    direction: "over" | "under" | "match";
  };
  risk: {
    risk_level: string;
    risk_flags: string[];
  };
  verdict: string;
  verdict_reason: string;
}

interface ExtractedLineItem {
  commodity_name: string;
  commodity_code?: string;
  quantity?: number;
  unit?: string;
  unit_price?: number;
  total_price?: number;
  currency: string;
  confidence: number;
}

interface ExtractionResult {
  success: boolean;
  extraction: {
    document_info: {
      document_type?: string;
      document_number?: string;
      document_date?: string;
      seller_name?: string;
      buyer_name?: string;
    };
    line_items: ExtractedLineItem[];
    totals: {
      total_amount?: number;
      currency: string;
    };
  };
  verifications?: VerificationResult[];
  summary?: {
    total_items: number;
    passed: number;
    warnings: number;
    failed: number;
    tbml_flags: number;
  };
}

export default function VerifyPage() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // State
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  
  // Form state
  const [commodity, setCommodity] = useState("");
  const [price, setPrice] = useState("");
  const [unit, setUnit] = useState("kg");
  const [currency] = useState("USD");
  const [quantity, setQuantity] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [documentRef, setDocumentRef] = useState("");
  
  // Document upload state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  
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
      // Use demo data
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
  
  // Document upload handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);
  
  const handleFileSelect = (file: File) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid File Type",
        description: "Please upload a PDF, JPG, PNG, or TIFF file.",
        variant: "destructive",
      });
      return;
    }
    
    // Validate file size (20MB max)
    if (file.size > 20 * 1024 * 1024) {
      toast({
        title: "File Too Large",
        description: "Maximum file size is 20MB.",
        variant: "destructive",
      });
      return;
    }
    
    setUploadedFile(file);
    setExtractionResult(null);
  };
  
  const extractPricesFromDocument = async () => {
    if (!uploadedFile) return;
    
    setIsExtracting(true);
    setExtractionResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      formData.append('auto_verify', 'true');
      
      const response = await fetch(`${API_BASE}/price-verify/extract`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      
      if (data.success) {
        setExtractionResult(data);
        
        const itemCount = data.extraction?.line_items?.length || 0;
        toast({
          title: "Extraction Complete",
          description: `Found ${itemCount} line item(s) with prices.`,
        });
      } else {
        toast({
          title: "Extraction Failed",
          description: data.detail || "Could not extract prices from document.",
          variant: "destructive",
        });
      }
    } catch (error) {
      // Demo extraction result
      const demoExtraction: ExtractionResult = {
        success: true,
        extraction: {
          document_info: {
            document_type: "invoice",
            document_number: "INV-2024-001",
            document_date: "2024-11-30",
            seller_name: "ABC Trading Co.",
            buyer_name: "XYZ Imports Ltd.",
          },
          line_items: [
            { commodity_name: "Raw Cotton", quantity: 5000, unit: "kg", unit_price: 2.45, total_price: 12250, currency: "USD", confidence: 0.92 },
            { commodity_name: "Polyester Fiber", quantity: 2000, unit: "kg", unit_price: 1.85, total_price: 3700, currency: "USD", confidence: 0.88 },
          ],
          totals: {
            total_amount: 15950,
            currency: "USD",
          },
        },
        verifications: [
          {
            success: true,
            verification_id: "demo-1",
            timestamp: new Date().toISOString(),
            commodity: { code: "COTTON_RAW", name: "Raw Cotton", category: "agriculture" },
            document_price: { price: 2.45, unit: "kg", currency: "USD", normalized_price: 2.45, normalized_unit: "kg" },
            market_price: { price: 2.20, price_low: 2.00, price_high: 2.40, unit: "kg", currency: "USD", source: "demo" },
            variance: { percent: 11.4, absolute: 0.25, direction: "over" },
            risk: { risk_level: "medium", risk_flags: [] },
            verdict: "warning",
            verdict_reason: "Price is 11.4% above market average.",
          },
          {
            success: true,
            verification_id: "demo-2",
            timestamp: new Date().toISOString(),
            commodity: { code: "POLYESTER_FIBER", name: "Polyester Fiber", category: "textiles" },
            document_price: { price: 1.85, unit: "kg", currency: "USD", normalized_price: 1.85, normalized_unit: "kg" },
            market_price: { price: 1.75, price_low: 1.60, price_high: 1.90, unit: "kg", currency: "USD", source: "demo" },
            variance: { percent: 5.7, absolute: 0.10, direction: "over" },
            risk: { risk_level: "low", risk_flags: [] },
            verdict: "pass",
            verdict_reason: "Price within acceptable market range.",
          },
        ],
        summary: {
          total_items: 2,
          passed: 1,
          warnings: 1,
          failed: 0,
          tbml_flags: 0,
        },
      };
      
      setExtractionResult(demoExtraction);
      toast({
        title: "Demo Mode",
        description: "Backend not connected. Showing simulated extraction.",
      });
    } finally {
      setIsExtracting(false);
    }
  };
  
  const clearUpload = () => {
    setUploadedFile(null);
    setExtractionResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const useExtractedItem = (item: ExtractedLineItem) => {
    setCommodity(item.commodity_name || '');
    setPrice(item.unit_price?.toString() || '');
    setUnit(item.unit || 'kg');
    setQuantity(item.quantity?.toString() || '');
    toast({
      title: "Item Loaded",
      description: `${item.commodity_name} loaded for manual verification.`,
    });
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
      }
    } catch (error) {
      // Demo result
      const demoResult: VerificationResult = {
        success: true,
        verification_id: "demo-" + Date.now(),
        timestamp: new Date().toISOString(),
        commodity: {
          code: commodity.toUpperCase().replace(/\s+/g, "_"),
          name: commodity,
          category: "agriculture",
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
          price: parseFloat(price) * 0.9,
          price_low: parseFloat(price) * 0.7,
          price_high: parseFloat(price) * 1.1,
          unit,
          currency: "USD",
          source: "demo",
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
  
  const filteredCommodities = selectedCategory === "all"
    ? commodities
    : commodities.filter(c => c.category === selectedCategory);
  
  const renderVerdictIcon = (verdict: string) => {
    switch (verdict) {
      case "pass":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "warning":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "fail":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const renderVarianceIcon = (direction: string) => {
    switch (direction) {
      case "over":
        return <TrendingUp className="h-4 w-4 text-red-500" />;
      case "under":
        return <TrendingDown className="h-4 w-4 text-blue-500" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">New Verification</h1>
        <p className="text-muted-foreground">
          Verify commodity prices against real-time market data.
        </p>
      </div>

      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Upload Document
          </TabsTrigger>
          <TabsTrigger value="manual" className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Manual Entry
          </TabsTrigger>
        </TabsList>

        {/* Document Upload Tab */}
        <TabsContent value="upload" className="mt-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Upload Area */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  AI-Powered Extraction
                </CardTitle>
                <CardDescription>
                  Upload an invoice, LC, or contract and we'll automatically extract prices.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!uploadedFile ? (
                  <div
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                      isDragOver 
                        ? 'border-primary bg-primary/5' 
                        : 'border-muted-foreground/25 hover:border-primary/50'
                    }`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                  >
                    <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
                    <p className="font-medium mb-1">Drop your document here</p>
                    <p className="text-sm text-muted-foreground mb-4">
                      PDF, JPG, PNG, or TIFF (max 20MB)
                    </p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif"
                      className="hidden"
                      onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    />
                    <Button 
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      Browse Files
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* File Preview */}
                    <div className="flex items-center gap-3 p-4 rounded-lg border bg-muted/30">
                      <FileText className="h-8 w-8 text-primary flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{uploadedFile.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(uploadedFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={clearUpload}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <Button
                      className="w-full"
                      onClick={extractPricesFromDocument}
                      disabled={isExtracting}
                    >
                      {isExtracting ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Extracting Prices...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4 mr-2" />
                          Extract & Verify Prices
                        </>
                      )}
                    </Button>
                  </div>
                )}
                
                {/* Supported Documents */}
                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-medium">Supported documents:</p>
                  <ul className="flex flex-wrap gap-2">
                    <li className="px-2 py-1 bg-muted rounded">Commercial Invoice</li>
                    <li className="px-2 py-1 bg-muted rounded">Letter of Credit</li>
                    <li className="px-2 py-1 bg-muted rounded">Purchase Contract</li>
                    <li className="px-2 py-1 bg-muted rounded">Proforma Invoice</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
            
            {/* Extraction Results */}
            <div className="space-y-6">
              {extractionResult ? (
                <>
                  {/* Summary Card */}
                  <Card>
                    <CardHeader className="pb-4">
                      <div className="flex items-center justify-between">
                        <CardTitle>Extraction Results</CardTitle>
                        {extractionResult.summary && (
                          <div className="flex gap-2">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                              {extractionResult.summary.passed} Passed
                            </Badge>
                            {extractionResult.summary.warnings > 0 && (
                              <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
                                {extractionResult.summary.warnings} Warning
                              </Badge>
                            )}
                            {extractionResult.summary.failed > 0 && (
                              <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
                                {extractionResult.summary.failed} Failed
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Document Info */}
                      {extractionResult.extraction.document_info.document_number && (
                        <div className="p-3 rounded-lg border bg-muted/30 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <span className="text-muted-foreground">Doc #:</span>{' '}
                              {extractionResult.extraction.document_info.document_number}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Date:</span>{' '}
                              {extractionResult.extraction.document_info.document_date || 'N/A'}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Seller:</span>{' '}
                              {extractionResult.extraction.document_info.seller_name || 'N/A'}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Buyer:</span>{' '}
                              {extractionResult.extraction.document_info.buyer_name || 'N/A'}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Line Items */}
                      <div className="space-y-3">
                        {extractionResult.extraction.line_items.map((item, index) => {
                          const verification = extractionResult.verifications?.[index];
                          return (
                            <div key={index} className="p-4 rounded-lg border">
                              <div className="flex items-start justify-between mb-2">
                                <div>
                                  <div className="font-medium">{item.commodity_name || 'Unknown'}</div>
                                  <div className="text-sm text-muted-foreground">
                                    {item.quantity} {item.unit} @ ${item.unit_price?.toFixed(2)}/{item.unit}
                                  </div>
                                </div>
                                {verification && (
                                  <Badge variant="outline" className={VERDICT_COLORS[verification.verdict]}>
                                    {renderVerdictIcon(verification.verdict)}
                                    <span className="ml-1 uppercase">{verification.verdict}</span>
                                  </Badge>
                                )}
                              </div>
                              
                              {verification && (
                                <div className="flex items-center gap-4 text-sm">
                                  <span className="text-muted-foreground">
                                    Market: ${verification.market_price.price.toFixed(2)}/{verification.market_price.unit}
                                  </span>
                                  <span className={`font-medium ${
                                    Math.abs(verification.variance.percent) < 15 ? "text-green-500" :
                                    Math.abs(verification.variance.percent) < 30 ? "text-yellow-500" : "text-red-500"
                                  }`}>
                                    {verification.variance.percent > 0 ? "+" : ""}{verification.variance.percent.toFixed(1)}%
                                  </span>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="ml-auto"
                                    onClick={() => useExtractedItem(item)}
                                  >
                                    Edit
                                  </Button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      
                      {/* Total */}
                      {extractionResult.extraction.totals.total_amount && (
                        <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
                          <span className="font-medium">Total Document Value</span>
                          <span className="text-lg font-bold">
                            ${extractionResult.extraction.totals.total_amount.toLocaleString()}
                          </span>
                        </div>
                      )}
                      
                      {/* Actions */}
                      <div className="flex gap-3">
                        <Button variant="outline" className="flex-1">
                          <Download className="h-4 w-4 mr-2" />
                          Download Report
                        </Button>
                        <Button variant="outline" onClick={clearUpload}>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          New Upload
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card>
                  <CardContent className="p-12 text-center">
                    <div className="h-16 w-16 rounded-xl bg-muted flex items-center justify-center mx-auto mb-4">
                      <FileText className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">Upload a Document</h3>
                    <p className="text-muted-foreground text-sm max-w-sm mx-auto">
                      Upload an invoice or LC and our AI will extract commodity prices and verify them automatically.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Manual Entry Tab */}
        <TabsContent value="manual" className="mt-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Input Form */}
            <Card>
              <CardHeader>
                <CardTitle>Price Details</CardTitle>
                <CardDescription>
                  Enter the commodity and price from your trade document.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
            {/* Commodity Search */}
            <div className="space-y-2">
              <Label>Commodity *</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, code, or HS code..."
                  value={commodity}
                  onChange={(e) => setCommodity(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              {/* Category filter */}
              <div className="flex flex-wrap gap-2 pt-2">
                <Badge
                  variant="outline"
                  className={`cursor-pointer ${selectedCategory === "all" ? "bg-primary/10 text-primary border-primary/20" : ""}`}
                  onClick={() => setSelectedCategory("all")}
                >
                  All
                </Badge>
                {CATEGORIES.map(cat => (
                  <Badge
                    key={cat.value}
                    variant="outline"
                    className={`cursor-pointer ${selectedCategory === cat.value ? "bg-primary/10 text-primary border-primary/20" : ""}`}
                    onClick={() => setSelectedCategory(cat.value)}
                  >
                    {cat.label}
                  </Badge>
                ))}
              </div>
              
              {/* Quick select commodities */}
              {commodity.length < 2 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {filteredCommodities.slice(0, 6).map(c => (
                    <Badge
                      key={c.code}
                      variant="secondary"
                      className="cursor-pointer hover:bg-secondary/80"
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
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <Input
                    type="number"
                    placeholder="0.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Unit *</Label>
                <Select value={unit} onValueChange={setUnit}>
                  <SelectTrigger>
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
              />
            </div>
            
            {/* Document context (optional) */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Document Type</Label>
                <Select value={documentType} onValueChange={setDocumentType}>
                  <SelectTrigger>
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
                />
              </div>
            </div>
            
            <Separator />
            
            <Button
              className="w-full"
              onClick={verifySinglePrice}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Verify Price
                </>
              )}
            </Button>
          </CardContent>
        </Card>
        
        {/* Results */}
        <div className="space-y-6">
          {result ? (
            <Card>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle>Verification Result</CardTitle>
                  <Badge variant="outline" className={VERDICT_COLORS[result.verdict]}>
                    {renderVerdictIcon(result.verdict)}
                    <span className="ml-1.5 uppercase">{result.verdict}</span>
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Commodity Info */}
                <div className="flex items-start gap-3 p-3 rounded-lg border bg-muted/30">
                  <Package className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <div className="font-medium">{result.commodity.name}</div>
                    <div className="text-sm text-muted-foreground">{result.commodity.code} • {result.commodity.category}</div>
                  </div>
                </div>
                
                {/* Price Comparison */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg border bg-muted/30">
                    <div className="text-sm text-muted-foreground mb-1">Your Price</div>
                    <div className="text-2xl font-bold">
                      ${result.document_price.normalized_price.toFixed(2)}
                      <span className="text-sm font-normal text-muted-foreground">/{result.document_price.normalized_unit}</span>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border bg-muted/30">
                    <div className="text-sm text-muted-foreground mb-1">Market Price</div>
                    <div className="text-2xl font-bold">
                      ${result.market_price.price.toFixed(2)}
                      <span className="text-sm font-normal text-muted-foreground">/{result.market_price.unit}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Range: ${result.market_price.price_low.toFixed(2)} - ${result.market_price.price_high.toFixed(2)}
                    </div>
                  </div>
                </div>
                
                {/* Variance */}
                <div className="p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-muted-foreground">Variance</span>
                    <div className="flex items-center gap-2">
                      {renderVarianceIcon(result.variance.direction)}
                      <span className={`font-bold ${
                        Math.abs(result.variance.percent) < 15 ? "text-green-500" :
                        Math.abs(result.variance.percent) < 30 ? "text-yellow-500" : "text-red-500"
                      }`}>
                        {result.variance.percent > 0 ? "+" : ""}{result.variance.percent.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <Progress 
                    value={Math.min(Math.abs(result.variance.percent), 100)} 
                    className="h-2"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>0%</span>
                    <span>±15% (OK)</span>
                    <span>±30% (Warning)</span>
                    <span>50%+</span>
                  </div>
                </div>
                
                {/* Risk Assessment */}
                <div className="p-4 rounded-lg border bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">Risk Level</span>
                    <Badge variant="outline" className={RISK_COLORS[result.risk.risk_level]}>
                      {result.risk.risk_level.toUpperCase()}
                    </Badge>
                  </div>
                  {result.risk.risk_flags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {result.risk.risk_flags.map((flag, i) => (
                        <Badge key={i} variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20 text-xs">
                          <AlertOctagon className="h-3 w-3 mr-1" />
                          {flag.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
                
                {/* Verdict Reason */}
                <div className="p-4 rounded-lg border">
                  <div className="flex items-start gap-3">
                    <Info className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                    <p className="text-sm">{result.verdict_reason}</p>
                  </div>
                </div>
                
                {/* Source Info */}
                <div className="text-xs text-muted-foreground flex items-center justify-between">
                  <span>Source: {result.market_price.source}</span>
                  <span>ID: {result.verification_id.slice(0, 8)}...</span>
                </div>
                
                {/* Actions */}
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1">
                    <Download className="h-4 w-4 mr-2" />
                    Download PDF
                  </Button>
                  <Button 
                    variant="outline"
                    onClick={() => setResult(null)}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <div className="h-16 w-16 rounded-xl bg-muted flex items-center justify-center mx-auto mb-4">
                  <Search className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium mb-2">Enter Price Details</h3>
                <p className="text-muted-foreground text-sm max-w-sm mx-auto">
                  Search for a commodity and enter the price from your trade document to verify against market data.
                </p>
              </CardContent>
            </Card>
          )}
          
          {/* Quick Info */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <p className="font-medium text-foreground mb-1">How it works</p>
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
      </Tabs>
    </div>
  );
}

