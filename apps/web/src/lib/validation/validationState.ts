/**
 * Validation State Machine - Phase 8: Frontend Hardening
 *
 * This module provides a state machine for validation status display.
 * It ensures the UI correctly reflects:
 * - BLOCKED: Red - Validation could not proceed (missing LC)
 * - NON_COMPLIANT: Red - Critical issues found
 * - PARTIAL: Yellow/Orange - Major issues found
 * - MOSTLY_COMPLIANT: Yellow - Minor issues found
 * - COMPLIANT: Green - All checks passed
 */

// ============================================================================
// Types
// ============================================================================

export type ValidationStatus =
  | "idle"
  | "loading"
  | "blocked"
  | "non_compliant"
  | "partial"
  | "mostly_compliant"
  | "compliant"
  | "error";

export type ComplianceLevel =
  | "blocked"
  | "non_compliant"
  | "partial"
  | "mostly_compliant"
  | "compliant";

export type IssueSeverity = "critical" | "major" | "minor" | "info";

export interface ValidationState {
  status: ValidationStatus;
  complianceLevel: ComplianceLevel | null;
  complianceScore: number;
  isBlocked: boolean;
  blockReason: string | null;

  // Issue counts
  criticalCount: number;
  majorCount: number;
  minorCount: number;
  totalIssues: number;

  // Extraction metrics
  extractionCompleteness: number;
  criticalCompleteness: number;
  missingCriticalFields: string[];

  // UI display
  statusLabel: string;
  statusColor: StatusColor;
  statusIcon: StatusIcon;
  canProceed: boolean;
}

export type StatusColor = "red" | "orange" | "yellow" | "green" | "gray";
export type StatusIcon = "block" | "error" | "warning" | "check" | "loading";

// ============================================================================
// State Derivation
// ============================================================================

/**
 * Derive validation state from API response.
 */
export function deriveValidationState(
  response: Record<string, unknown> | null | undefined
): ValidationState {
  // Default/empty state
  if (!response) {
    return createIdleState();
  }

  // Check if validation was blocked
  if (response.validation_blocked === true) {
    return createBlockedState(response);
  }

  // Get compliance data
  const complianceScore = normalizeScore(
    response.compliance_rate ??
      response.processing_summary?.compliance_rate ??
      response.analytics?.lc_compliance_score ??
      0
  );

  const complianceLevel = deriveComplianceLevel(
    response.gate_result?.level ??
      response.compliance_level ??
      scoreToLevel(complianceScore)
  );

  // Get issue counts
  const issues = normalizeArray(response.issues ?? response.issue_cards ?? []);
  const criticalCount = countBySeverity(issues, "critical");
  const majorCount = countBySeverity(issues, "major");
  const minorCount = countBySeverity(issues, "minor");
  const totalIssues = issues.length;

  // Get extraction metrics
  const extractionCompleteness = normalizeScore(
    response.extraction_summary?.completeness ??
      response.gate_result?.completeness ??
      100
  );
  const criticalCompleteness = normalizeScore(
    response.extraction_summary?.critical_completeness ??
      response.gate_result?.critical_completeness ??
      100
  );
  const missingCriticalFields = normalizeArray(
    response.extraction_summary?.missing_critical ??
      response.gate_result?.missing_critical ??
      []
  );

  // Determine status
  const status = deriveStatus(complianceLevel, criticalCount);

  // Get UI properties
  const { statusLabel, statusColor, statusIcon } = getStatusDisplay(
    status,
    complianceScore,
    criticalCount,
    majorCount
  );

  return {
    status,
    complianceLevel,
    complianceScore,
    isBlocked: false,
    blockReason: null,
    criticalCount,
    majorCount,
    minorCount,
    totalIssues,
    extractionCompleteness,
    criticalCompleteness,
    missingCriticalFields,
    statusLabel,
    statusColor,
    statusIcon,
    canProceed: criticalCount === 0,
  };
}

/**
 * Create idle state (no validation yet).
 */
function createIdleState(): ValidationState {
  return {
    status: "idle",
    complianceLevel: null,
    complianceScore: 0,
    isBlocked: false,
    blockReason: null,
    criticalCount: 0,
    majorCount: 0,
    minorCount: 0,
    totalIssues: 0,
    extractionCompleteness: 0,
    criticalCompleteness: 0,
    missingCriticalFields: [],
    statusLabel: "Not Validated",
    statusColor: "gray",
    statusIcon: "loading",
    canProceed: false,
  };
}

/**
 * Create blocked state (validation could not proceed).
 */
