import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  Search,
  Shield,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  Download,
  RotateCcw,
  Users,
  Clock,
  FileCheck,
} from "lucide-react";

const availableLists = [
  { code: "OFAC_SDN", name: "OFAC SDN", jurisdiction: "US" },
  { code: "OFAC_SSI", name: "OFAC Sectoral", jurisdiction: "US" },
  { code: "EU_CONS", name: "EU Consolidated", jurisdiction: "EU" },
  { code: "UN_SC", name: "UN Security Council", jurisdiction: "UN" },
  { code: "UK_OFSI", name: "UK OFSI", jurisdiction: "UK" },
  { code: "BIS_EL", name: "BIS Entity List", jurisdiction: "US" },
];

const countries = [
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "CN", name: "China" },
  { code: "RU", name: "Russia" },
  { code: "IR", name: "Iran" },
  { code: "AE", name: "United Arab Emirates" },
  { code: "SG", name: "Singapore" },
  { code: "HK", name: "Hong Kong" },
];

interface ScreeningMatch {
  list_code: string;
  list_name: string;
  matched_name: string;
  matched_type: string;
  match_type: string;
  match_score: number;
  match_method: string;
  programs: string[];
  country?: string;
  source_id?: string;
  listed_date?: string;
  remarks?: string;
}

interface ScreeningResult {
  query: string;
  screening_type: string;
  screened_at: string;
  status: "clear" | "potential_match" | "match";
  risk_level: string;
  lists_screened: string[];
  matches: ScreeningMatch[];
  total_matches: number;
  highest_score: number;
  flags: string[];
  recommendation: string;
  certificate_id: string;
  processing_time_ms: number;
}

