/**
 * BankVerdictCard Component
 * 
 * Displays the bank submission verdict with color-coded status,
 * recommendation text, and action items.
 */

import { CheckCircle, AlertTriangle, Clock, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Bank Verdict Types
export interface BankVerdictActionItem {
  priority: "critical" | "high" | "medium";
  issue: string;
  action: string;
}

export interface BankVerdict {
  verdict?: "SUBMIT" | "CAUTION" | "HOLD" | "REJECT" | string;
  verdict_color?: "green" | "yellow" | "orange" | "red" | string;
  verdict_message?: string;
  recommendation?: string;
  can_submit?: boolean;
  will_be_rejected?: boolean;
  estimated_discrepancy_fee?: number;
  issue_summary?: {
    critical?: number;
    major?: number;
    minor?: number;
    total?: number;
  };
  action_items?: BankVerdictActionItem[];
  action_items_count?: number;
}

const verdictColors = {
  SUBMIT: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
  CAUTION: "bg-yellow-500/10 border-yellow-500/30 text-yellow-400",
  HOLD: "bg-orange-500/10 border-orange-500/30 text-orange-400",
  REJECT: "bg-red-500/10 border-red-500/30 text-red-400",
};

const verdictIcons = {
  SUBMIT: <CheckCircle className="w-6 h-6" />,
  CAUTION: <AlertTriangle className="w-6 h-6" />,
  HOLD: <Clock className="w-6 h-6" />,
  REJECT: <XCircle className="w-6 h-6" />,
};

const verdictBadgeColors = {
  SUBMIT: "bg-emerald-500 text-white",
  CAUTION: "bg-yellow-500 text-black",
  HOLD: "bg-orange-500 text-white",
  REJECT: "bg-red-500 text-white",
};

interface BankVerdictCardProps {
  verdict: BankVerdict | string;
}

type NormalizedVerdictKey = keyof typeof verdictColors;

const fallbackVerdictMessage: Record<NormalizedVerdictKey, string> = {
  SUBMIT: "Bank submission appears ready.",
  CAUTION: "Bank review is advised before submission.",
  HOLD: "Submission should be held pending review.",
  REJECT: "Bank would reject this presentation in its current state.",
};

const fallbackRecommendation: Record<NormalizedVerdictKey, string> = {
  SUBMIT: "Proceed with bank submission once supporting controls are complete.",
  CAUTION: "Resolve review items before bank submission.",
  HOLD: "Address the blocking items before attempting submission.",
  REJECT: "Do not submit until the blocking discrepancies are corrected.",
};

const normalizeVerdictKey = (verdict: BankVerdict | string): NormalizedVerdictKey => {
  const rawVerdict = typeof verdict === "string" ? verdict : verdict?.verdict;
  const normalized = String(rawVerdict || "").trim().toUpperCase();

  if (normalized in verdictColors) {
    return normalized as NormalizedVerdictKey;
  }

  if (typeof verdict !== "string" && verdict?.can_submit) {
    return "SUBMIT";
  }

  return "HOLD";
};

const toSafeNumber = (value: unknown): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

function normalizeVerdict(verdict: BankVerdict | string) {
  const verdictObject = typeof verdict === "string" ? {} : verdict;
  const verdictKey = normalizeVerdictKey(verdict);
  const issueSummary = {
    critical: toSafeNumber(verdictObject.issue_summary?.critical),
    major: toSafeNumber(verdictObject.issue_summary?.major),
    minor: toSafeNumber(verdictObject.issue_summary?.minor),
  };
  const actionItems = Array.isArray(verdictObject.action_items) ? verdictObject.action_items : [];
  const totalIssues =
    toSafeNumber(verdictObject.issue_summary?.total) ||
    issueSummary.critical + issueSummary.major + issueSummary.minor;

  return {
    verdict: verdictKey,
    verdict_message: verdictObject.verdict_message || fallbackVerdictMessage[verdictKey],
    recommendation: verdictObject.recommendation || fallbackRecommendation[verdictKey],
    estimated_discrepancy_fee: toSafeNumber(verdictObject.estimated_discrepancy_fee),
    issue_summary: {
      ...issueSummary,
      total: totalIssues,
    },
    action_items: actionItems,
    action_items_count: toSafeNumber(verdictObject.action_items_count) || actionItems.length,
  };
}

export function BankVerdictCard({ verdict }: BankVerdictCardProps) {
  const normalizedVerdict = normalizeVerdict(verdict);

  return (
    <Card className={cn(
      "mt-4 border-2 shadow-lg transition-all",
      verdictColors[normalizedVerdict.verdict]
    )}>
      <CardContent className="pt-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          {/* Verdict Badge */}
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-3 rounded-xl",
              verdictColors[normalizedVerdict.verdict]
            )}>
              {verdictIcons[normalizedVerdict.verdict]}
            </div>
            <div>
              <Badge className={cn("text-sm font-bold px-3 py-1", verdictBadgeColors[normalizedVerdict.verdict])}>
                {normalizedVerdict.verdict === "SUBMIT" ? "READY TO SUBMIT" : normalizedVerdict.verdict}
              </Badge>
              <p className="text-sm font-medium mt-1">{normalizedVerdict.verdict_message}</p>
            </div>
          </div>
          
          {/* Recommendation */}
          <div className="flex-1 md:border-l md:pl-4 border-border/50">
            <p className="text-sm text-muted-foreground">{normalizedVerdict.recommendation}</p>
            
            {normalizedVerdict.estimated_discrepancy_fee > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                Estimated discrepancy fee: <span className="font-semibold text-orange-400">USD {normalizedVerdict.estimated_discrepancy_fee.toFixed(2)}</span>
              </p>
            )}
          </div>
          
          {/* Issue Summary */}
          <div className="flex items-center gap-4 text-xs">
            {normalizedVerdict.issue_summary.critical > 0 && (
              <div className="flex items-center gap-1 text-red-400">
                <span className="font-bold text-lg">{normalizedVerdict.issue_summary.critical}</span>
                <span>Critical</span>
              </div>
            )}
            {normalizedVerdict.issue_summary.major > 0 && (
              <div className="flex items-center gap-1 text-orange-400">
                <span className="font-bold text-lg">{normalizedVerdict.issue_summary.major}</span>
                <span>Major</span>
              </div>
            )}
            {normalizedVerdict.issue_summary.minor > 0 && (
              <div className="flex items-center gap-1 text-yellow-400">
                <span className="font-bold text-lg">{normalizedVerdict.issue_summary.minor}</span>
                <span>Minor</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Action Items */}
        {normalizedVerdict.action_items.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border/30">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Required Actions ({normalizedVerdict.action_items_count})
            </p>
            <div className="space-y-2">
              {normalizedVerdict.action_items.slice(0, 3).map((item, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <span className={cn(
                    "mt-0.5 w-2 h-2 rounded-full flex-shrink-0",
                    item.priority === "critical" ? "bg-red-500" : "bg-orange-500"
                  )} />
                  <div>
                    <span className="font-medium">{item.issue}</span>
                    <span className="text-muted-foreground"> — {item.action}</span>
                  </div>
                </div>
              ))}
              {normalizedVerdict.action_items_count > 3 && (
                <p className="text-xs text-muted-foreground pl-4">
                  + {normalizedVerdict.action_items_count - 3} more action(s) in Issues tab
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

