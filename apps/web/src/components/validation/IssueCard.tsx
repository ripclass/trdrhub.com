/**
 * Issue Card - Phase 8: Frontend Hardening
 *
 * A card component for displaying validation issues with:
 * - Severity-based coloring (red, orange, yellow)
 * - Expected/Found/Suggestion structure
 * - Document references
 * - UCP/ISBP references
 */

import React, { useState } from "react";
import {
  AlertTriangle,
  XCircle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  FileText,
  BookOpen,
} from "lucide-react";
import {
  IssueSeverity,
  getSeverityColorClasses,
  getSeverityLabel,
} from "@/lib/validation/validationState";

/**
 * Humanize rule IDs for display
 * CROSSDOC-BIN → Cross-Document Check
 * AI-MISSING-INSPECTION_CERTIFICATE → AI Validation
 * BL-VOYAGE-001 → Bill of Lading Check
 */
function humanizeRuleId(ruleId: string): string {
  if (!ruleId) return "";
  
  // Rule category mappings
  const categoryMap: Record<string, string> = {
    "CROSSDOC": "Cross-Document",
    "AI-MISSING": "AI Detection",
    "AI-": "AI Validation",
    "BL-": "Bill of Lading",
    "INV-": "Invoice",
    "LC-": "LC Requirement",
    "COO-": "Certificate of Origin",
    "PL-": "Packing List",
    "INS-": "Insurance",
    "SANCTIONS": "Sanctions Check",
    "UCP-": "UCP600",
    "ISBP-": "ISBP745",
  };
  
  // Find matching category
  for (const [prefix, label] of Object.entries(categoryMap)) {
    if (ruleId.toUpperCase().startsWith(prefix)) {
      return label;
    }
  }
  
  // Fallback: clean up the rule ID
  return ruleId
    .replace(/-/g, " ")
    .replace(/_/g, " ")
    .replace(/\d+$/, "")
    .trim()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export interface IssueData {
  rule?: string;
  title?: string;
  severity?: string;
  message?: string;
  expected?: string;
  actual?: string;
  found?: string; // Alias for actual
  suggestion?: string;
  documents?: string[];
  document_names?: string[];
  ucp_reference?: string;
  isbp_reference?: string;
  ruleset_domain?: string;
  blocks_validation?: boolean;
}

interface IssueCardProps {
  issue: IssueData;
  defaultExpanded?: boolean;
  className?: string;
}

/**
 * Get icon for severity.
 */
function getSeverityIcon(severity: IssueSeverity, className: string) {
  switch (severity) {
    case "critical":
      return <XCircle className={className} />;
    case "major":
      return <AlertTriangle className={className} />;
    case "minor":
      return <AlertCircle className={className} />;
    default:
      return <Info className={className} />;
  }
}

/**
 * Normalize severity string.
 */
function normalizeSeverity(severity?: string): IssueSeverity {
  const s = (severity || "info").toLowerCase();
  if (s === "critical") return "critical";
  if (s === "major" || s === "warning") return "major";
  if (s === "minor") return "minor";
  return "info";
}

export function IssueCard({
  issue,
  defaultExpanded = false,
  className = "",
}: IssueCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const severity = normalizeSeverity(issue.severity);
  const colors = getSeverityColorClasses(severity);
  const actualValue = issue.actual || issue.found || "N/A";

  return (
    <div
      className={`rounded-lg border ${colors.bg} ${className}`}
      style={{
        borderColor:
          severity === "critical"
            ? "rgb(254 202 202)"
            : severity === "major"
            ? "rgb(254 215 170)"
            : severity === "minor"
            ? "rgb(254 240 138)"
            : "rgb(191 219 254)",
      }}
    >
      {/* Header - Always Visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left"
      >
        {/* Severity Icon */}
        <div className={`flex-shrink-0 ${colors.text}`}>
          {getSeverityIcon(severity, "h-5 w-5")}
        </div>

        {/* Title and Summary */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={`font-medium ${colors.text} truncate`}>
              {issue.title || "Validation Issue"}
            </h4>
            {issue.blocks_validation && (
              <span className="px-1.5 py-0.5 text-xs font-medium bg-red-200 text-red-800 rounded">
                BLOCKING
              </span>
            )}
          </div>
          {!expanded && issue.message && (
            <p className="text-sm text-gray-600 dark:text-gray-400 truncate mt-0.5">
              {issue.message}
            </p>
          )}
        </div>

        {/* Severity Badge */}
        <span
          className={`flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded ${colors.bg} ${colors.text}`}
        >
          {getSeverityLabel(severity)}
        </span>

        {/* Expand/Collapse */}
        <div className="flex-shrink-0 text-gray-400">
          {expanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-200 dark:border-gray-700">
          {/* Message */}
          {issue.message && (
            <p className="text-sm text-gray-700 dark:text-gray-300 pt-3">
              {issue.message}
            </p>
          )}

          {/* Expected / Found / Suggestion */}
          <div className="grid gap-2">
            {issue.expected && (
              <div className="bg-green-50 dark:bg-green-950 rounded-md p-3">
                <div className="text-xs font-medium text-green-800 dark:text-green-300 uppercase tracking-wide mb-1">
                  Expected
                </div>
                <div className="text-sm text-green-700 dark:text-green-400">
                  {issue.expected}
                </div>
              </div>
            )}

            {actualValue && actualValue !== "N/A" && (
              <div className="bg-red-50 dark:bg-red-950 rounded-md p-3">
                <div className="text-xs font-medium text-red-800 dark:text-red-300 uppercase tracking-wide mb-1">
                  Found
                </div>
                <div className="text-sm text-red-700 dark:text-red-400">
                  {actualValue}
                </div>
              </div>
            )}

            {issue.suggestion && (
              <div className="bg-blue-50 dark:bg-blue-950 rounded-md p-3">
                <div className="text-xs font-medium text-blue-800 dark:text-blue-300 uppercase tracking-wide mb-1">
                  Suggested Action
                </div>
                <div className="text-sm text-blue-700 dark:text-blue-400">
                  {issue.suggestion}
                </div>
              </div>
            )}
          </div>

          {/* Document References */}
          {(issue.document_names?.length || issue.documents?.length) && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <FileText className="h-4 w-4" />
              <span>
                Documents:{" "}
                {(issue.document_names || issue.documents)?.join(", ")}
              </span>
            </div>
          )}

          {/* Compliance References */}
          {(issue.ucp_reference || issue.isbp_reference) && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <BookOpen className="h-4 w-4" />
              <span>
                {issue.ucp_reference && <span>{issue.ucp_reference}</span>}
                {issue.ucp_reference && issue.isbp_reference && <span> • </span>}
                {issue.isbp_reference && <span>{issue.isbp_reference}</span>}
              </span>
            </div>
          )}

          {/* Rule Category */}
          {issue.rule && (
            <div className="text-xs text-gray-400">
              <span className="font-medium">{humanizeRuleId(issue.rule)}</span>
              <span className="ml-2 font-mono text-gray-500 text-[10px]">({issue.rule})</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Issue List
// ============================================================================

interface IssueListProps {
  issues: IssueData[];
  title?: string;
  emptyMessage?: string;
  maxVisible?: number;
  className?: string;
}

export function IssueList({
  issues,
  title,
  emptyMessage = "No issues found",
  maxVisible,
  className = "",
}: IssueListProps) {
  const [showAll, setShowAll] = useState(false);

  // Sort by severity
  const sortedIssues = [...issues].sort((a, b) => {
    const severityOrder: Record<string, number> = {
      critical: 0,
      major: 1,
      minor: 2,
      info: 3,
    };
    const aSev = severityOrder[a.severity?.toLowerCase() || "info"] ?? 4;
    const bSev = severityOrder[b.severity?.toLowerCase() || "info"] ?? 4;
    return aSev - bSev;
  });

  const visibleIssues =
    maxVisible && !showAll ? sortedIssues.slice(0, maxVisible) : sortedIssues;
  const hasMore = maxVisible && sortedIssues.length > maxVisible;

  if (issues.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 dark:text-gray-400 ${className}`}>
        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {title}
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({issues.length} issue{issues.length !== 1 ? "s" : ""})
          </span>
        </h3>
      )}

      <div className="space-y-3">
        {visibleIssues.map((issue, index) => (
          <IssueCard
            key={issue.rule || `issue-${index}`}
            issue={issue}
            defaultExpanded={index === 0 && issue.severity === "critical"}
          />
        ))}
      </div>

      {hasMore && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-4 w-full py-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {showAll
            ? "Show less"
            : `Show ${sortedIssues.length - maxVisible!} more issues`}
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Issue Summary
// ============================================================================

interface IssueSummaryProps {
  criticalCount: number;
  majorCount: number;
  minorCount: number;
  className?: string;
}

export function IssueSummary({
  criticalCount,
  majorCount,
  minorCount,
  className = "",
}: IssueSummaryProps) {
  const total = criticalCount + majorCount + minorCount;

  if (total === 0) {
    return (
      <div
        className={`flex items-center gap-2 text-green-600 dark:text-green-400 ${className}`}
      >
        <span className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-sm font-medium">No issues found</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {criticalCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {criticalCount} Critical
          </span>
        </div>
      )}
      {majorCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-orange-500" />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {majorCount} Major
          </span>
        </div>
      )}
      {minorCount > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {minorCount} Minor
          </span>
        </div>
      )}
    </div>
  );
}

export default IssueCard;

