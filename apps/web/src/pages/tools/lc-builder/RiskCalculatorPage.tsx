/**
 * Risk Calculator Page
 * 
 * Calculate risk score for LC applications based on various factors.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
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
  AlertTriangle,
  Calculator,
  CheckCircle,
  AlertCircle,
  Shield,
  Info,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

interface RiskFactor {
  name: string;
  value: string;
  impact: "positive" | "negative" | "neutral";
  points: number;
  recommendation?: string;
}

interface RiskResult {
  score: number;
  level: "low" | "medium" | "high" | "critical";
  factors: RiskFactor[];
}

export default function RiskCalculatorPage() {
  const [formData, setFormData] = useState({
    lcAmount: "",
    currency: "USD",
    paymentTerms: "sight",
    beneficiaryCountry: "",
    applicantCountry: "",
    goodsType: "general",
    isConfirmed: "no",
    firstTimeTransaction: "no",
    documentComplexity: "standard",
    tenor: "0",
  });
  
  const [result, setResult] = useState<RiskResult | null>(null);

  const calculateRisk = () => {
    let score = 100;
    const factors: RiskFactor[] = [];

    // Payment terms risk
    if (formData.paymentTerms === "sight") {
      factors.push({
        name: "Payment Terms",
        value: "At Sight",
        impact: "positive",
        points: 0,
      });
    } else if (formData.paymentTerms === "usance") {
      const tenorDays = parseInt(formData.tenor) || 0;
      if (tenorDays <= 60) {
        factors.push({
          name: "Payment Terms",
          value: `Usance ${tenorDays} days`,
          impact: "neutral",
          points: -5,
        });
        score -= 5;
      } else if (tenorDays <= 120) {
        factors.push({
          name: "Payment Terms",
          value: `Usance ${tenorDays} days`,
          impact: "negative",
          points: -10,
          recommendation: "Consider requiring confirmation for long tenors",
        });
        score -= 10;
      } else {
        factors.push({
          name: "Payment Terms",
          value: `Usance ${tenorDays} days`,
          impact: "negative",
          points: -20,
          recommendation: "Long tenor increases non-payment risk significantly",
        });
        score -= 20;
      }
    }

    // Confirmation
    if (formData.isConfirmed === "yes") {
      factors.push({
        name: "Confirmation",
        value: "Confirmed LC",
        impact: "positive",
        points: 10,
        recommendation: "Confirmation adds second bank guarantee",
      });
      score += 10;
    } else {
      factors.push({
        name: "Confirmation",
        value: "Unconfirmed",
        impact: "neutral",
        points: 0,
      });
    }

    // First time transaction
    if (formData.firstTimeTransaction === "yes") {
      factors.push({
        name: "Transaction History",
        value: "First Transaction",
        impact: "negative",
        points: -15,
        recommendation: "Request confirmation or consider smaller initial order",
      });
      score -= 15;
    } else {
      factors.push({
        name: "Transaction History",
        value: "Repeat Buyer",
        impact: "positive",
        points: 5,
      });
      score += 5;
    }

    // Document complexity
    if (formData.documentComplexity === "simple") {
      factors.push({
        name: "Document Requirements",
        value: "Simple (3-4 docs)",
        impact: "positive",
        points: 5,
      });
      score += 5;
    } else if (formData.documentComplexity === "complex") {
      factors.push({
        name: "Document Requirements",
        value: "Complex (7+ docs)",
        impact: "negative",
        points: -10,
        recommendation: "Complex documents increase discrepancy risk",
      });
      score -= 10;
    } else {
      factors.push({
        name: "Document Requirements",
        value: "Standard (5-6 docs)",
        impact: "neutral",
        points: 0,
      });
    }

    // Amount risk (simplified)
    const amount = parseFloat(formData.lcAmount.replace(/,/g, "")) || 0;
    if (amount > 1000000) {
      factors.push({
        name: "LC Amount",
        value: `${formData.currency} ${amount.toLocaleString()}`,
        impact: "negative",
        points: -10,
        recommendation: "Large amounts warrant extra due diligence",
      });
      score -= 10;
    } else if (amount > 500000) {
      factors.push({
        name: "LC Amount",
        value: `${formData.currency} ${amount.toLocaleString()}`,
        impact: "neutral",
        points: -5,
      });
      score -= 5;
    } else {
      factors.push({
        name: "LC Amount",
        value: `${formData.currency} ${amount.toLocaleString()}`,
        impact: "positive",
        points: 0,
      });
    }

    // Goods type
    if (formData.goodsType === "perishable") {
      factors.push({
        name: "Goods Type",
        value: "Perishable",
        impact: "negative",
        points: -15,
        recommendation: "Perishable goods have tight timelines and quality risks",
      });
      score -= 15;
    } else if (formData.goodsType === "machinery") {
      factors.push({
        name: "Goods Type",
        value: "Machinery/Equipment",
        impact: "neutral",
        points: -5,
        recommendation: "Ensure performance bonds and warranty terms are clear",
      });
      score -= 5;
    } else {
      factors.push({
        name: "Goods Type",
        value: formData.goodsType.charAt(0).toUpperCase() + formData.goodsType.slice(1),
        impact: "positive",
        points: 0,
      });
    }

    // Ensure score is within bounds
    score = Math.max(0, Math.min(100, score));

    // Determine risk level
    let level: "low" | "medium" | "high" | "critical";
    if (score >= 80) level = "low";
    else if (score >= 60) level = "medium";
    else if (score >= 40) level = "high";
    else level = "critical";

    setResult({ score, level, factors });
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case "low":
        return "text-green-400";
      case "medium":
        return "text-yellow-400";
      case "high":
        return "text-orange-400";
      case "critical":
        return "text-red-400";
      default:
        return "text-slate-400";
    }
  };

  const getRiskBgColor = (level: string) => {
    switch (level) {
      case "low":
        return "bg-green-500/10 border-green-500/20";
      case "medium":
        return "bg-yellow-500/10 border-yellow-500/20";
      case "high":
        return "bg-orange-500/10 border-orange-500/20";
      case "critical":
        return "bg-red-500/10 border-red-500/20";
      default:
        return "bg-slate-500/10 border-slate-500/20";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Calculator className="h-5 w-5 text-emerald-400" />
              Risk Calculator
            </h1>
            <p className="text-sm text-slate-400">
              Assess risk factors for your LC application
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Input Form */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">LC Parameters</CardTitle>
              <CardDescription>
                Enter details to calculate risk score
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>LC Amount</Label>
                  <Input
                    value={formData.lcAmount}
                    onChange={(e) => setFormData({ ...formData, lcAmount: e.target.value })}
                    placeholder="100,000"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Currency</Label>
                  <Select
                    value={formData.currency}
                    onValueChange={(v) => setFormData({ ...formData, currency: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="EUR">EUR</SelectItem>
                      <SelectItem value="GBP">GBP</SelectItem>
                      <SelectItem value="CNY">CNY</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Payment Terms</Label>
                  <Select
                    value={formData.paymentTerms}
                    onValueChange={(v) => setFormData({ ...formData, paymentTerms: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sight">At Sight</SelectItem>
                      <SelectItem value="usance">Usance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {formData.paymentTerms === "usance" && (
                  <div className="space-y-2">
                    <Label>Tenor (Days)</Label>
                    <Select
                      value={formData.tenor}
                      onValueChange={(v) => setFormData({ ...formData, tenor: v })}
                    >
                      <SelectTrigger className="bg-slate-800 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="30">30 Days</SelectItem>
                        <SelectItem value="60">60 Days</SelectItem>
                        <SelectItem value="90">90 Days</SelectItem>
                        <SelectItem value="120">120 Days</SelectItem>
                        <SelectItem value="180">180 Days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Goods Type</Label>
                  <Select
                    value={formData.goodsType}
                    onValueChange={(v) => setFormData({ ...formData, goodsType: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="general">General Merchandise</SelectItem>
                      <SelectItem value="textiles">Textiles/Garments</SelectItem>
                      <SelectItem value="electronics">Electronics</SelectItem>
                      <SelectItem value="machinery">Machinery/Equipment</SelectItem>
                      <SelectItem value="perishable">Perishable Goods</SelectItem>
                      <SelectItem value="chemicals">Chemicals</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Document Complexity</Label>
                  <Select
                    value={formData.documentComplexity}
                    onValueChange={(v) => setFormData({ ...formData, documentComplexity: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="simple">Simple (3-4 docs)</SelectItem>
                      <SelectItem value="standard">Standard (5-6 docs)</SelectItem>
                      <SelectItem value="complex">Complex (7+ docs)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Is LC Confirmed?</Label>
                  <Select
                    value={formData.isConfirmed}
                    onValueChange={(v) => setFormData({ ...formData, isConfirmed: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yes">Yes - Confirmed</SelectItem>
                      <SelectItem value="no">No - Unconfirmed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>First Transaction?</Label>
                  <Select
                    value={formData.firstTimeTransaction}
                    onValueChange={(v) => setFormData({ ...formData, firstTimeTransaction: v })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yes">Yes - First Time</SelectItem>
                      <SelectItem value="no">No - Repeat Buyer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                className="w-full bg-emerald-600 hover:bg-emerald-700 mt-4"
                onClick={calculateRisk}
              >
                <Calculator className="h-4 w-4 mr-2" />
                Calculate Risk Score
              </Button>
            </CardContent>
          </Card>

          {/* Results */}
          <div className="space-y-6">
            {result ? (
              <>
                {/* Score Card */}
                <Card className={`border ${getRiskBgColor(result.level)}`}>
                  <CardContent className="pt-6">
                    <div className="text-center">
                      <div className={`text-6xl font-bold ${getRiskColor(result.level)}`}>
                        {result.score}
                      </div>
                      <p className="text-lg text-slate-400 mt-2">Risk Score</p>
                      <Badge className={`mt-4 text-lg px-4 py-1 ${getRiskBgColor(result.level)} ${getRiskColor(result.level)}`}>
                        {result.level.toUpperCase()} RISK
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Factors */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white">Risk Factors</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {result.factors.map((factor, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50"
                      >
                        {factor.impact === "positive" ? (
                          <TrendingUp className="h-5 w-5 text-green-400 mt-0.5" />
                        ) : factor.impact === "negative" ? (
                          <TrendingDown className="h-5 w-5 text-red-400 mt-0.5" />
                        ) : (
                          <Minus className="h-5 w-5 text-slate-400 mt-0.5" />
                        )}
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-white">{factor.name}</span>
                            <span className={`text-sm ${
                              factor.impact === "positive" ? "text-green-400" :
                              factor.impact === "negative" ? "text-red-400" :
                              "text-slate-400"
                            }`}>
                              {factor.points > 0 ? "+" : ""}{factor.points} pts
                            </span>
                          </div>
                          <p className="text-sm text-slate-400">{factor.value}</p>
                          {factor.recommendation && (
                            <p className="text-xs text-yellow-400 mt-1 flex items-center gap-1">
                              <Info className="h-3 w-3" />
                              {factor.recommendation}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="py-12">
                  <div className="text-center">
                    <Shield className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-white mb-2">
                      Calculate Risk Score
                    </h3>
                    <p className="text-slate-400">
                      Enter LC parameters and click calculate to see risk assessment
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

