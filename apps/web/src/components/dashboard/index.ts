/**
 * Shared Dashboard Components
 * 
 * Common utilities, hooks, and components for Exporter and Importer dashboards.
 */

// Utilities
export {
  formatTimeAgo,
  formatDuration,
  calculateDashboardStats,
  sessionsToHistory,
  isValidSection,
  COMMON_SECTIONS,
} from "./utils";
export type { DashboardStats, HistoryItem, DashboardSection } from "./utils";

// Hook
export { useDashboardBase } from "./useDashboardBase";
export type { DashboardBaseOptions, DashboardBaseReturn } from "./useDashboardBase";

// Components
export { DashboardLoading } from "./DashboardLoading";
export {
  StatCard,
  DashboardStatsGrid,
  UsageQuotaCard,
  PendingInvoiceCard,
} from "./DashboardStatCards";
export { RecentValidationsCard } from "./RecentValidationsCard";

