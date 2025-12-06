import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  Search,
  Package,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  Download,
  RotateCcw,
  Clock,
  FileCheck,
  ShieldAlert,
} from "lucide-react";

const destinationCountries = [
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "CN", name: "China" },
  { code: "RU", name: "Russia" },
  { code: "IR", name: "Iran" },
  { code: "KP", name: "North Korea" },
  { code: "SY", name: "Syria" },
  { code: "CU", name: "Cuba" },
  { code: "AE", name: "United Arab Emirates" },
  { code: "SG", name: "Singapore" },
  { code: "IN", name: "India" },
  { code: "BR", name: "Brazil" },
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

export default function SanctionsScreenGoods() {
  const { toast } = useToast();
  const [description, setDescription] = useState("");
  const [hsCode, setHsCode] = useState("");
  const [destinationCountry, setDestinationCountry] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ScreeningResult | null>(null);

  const handleScreen = async () => {
    if (!description.trim()) {
      toast({
        title: "Description required",
        description: "Please enter a goods description to screen",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await fetch("/api/sanctions/screen/goods", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description,
          hs_code: hsCode || undefined,
          destination_country: destinationCountry && destinationCountry !== "none" ? destinationCountry : undefined,
        }),
      });

      if (!response.ok) throw new Error("Screening failed");

      const data = await response.json();
      setResult(data);

      if (data.status === "clear") {
        toast({
          title: "✅ No Export Control Issues",
          description: "Goods passed screening",
        });
      } else {
        toast({
          title: "⚠️ Export Control Flags",
          description: `${data.flags.length} issue(s) detected`,
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
    setDescription("");
    setHsCode("");
    setDestinationCountry("");
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
          <Package className="w-6 h-6 text-yellow-400" />
          Screen Goods
        </h1>
        <p className="text-slate-400 mt-1">
          Check goods against dual-use, export control, and sanctions lists
        </p>
      </div>

      {/* Screening Form */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Goods Details</CardTitle>
          <CardDescription className="text-slate-400">
            Enter goods description and destination for export control screening
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description" className="text-white">Goods Description *</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Industrial centrifuge for pharmaceutical processing, model XYZ-500"
              rows={3}
              className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* HS Code */}
            <div className="space-y-2">
              <Label htmlFor="hsCode" className="text-white">HS Code (optional)</Label>
              <Input
                id="hsCode"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
                placeholder="e.g., 8421.19.0000"
                className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>

            {/* Destination Country */}
            <div className="space-y-2">
              <Label htmlFor="destination" className="text-white">Destination Country</Label>
              <Select value={destinationCountry} onValueChange={setDestinationCountry}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="Select destination" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700 max-h-60">
                  <SelectItem value="none" className="text-slate-400">Not specified</SelectItem>
                  {destinationCountries.map((country) => (
                    <SelectItem key={country.code} value={country.code} className="text-white">
                      {country.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Screening Info */}
          <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-yellow-400" />
              Export Control Screening Includes
            </h4>
            <ul className="text-sm text-slate-400 grid grid-cols-2 gap-1">
              <li>• Destination country sanctions</li>
              <li>• Dual-use indicators</li>
              <li>• Nuclear/WMD keywords</li>
              <li>• Military/defense items</li>
              <li>• Encryption technology</li>
              <li>• Missile technology</li>
            </ul>
          </div>

          {/* Warning */}
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <p className="text-sm text-amber-400">
              <strong>Note:</strong> This screening checks for common export control indicators. 
              For definitive ECCN classification, consult a licensed trade compliance specialist.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              onClick={handleScreen}
              disabled={isLoading || !description.trim()}
              className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-black"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Screening...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Screen Goods
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
                    {result.status === "clear" && "✅ NO EXPORT CONTROL FLAGS"}
                    {result.status === "potential_match" && "⚠️ EXPORT CONTROL REVIEW REQUIRED"}
                    {result.status === "match" && "❌ EXPORT PROHIBITED"}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Screened: {new Date(result.screened_at).toLocaleString()}
                  </CardDescription>
                </div>
              </div>
              <Badge className={`bg-${getStatusColor(result.status)}-500/20 text-${getStatusColor(result.status)}-400`}>
                {result.risk_level.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Flags */}
            {result.flags.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">Export Control Flags</h4>
                {result.flags.map((flag, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-2"
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span className="text-sm text-amber-400">{flag}</span>
                  </div>
                ))}
              </div>
            )}

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
                      <span className="font-medium text-white">{match.list_name}</span>
                      <Badge className="bg-amber-500/20 text-amber-400">
                        {match.match_type}
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
                : "bg-amber-500/10 border-amber-500/30"
            }`}>
              <p className={`text-sm font-medium ${
                result.status === "clear" ? "text-emerald-400" : "text-amber-400"
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
                Download Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

