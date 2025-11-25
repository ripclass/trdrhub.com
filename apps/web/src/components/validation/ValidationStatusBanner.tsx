/**
 * Validation Status Banner - Phase 8: Frontend Hardening
 *
 * A banner component that displays validation status with appropriate
 * colors and icons based on the validation state.
 *
 * States:
 * - BLOCKED (Red): Validation could not proceed
 * - NON_COMPLIANT (Red): Critical issues found
 * - PARTIAL (Orange): Major issues found
 * - MOSTLY_COMPLIANT (Yellow): Minor issues found
 * - COMPLIANT (Green): All checks passed
 */

import React from "react";
import {
  AlertTriangle,
  XCircle,
  CheckCircle,
  AlertOctagon,
  Loader2,
} from "lucide-react";
import {
  ValidationState,
  StatusColor,
  StatusIcon,
  getStatusColorClasses,
} from "@/lib/validation/validationState";

interface ValidationStatusBannerProps {
  state: ValidationState;
  showDetails?: boolean;
  className?: string;
}

/**
 * Get icon component for status.
 */
function getIconComponent(icon: StatusIcon, className: string) {
  switch (icon) {
    case "block":
      return <AlertOctagon className={className} />;
    case "error":
      return <XCircle className={className} />;
    case "warning":
      return <AlertTriangle className={className} />;
    case "check":
      return <CheckCircle className={className} />;
    case "loading":
      return <Loader2 className={`${className} animate-spin`} />;
    default:
      return <AlertTriangle className={className} />;
  }
}

export function ValidationStatusBanner({
  state,
  showDetails = true,
  className = "",
}: ValidationStatusBannerProps) {
  const colors = getStatusColorClasses(state.statusColor);

  return (
    <div
      className={`rounded-lg border p-4 ${colors.bg} ${colors.border} ${className}`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`flex-shrink-0 ${colors.text}`}>
          {getIconComponent(state.statusIcon, "h-5 w-5")}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Status Label */}
          <h3 className={`font-semibold ${colors.text}`}>{state.statusLabel}</h3>

          {/* Block Reason (if blocked) */}
          {state.isBlocked && state.blockReason && (
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              {state.blockReason}
            </p>
          )}

          {/* Issue Summary */}
          {showDetails && state.totalIssues > 0 && !state.isBlocked && (
            <div className="mt-2 flex flex-wrap gap-2">
              {state.criticalCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                  {state.criticalCount} Critical
                </span>
              )}
              {state.majorCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">
                  {state.majorCount} Major
                </span>
              )}
              {state.minorCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                  {state.minorCount} Minor
                </span>
              )}
            </div>
          )}

          {/* Missing Fields (if blocked or low completeness) */}
          {showDetails &&
            state.missingCriticalFields.length > 0 &&
            state.extractionCompleteness < 50 && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Missing critical fields:{" "}
                  <span className="font-medium">
                    {state.missingCriticalFields.slice(0, 3).join(", ")}
                    {state.missingCriticalFields.length > 3 &&
                      ` +${state.missingCriticalFields.length - 3} more`}
                  </span>
                </p>
              </div>
            )}
        </div>

        {/* Score Badge */}
        {!state.isBlocked && state.status !== "idle" && state.status !== "loading" && (
          <div className="flex-shrink-0">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-semibold ${colors.badge}`}>
              {state.complianceScore}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Compact Variant
// ============================================================================

interface ValidationStatusBadgeProps {
  state: ValidationState;
  size?: "sm" | "md" | "lg";
  showScore?: boolean;
}

export function ValidationStatusBadge({
  state,
  size = "md",
  showScore = true,
}: ValidationStatusBadgeProps) {
  const colors = getStatusColorClasses(state.statusColor);

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm",
    lg: "px-3 py-1.5 text-base",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses[size]} ${colors.badge}`}
    >
      {getIconComponent(state.statusIcon, iconSizes[size])}
      {showScore && !state.isBlocked ? (
        <span>{state.complianceScore}%</span>
      ) : state.isBlocked ? (
        <span>Blocked</span>
      ) : (
        <span>{state.statusLabel}</span>
      )}
    </span>
  );
}

// ============================================================================
// Compliance Score Ring
// ============================================================================

interface ComplianceScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
}

export function ComplianceScoreRing({
  score,
  size = 80,
  strokeWidth = 8,
  showLabel = true,
}: ComplianceScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  // Color based on score
  let strokeColor = "#ef4444"; // red
  if (score >= 85) strokeColor = "#22c55e"; // green
  else if (score >= 70) strokeColor = "#eab308"; // yellow
  else if (score >= 30) strokeColor = "#f97316"; // orange

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-200 dark:text-gray-700"
        />
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold">{Math.round(score)}%</span>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Blocked Validation Card
// ============================================================================

interface BlockedValidationCardProps {
  state: ValidationState;
  onRetry?: () => void;
}

export function BlockedValidationCard({
  state,
  onRetry,
}: BlockedValidationCardProps) {
  if (!state.isBlocked) return null;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
          <AlertOctagon className="h-6 w-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            Validation Blocked
          </h3>
          <p className="text-sm text-red-600 dark:text-red-400">
            Unable to proceed with document validation
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-md p-4 mb-4">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
          Reason
        </h4>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {state.blockReason}
        </p>
      </div>

      {state.missingCriticalFields.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-md p-4 mb-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            Missing Critical Fields
          </h4>
          <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400">
            {state.missingCriticalFields.map((field) => (
              <li key={field}>{field.replace(/_/g, " ")}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-md p-4 mb-4">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
          Extraction Quality
        </h4>
        <div className="flex items-center gap-4">
          <div>
            <span className="text-2xl font-bold text-red-600 dark:text-red-400">
              {Math.round(state.extractionCompleteness)}%
            </span>
            <span className="text-sm text-gray-500 ml-1">overall</span>
          </div>
          <div>
            <span className="text-2xl font-bold text-red-600 dark:text-red-400">
              {Math.round(state.criticalCompleteness)}%
            </span>
            <span className="text-sm text-gray-500 ml-1">critical fields</span>
          </div>
        </div>
      </div>

      <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        <strong>What to do:</strong>
        <ul className="list-disc list-inside mt-1">
          <li>Ensure you've uploaded a valid Letter of Credit document</li>
          <li>Check that the document is clearly scanned with good quality</li>
          <li>Verify the document is in a supported format (PDF, PNG, JPG)</li>
        </ul>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="w-full py-2 px-4 bg-red-600 hover:bg-red-700 text-white font-medium rounded-md transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}

export default ValidationStatusBanner;