export default function SanctionsScreenParty() {
  const { toast } = useToast();
  const [partyName, setPartyName] = useState("");
  const [country, setCountry] = useState<string>("");
  const [selectedLists, setSelectedLists] = useState<string[]>(availableLists.map(l => l.code));
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ScreeningResult | null>(null);

  const handleListToggle = (listCode: string) => {
    setSelectedLists(prev =>
      prev.includes(listCode)
        ? prev.filter(l => l !== listCode)
        : [...prev, listCode]
    );
  };

  const handleScreen = async () => {
    if (!partyName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a party name to screen",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await fetch("/api/sanctions/screen/party", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: partyName,
          country: country || undefined,
          lists: selectedLists,
        }),
      });

      if (!response.ok) throw new Error("Screening failed");

      const data = await response.json();
      setResult(data);

      if (data.status === "clear") {
        toast({
          title: "✅ No Matches Found",
          description: `${partyName} is clear against ${selectedLists.length} lists`,
        });
      } else {
        toast({
          title: "⚠️ Review Required",
          description: `${data.total_matches} potential match(es) found`,
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
    setPartyName("");
    setCountry("");
    setSelectedLists(availableLists.map(l => l.code));
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "clear": return CheckCircle;
      case "potential_match": return AlertTriangle;
      case "match": return XCircle;
      default: return Shield;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Users className="w-6 h-6 text-red-400" />
          Screen a Party
        </h1>
        <p className="text-slate-400 mt-1">
          Check buyers, sellers, banks, and agents against sanctions lists
        </p>
      </div>

      {/* Screening Form */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Party Details</CardTitle>
          <CardDescription className="text-slate-400">
            Enter the party name and select which lists to screen against
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Party Name */}
          <div className="space-y-2">
            <Label htmlFor="partyName" className="text-white">Party Name *</Label>
            <Input
              id="partyName"
              value={partyName}
              onChange={(e) => setPartyName(e.target.value)}
              placeholder="e.g., Acme Trading Company Limited"
              className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
            />
          </div>

          {/* Country */}
          <div className="space-y-2">
            <Label htmlFor="country" className="text-white">Country (optional)</Label>
            <Select value={country} onValueChange={setCountry}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                <SelectValue placeholder="Select country" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="none" className="text-slate-400">Not specified</SelectItem>
                {countries.map((c) => (
                  <SelectItem key={c.code} value={c.code} className="text-white">
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Lists to Screen */}
          <div className="space-y-3">
            <Label className="text-white">Lists to Screen</Label>
            <div className="grid grid-cols-2 gap-3">
              {availableLists.map((list) => (
                <div
                  key={list.code}
                  className="flex items-center space-x-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700"
                >
                  <Checkbox
                    id={list.code}
                    checked={selectedLists.includes(list.code)}
                    onCheckedChange={() => handleListToggle(list.code)}
                    className="border-slate-600"
                  />
                  <label
                    htmlFor={list.code}
                    className="flex-1 text-sm cursor-pointer"
                  >
                    <span className="text-white font-medium">{list.name}</span>
                    <span className="text-slate-500 ml-2">({list.jurisdiction})</span>
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              onClick={handleScreen}
              disabled={isLoading || !partyName.trim()}
              className="flex-1 bg-red-500 hover:bg-red-600 text-white"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Screening...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Screen Now
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
                {(() => {
                  const StatusIcon = getStatusIcon(result.status);
                  return (
                    <div className={`w-12 h-12 bg-${getStatusColor(result.status)}-500/20 rounded-lg flex items-center justify-center`}>
                      <StatusIcon className={`w-6 h-6 text-${getStatusColor(result.status)}-400`} />
                    </div>
                  );
                })()}
                <div>
                  <CardTitle className="text-white">
                    {result.status === "clear" && "✅ NO MATCHES FOUND"}
                    {result.status === "potential_match" && "⚠️ POTENTIAL MATCH - REVIEW REQUIRED"}
                    {result.status === "match" && "❌ MATCH FOUND - DO NOT PROCEED"}
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Party: "{result.query}" • Screened: {new Date(result.screened_at).toLocaleString()}
                  </CardDescription>
                </div>
              </div>
              <Badge className={`bg-${getStatusColor(result.status)}-500/20 text-${getStatusColor(result.status)}-400 border-${getStatusColor(result.status)}-500/30`}>
                {result.risk_level.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* List Results Summary */}
            <div className="grid grid-cols-3 gap-3">
              {result.lists_screened.map((listCode) => {
                const hasMatch = result.matches.some(m => m.list_code === listCode);
                return (
                  <div
                    key={listCode}
                    className={`p-3 rounded-lg border ${
                      hasMatch
                        ? "bg-red-500/10 border-red-500/30"
                        : "bg-emerald-500/10 border-emerald-500/30"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {hasMatch ? (
                        <XCircle className="w-4 h-4 text-red-400" />
                      ) : (
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                      )}
                      <span className="text-sm font-medium text-white">{listCode.replace("_", " ")}</span>
                    </div>
                    <span className={`text-xs ${hasMatch ? "text-red-400" : "text-emerald-400"}`}>
                      {hasMatch ? "Match" : "Clear"}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Match Details */}
            {result.matches.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">Match Details</h4>
                {result.matches.map((match, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-white">{match.list_name}</span>
                      <Badge className={`${
                        match.match_score >= 95
                          ? "bg-red-500/20 text-red-400"
                          : match.match_score >= 85
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}>
                        {match.match_score}% Match
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-400">
                      <strong className="text-slate-300">Listed Entity:</strong> {match.matched_name}
                    </p>
                    {match.source_id && (
                      <p className="text-sm text-slate-400">
                        <strong className="text-slate-300">ID:</strong> {match.source_id}
                      </p>
                    )}
                    {match.programs.length > 0 && (
                      <p className="text-sm text-slate-400">
                        <strong className="text-slate-300">Programs:</strong> {match.programs.join(", ")}
                      </p>
                    )}
                    {match.listed_date && (
                      <p className="text-sm text-slate-400">
                        <strong className="text-slate-300">Listed:</strong> {match.listed_date}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Flags */}
            {result.flags.length > 0 && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <h4 className="text-sm font-medium text-amber-400 mb-2">⚠️ Flags</h4>
                <ul className="text-sm text-slate-400 space-y-1">
                  {result.flags.map((flag, idx) => (
                    <li key={idx}>• {flag}</li>
                  ))}
                </ul>
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

