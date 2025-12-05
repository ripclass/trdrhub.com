/**
 * AIS Gap Analysis Card
 * 
 * Displays AIS transmission gap analysis for a vessel.
 * This is a bank-grade compliance feature.
 */

import { useState } from "react";
import {
  Radio,
  RadioReceiver,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MapPin,
  Clock,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Activity,
  Globe,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface AISGap {
  gap_id: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  last_known_position: { lat: number; lon: number };
  first_position_after: { lat: number; lon: number };
  distance_nm?: number;
  avg_speed_during_gap?: number;
  risk_level: string;
  risk_factors: string[];
  possible_explanations: string[];
}

interface AISAnalysisResult {
  vessel_name: string;
  imo?: string;
  mmsi?: string;
  analysis_period_days: number;
  analyzed_at: string;
  total_positions: number;
  first_position?: string;
  last_position?: string;
  total_gaps: number;
  suspicious_gaps: number;
  longest_gap_hours: number;
  gaps: AISGap[];
  overall_risk_score: number;
  risk_level: string;
  risk_factors: string[];
  recommendation: string;
  high_risk_areas_visited: string[];
  port_calls: number;
}

interface AISGapAnalysisCardProps {
  vesselName: string;
  imo?: string;
  mmsi?: string;
  className?: string;
}

export default function AISGapAnalysisCard({
  vesselName,
  imo,
  mmsi,
  className = "",
}: AISGapAnalysisCardProps) {
  const [result, setResult] = useState<AISAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gapsOpen, setGapsOpen] = useState(false);

  const runAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const identifier = imo || mmsi || vesselName;
      const response = await fetch(
        `${API_BASE}/tracking/ais-analysis/${encodeURIComponent(identifier)}?days=30`,
        { credentials: "include" }
      );
      
      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        const err = await response.json();
        setError(err.detail || "Analysis failed");
      }
    } catch (e) {
      setError("Failed to connect to analysis service");
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case "LOW": return "text-emerald-500";
      case "MEDIUM": return "text-amber-500";
      case "HIGH": return "text-orange-500";
      case "CRITICAL": return "text-red-500";
      default: return "text-muted-foreground";
    }
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case "LOW":
        return <Badge className="bg-emerald-500/20 text-emerald-500 border-emerald-500/30">LOW RISK</Badge>;
      case "MEDIUM":
        return <Badge className="bg-amber-500/20 text-amber-500 border-amber-500/30">MEDIUM RISK</Badge>;
      case "HIGH":
        return <Badge className="bg-orange-500/20 text-orange-500 border-orange-500/30">HIGH RISK</Badge>;
      case "CRITICAL":
        return <Badge className="bg-red-500/20 text-red-500 border-red-500/30">CRITICAL</Badge>;
      default:
        return <Badge variant="outline">UNKNOWN</Badge>;
    }
  };

  const getScoreColor = (score: number) => {
    if (score <= 30) return "bg-emerald-500";
    if (score <= 50) return "bg-amber-500";
    if (score <= 70) return "bg-orange-500";
    return "bg-red-500";
  };

  // Not yet analyzed
  if (!result && !isLoading && !error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="w-5 h-5" />
            AIS Gap Analysis
          </CardTitle>
          <CardDescription>
            Analyze AIS transmission history for suspicious gaps
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 mb-4">
            <h4 className="font-medium text-blue-400 mb-2">What This Detects</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li className="flex items-center gap-2">
                <EyeOff className="w-3 h-3" /> Dark shipping (AIS shutdown)
              </li>
              <li className="flex items-center gap-2">
                <Globe className="w-3 h-3" /> High-risk area visits
              </li>
              <li className="flex items-center gap-2">
                <Activity className="w-3 h-3" /> Ship-to-ship transfers
              </li>
            </ul>
          </div>
          <Button onClick={runAnalysis} className="w-full">
            <Radio className="w-4 h-4 mr-2" />
            Analyze AIS History (30 Days)
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Loading
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="w-5 h-5" />
            AIS Gap Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center py-8">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <p className="text-sm text-muted-foreground">Analyzing AIS transmission history...</p>
          <p className="text-xs text-muted-foreground mt-1">Checking for gaps and anomalies</p>
        </CardContent>
      </Card>
    );
  }

  // Error
  if (error) {
    return (
      <Card className={`${className} border-red-500/30`}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-500" />
            Analysis Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-400 mb-4">{error}</p>
          <Button onClick={runAnalysis} variant="outline" className="w-full">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!result) return null;

  const borderColor = result.risk_level === "LOW" 
    ? "border-emerald-500/30" 
    : result.risk_level === "CRITICAL" || result.risk_level === "HIGH"
    ? "border-red-500/30"
    : "border-amber-500/30";

  return (
    <Card className={`${className} ${borderColor}`}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Radio className={`w-6 h-6 ${getRiskColor(result.risk_level)}`} />
            <div>
              <CardTitle className="text-lg">AIS Gap Analysis</CardTitle>
              <CardDescription>
                {result.analysis_period_days}-day analysis • {result.total_positions} positions
              </CardDescription>
            </div>
          </div>
          {getRiskBadge(result.risk_level)}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Risk Score */}
        <div>
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-muted-foreground">Risk Score</span>
            <span className={`font-bold ${getRiskColor(result.risk_level)}`}>{result.overall_risk_score}/100</span>
          </div>
          <Progress value={result.overall_risk_score} className={`h-2 ${getScoreColor(result.overall_risk_score)}`} />
        </div>

        {/* Summary */}
        <div className={`p-3 rounded-lg ${
          result.risk_level === "LOW" 
            ? "bg-emerald-500/10" 
            : result.risk_level === "CRITICAL" || result.risk_level === "HIGH"
            ? "bg-red-500/10"
            : "bg-amber-500/10"
        }`}>
          <p className="text-sm font-medium">{result.recommendation}</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className="text-2xl font-bold">{result.total_gaps}</p>
            <p className="text-xs text-muted-foreground">Total Gaps</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className={`text-2xl font-bold ${result.suspicious_gaps > 0 ? "text-amber-500" : ""}`}>
              {result.suspicious_gaps}
            </p>
            <p className="text-xs text-muted-foreground">Suspicious</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className="text-2xl font-bold">{result.longest_gap_hours}h</p>
            <p className="text-xs text-muted-foreground">Longest Gap</p>
          </div>
        </div>

        {/* Risk Factors */}
        {result.risk_factors.length > 0 && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <h4 className="text-sm font-medium text-amber-400 mb-2">Risk Factors</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              {result.risk_factors.map((factor, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <AlertTriangle className="w-3 h-3 mt-1 text-amber-500 flex-shrink-0" />
                  {factor}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* High Risk Areas */}
        {result.high_risk_areas_visited.length > 0 && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <h4 className="text-sm font-medium text-red-400 mb-2">High-Risk Areas Visited</h4>
            <div className="flex flex-wrap gap-2">
              {result.high_risk_areas_visited.map((area, idx) => (
                <Badge key={idx} variant="outline" className="border-red-500/30 text-red-400">
                  {area}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Detailed Gaps */}
        {result.gaps.length > 0 && (
          <Collapsible open={gapsOpen} onOpenChange={setGapsOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <EyeOff className="w-4 h-4" />
                  View {result.gaps.length} Gap(s) Detail
                </span>
                {gapsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 mt-2">
              {result.gaps.map((gap) => (
                <div 
                  key={gap.gap_id} 
                  className={`p-3 rounded-lg border ${
                    gap.risk_level === "CRITICAL" || gap.risk_level === "HIGH"
                      ? "bg-red-500/5 border-red-500/20"
                      : gap.risk_level === "MEDIUM"
                      ? "bg-amber-500/5 border-amber-500/20"
                      : "bg-muted/30 border-muted"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{gap.duration_hours}h gap</span>
                    <Badge variant="outline" className={`text-xs ${getRiskColor(gap.risk_level)}`}>
                      {gap.risk_level}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground mb-2">
                    <div>
                      <Clock className="w-3 h-3 inline mr-1" />
                      {new Date(gap.start_time).toLocaleDateString()}
                    </div>
                    <div>
                      <MapPin className="w-3 h-3 inline mr-1" />
                      {gap.distance_nm}nm traveled
                    </div>
                  </div>
                  
                  {gap.risk_factors.length > 0 && (
                    <ul className="text-xs text-muted-foreground space-y-1">
                      {gap.risk_factors.map((factor, idx) => (
                        <li key={idx}>• {factor}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={runAnalysis} className="flex-1">
            <RefreshCw className="w-4 h-4 mr-1" />
            Re-analyze
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

