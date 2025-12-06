import { AlertTriangle, ShieldAlert, CheckCircle, XCircle, Info, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SanctionsScreeningSummary } from "@/types/lcopilot";
import { Link } from "react-router-dom";

interface SanctionsAlertProps {
  sanctionsScreening: SanctionsScreeningSummary | null;
  sanctionsBlocked?: boolean;
  sanctionsBlockReason?: string | null;
  compact?: boolean;
}

export function SanctionsAlert({
  sanctionsScreening,
  sanctionsBlocked,
  sanctionsBlockReason,
  compact = false,
}: SanctionsAlertProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sanctionsScreening || !sanctionsScreening.screened) {
    return null;
  }

  const hasMatches = sanctionsScreening.matches > 0;
  const hasPotentialMatches = sanctionsScreening.potential_matches > 0;
  const hasIssues = hasMatches || hasPotentialMatches;

  // If compact mode and no issues, don't show anything
  if (compact && !hasIssues) {
    return null;
  }

  // Blocked state - critical alert
  if (sanctionsBlocked) {
    return (
      <Card className="bg-red-500/10 border-red-500/50 animate-pulse-slow">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-red-400">
            <ShieldAlert className="w-5 h-5" />
            Sanctions Match Detected - Processing Blocked
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-red-300 text-sm">
            {sanctionsBlockReason || `${sanctionsScreening.matches} sanctioned party match(es) found. LC processing has been halted pending compliance review.`}
          </p>
          
          {sanctionsScreening.issues.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-white">Matched Parties:</h4>
              {sanctionsScreening.issues
                .filter(issue => issue.status === "match")
                .map((issue, idx) => (
                  <div key={idx} className="p-3 bg-red-950/50 rounded-lg border border-red-500/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-medium text-white">{issue.party}</span>
                        <Badge className="ml-2 bg-slate-700 text-slate-300 text-xs">
                          {issue.type}
                        </Badge>
                      </div>
                      <Badge className="bg-red-500/30 text-red-300">
                        {issue.score ? `${(issue.score * 100).toFixed(0)}% Match` : "Confirmed Match"}
                      </Badge>
                    </div>
                  </div>
                ))}
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-red-500/30">
            <span className="text-xs text-red-400">
              Contact your compliance team immediately
            </span>
            <Button asChild size="sm" variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/20">
              <Link to="/sanctions/dashboard">
                View Details <ExternalLink className="w-4 h-4 ml-2" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Potential matches - warning state
  if (hasPotentialMatches && !hasMatches) {
    return (
      <Card className="bg-amber-500/10 border-amber-500/30">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="w-5 h-5" />
            Sanctions Review Required
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-amber-200 text-sm">
            {sanctionsScreening.potential_matches} party/parties require manual review due to potential sanctions matches.
          </p>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-amber-400 hover:text-amber-300 p-0"
          >
            {isExpanded ? (
              <>Hide Details <ChevronUp className="w-4 h-4 ml-1" /></>
            ) : (
              <>Show Details <ChevronDown className="w-4 h-4 ml-1" /></>
            )}
          </Button>

          {isExpanded && sanctionsScreening.issues.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-amber-500/20">
              {sanctionsScreening.issues.map((issue, idx) => (
                <div key={idx} className="p-3 bg-amber-950/30 rounded-lg border border-amber-500/20">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-white">{issue.party}</span>
                      <Badge className="ml-2 bg-slate-700 text-slate-300 text-xs">
                        {issue.type}
                      </Badge>
                    </div>
                    <Badge className="bg-amber-500/30 text-amber-300">
                      {issue.score ? `${(issue.score * 100).toFixed(0)}% Similarity` : "Potential Match"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Clear status - success state (only show if not compact)
  if (!compact) {
    return (
      <Card className="bg-emerald-500/10 border-emerald-500/30">
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Sanctions Screening Clear</span>
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-400">
              <span>{sanctionsScreening.parties_screened} parties screened</span>
              <span className="text-xs text-slate-500">
                {new Date(sanctionsScreening.screened_at).toLocaleString()}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}

// Compact inline badge for overview displays
export function SanctionsBadge({
  sanctionsScreening,
  sanctionsBlocked,
}: Pick<SanctionsAlertProps, "sanctionsScreening" | "sanctionsBlocked">) {
  if (!sanctionsScreening || !sanctionsScreening.screened) {
    return (
      <Badge className="bg-slate-700 text-slate-400">
        <Info className="w-3 h-3 mr-1" />
        Not Screened
      </Badge>
    );
  }

  if (sanctionsBlocked || sanctionsScreening.matches > 0) {
    return (
      <Badge className="bg-red-500/20 text-red-400">
        <XCircle className="w-3 h-3 mr-1" />
        Sanctions Match
      </Badge>
    );
  }

  if (sanctionsScreening.potential_matches > 0) {
    return (
      <Badge className="bg-amber-500/20 text-amber-400">
        <AlertTriangle className="w-3 h-3 mr-1" />
        Review Required
      </Badge>
    );
  }

  return (
    <Badge className="bg-emerald-500/20 text-emerald-400">
      <CheckCircle className="w-3 h-3 mr-1" />
      Clear
    </Badge>
  );
}

export default SanctionsAlert;

