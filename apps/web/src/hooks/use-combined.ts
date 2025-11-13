import { useSearchParams } from "react-router-dom";
import { useMemo, useCallback } from "react";
import { useOnboarding } from "./use-onboarding";

export type ViewMode = "export" | "import" | "all";

export interface CombinedFilters {
  status?: string[];
  bank?: string[];
  dateRange?: "today" | "week" | "month" | "quarter" | "all";
}

export interface CombinedState {
  viewMode: ViewMode;
  filters: CombinedFilters;
  timeRange: "7d" | "30d" | "90d" | "all";
}

const DEFAULT_TIME_RANGE: CombinedState["timeRange"] = "30d";
const DEFAULT_VIEW_MODE: ViewMode = "all";

/**
 * Hook for managing combined dashboard state (viewMode, filters, timeRange)
 * Syncs with URL search params for shareable/bookmarkable state
 */
export function useCombined() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { status: onboardingStatus } = useOnboarding();

  // Derive default viewMode from onboarding business types
  const defaultViewMode = useMemo<ViewMode>(() => {
    if (!onboardingStatus?.details) return DEFAULT_VIEW_MODE;
    
    const details = onboardingStatus.details as Record<string, any>;
    const businessTypes = Array.isArray(details?.business_types) 
      ? details.business_types 
      : [];
    
    const hasExport = businessTypes.includes("exporter");
    const hasImport = businessTypes.includes("importer");
    
    if (hasExport && hasImport) {
      return "all"; // Show both by default
    } else if (hasExport) {
      return "export";
    } else if (hasImport) {
      return "import";
    }
    
    return DEFAULT_VIEW_MODE;
  }, [onboardingStatus]);

  // Get viewMode from URL or use default
  const viewMode = useMemo<ViewMode>(() => {
    const urlView = searchParams.get("view");
    if (urlView === "export" || urlView === "import" || urlView === "all") {
      return urlView;
    }
    return defaultViewMode;
  }, [searchParams, defaultViewMode]);

  // Get filters from URL
  const filters = useMemo<CombinedFilters>(() => {
    const statusParam = searchParams.get("status");
    const bankParam = searchParams.get("bank");
    const dateRangeParam = searchParams.get("dateRange");
    
    return {
      status: statusParam ? statusParam.split(",") : undefined,
      bank: bankParam ? bankParam.split(",") : undefined,
      dateRange: dateRangeParam as CombinedFilters["dateRange"] || undefined,
    };
  }, [searchParams]);

  // Get timeRange from URL
  const timeRange = useMemo<CombinedState["timeRange"]>(() => {
    const urlTimeRange = searchParams.get("timeRange");
    if (urlTimeRange === "7d" || urlTimeRange === "30d" || urlTimeRange === "90d" || urlTimeRange === "all") {
      return urlTimeRange;
    }
    return DEFAULT_TIME_RANGE;
  }, [searchParams]);

  // Update viewMode
  const setViewMode = useCallback((mode: ViewMode) => {
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev);
      newParams.set("view", mode);
      // Log telemetry
      console.log("📊 Combined dashboard viewMode changed:", mode);
      return newParams;
    });
  }, [setSearchParams]);

  // Update filters
  const setFilters = useCallback((newFilters: Partial<CombinedFilters>) => {
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev);
      
      if (newFilters.status !== undefined) {
        if (newFilters.status.length > 0) {
          newParams.set("status", newFilters.status.join(","));
        } else {
          newParams.delete("status");
        }
      }
      
      if (newFilters.bank !== undefined) {
        if (newFilters.bank.length > 0) {
          newParams.set("bank", newFilters.bank.join(","));
        } else {
          newParams.delete("bank");
        }
      }
      
      if (newFilters.dateRange !== undefined) {
        if (newFilters.dateRange) {
          newParams.set("dateRange", newFilters.dateRange);
        } else {
          newParams.delete("dateRange");
        }
      }
      
      return newParams;
    });
  }, [setSearchParams]);

  // Update timeRange
  const setTimeRange = useCallback((range: CombinedState["timeRange"]) => {
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev);
      newParams.set("timeRange", range);
      return newParams;
    });
  }, [setSearchParams]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev);
      newParams.delete("status");
      newParams.delete("bank");
      newParams.delete("dateRange");
      return newParams;
    });
  }, [setSearchParams]);

  return {
    viewMode,
    filters,
    timeRange,
    setViewMode,
    setFilters,
    setTimeRange,
    clearFilters,
  };
}

