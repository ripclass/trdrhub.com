/**
 * Vessel Sanctions Card
 * 
 * Displays sanctions screening results for a vessel.
 */

import { useState } from "react";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Flag,
  Loader2,
  FileText,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Globe,
  Building,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface SanctionsHit {
  list_name: string;
  entity_name: string;
  entity_type: string;
  match_type: string;
  match_score: number;
  program?: string;
  remarks?: string;
}

interface FlagAssessment {
  flag_state: string;
  flag_code: string;
  risk_level: string;
  paris_mou_status: string;
  tokyo_mou_status: string;
  is_flag_of_convenience: boolean;
  notes: string;
}

interface SanctionsResult {
  vessel_name: string;
  imo?: string;
  mmsi?: string;
  screened_at: string;
  is_clear: boolean;
  risk_level: string;
  ofac_clear: boolean;
  ofac_hits: SanctionsHit[];
  eu_clear: boolean;
  eu_hits: SanctionsHit[];
  un_clear: boolean;
  un_hits: SanctionsHit[];
  flag_assessment?: FlagAssessment;
  total_hits: number;
  recommendation: string;
  confidence: number;
}

interface VesselSanctionsCardProps {
  vesselName: string;
  imo?: string;
  mmsi?: string;
  flagState?: string;
  className?: string;
}