function createBlockedState(
  response: Record<string, unknown>
): ValidationState {
  const blockReason =
    (response.block_reason as string) ??
    (response.gate_result as Record<string, unknown>)?.block_reason ??
    "LC extraction failed";

  const missingCritical = normalizeArray(
    (response.gate_result as Record<string, unknown>)?.missing_critical ??
      (response.extraction_summary as Record<string, unknown>)
        ?.missing_critical ??
      []
  );

  return {
    status: "blocked",
    complianceLevel: "blocked",
    complianceScore: 0,
    isBlocked: true,
    blockReason: String(blockReason),
    criticalCount: 1, // Blocked always has at least 1 critical issue
    majorCount: 0,
    minorCount: 0,
    totalIssues: 1,
    extractionCompleteness: normalizeScore(
      (response.gate_result as Record<string, unknown>)?.completeness ?? 0
    ),
    criticalCompleteness: normalizeScore(
      (response.gate_result as Record<string, unknown>)?.critical_completeness ??
        0
    ),
    missingCriticalFields: missingCritical.map(String),
    statusLabel: "Validation Blocked",
    statusColor: "red",
    statusIcon: "block",
    canProceed: false,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

function normalizeScore(value: unknown): number {
  if (typeof value === "number") {
    return Math.max(0, Math.min(100, value));
  }
  if (typeof value === "string") {
    const num = parseFloat(value);
    return isNaN(num) ? 0 : Math.max(0, Math.min(100, num));
  }
  return 0;
}

function normalizeArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  return [];
}

function countBySeverity(issues: unknown[], severity: IssueSeverity): number {
  return issues.filter((issue) => {
    if (typeof issue !== "object" || issue === null) return false;
    const issueSeverity = (issue as Record<string, unknown>).severity;
    return String(issueSeverity).toLowerCase() === severity;
  }).length;
}

function deriveComplianceLevel(level: unknown): ComplianceLevel {
  const levelStr = String(level).toLowerCase();
  if (levelStr === "blocked") return "blocked";
  if (levelStr === "non_compliant") return "non_compliant";
  if (levelStr === "partial") return "partial";
  if (levelStr === "mostly_compliant") return "mostly_compliant";
  if (levelStr === "compliant") return "compliant";
  return "non_compliant"; // Default to non-compliant
}

function scoreToLevel(score: number): ComplianceLevel {
  if (score >= 85) return "compliant";
  if (score >= 70) return "mostly_compliant";
  if (score >= 30) return "partial";
  return "non_compliant";
}

function deriveStatus(
  level: ComplianceLevel,
  criticalCount: number
): ValidationStatus {
  if (level === "blocked") return "blocked";
  if (criticalCount > 0) return "non_compliant";
  if (level === "non_compliant") return "non_compliant";
  if (level === "partial") return "partial";
  if (level === "mostly_compliant") return "mostly_compliant";
  return "compliant";
}

function getStatusDisplay(
  status: ValidationStatus,
  score: number,
  criticalCount: number,
  majorCount: number
): {
  statusLabel: string;
  statusColor: StatusColor;
  statusIcon: StatusIcon;
} {
  switch (status) {
    case "blocked":
      return {
        statusLabel: "Validation Blocked",
        statusColor: "red",
        statusIcon: "block",
      };

    case "non_compliant":
      return {
        statusLabel: `Non-Compliant (${criticalCount} Critical)`,
        statusColor: "red",
        statusIcon: "error",
      };

    case "partial":
      return {
        statusLabel: `Partial Compliance (${score}%)`,
        statusColor: "orange",
        statusIcon: "warning",
      };

    case "mostly_compliant":
      return {
        statusLabel: `Mostly Compliant (${score}%)`,
        statusColor: "yellow",
        statusIcon: "warning",
      };

    case "compliant":
      return {
        statusLabel: `Compliant (${score}%)`,
        statusColor: "green",
        statusIcon: "check",
      };

    case "loading":
      return {
        statusLabel: "Validating...",
        statusColor: "gray",
        statusIcon: "loading",
      };

    case "error":
      return {
        statusLabel: "Validation Error",
        statusColor: "red",
        statusIcon: "error",
      };

    default:
      return {
        statusLabel: "Not Validated",
        statusColor: "gray",
        statusIcon: "loading",
      };
  }
}

// ============================================================================
// CSS Class Mapping
// ============================================================================

/**
 * Get Tailwind CSS classes for status color.
 */
export function getStatusColorClasses(color: StatusColor): {
  bg: string;
  text: string;
  border: string;
  badge: string;
} {
  switch (color) {
    case "red":
      return {
        bg: "bg-red-50 dark:bg-red-950",
        text: "text-red-700 dark:text-red-300",
        border: "border-red-200 dark:border-red-800",
        badge: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
      };

    case "orange":
      return {
        bg: "bg-orange-50 dark:bg-orange-950",
        text: "text-orange-700 dark:text-orange-300",
        border: "border-orange-200 dark:border-orange-800",
        badge:
          "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
      };

    case "yellow":
      return {
        bg: "bg-yellow-50 dark:bg-yellow-950",
        text: "text-yellow-700 dark:text-yellow-300",
        border: "border-yellow-200 dark:border-yellow-800",
        badge:
          "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      };

    case "green":
      return {
        bg: "bg-green-50 dark:bg-green-950",
        text: "text-green-700 dark:text-green-300",
        border: "border-green-200 dark:border-green-800",
        badge:
          "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      };

    default:
      return {
        bg: "bg-gray-50 dark:bg-gray-900",
        text: "text-gray-700 dark:text-gray-300",
        border: "border-gray-200 dark:border-gray-700",
        badge:
          "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
      };
  }
}

/**
 * Get severity color classes.
 */
export function getSeverityColorClasses(severity: IssueSeverity): {
  bg: string;
  text: string;
  dot: string;
} {
  switch (severity) {
    case "critical":
      return {
        bg: "bg-red-100 dark:bg-red-900",
        text: "text-red-800 dark:text-red-200",
        dot: "bg-red-500",
      };

    case "major":
      return {
        bg: "bg-orange-100 dark:bg-orange-900",
        text: "text-orange-800 dark:text-orange-200",
        dot: "bg-orange-500",
      };

    case "minor":
      return {
        bg: "bg-yellow-100 dark:bg-yellow-900",
        text: "text-yellow-800 dark:text-yellow-200",
        dot: "bg-yellow-500",
      };

    default:
      return {
        bg: "bg-blue-100 dark:bg-blue-900",
        text: "text-blue-800 dark:text-blue-200",
        dot: "bg-blue-500",
      };
  }
}

// ============================================================================
// Compliance Score Formatting
// ============================================================================

/**
 * Format compliance score for display.
 */
export function formatComplianceScore(score: number): string {
  return `${Math.round(score)}%`;
}

/**
 * Get compliance score ring color (for circular progress).
 */
export function getScoreRingColor(score: number): string {
  if (score >= 85) return "#22c55e"; // green-500
  if (score >= 70) return "#eab308"; // yellow-500
  if (score >= 30) return "#f97316"; // orange-500
  return "#ef4444"; // red-500
}

/**
 * Get compliance level label.
 */
export function getComplianceLevelLabel(level: ComplianceLevel): string {
  switch (level) {
    case "blocked":
      return "Blocked";
    case "non_compliant":
      return "Non-Compliant";
    case "partial":
      return "Partial";
    case "mostly_compliant":
      return "Mostly Compliant";
    case "compliant":
      return "Compliant";
  }
}

// ============================================================================
// Issue Helpers
// ============================================================================

/**
 * Sort issues by severity (critical first).
 */
export function sortIssuesBySeverity<T extends { severity?: string }>(
  issues: T[]
): T[] {
  const severityOrder: Record<string, number> = {
    critical: 0,
    major: 1,
    minor: 2,
    info: 3,
  };

  return [...issues].sort((a, b) => {
    const aSev = severityOrder[a.severity?.toLowerCase() ?? "info"] ?? 4;
    const bSev = severityOrder[b.severity?.toLowerCase() ?? "info"] ?? 4;
    return aSev - bSev;
  });
}

/**
 * Group issues by severity.
 */
export function groupIssuesBySeverity<T extends { severity?: string }>(
  issues: T[]
): Record<IssueSeverity, T[]> {
  return {
    critical: issues.filter(
      (i) => i.severity?.toLowerCase() === "critical"
    ),
    major: issues.filter((i) => i.severity?.toLowerCase() === "major"),
    minor: issues.filter((i) => i.severity?.toLowerCase() === "minor"),
    info: issues.filter(
      (i) =>
        !i.severity ||
        !["critical", "major", "minor"].includes(i.severity.toLowerCase())
    ),
  };
}

/**
 * Get issue severity label.
 */
export function getSeverityLabel(severity: IssueSeverity): string {
  switch (severity) {
    case "critical":
      return "Critical";
    case "major":
      return "Major";
    case "minor":
      return "Minor";
    default:
      return "Info";
  }
}

