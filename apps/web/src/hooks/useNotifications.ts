/**
 * React Query hooks for notifications functionality
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notificationsApi } from '../api/notifications';
import type {
  NotificationFilters,
  CreateChannelRequest,
  UpdateChannelRequest,
  TestChannelRequest,
  CreateNotificationRequest,
  BulkNotificationRequest
} from '../types/notifications';

// Query keys
export const notificationsKeys = {
  all: ['notifications'] as const,
  channels: () => [...notificationsKeys.all, 'channels'] as const,
  channel: (id: string) => [...notificationsKeys.all, 'channel', id] as const,
  history: (filters: NotificationFilters) => [...notificationsKeys.all, 'history', filters] as const,
  stats: (timeRange: string) => [...notificationsKeys.all, 'stats', timeRange] as const,
  settings: () => [...notificationsKeys.all, 'settings'] as const,
  templates: () => [...notificationsKeys.all, 'templates'] as const,
  deliveryRules: () => [...notificationsKeys.all, 'delivery-rules'] as const,
};

// Notification channels
export const useNotificationChannels = (options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: notificationsKeys.channels(),
    queryFn: notificationsApi.getNotificationChannels,
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? true,
  });
};

export const useNotificationChannel = (channelId: string) => {
  return useQuery({
    queryKey: notificationsKeys.channel(channelId),
    queryFn: () => notificationsApi.getNotificationChannel(channelId),
    enabled: !!channelId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Notification history and stats
export const useNotificationHistory = (
  filters: NotificationFilters,
  options?: { enabled?: boolean }
) => {
  return useQuery({
    queryKey: notificationsKeys.history(filters),
    queryFn: () => notificationsApi.getNotificationHistory(filters),
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? true,
  });
};

export const useNotificationStats = (
  params: { time_range: string },
  options?: { enabled?: boolean }
) => {
  return useQuery({
    queryKey: notificationsKeys.stats(params.time_range),
    queryFn: () => notificationsApi.getNotificationStats(params.time_range),
    staleTime: 2 * 60 * 1000, // 2 minutes
    enabled: options?.enabled ?? true,
  });
};

// Settings and configuration
export const useNotificationSettings = () => {
  return useQuery({
    queryKey: notificationsKeys.settings(),
    queryFn: notificationsApi.getNotificationSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useNotificationTemplates = () => {
  return useQuery({
    queryKey: notificationsKeys.templates(),
    queryFn: notificationsApi.getNotificationTemplates,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

export const useDeliveryRules = () => {
  return useQuery({
    queryKey: notificationsKeys.deliveryRules(),
    queryFn: notificationsApi.getDeliveryRules,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Channel management mutations
export const useCreateNotificationChannel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateChannelRequest) =>
      notificationsApi.createNotificationChannel(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.channels() });
      toast.success('Notification channel created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create notification channel: ${error.message}`);
    },
  });
};

export const useUpdateNotificationChannel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateChannelRequest) =>
      notificationsApi.updateNotificationChannel(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.channels() });
      queryClient.invalidateQueries({ queryKey: notificationsKeys.channel(variables.id) });
      toast.success('Notification channel updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update notification channel: ${error.message}`);
    },
  });
};

export const useDeleteNotificationChannel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) =>
      notificationsApi.deleteNotificationChannel(channelId),
    onSuccess: (_, channelId) => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.channels() });
      queryClient.removeQueries({ queryKey: notificationsKeys.channel(channelId) });
      toast.success('Notification channel deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete notification channel: ${error.message}`);
    },
  });
};

export const useTestNotificationChannel = () => {
  return useMutation({
    mutationFn: (request: TestChannelRequest) =>
      notificationsApi.testNotificationChannel(request),
    onSuccess: () => {
      toast.success('Test notification sent successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to send test notification: ${error.message}`);
    },
  });
};

// Notification sending
export const useSendNotification = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateNotificationRequest) =>
      notificationsApi.sendNotification(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.history({}) });
      toast.success('Notification sent successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to send notification: ${error.message}`);
    },
  });
};

export const useSendBulkNotifications = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkNotificationRequest) =>
      notificationsApi.sendBulkNotifications(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.history({}) });
      toast.success(`${variables.notifications.length} notifications queued successfully`);
    },
    onError: (error: any) => {
      toast.error(`Failed to send bulk notifications: ${error.message}`);
    },
  });
};

export const useSendTestNotification = () => {
  return useMutation({
    mutationFn: (data: { recipient: string; message: string; type?: string }) =>
      notificationsApi.sendTestNotification(data),
    onSuccess: () => {
      toast.success('Test notification sent successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to send test notification: ${error.message}`);
    },
  });
};

// Notification actions
export const useRetryNotification = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) =>
      notificationsApi.retryNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.history({}) });
      toast.success('Notification retry initiated');
    },
    onError: (error: any) => {
      toast.error(`Failed to retry notification: ${error.message}`);
    },
  });
};

export const useCancelNotification = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) =>
      notificationsApi.cancelNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.history({}) });
      toast.success('Notification cancelled');
    },
    onError: (error: any) => {
      toast.error(`Failed to cancel notification: ${error.message}`);
    },
  });
};

// Settings management
export const useUpdateNotificationSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: notificationsApi.updateNotificationSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.settings() });
      toast.success('Notification settings updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update notification settings: ${error.message}`);
    },
  });
};

// Template management
export const useCreateNotificationTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: notificationsApi.createNotificationTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.templates() });
      toast.success('Notification template created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create notification template: ${error.message}`);
    },
  });
};

export const useUpdateNotificationTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: notificationsApi.updateNotificationTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.templates() });
      toast.success('Notification template updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update notification template: ${error.message}`);
    },
  });
};

export const useDeleteNotificationTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (templateId: string) =>
      notificationsApi.deleteNotificationTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.templates() });
      toast.success('Notification template deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete notification template: ${error.message}`);
    },
  });
};

// Delivery rules management
export const useCreateDeliveryRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: notificationsApi.createDeliveryRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.deliveryRules() });
      toast.success('Delivery rule created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create delivery rule: ${error.message}`);
    },
  });
};

export const useUpdateDeliveryRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: notificationsApi.updateDeliveryRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.deliveryRules() });
      toast.success('Delivery rule updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update delivery rule: ${error.message}`);
    },
  });
};

export const useDeleteDeliveryRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: string) =>
      notificationsApi.deleteDeliveryRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationsKeys.deliveryRules() });
      toast.success('Delivery rule deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete delivery rule: ${error.message}`);
    },
  });
};

// Export functionality
export const useExportNotificationData = () => {
  return useMutation({
    mutationFn: (params: { time_range: string; format?: string }) =>
      notificationsApi.exportNotificationData(params),
    onSuccess: (blob: Blob, variables) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const format = variables.format || 'xlsx';
      a.download = `notifications-export-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Notification data exported successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to export notification data: ${error.message}`);
    },
  });
};

// Utility hooks
export const useRefreshNotificationData = () => {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: notificationsKeys.all });
    toast.success('Notification data refreshed');
  };
};

// Real-time notifications hook
export const useRealTimeNotifications = (enabled: boolean = false) => {
  const queryClient = useQueryClient();

  // This would connect to a WebSocket for real-time updates
  // For now, we'll use polling
  useQuery({
    queryKey: ['notifications-realtime'],
    queryFn: async () => {
      // Refresh notification data
      queryClient.invalidateQueries({ queryKey: notificationsKeys.history({}) });
      queryClient.invalidateQueries({ queryKey: notificationsKeys.stats('1h') });
      return null;
    },
    refetchInterval: 15 * 1000, // 15 seconds
    enabled,
  });
};

// Notification analytics hooks
export const useNotificationAnalytics = (timeRange: string = '7d') => {
  return useQuery({
    queryKey: [...notificationsKeys.all, 'analytics', timeRange],
    queryFn: () => notificationsApi.getNotificationAnalytics(timeRange),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useChannelPerformance = (channelId: string, timeRange: string = '7d') => {
  return useQuery({
    queryKey: [...notificationsKeys.all, 'channel-performance', channelId, timeRange],
    queryFn: () => notificationsApi.getChannelPerformance(channelId, timeRange),
    enabled: !!channelId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Notification compliance and audit
export const useNotificationAuditLog = (filters: any) => {
  return useQuery({
    queryKey: [...notificationsKeys.all, 'audit-log', filters],
    queryFn: () => notificationsApi.getNotificationAuditLog(filters),
    staleTime: 60 * 1000, // 1 minute
  });
};

export const useExportNotificationAuditLog = () => {
  return useMutation({
    mutationFn: (params: { start_date: string; end_date: string; format?: string }) =>
      notificationsApi.exportNotificationAuditLog(params),
    onSuccess: (blob: Blob, variables) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const format = variables.format || 'xlsx';
      a.download = `notification-audit-${variables.start_date}-to-${variables.end_date}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('Notification audit log exported successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to export notification audit log: ${error.message}`);
    },
  });
};