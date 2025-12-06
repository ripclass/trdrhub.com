import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  Search,
  Ship,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  Download,
  RotateCcw,
  Clock,
  FileCheck,
  Flag,
  Anchor,
} from "lucide-react";

const flagStates = [
  { code: "PA", name: "Panama" },
  { code: "LR", name: "Liberia" },
  { code: "MH", name: "Marshall Islands" },
  { code: "HK", name: "Hong Kong" },
  { code: "SG", name: "Singapore" },
  { code: "BS", name: "Bahamas" },
  { code: "MT", name: "Malta" },
  { code: "CY", name: "Cyprus" },
  { code: "GB", name: "United Kingdom" },
  { code: "NO", name: "Norway" },
  { code: "GR", name: "Greece" },
  { code: "JP", name: "Japan" },
  { code: "CN", name: "China" },
  { code: "RU", name: "Russia" },
  { code: "IR", name: "Iran" },
  { code: "KP", name: "North Korea" },
];

interface ScreeningResult {
  query: string;
  screening_type: string;
  screened_at: string;
  status: "clear" | "potential_match" | "match";
  risk_level: string;
  lists_screened: string[];
  matches: any[];
  total_matches: number;
  highest_score: number;
  flags: string[];
  recommendation: string;
  certificate_id: string;
  processing_time_ms: number;
}

export default function SanctionsScreenVessel() {
  const { toast } = useToast();
  const [vesselName, setVesselName] = useState("");
  const [imo, setImo] = useState("");
  const [mmsi, setMmsi] = useState("");
  const [flagCode, setFlagCode] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ScreeningResult | null>(null);

  const handleScreen = async () => {
    if (!vesselName.trim()) {
      toast({
        title: "Vessel name required",
        description: "Please enter a vessel name to screen",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await fetch("/api/sanctions/screen/vessel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: vesselName,
          imo: imo || undefined,
          mmsi: mmsi || undefined,
          flag_code: flagCode && flagCode !== "none" ? flagCode : undefined,
        }),
      });

      if (!response.ok) throw new Error("Screening failed");

      const data = await response.json();
      setResult(data);

      if (data.status === "clear") {
        toast({
          title: "✅ Vessel Clear",
          description: `${vesselName} passed sanctions screening`,
        });
      } else {
        toast({
          title: "⚠️ Review Required",
          description: `${data.total_matches} issue(s) detected`,
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Screening failed",
        description: "Please try again or contact support",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setVesselName("");
    setImo("");
    setMmsi("");
    setFlagCode("");
    setResult(null);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "clear": return "emerald";
      case "potential_match": return "amber";
      case "match": return "red";
      default: return "slate";
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Ship className="w-6 h-6 text-orange-400" />
          Screen a Vessel
        </h1>
        <p className="text-slate-400 mt-1">
          Verify vessels against sanctioned flags, owners, and dark activity patterns
        </p>
      </div>

      {/* Screening Form */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Vessel Details</CardTitle>
          <CardDescription className="text-slate-400">
            Enter vessel information for comprehensive screening
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Vessel Name */}
          <div className="space-y-2">
            <Label htmlFor="vesselName" className="text-white">Vessel Name *</Label>
            <Input
              id="vesselName"
              value={vesselName}
              onChange={(e) => setVesselName(e.target.value)}
              placeholder="e.g., M/V PACIFIC TRADER"
              className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* IMO Number */}
            <div className="space-y-2">
              <Label htmlFor="imo" className="text-white">IMO Number</Label>
              <Input
                id="imo"
                value={imo}
                onChange={(e) => setImo(e.target.value)}
                placeholder="e.g., 9123456"
                className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>

            {/* MMSI */}
            <div className="space-y-2">
              <Label htmlFor="mmsi" className="text-white">MMSI</Label>
              <Input
                id="mmsi"
                value={mmsi}
                onChange={(e) => setMmsi(e.target.value)}
                placeholder="e.g., 123456789"
                className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>
          </div>

          {/* Flag State */}
          <div className="space-y-2">
            <Label htmlFor="flagState" className="text-white">Flag State</Label>
            <Select value={flagCode} onValueChange={setFlagCode}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                <SelectValue placeholder="Select flag state" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700 max-h-60">
                <SelectItem value="none" className="text-slate-400">Unknown</SelectItem>
                {flagStates.map((flag) => (
                  <SelectItem key={flag.code} value={flag.code} className="text-white">
                    {flag.name} ({flag.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Screening Info */}
          <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
              <Anchor className="w-4 h-4 text-orange-400" />
              Vessel Screening Includes
            </h4>
            <ul className="text-sm text-slate-400 grid grid-cols-2 gap-1">
              <li>• OFAC SDN vessel list</li>
              <li>• EU sanctioned vessels</li>
              <li>• Flag state risk assessment</li>
              <li>• Paris MoU performance</li>
              <li>• Ownership chain analysis</li>
              <li>• Flags of convenience check</li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              onClick={handleScreen}
              disabled={isLoading || !vesselName.trim()}
              className="flex-1 bg-orange-500 hover:bg-orange-600 text-white"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Screening...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Screen Vessel
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              className="border-slate-700 text-slate-400 hover:text-white"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card className={`border-${getStatusColor(result.status)}-500/30 bg-${getStatusColor(result.status)}-500/5`}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 bg-${getStatusColor(result.status)}-500/20 rounded-lg flex items-center justify-center`}>
                  {result.status === "clear" ? (
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  ) : result.status === "potential_match" ? (
                    <AlertTriangle className="w-6 h-6 text-amber-400" />
                  ) : (
                    <XCircle className="w-6 h-6 text-red-400" />
                  )}
                </div>
                <div>
                  <CardTitle className="text-white">
                    {result.status === "clear" && "✅ VESSEL CLEAR"}
                    {result.status === "potential_match" && "⚠️ REVIEW REQUIRED"}
                    {result.status === "match" && "❌ VESSEL FLAGGED"}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Vessel: "{result.query}" • Screened: {new Date(result.screened_at).toLocaleString()}
                  </CardDescription>
                </div>
              </div>
              <Badge className={`bg-${getStatusColor(result.status)}-500/20 text-${getStatusColor(result.status)}-400`}>
                {result.risk_level.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Matches */}
            {result.matches.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">Issues Detected</h4>
                {result.matches.map((match, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-white flex items-center gap-2">
                        {match.list_code === "FLAG_RISK" ? (
                          <Flag className="w-4 h-4 text-amber-400" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                        )}
                        {match.list_name}
                      </span>
                      <Badge className={`${
                        match.match_score >= 90
                          ? "bg-red-500/20 text-red-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}>
                        {match.match_type === "risk_assessment" ? match.remarks?.split(" - ")[0] : `${match.match_score}% Match`}
                      </Badge>
                    </div>
                    {match.remarks && (
                      <p className="text-sm text-slate-400">{match.remarks}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Recommendation */}
            <div className={`p-4 rounded-lg border ${
              result.status === "clear"
                ? "bg-emerald-500/10 border-emerald-500/30"
                : "bg-red-500/10 border-red-500/30"
            }`}>
              <p className={`text-sm font-medium ${
                result.status === "clear" ? "text-emerald-400" : "text-red-400"
              }`}>
                {result.recommendation}
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
              <div className="flex items-center gap-4 text-sm text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {result.processing_time_ms}ms
                </span>
                <span className="flex items-center gap-1">
                  <FileCheck className="w-4 h-4" />
                  {result.certificate_id}
                </span>
              </div>
              <Button variant="outline" className="border-slate-700 text-slate-400 hover:text-white">
                <Download className="w-4 h-4 mr-2" />
                Download Certificate
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

