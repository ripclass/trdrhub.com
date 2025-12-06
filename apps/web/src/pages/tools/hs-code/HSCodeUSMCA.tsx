/**
 * USMCA Rules of Origin Calculator
 * Phase 3: Complete USMCA origin determination with RVC calculator
 */
import { useState } from "react";
import { 
  Globe2, Calculator, CheckCircle2, XCircle, Info,
  Loader2, FileText, AlertTriangle, ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

interface RuleResult {
  rule_type: string;
  rule_text: string;
  ctc_type?: string;
  ctc_exceptions?: string;
  rvc_required: boolean;
  rvc_threshold?: number;
  rvc_method?: string;
  lvc_required?: boolean;
  lvc_threshold?: number;
  steel_aluminum_required?: boolean;
  process_requirements?: string;
  annex_reference?: string;
}

interface RVCResult {
  rvc_percent: number;
  threshold: number;
  meets_requirement: boolean;
}

const USMCA_COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "MX", name: "Mexico" },
];

export default function HSCodeUSMCA() {
  const { token } = useAuth();
  const { toast } = useToast();
  
  // Rule lookup
  const [hsCode, setHsCode] = useState("");
  const [exportCountry, setExportCountry] = useState("MX");
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [rule, setRule] = useState<RuleResult | null>(null);
  
  // RVC Calculator
  const [productDescription, setProductDescription] = useState("");
  const [transactionValue, setTransactionValue] = useState("");
  const [vomValue, setVomValue] = useState("");
  const [method, setMethod] = useState("transaction_value");
  const [isAutomotive, setIsAutomotive] = useState(false);
  const [highWageLabor, setHighWageLabor] = useState("");
  const [isCalculating, setIsCalculating] = useState(false);
  const [rvcResult, setRvcResult] = useState<RVCResult | null>(null);

  const lookupRules = async () => {
    if (!hsCode.trim()) {
      toast({
        title: "HS Code required",
        description: "Please enter an HS code",
        variant: "destructive"
      });
      return;
    }

    setIsLoadingRules(true);
    setRule(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/roo/rules/USMCA/${hsCode}`
      );

      if (!response.ok) {
        throw new Error('Failed to get rules');
      }

      const data = await response.json();
      setRule(data.product_specific_rule || data.general_rule || data.default_rule);
    } catch (error) {
      toast({
        title: "Lookup failed",
        description: "Could not retrieve rules of origin",
        variant: "destructive"
      });
    } finally {
      setIsLoadingRules(false);
    }
  };

  const calculateRVC = async () => {
    if (!transactionValue || !vomValue) {
      toast({
        title: "Values required",
        description: "Please enter transaction value and VOM",
        variant: "destructive"
      });
      return;
    }

    setIsCalculating(true);
    setRvcResult(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/roo/calculate-rvc`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
          },
          body: JSON.stringify({
            product_description: productDescription || `Product ${hsCode}`,
            hs_code: hsCode,
            fta_code: "USMCA",
            transaction_value: parseFloat(transactionValue),
            vom_value: parseFloat(vomValue),
            method,
            is_automotive: isAutomotive,
            high_wage_labor: highWageLabor ? parseFloat(highWageLabor) : undefined,
          })
        }
      );

      if (!response.ok) {
        throw new Error('Calculation failed');
      }

      const data = await response.json();
      setRvcResult(data.rvc_result);

      if (data.rvc_result.meets_requirement) {
        toast({
          title: "Qualifies for USMCA!",
          description: `RVC of ${data.rvc_result.rvc_percent}% meets the ${data.rvc_result.threshold}% threshold`
        });
      }
    } catch (error) {
      toast({
        title: "Calculation failed",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Globe2 className="h-5 w-5 text-emerald-400" />
            USMCA Rules of Origin
          </h1>
          <p className="text-sm text-slate-400">
            Determine USMCA eligibility with RVC calculator
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* USMCA Overview */}
        <Card className="bg-gradient-to-r from-blue-900/30 to-red-900/30 border-slate-700 mb-8">
          <CardContent className="p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="flex gap-2">
                {USMCA_COUNTRIES.map(c => (
                  <Badge key={c.code} variant="outline" className="text-white">
                    {c.code}
                  </Badge>
                ))}
              </div>
              <span className="text-white font-medium">United States-Mexico-Canada Agreement</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-slate-400">Effective</div>
                <div className="text-white">July 1, 2020</div>
              </div>
              <div>
                <div className="text-slate-400">Certificate</div>
                <div className="text-white">USMCA Certificate of Origin</div>
              </div>
              <div>
                <div className="text-slate-400">De Minimis</div>
                <div className="text-white">10% (7% for textiles)</div>
              </div>
              <div>
                <div className="text-slate-400">Cumulation</div>
                <div className="text-white">Full cumulation</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="rules" className="space-y-6">
          <TabsList className="bg-slate-800">
            <TabsTrigger value="rules">Rule Lookup</TabsTrigger>
            <TabsTrigger value="rvc">RVC Calculator</TabsTrigger>
            <TabsTrigger value="auto">Automotive Rules</TabsTrigger>
          </TabsList>

          {/* Rules Lookup Tab */}
          <TabsContent value="rules">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Find Product-Specific Rule</CardTitle>
                  <CardDescription>
                    Enter your HS code to see the applicable USMCA rule
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">HS Code</label>
                    <Input
                      placeholder="e.g., 6109.10.00"
                      value={hsCode}
                      onChange={(e) => setHsCode(e.target.value)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Export Country</label>
                    <Select value={exportCountry} onValueChange={setExportCountry}>
                      <SelectTrigger className="bg-slate-900 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {USMCA_COUNTRIES.map(c => (
                          <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button 
                    onClick={lookupRules}
                    disabled={isLoadingRules}
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                  >
                    {isLoadingRules ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <FileText className="h-4 w-4 mr-2" />
                        Find Rule
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {rule && (
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Badge className="bg-emerald-500">{rule.rule_type}</Badge>
                      Applicable Rule
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="bg-slate-900 p-4 rounded-lg">
                      <p className="text-white text-sm">{rule.rule_text}</p>
                    </div>

                    {rule.ctc_type && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">CTC Requirement</span>
                        <Badge variant="outline">{rule.ctc_type}</Badge>
                      </div>
                    )}

                    {rule.rvc_required && (
                      <div className="bg-yellow-900/20 border border-yellow-800/50 p-3 rounded">
                        <div className="flex items-center gap-2 mb-2">
                          <Calculator className="h-4 w-4 text-yellow-400" />
                          <span className="text-yellow-400 font-medium">RVC Required</span>
                        </div>
                        <div className="text-sm text-slate-400">
                          Threshold: {rule.rvc_threshold}% using {rule.rvc_method?.replace("_", " ")} method
                        </div>
                      </div>
                    )}

                    {rule.lvc_required && (
                      <div className="bg-blue-900/20 border border-blue-800/50 p-3 rounded">
                        <div className="flex items-center gap-2 mb-2">
                          <Info className="h-4 w-4 text-blue-400" />
                          <span className="text-blue-400 font-medium">LVC Required (Automotive)</span>
                        </div>
                        <div className="text-sm text-slate-400">
                          High-wage labor threshold: {rule.lvc_threshold}%
                        </div>
                      </div>
                    )}

                    {rule.process_requirements && (
                      <div>
                        <div className="text-slate-400 text-sm mb-1">Process Requirements</div>
                        <p className="text-white text-sm">{rule.process_requirements}</p>
                      </div>
                    )}

                    {rule.annex_reference && (
                      <div className="text-xs text-slate-500">
                        Reference: {rule.annex_reference}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* RVC Calculator Tab */}
          <TabsContent value="rvc">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Regional Value Content Calculator</CardTitle>
                  <CardDescription>
                    Calculate RVC to determine USMCA eligibility
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Product Description</label>
                    <Textarea
                      placeholder="Describe your product..."
                      value={productDescription}
                      onChange={(e) => setProductDescription(e.target.value)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">HS Code</label>
                    <Input
                      placeholder="e.g., 6109.10.00"
                      value={hsCode}
                      onChange={(e) => setHsCode(e.target.value)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Transaction Value (FOB)</label>
                    <Input
                      type="number"
                      placeholder="e.g., 100000"
                      value={transactionValue}
                      onChange={(e) => setTransactionValue(e.target.value)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Value of Non-Originating Materials (VOM)</label>
                    <Input
                      type="number"
                      placeholder="e.g., 35000"
                      value={vomValue}
                      onChange={(e) => setVomValue(e.target.value)}
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">RVC Method</label>
                    <Select value={method} onValueChange={setMethod}>
                      <SelectTrigger className="bg-slate-900 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="transaction_value">Transaction Value</SelectItem>
                        <SelectItem value="net_cost">Net Cost</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button 
                    onClick={calculateRVC}
                    disabled={isCalculating}
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                  >
                    {isCalculating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Calculator className="h-4 w-4 mr-2" />
                        Calculate RVC
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Results */}
              <div className="space-y-6">
                {rvcResult && (
                  <Card className={`border-2 ${rvcResult.meets_requirement ? 'border-emerald-500 bg-emerald-900/20' : 'border-red-500 bg-red-900/20'}`}>
                    <CardContent className="p-6">
                      <div className="flex items-center gap-4 mb-4">
                        {rvcResult.meets_requirement ? (
                          <CheckCircle2 className="h-12 w-12 text-emerald-400" />
                        ) : (
                          <XCircle className="h-12 w-12 text-red-400" />
                        )}
                        <div>
                          <h3 className="text-2xl font-bold text-white">
                            {rvcResult.rvc_percent.toFixed(1)}% RVC
                          </h3>
                          <p className={rvcResult.meets_requirement ? 'text-emerald-400' : 'text-red-400'}>
                            {rvcResult.meets_requirement 
                              ? 'Qualifies for USMCA preferential treatment' 
                              : `Does not meet ${rvcResult.threshold}% threshold`
                            }
                          </p>
                        </div>
                      </div>

                      <div className="bg-slate-900/50 p-4 rounded-lg">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <div className="text-slate-400">Transaction Value</div>
                            <div className="text-white font-medium">${parseFloat(transactionValue).toLocaleString()}</div>
                          </div>
                          <div>
                            <div className="text-slate-400">VOM</div>
                            <div className="text-white font-medium">${parseFloat(vomValue).toLocaleString()}</div>
                          </div>
                          <div>
                            <div className="text-slate-400">Originating Content</div>
                            <div className="text-emerald-400 font-medium">
                              ${(parseFloat(transactionValue) - parseFloat(vomValue)).toLocaleString()}
                            </div>
                          </div>
                          <div>
                            <div className="text-slate-400">Required Threshold</div>
                            <div className="text-white font-medium">{rvcResult.threshold}%</div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* RVC Formula Reference */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-base">RVC Formulas</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm">
                    <div className="bg-slate-900 p-3 rounded">
                      <div className="text-slate-400 mb-1">Transaction Value Method:</div>
                      <code className="text-emerald-400">RVC = ((TV - VNM) / TV) × 100</code>
                    </div>
                    <div className="bg-slate-900 p-3 rounded">
                      <div className="text-slate-400 mb-1">Net Cost Method:</div>
                      <code className="text-emerald-400">RVC = ((NC - VNM) / NC) × 100</code>
                    </div>
                    <div className="text-slate-500 text-xs">
                      <p>TV = Transaction Value (FOB price)</p>
                      <p>NC = Net Cost (total cost minus excluded costs)</p>
                      <p>VNM = Value of Non-originating Materials</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Automotive Rules Tab */}
          <TabsContent value="auto">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">USMCA Automotive Rules</CardTitle>
                <CardDescription>
                  Special requirements for motor vehicles and auto parts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-slate-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold text-emerald-400 mb-2">75%</div>
                    <div className="text-white font-medium mb-1">Regional Value Content</div>
                    <div className="text-sm text-slate-400">
                      Passenger vehicles must meet 75% RVC (up from 62.5% under NAFTA)
                    </div>
                  </div>

                  <div className="bg-slate-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold text-blue-400 mb-2">40-45%</div>
                    <div className="text-white font-medium mb-1">Labor Value Content</div>
                    <div className="text-sm text-slate-400">
                      Must be produced with high-wage labor ($16+/hour)
                    </div>
                  </div>

                  <div className="bg-slate-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold text-yellow-400 mb-2">70%</div>
                    <div className="text-white font-medium mb-1">Steel & Aluminum</div>
                    <div className="text-sm text-slate-400">
                      70% of steel and aluminum must be sourced from North America
                    </div>
                  </div>

                  <div className="bg-slate-900 p-4 rounded-lg">
                    <div className="text-3xl font-bold text-purple-400 mb-2">75%</div>
                    <div className="text-white font-medium mb-1">Core Parts</div>
                    <div className="text-sm text-slate-400">
                      Engine, transmission, body/chassis must meet 75% RVC
                    </div>
                  </div>
                </div>

                <div className="mt-6 bg-yellow-900/20 border border-yellow-800/50 p-4 rounded-lg">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-yellow-400 mb-1">Phase-in Period</p>
                      <p className="text-sm text-slate-400">
                        Automotive RVC requirements are phased in through 2027. 
                        Check current year requirements for your specific products.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

