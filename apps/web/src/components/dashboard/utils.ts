/**
 * Shared Dashboard Utilities
 * 
 * Common functions used by both Exporter and Importer dashboards.
 */

import type { ValidationSession } from "@/api/sessions";

// =============================================================================
// TYPES
// =============================================================================

export interface DashboardStats {
  thisMonth: number;
  successRate: number;
  avgProcessingTime: string;
  risksIdentified: number;
  totalReviews: number;
  documentsProcessed: number;
}

export interface HistoryItem {
  id: string;
  date: string;
  type: string;
  party: string;  // beneficiary for importer, applicant for exporter
  status: "approved" | "flagged" | "pending";
  risks: number;
}

// =============================================================================
// TIME UTILITIES
// =============================================================================

/**
 * Format a date string into a relative time (e.g., "2h ago", "3d ago")
 */
export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

  if (diffInHours < 1) return "Just now";
  if (diffInHours < 24) return `${diffInHours}h ago`;

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return `${diffInDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format milliseconds into a human-readable duration
 */
export function formatDuration(ms: number): string {
  if (ms <= 0) return "N/A";
  
  const minutes = ms / 60000;
  if (minutes < 1) return `${(ms / 1000).toFixed(1)}s`;
  if (minutes < 60) return `${minutes.toFixed(1)} min`;
  
  const hours = minutes / 60;
  return `${hours.toFixed(1)}h`;
}

// =============================================================================
// STATS CALCULATION
// =============================================================================

/**
 * Calculate dashboard statistics from validation sessions
 */
export function calculateDashboardStats(
  sessions: ValidationSession[],
  options: {
    criticalOnly?: boolean;  // For importer: only count critical as failures
  } = {}
): DashboardStats {
  const now = new Date();
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  
  const thisMonthSessions = sessions.filter(
    s => new Date(s.created_at) >= thisMonthStart
  );
  
  const completedSessions = sessions.filter(s => s.status === "completed");
  
  const totalDiscrepancies = sessions.reduce(
    (sum, s) => sum + (s.discrepancies?.length || 0),
    0
  );
  
  const totalDocuments = sessions.reduce(
    (sum, s) => sum + (s.documents?.length || 0),
    0
  );

  // Calculate success rate
  let successfulSessions: ValidationSession[];
  if (options.criticalOnly) {
    // Importer mode: only critical discrepancies count as failures
    successfulSessions = completedSessions.filter(s => {
      const criticalCount = (s.discrepancies || []).filter(
        d => d.severity === "critical"
      ).length;
      return criticalCount === 0;
    });
  } else {
    // Exporter mode: any discrepancy counts as a flag
    successfulSessions = completedSessions.filter(
      s => (s.discrepancies?.length || 0) === 0
    );
  }
  
  const successRate = completedSessions.length > 0
    ? Math.round((successfulSessions.length / completedSessions.length) * 100 * 10) / 10
    : 0;

  // Calculate average processing time
  const sessionsWithTime = completedSessions.filter(
    s => s.processing_started_at && s.processing_completed_at
  );
  
  const avgProcessingMs = sessionsWithTime.length > 0
    ? sessionsWithTime.reduce((sum, s) => {
        const start = new Date(s.processing_started_at!).getTime();
        const end = new Date(s.processing_completed_at!).getTime();
        return sum + (end - start);
      }, 0) / sessionsWithTime.length
    : 0;

  return {
    thisMonth: thisMonthSessions.length,
    successRate,
    avgProcessingTime: formatDuration(avgProcessingMs),
    risksIdentified: totalDiscrepancies,
    totalReviews: sessions.length,
    documentsProcessed: totalDocuments,
  };
}

/**
 * Transform sessions into history items for display
 */
export function sessionsToHistory(
  sessions: ValidationSession[],
  options: {
    limit?: number;
    partyField?: "beneficiary" | "applicant";  // Which field to show as party
    criticalOnly?: boolean;  // Use critical-only logic for status
  } = {}
): HistoryItem[] {
  const { limit = 5, partyField = "beneficiary", criticalOnly = false } = options;
  
  return [...sessions]
    .filter(s => s.status === "completed")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit)
    .map(s => {
      // Determine party name based on option
      let party = "Unknown";
      if (partyField === "beneficiary") {
        party = s.extracted_data?.beneficiary_name || s.extracted_data?.beneficiary || "Unknown";
      } else {
        party = s.extracted_data?.applicant_name || s.extracted_data?.applicant || "Unknown";
      }
      
      // Determine status
      let status: "approved" | "flagged" | "pending";
      if (criticalOnly) {
        const criticalCount = (s.discrepancies || []).filter(
          d => d.severity === "critical"
        ).length;
        status = criticalCount > 0 ? "flagged" : "approved";
      } else {
        status = (s.discrepancies?.length || 0) > 0 ? "flagged" : "approved";
      }
      
      return {
        id: s.id,
        date: new Date(s.created_at).toISOString().split("T")[0],
        type: "LC Review",
        party,
        status,
        risks: s.discrepancies?.length || 0,
      };
    });
}

// =============================================================================
// SECTION MANAGEMENT
// =============================================================================

export type DashboardSection =
  | "dashboard"
  | "overview"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "billing"
  | "billing-usage"
  | "ai-assistance"
  | "content-library"
  | "shipment-timeline"
  | "settings"
  | "help";

/**
 * Common section options available in both dashboards
 */
export const COMMON_SECTIONS: DashboardSection[] = [
  "dashboard",
  "workspace",
  "templates",
  "upload",
  "reviews",
  "analytics",
  "notifications",
  "billing",
  "billing-usage",
  "ai-assistance",
  "content-library",
  "shipment-timeline",
  "settings",
  "help",
];

/**
 * Check if a section is valid
 */
export function isValidSection(section: string | null): section is DashboardSection {
  if (!section) return false;
  return COMMON_SECTIONS.includes(section as DashboardSection);
}

