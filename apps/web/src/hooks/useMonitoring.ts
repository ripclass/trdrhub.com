/**
 * React Query hooks for monitoring functionality
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { monitoringApi } from '../api/monitoring';
import type {
  MonitoringFilters,
  AlertFilters,
  AcknowledgeAlertRequest,
  ResolveAlertRequest,
  ExportMonitoringRequest
} from '../types/monitoring';

// Query keys
export const monitoringKeys = {
  all: ['monitoring'] as const,
  kpis: (filters: MonitoringFilters) => [...monitoringKeys.all, 'kpis', filters] as const,
  alerts: (filters: AlertFilters) => [...monitoringKeys.all, 'alerts', filters] as const,
  alert: (id: string) => [...monitoringKeys.all, 'alert', id] as const,
  anomalies: (filters: MonitoringFilters) => [...monitoringKeys.all, 'anomalies', filters] as const,
  performance: (filters: MonitoringFilters) => [...monitoringKeys.all, 'performance', filters] as const,
  systemHealth: () => [...monitoringKeys.all, 'system-health'] as const,
  dashboards: () => [...monitoringKeys.all, 'dashboards'] as const,
  notifications: () => [...monitoringKeys.all, 'notifications'] as const,
};

// System KPIs hook
export const useSystemKPIs = (
  filters: MonitoringFilters,
  options?: { enabled?: boolean; refetchInterval?: number }
) => {
  return useQuery({
    queryKey: monitoringKeys.kpis(filters),
    queryFn: () => monitoringApi.getSystemKPIs(filters),
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
  });
};

// System alerts hook
export const useSystemAlerts = (
  filters: AlertFilters = {},
  options?: { enabled?: boolean; refetchInterval?: number }
) => {
  return useQuery({
    queryKey: monitoringKeys.alerts(filters),
    queryFn: () => monitoringApi.getSystemAlerts(filters),
    staleTime: 15 * 1000, // 15 seconds
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
  });
};

// Single alert hook
export const useSystemAlert = (alertId: string) => {
  return useQuery({
    queryKey: monitoringKeys.alert(alertId),
    queryFn: () => monitoringApi.getSystemAlert(alertId),
    enabled: !!alertId,
    staleTime: 60 * 1000, // 1 minute
  });
};

// Anomaly detection hook
export const useAnomalyDetection = (
  filters: MonitoringFilters,
  options?: { enabled?: boolean }
) => {
  return useQuery({
    queryKey: monitoringKeys.anomalies(filters),
    queryFn: () => monitoringApi.getAnomalyData(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
    enabled: options?.enabled ?? true,
  });
};

// Performance metrics hook
export const usePerformanceMetrics = (
  filters: MonitoringFilters,
  options?: { enabled?: boolean }
) => {
  return useQuery({
    queryKey: monitoringKeys.performance(filters),
    queryFn: () => monitoringApi.getPerformanceMetrics(filters),
    staleTime: 60 * 1000, // 1 minute
    enabled: options?.enabled ?? true,
  });
};

// System health hook
export const useSystemHealth = (options?: { enabled?: boolean; refetchInterval?: number }) => {
  return useQuery({
    queryKey: monitoringKeys.systemHealth(),
    queryFn: monitoringApi.getSystemHealth,
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30 * 1000, // Auto-refresh every 30s
  });
};

// Monitoring dashboards hook
export const useMonitoringDashboards = () => {
  return useQuery({
    queryKey: monitoringKeys.dashboards(),
    queryFn: monitoringApi.getMonitoringDashboards,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Notification settings hook
export const useNotificationSettings = () => {
  return useQuery({
    queryKey: monitoringKeys.notifications(),
    queryFn: monitoringApi.getNotificationSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Acknowledge alert mutation
export const useAcknowledgeAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: AcknowledgeAlertRequest) =>
      monitoringApi.acknowledgeAlert(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alert(variables.alertId) });
      toast.success('Alert acknowledged successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to acknowledge alert: ${error.message}`);
    },
  });
};

// Resolve alert mutation
export const useResolveAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ResolveAlertRequest) =>
      monitoringApi.resolveAlert(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alert(variables.alertId) });
      toast.success('Alert resolved successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to resolve alert: ${error.message}`);
    },
  });
};

// Dismiss alert mutation
export const useDismissAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) =>
      monitoringApi.dismissAlert(alertId),
    onSuccess: (_, alertId) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alert(alertId) });
      toast.success('Alert dismissed');
    },
    onError: (error: any) => {
      toast.error(`Failed to dismiss alert: ${error.message}`);
    },
  });
};

// Create alert mutation (for testing)
export const useCreateTestAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: monitoringApi.createTestAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      toast.success('Test alert created');
    },
    onError: (error: any) => {
      toast.error(`Failed to create test alert: ${error.message}`);
    },
  });
};

// Update notification settings mutation
export const useUpdateNotificationSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: monitoringApi.updateNotificationSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.notifications() });
      toast.success('Notification settings updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update notification settings: ${error.message}`);
    },
  });
};

// Test notification mutation
export const useTestNotification = () => {
  return useMutation({
    mutationFn: (channelId: string) =>
      monitoringApi.testNotification(channelId),
    onSuccess: () => {
      toast.success('Test notification sent successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to send test notification: ${error.message}`);
    },
  });
};

// Export monitoring data mutation
export const useExportMonitoringData = () => {
  return useMutation({
    mutationFn: (request: ExportMonitoringRequest) =>
      monitoringApi.exportMonitoringData(request),
    onSuccess: (blob: Blob, variables: ExportMonitoringRequest) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const format = variables.format || 'xlsx';
      a.download = `monitoring-report-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Monitoring report exported successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to export monitoring report: ${error.message}`);
    },
  });
};

// Bulk operations
export const useBulkAcknowledgeAlerts = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertIds: string[]) =>
      monitoringApi.bulkAcknowledgeAlerts(alertIds),
    onSuccess: (_, alertIds) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      alertIds.forEach(id => {
        queryClient.invalidateQueries({ queryKey: monitoringKeys.alert(id) });
      });
      toast.success(`${alertIds.length} alerts acknowledged successfully`);
    },
    onError: (error: any) => {
      toast.error(`Failed to acknowledge alerts: ${error.message}`);
    },
  });
};

export const useBulkResolveAlerts = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertIds: string[]) =>
      monitoringApi.bulkResolveAlerts(alertIds),
    onSuccess: (_, alertIds) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      alertIds.forEach(id => {
        queryClient.invalidateQueries({ queryKey: monitoringKeys.alert(id) });
      });
      toast.success(`${alertIds.length} alerts resolved successfully`);
    },
    onError: (error: any) => {
      toast.error(`Failed to resolve alerts: ${error.message}`);
    },
  });
};

// Dashboard operations
export const useCreateMonitoringDashboard = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: monitoringApi.createMonitoringDashboard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.dashboards() });
      toast.success('Dashboard created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create dashboard: ${error.message}`);
    },
  });
};

export const useUpdateMonitoringDashboard = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: monitoringApi.updateMonitoringDashboard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.dashboards() });
      toast.success('Dashboard updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update dashboard: ${error.message}`);
    },
  });
};

// Utility hooks
export const useRefreshMonitoringData = () => {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: monitoringKeys.all });
    toast.success('Monitoring data refreshed');
  };
};

// Real-time monitoring hook with WebSocket
export const useRealTimeMonitoring = (enabled: boolean = false) => {
  const queryClient = useQueryClient();

  // This would connect to a WebSocket for real-time updates
  // For now, we'll use polling
  useQuery({
    queryKey: ['monitoring-realtime'],
    queryFn: async () => {
      // Refresh critical data
      queryClient.invalidateQueries({ queryKey: monitoringKeys.kpis({}) });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts({}) });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.systemHealth() });
      return null;
    },
    refetchInterval: 10 * 1000, // 10 seconds
    enabled,
  });
};

// Alert statistics hook
export const useAlertStatistics = (timeRange: string = '24h') => {
  return useQuery({
    queryKey: [...monitoringKeys.all, 'alert-stats', timeRange],
    queryFn: () => monitoringApi.getAlertStatistics(timeRange),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// System metrics summary hook
export const useSystemMetricsSummary = (timeRange: string = '24h') => {
  return useQuery({
    queryKey: [...monitoringKeys.all, 'metrics-summary', timeRange],
    queryFn: () => monitoringApi.getSystemMetricsSummary(timeRange),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};