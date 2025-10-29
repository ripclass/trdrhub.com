/**
 * Monitoring API client functions
 */

import { api } from './client';
import type {
  SystemKPIs,
  SystemAlert,
  AlertList,
  AnomalyData,
  PerformanceMetrics,
  SystemHealth,
  MonitoringDashboard,
  MonitoringNotificationSettings,
  MonitoringFilters,
  AlertFilters,
  AcknowledgeAlertRequest,
  ResolveAlertRequest,
  ExportMonitoringRequest
} from '../types/monitoring';

// System monitoring endpoints
export const monitoringApi = {
  // Get system KPIs
  getSystemKPIs: async (filters: MonitoringFilters): Promise<SystemKPIs> => {
    const response = await api.get('/monitoring/kpis', { params: filters });
    return response.data;
  },

  // Get system alerts
  getSystemAlerts: async (filters: AlertFilters = {}): Promise<AlertList> => {
    const response = await api.get('/monitoring/alerts', { params: filters });
    return response.data;
  },

  // Get single alert
  getSystemAlert: async (alertId: string): Promise<SystemAlert> => {
    const response = await api.get(`/monitoring/alerts/${alertId}`);
    return response.data;
  },

  // Get anomaly detection data
  getAnomalyData: async (filters: MonitoringFilters): Promise<AnomalyData[]> => {
    const response = await api.get('/monitoring/anomalies', { params: filters });
    return response.data;
  },

  // Get performance metrics
  getPerformanceMetrics: async (filters: MonitoringFilters): Promise<PerformanceMetrics[]> => {
    const response = await api.get('/monitoring/performance', { params: filters });
    return response.data;
  },

  // Get system health status
  getSystemHealth: async (): Promise<SystemHealth> => {
    const response = await api.get('/monitoring/health');
    return response.data;
  },

  // Alert management
  acknowledgeAlert: async (request: AcknowledgeAlertRequest): Promise<SystemAlert> => {
    const response = await api.post(`/monitoring/alerts/${request.alertId}/acknowledge`, {
      message: request.message
    });
    return response.data;
  },

  resolveAlert: async (request: ResolveAlertRequest): Promise<SystemAlert> => {
    const response = await api.post(`/monitoring/alerts/${request.alertId}/resolve`, {
      resolution: request.resolution
    });
    return response.data;
  },

  dismissAlert: async (alertId: string): Promise<SystemAlert> => {
    const response = await api.post(`/monitoring/alerts/${alertId}/dismiss`);
    return response.data;
  },

  // Bulk operations
  bulkAcknowledgeAlerts: async (alertIds: string[]): Promise<void> => {
    await api.post('/monitoring/alerts/bulk-acknowledge', { alert_ids: alertIds });
  },

  bulkResolveAlerts: async (alertIds: string[]): Promise<void> => {
    await api.post('/monitoring/alerts/bulk-resolve', { alert_ids: alertIds });
  },

  // Create test alert (for testing purposes)
  createTestAlert: async (): Promise<SystemAlert> => {
    const response = await api.post('/monitoring/alerts/test');
    return response.data;
  },

  // Dashboard management
  getMonitoringDashboards: async (): Promise<MonitoringDashboard[]> => {
    const response = await api.get('/monitoring/dashboards');
    return response.data;
  },

  createMonitoringDashboard: async (dashboard: Partial<MonitoringDashboard>): Promise<MonitoringDashboard> => {
    const response = await api.post('/monitoring/dashboards', dashboard);
    return response.data;
  },

  updateMonitoringDashboard: async (dashboard: MonitoringDashboard): Promise<MonitoringDashboard> => {
    const response = await api.put(`/monitoring/dashboards/${dashboard.id}`, dashboard);
    return response.data;
  },

  deleteMonitoringDashboard: async (dashboardId: string): Promise<void> => {
    await api.delete(`/monitoring/dashboards/${dashboardId}`);
  },

  // Notification settings
  getNotificationSettings: async (): Promise<MonitoringNotificationSettings> => {
    const response = await api.get('/monitoring/notifications/settings');
    return response.data;
  },

  updateNotificationSettings: async (settings: MonitoringNotificationSettings): Promise<MonitoringNotificationSettings> => {
    const response = await api.put('/monitoring/notifications/settings', settings);
    return response.data;
  },

  testNotification: async (channelId: string): Promise<void> => {
    await api.post(`/monitoring/notifications/test/${channelId}`);
  },

  // Export functionality
  exportMonitoringData: async (request: ExportMonitoringRequest): Promise<Blob> => {
    const response = await api.get('/monitoring/export', {
      params: request,
      responseType: 'blob'
    });
    return response.data;
  },

  // Statistics and summaries
  getAlertStatistics: async (timeRange: string): Promise<any> => {
    const response = await api.get('/monitoring/statistics/alerts', {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  getSystemMetricsSummary: async (timeRange: string): Promise<any> => {
    const response = await api.get('/monitoring/statistics/metrics', {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  // Threshold management
  getAlertThresholds: async (): Promise<any> => {
    const response = await api.get('/monitoring/thresholds');
    return response.data;
  },

  updateAlertThresholds: async (thresholds: any): Promise<any> => {
    const response = await api.put('/monitoring/thresholds', thresholds);
    return response.data;
  },

  // Service-specific monitoring
  getServiceMetrics: async (serviceName: string, filters: MonitoringFilters): Promise<any> => {
    const response = await api.get(`/monitoring/services/${serviceName}/metrics`, {
      params: filters
    });
    return response.data;
  },

  getServiceHealth: async (serviceName: string): Promise<any> => {
    const response = await api.get(`/monitoring/services/${serviceName}/health`);
    return response.data;
  },

  // Real-time data (WebSocket would be preferred, but HTTP polling for now)
  getRealtimeMetrics: async (): Promise<any> => {
    const response = await api.get('/monitoring/realtime');
    return response.data;
  },

  // Log analysis
  getSystemLogs: async (filters: any): Promise<any> => {
    const response = await api.get('/monitoring/logs', { params: filters });
    return response.data;
  },

  searchLogs: async (query: string, filters: any): Promise<any> => {
    const response = await api.get('/monitoring/logs/search', {
      params: { query, ...filters }
    });
    return response.data;
  },

  // Webhook monitoring
  getWebhookMetrics: async (filters: MonitoringFilters): Promise<any> => {
    const response = await api.get('/monitoring/webhooks', { params: filters });
    return response.data;
  },

  getWebhookErrors: async (filters: any): Promise<any> => {
    const response = await api.get('/monitoring/webhooks/errors', { params: filters });
    return response.data;
  },

  // Payment monitoring
  getPaymentMetrics: async (filters: MonitoringFilters): Promise<any> => {
    const response = await api.get('/monitoring/payments', { params: filters });
    return response.data;
  },

  getPaymentFailures: async (filters: any): Promise<any> => {
    const response = await api.get('/monitoring/payments/failures', { params: filters });
    return response.data;
  },

  // Quota monitoring
  getQuotaMetrics: async (filters: MonitoringFilters): Promise<any> => {
    const response = await api.get('/monitoring/quotas', { params: filters });
    return response.data;
  },

  getQuotaBreaches: async (filters: any): Promise<any> => {
    const response = await api.get('/monitoring/quotas/breaches', { params: filters });
    return response.data;
  },

  // Infrastructure monitoring
  getInfrastructureMetrics: async (filters: MonitoringFilters): Promise<any> => {
    const response = await api.get('/monitoring/infrastructure', { params: filters });
    return response.data;
  },

  // API monitoring
  getAPIMetrics: async (filters: MonitoringFilters): Promise<any> => {
    const response = await api.get('/monitoring/api', { params: filters });
    return response.data;
  },

  getAPIEndpointMetrics: async (endpoint: string, filters: MonitoringFilters): Promise<any> => {
    const response = await api.get(`/monitoring/api/endpoints/${encodeURIComponent(endpoint)}`, {
      params: filters
    });
    return response.data;
  }
};

// Utility functions
export const downloadMonitoringReport = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export const formatMonitoringDate = (date: Date): string => {
  return date.toISOString();
};

// Export default API object
export default monitoringApi;