export default function VesselSanctionsCard({
  vesselName,
  imo,
  mmsi,
  flagState,
  className = "",
}: VesselSanctionsCardProps) {
  const [result, setResult] = useState<SanctionsResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const runScreening = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/tracking/sanctions/screen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          vessel_name: vesselName,
          imo,
          mmsi,
          flag_state: flagState,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        const err = await response.json();
        setError(err.detail || "Screening failed");
      }
    } catch (e) {
      setError("Failed to connect to screening service");
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case "CLEAR":
        return <ShieldCheck className="w-6 h-6 text-emerald-500" />;
      case "LOW":
        return <Shield className="w-6 h-6 text-emerald-500" />;
      case "MEDIUM":
        return <ShieldAlert className="w-6 h-6 text-amber-500" />;
      case "HIGH":
        return <ShieldAlert className="w-6 h-6 text-orange-500" />;
      case "CRITICAL":
        return <ShieldX className="w-6 h-6 text-red-500" />;
      default:
        return <Shield className="w-6 h-6 text-muted-foreground" />;
    }
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case "CLEAR":
        return <Badge className="bg-emerald-500/20 text-emerald-500 border-emerald-500/30">CLEAR</Badge>;
      case "LOW":
        return <Badge className="bg-emerald-500/20 text-emerald-500 border-emerald-500/30">LOW RISK</Badge>;
      case "MEDIUM":
        return <Badge className="bg-amber-500/20 text-amber-500 border-amber-500/30">MEDIUM RISK</Badge>;
      case "HIGH":
        return <Badge className="bg-orange-500/20 text-orange-500 border-orange-500/30">HIGH RISK</Badge>;
      case "CRITICAL":
        return <Badge className="bg-red-500/20 text-red-500 border-red-500/30">CRITICAL</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const getListStatus = (isClear: boolean, hits: SanctionsHit[]) => {
    if (isClear) {
      return (
        <div className="flex items-center gap-2 text-emerald-500">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Clear</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 text-red-500">
        <XCircle className="w-4 h-4" />
        <span className="text-sm font-medium">{hits.length} Hit(s)</span>
      </div>
    );
  };

  // Not yet screened
  if (!result && !isLoading && !error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Sanctions Screening
          </CardTitle>
          <CardDescription>
            Screen this vessel against OFAC, EU, and UN sanctions lists
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={runScreening} className="w-full">
            <Shield className="w-4 h-4 mr-2" />
            Run Sanctions Check
          </Button>
          <p className="text-xs text-muted-foreground text-center mt-2">
            Free screening against official government databases
          </p>
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
            <Shield className="w-5 h-5" />
            Sanctions Screening
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center py-8">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <p className="text-sm text-muted-foreground">Checking sanctions lists...</p>
          <p className="text-xs text-muted-foreground mt-1">OFAC • EU • UN</p>
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
            <ShieldX className="w-5 h-5 text-red-500" />
            Screening Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-400 mb-4">{error}</p>
          <Button onClick={runScreening} variant="outline" className="w-full">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Result
  if (!result) return null;

  const borderColor = result.is_clear 
    ? "border-emerald-500/30" 
    : result.risk_level === "CRITICAL" || result.risk_level === "HIGH"
    ? "border-red-500/30"
    : "border-amber-500/30";

  return (
    <Card className={`${className} ${borderColor}`}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {getRiskIcon(result.risk_level)}
            <div>
              <CardTitle className="text-lg">Sanctions Screening</CardTitle>
              <CardDescription>
                Screened {new Date(result.screened_at).toLocaleString()}
              </CardDescription>
            </div>
          </div>
          {getRiskBadge(result.risk_level)}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className={`p-3 rounded-lg ${
          result.is_clear 
            ? "bg-emerald-500/10" 
            : result.risk_level === "CRITICAL" || result.risk_level === "HIGH"
            ? "bg-red-500/10"
            : "bg-amber-500/10"
        }`}>
          <p className="text-sm font-medium">{result.recommendation}</p>
          <p className="text-xs text-muted-foreground mt-1">
            Confidence: {result.confidence}%
          </p>
        </div>

        {/* List Results */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className="text-xs text-muted-foreground mb-1">OFAC SDN</p>
            {getListStatus(result.ofac_clear, result.ofac_hits)}
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className="text-xs text-muted-foreground mb-1">EU Sanctions</p>
            {getListStatus(result.eu_clear, result.eu_hits)}
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/30">
            <p className="text-xs text-muted-foreground mb-1">UN Sanctions</p>
            {getListStatus(result.un_clear, result.un_hits)}
          </div>
        </div>

        {/* Flag Assessment */}
        {result.flag_assessment && (
          <div className="p-3 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Flag className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">Flag State Assessment</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Flag:</span>{" "}
                <span className="font-medium">{result.flag_assessment.flag_state} ({result.flag_assessment.flag_code})</span>
              </div>
              <div>
                <span className="text-muted-foreground">Risk:</span>{" "}
                <span className={`font-medium ${
                  result.flag_assessment.risk_level === "LOW" ? "text-emerald-500" :
                  result.flag_assessment.risk_level === "MEDIUM" ? "text-amber-500" :
                  "text-red-500"
                }`}>{result.flag_assessment.risk_level}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Paris MoU:</span>{" "}
                <span className={`font-medium capitalize ${
                  result.flag_assessment.paris_mou_status === "white" ? "text-emerald-500" :
                  result.flag_assessment.paris_mou_status === "grey" ? "text-amber-500" :
                  "text-red-500"
                }`}>{result.flag_assessment.paris_mou_status}</span>
              </div>
              <div>
                <span className="text-muted-foreground">FOC:</span>{" "}
                <span className="font-medium">{result.flag_assessment.is_flag_of_convenience ? "Yes" : "No"}</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{result.flag_assessment.notes}</p>
          </div>
        )}

        {/* Detailed Hits (Collapsible) */}
        {result.total_hits > 0 && (
          <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  View {result.total_hits} Match(es)
                </span>
                {detailsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 mt-2">
              {[...result.ofac_hits, ...result.eu_hits, ...result.un_hits].map((hit, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{hit.entity_name}</span>
                    <Badge variant="outline" className="text-xs">{hit.list_name}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>Match: {hit.match_type} ({hit.match_score}%)</p>
                    {hit.program && <p>Program: {hit.program}</p>}
                    {hit.remarks && <p>{hit.remarks}</p>}
                  </div>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={runScreening} className="flex-1">
            <RefreshCw className="w-4 h-4 mr-1" />
            Re-screen
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1"
            onClick={async () => {
              try {
                const response = await fetch(`${API_BASE}/tracking/compliance-report`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  credentials: 'include',
                  body: JSON.stringify({
                    vessel_name: vesselName,
                    imo,
                    mmsi,
                    flag_state: flagState,
                  }),
                });
                if (response.ok) {
                  const blob = await response.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `VesselDueDiligence_${vesselName.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  window.URL.revokeObjectURL(url);
                }
              } catch (e) {
                console.error('Failed to download report:', e);
              }
            }}
          >
            <FileText className="w-4 h-4 mr-1" />
            PDF Report
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

