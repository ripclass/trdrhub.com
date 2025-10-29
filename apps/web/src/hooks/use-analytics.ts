import * as React from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { analyticsApi } from "@/api/analytics";
import { useAuth } from "@/hooks/use-auth";
import type {
  AnalyticsQueryParams,
  SummaryStats,
  AnalyticsDashboard,
  AnalyticsFilters
} from "@/types/analytics";

// Query key factory
export const analyticsQueryKeys = {
  all: ['analytics'] as const,
  summary: (params?: AnalyticsQueryParams) => ['analytics', 'summary', params] as const,
  discrepancies: (params?: AnalyticsQueryParams) => ['analytics', 'discrepancies', params] as const,
  trends: (params?: AnalyticsQueryParams) => ['analytics', 'trends', params] as const,
  users: (params?: AnalyticsQueryParams) => ['analytics', 'users', params] as const,
  system: (params?: AnalyticsQueryParams) => ['analytics', 'system', params] as const,
  dashboard: (params?: AnalyticsQueryParams) => ['analytics', 'dashboard', params] as const,
  user: (userId: number, params?: AnalyticsQueryParams) => ['analytics', 'user', userId, params] as const,
  export: (format: 'csv' | 'pdf', params?: AnalyticsQueryParams) => ['analytics', 'export', format, params] as const,
};

// Convert AnalyticsFilters to AnalyticsQueryParams
const filtersToParams = (filters: AnalyticsFilters): AnalyticsQueryParams => ({
  time_range: filters.timeRange,
  start_date: filters.timeRange === "custom" ? filters.startDate?.toISOString() : undefined,
  end_date: filters.timeRange === "custom" ? filters.endDate?.toISOString() : undefined,
});

// Hook for summary stats
export function useAnalyticsSummary(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);

  return useQuery({
    queryKey: analyticsQueryKeys.summary(params),
    queryFn: () => analyticsApi.getSummary(params),
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
}

// Hook for discrepancy stats
export function useAnalyticsDiscrepancies(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);

  return useQuery({
    queryKey: analyticsQueryKeys.discrepancies(params),
    queryFn: () => analyticsApi.getDiscrepancies(params),
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for trend stats
export function useAnalyticsTrends(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);

  return useQuery({
    queryKey: analyticsQueryKeys.trends(params),
    queryFn: () => analyticsApi.getTrends(params),
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for user stats (bank/admin only)
export function useAnalyticsUsers(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);
  const canViewUsers = user?.role === "bank" || user?.role === "admin";

  return useQuery({
    queryKey: analyticsQueryKeys.users(params),
    queryFn: () => analyticsApi.getUsers(params),
    enabled: !!user && canViewUsers,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for system metrics (admin only)
export function useAnalyticsSystem(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);
  const canViewSystem = user?.role === "admin";

  return useQuery({
    queryKey: analyticsQueryKeys.system(params),
    queryFn: () => analyticsApi.getSystem(params),
    enabled: !!user && canViewSystem,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for complete dashboard (most commonly used)
export function useAnalyticsDashboard(filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);

  return useQuery({
    queryKey: analyticsQueryKeys.dashboard(params),
    queryFn: () => analyticsApi.getDashboard(params),
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for specific user analytics (bank/admin only)
export function useUserAnalytics(userId: number, filters: AnalyticsFilters) {
  const { user } = useAuth();
  const params = filtersToParams(filters);
  const canViewUser = user?.role === "bank" || user?.role === "admin";

  return useQuery({
    queryKey: analyticsQueryKeys.user(userId, params),
    queryFn: () => analyticsApi.getUserAnalytics(userId, params),
    enabled: !!user && canViewUser && !!userId,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });
}

// Hook for prefetching related analytics data
export function usePrefetchAnalytics() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const prefetchDashboard = (filters: AnalyticsFilters) => {
    if (!user) return;

    const params = filtersToParams(filters);

    queryClient.prefetchQuery({
      queryKey: analyticsQueryKeys.dashboard(params),
      queryFn: () => analyticsApi.getDashboard(params),
      staleTime: 5 * 60 * 1000,
    });
  };

  const prefetchSummary = (filters: AnalyticsFilters) => {
    if (!user) return;

    const params = filtersToParams(filters);

    queryClient.prefetchQuery({
      queryKey: analyticsQueryKeys.summary(params),
      queryFn: () => analyticsApi.getSummary(params),
      staleTime: 5 * 60 * 1000,
    });
  };

  return { prefetchDashboard, prefetchSummary };
}

// Hook for invalidating analytics cache
export function useInvalidateAnalytics() {
  const queryClient = useQueryClient();

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: analyticsQueryKeys.all });
  };

  const invalidateSummary = () => {
    queryClient.invalidateQueries({ queryKey: analyticsQueryKeys.summary() });
  };

  const invalidateDashboard = () => {
    queryClient.invalidateQueries({ queryKey: analyticsQueryKeys.dashboard() });
  };

  return { invalidateAll, invalidateSummary, invalidateDashboard };
}

// Export mutation hook for CSV/PDF downloads
export function useAnalyticsExport() {
  const exportCsv = useMutation({
    mutationFn: (params: AnalyticsQueryParams) => analyticsApi.exportCsv(params),
    onSuccess: (blob) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `analytics-export-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });

  const exportPdf = useMutation({
    mutationFn: (params: AnalyticsQueryParams) => analyticsApi.exportPdf(params),
    onSuccess: (blob) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `analytics-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });

  return { exportCsv, exportPdf };
}

// Background refresh hook for real-time updates
export function useAnalyticsAutoRefresh(filters: AnalyticsFilters, intervalMs = 5 * 60 * 1000) {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  React.useEffect(() => {
    if (!user) return;

    const interval = setInterval(() => {
      const params = filtersToParams(filters);

      // Refresh dashboard data in background
      queryClient.invalidateQueries({
        queryKey: analyticsQueryKeys.dashboard(params),
        refetchType: 'active'
      });
    }, intervalMs);

    return () => clearInterval(interval);
  }, [user, filters, intervalMs, queryClient]);
}

// Optimistic updates for better UX
export function useOptimisticAnalytics() {
  const queryClient = useQueryClient();

  const updateSummaryCache = (filters: AnalyticsFilters, updater: (old: SummaryStats | undefined) => SummaryStats | undefined) => {
    const params = filtersToParams(filters);
    queryClient.setQueryData(analyticsQueryKeys.summary(params), updater);
  };

  const updateDashboardCache = (filters: AnalyticsFilters, updater: (old: AnalyticsDashboard | undefined) => AnalyticsDashboard | undefined) => {
    const params = filtersToParams(filters);
    queryClient.setQueryData(analyticsQueryKeys.dashboard(params), updater);
  };

  return { updateSummaryCache, updateDashboardCache };
}