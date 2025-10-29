/**
 * Notifications API client functions
 */

import { api } from './client';
import type {
  NotificationChannel,
  Notification,
  NotificationList,
  NotificationStats,
  NotificationSettings,
  NotificationTemplate,
  DeliveryRule,
  NotificationFilters,
  CreateChannelRequest,
  UpdateChannelRequest,
  TestChannelRequest,
  CreateNotificationRequest,
  BulkNotificationRequest
} from '../types/notifications';

// Notifications API endpoints
export const notificationsApi = {
  // Channel management
  getNotificationChannels: async (): Promise<NotificationChannel[]> => {
    const response = await api.get('/notifications/channels');
    return response.data;
  },

  getNotificationChannel: async (channelId: string): Promise<NotificationChannel> => {
    const response = await api.get(`/notifications/channels/${channelId}`);
    return response.data;
  },

  createNotificationChannel: async (request: CreateChannelRequest): Promise<NotificationChannel> => {
    const response = await api.post('/notifications/channels', request);
    return response.data;
  },

  updateNotificationChannel: async (request: UpdateChannelRequest): Promise<NotificationChannel> => {
    const response = await api.put(`/notifications/channels/${request.id}`, request);
    return response.data;
  },

  deleteNotificationChannel: async (channelId: string): Promise<void> => {
    await api.delete(`/notifications/channels/${channelId}`);
  },

  testNotificationChannel: async (request: TestChannelRequest): Promise<void> => {
    await api.post(`/notifications/channels/${request.channel_id}/test`, {
      message: request.message,
      recipients: request.recipients
    });
  },

  // Notification history and management
  getNotificationHistory: async (filters: NotificationFilters = {}): Promise<NotificationList> => {
    const response = await api.get('/notifications/history', { params: filters });
    return response.data;
  },

  getNotification: async (notificationId: string): Promise<Notification> => {
    const response = await api.get(`/notifications/${notificationId}`);
    return response.data;
  },

  sendNotification: async (request: CreateNotificationRequest): Promise<Notification> => {
    const response = await api.post('/notifications/send', request);
    return response.data;
  },

  sendBulkNotifications: async (request: BulkNotificationRequest): Promise<void> => {
    await api.post('/notifications/send-bulk', request);
  },

  sendTestNotification: async (data: { recipient: string; message: string; type?: string }): Promise<void> => {
    await api.post('/notifications/test', data);
  },

  retryNotification: async (notificationId: string): Promise<Notification> => {
    const response = await api.post(`/notifications/${notificationId}/retry`);
    return response.data;
  },

  cancelNotification: async (notificationId: string): Promise<Notification> => {
    const response = await api.post(`/notifications/${notificationId}/cancel`);
    return response.data;
  },

  // Statistics and analytics
  getNotificationStats: async (timeRange: string): Promise<NotificationStats> => {
    const response = await api.get('/notifications/stats', {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  getNotificationAnalytics: async (timeRange: string): Promise<any> => {
    const response = await api.get('/notifications/analytics', {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  getChannelPerformance: async (channelId: string, timeRange: string): Promise<any> => {
    const response = await api.get(`/notifications/channels/${channelId}/performance`, {
      params: { time_range: timeRange }
    });
    return response.data;
  },

  // Settings and configuration
  getNotificationSettings: async (): Promise<NotificationSettings> => {
    const response = await api.get('/notifications/settings');
    return response.data;
  },

  updateNotificationSettings: async (settings: NotificationSettings): Promise<NotificationSettings> => {
    const response = await api.put('/notifications/settings', settings);
    return response.data;
  },

  // Templates
  getNotificationTemplates: async (): Promise<NotificationTemplate[]> => {
    const response = await api.get('/notifications/templates');
    return response.data;
  },

  getNotificationTemplate: async (templateId: string): Promise<NotificationTemplate> => {
    const response = await api.get(`/notifications/templates/${templateId}`);
    return response.data;
  },

  createNotificationTemplate: async (template: Partial<NotificationTemplate>): Promise<NotificationTemplate> => {
    const response = await api.post('/notifications/templates', template);
    return response.data;
  },

  updateNotificationTemplate: async (template: NotificationTemplate): Promise<NotificationTemplate> => {
    const response = await api.put(`/notifications/templates/${template.id}`, template);
    return response.data;
  },

  deleteNotificationTemplate: async (templateId: string): Promise<void> => {
    await api.delete(`/notifications/templates/${templateId}`);
  },

  // Delivery rules
  getDeliveryRules: async (): Promise<DeliveryRule[]> => {
    const response = await api.get('/notifications/delivery-rules');
    return response.data;
  },

  getDeliveryRule: async (ruleId: string): Promise<DeliveryRule> => {
    const response = await api.get(`/notifications/delivery-rules/${ruleId}`);
    return response.data;
  },

  createDeliveryRule: async (rule: Partial<DeliveryRule>): Promise<DeliveryRule> => {
    const response = await api.post('/notifications/delivery-rules', rule);
    return response.data;
  },

  updateDeliveryRule: async (rule: DeliveryRule): Promise<DeliveryRule> => {
    const response = await api.put(`/notifications/delivery-rules/${rule.id}`, rule);
    return response.data;
  },

  deleteDeliveryRule: async (ruleId: string): Promise<void> => {
    await api.delete(`/notifications/delivery-rules/${ruleId}`);
  },

  // Export functionality
  exportNotificationData: async (params: { time_range: string; format?: string }): Promise<Blob> => {
    const response = await api.get('/notifications/export', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // Audit and compliance
  getNotificationAuditLog: async (filters: any): Promise<any[]> => {
    const response = await api.get('/notifications/audit-log', { params: filters });
    return response.data;
  },

  exportNotificationAuditLog: async (params: { start_date: string; end_date: string; format?: string }): Promise<Blob> => {
    const response = await api.get('/notifications/audit-log/export', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // Integration-specific endpoints

  // Slack integration
  validateSlackWebhook: async (webhookUrl: string): Promise<{ valid: boolean; error?: string }> => {
    const response = await api.post('/notifications/integrations/slack/validate', {
      webhook_url: webhookUrl
    });
    return response.data;
  },

  getSlackChannels: async (webhookUrl: string): Promise<string[]> => {
    const response = await api.post('/notifications/integrations/slack/channels', {
      webhook_url: webhookUrl
    });
    return response.data;
  },

  // Email integration
  validateEmailConfiguration: async (config: any): Promise<{ valid: boolean; error?: string }> => {
    const response = await api.post('/notifications/integrations/email/validate', config);
    return response.data;
  },

  testEmailConfiguration: async (config: any, testRecipient: string): Promise<void> => {
    await api.post('/notifications/integrations/email/test', {
      ...config,
      test_recipient: testRecipient
    });
  },

  // SMS integration
  validateSMSConfiguration: async (config: any): Promise<{ valid: boolean; error?: string }> => {
    const response = await api.post('/notifications/integrations/sms/validate', config);
    return response.data;
  },

  testSMSConfiguration: async (config: any, testNumber: string): Promise<void> => {
    await api.post('/notifications/integrations/sms/test', {
      ...config,
      test_number: testNumber
    });
  },

  // Webhook integration
  validateWebhookConfiguration: async (config: any): Promise<{ valid: boolean; error?: string }> => {
    const response = await api.post('/notifications/integrations/webhook/validate', config);
    return response.data;
  },

  testWebhookConfiguration: async (config: any): Promise<void> => {
    await api.post('/notifications/integrations/webhook/test', config);
  },

  // Rate limiting and throttling
  getChannelRateLimits: async (channelId: string): Promise<any> => {
    const response = await api.get(`/notifications/channels/${channelId}/rate-limits`);
    return response.data;
  },

  updateChannelRateLimits: async (channelId: string, rateLimits: any): Promise<any> => {
    const response = await api.put(`/notifications/channels/${channelId}/rate-limits`, rateLimits);
    return response.data;
  },

  // Notification queue management
  getNotificationQueue: async (): Promise<any[]> => {
    const response = await api.get('/notifications/queue');
    return response.data;
  },

  clearNotificationQueue: async (): Promise<void> => {
    await api.delete('/notifications/queue');
  },

  pauseNotificationQueue: async (): Promise<void> => {
    await api.post('/notifications/queue/pause');
  },

  resumeNotificationQueue: async (): Promise<void> => {
    await api.post('/notifications/queue/resume');
  },

  // Maintenance mode
  enableMaintenanceMode: async (): Promise<void> => {
    await api.post('/notifications/maintenance/enable');
  },

  disableMaintenanceMode: async (): Promise<void> => {
    await api.post('/notifications/maintenance/disable');
  },

  getMaintenanceStatus: async (): Promise<{ enabled: boolean; message?: string }> => {
    const response = await api.get('/notifications/maintenance/status');
    return response.data;
  },

  // Health checks
  getNotificationSystemHealth: async (): Promise<any> => {
    const response = await api.get('/notifications/health');
    return response.data;
  },

  getChannelHealth: async (channelId: string): Promise<any> => {
    const response = await api.get(`/notifications/channels/${channelId}/health`);
    return response.data;
  },

  // Metrics for monitoring
  getNotificationMetrics: async (): Promise<any> => {
    const response = await api.get('/notifications/metrics');
    return response.data;
  },

  // Failover and disaster recovery
  triggerFailover: async (fromChannelId: string, toChannelId: string): Promise<void> => {
    await api.post('/notifications/failover', {
      from_channel_id: fromChannelId,
      to_channel_id: toChannelId
    });
  },

  getFailoverStatus: async (): Promise<any> => {
    const response = await api.get('/notifications/failover/status');
    return response.data;
  },

  // Scheduled notifications
  scheduleNotification: async (notification: CreateNotificationRequest & { scheduled_at: string }): Promise<any> => {
    const response = await api.post('/notifications/schedule', notification);
    return response.data;
  },

  getScheduledNotifications: async (): Promise<any[]> => {
    const response = await api.get('/notifications/scheduled');
    return response.data;
  },

  cancelScheduledNotification: async (scheduledId: string): Promise<void> => {
    await api.delete(`/notifications/scheduled/${scheduledId}`);
  },

  // Notification preferences (user-level)
  getUserNotificationPreferences: async (userId: string): Promise<any> => {
    const response = await api.get(`/notifications/users/${userId}/preferences`);
    return response.data;
  },

  updateUserNotificationPreferences: async (userId: string, preferences: any): Promise<any> => {
    const response = await api.put(`/notifications/users/${userId}/preferences`, preferences);
    return response.data;
  },

  // Company-level notification settings
  getCompanyNotificationSettings: async (companyId: string): Promise<any> => {
    const response = await api.get(`/notifications/companies/${companyId}/settings`);
    return response.data;
  },

  updateCompanyNotificationSettings: async (companyId: string, settings: any): Promise<any> => {
    const response = await api.put(`/notifications/companies/${companyId}/settings`, settings);
    return response.data;
  }
};

// Utility functions
export const downloadNotificationReport = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export const formatNotificationDate = (date: Date): string => {
  return date.toISOString();
};

// Validation helpers
export const validateNotificationChannel = (channel: CreateChannelRequest): string[] => {
  const errors: string[] = [];

  if (!channel.name?.trim()) {
    errors.push('Channel name is required');
  }

  if (!channel.type) {
    errors.push('Channel type is required');
  }

  switch (channel.type) {
    case 'SLACK':
      if (!channel.configuration?.webhook_url) {
        errors.push('Slack webhook URL is required');
      } else if (!channel.configuration.webhook_url.startsWith('https://hooks.slack.com/')) {
        errors.push('Invalid Slack webhook URL format');
      }
      break;

    case 'EMAIL':
      if (!channel.configuration?.from_email) {
        errors.push('From email address is required');
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(channel.configuration.from_email)) {
        errors.push('Invalid email address format');
      }
      break;

    case 'SMS':
      if (!channel.configuration?.api_key) {
        errors.push('SMS API key is required');
      }
      if (!channel.configuration?.from_number) {
        errors.push('SMS from number is required');
      }
      break;

    case 'WEBHOOK':
      if (!channel.configuration?.url) {
        errors.push('Webhook URL is required');
      } else if (!/^https?:\/\/.+/.test(channel.configuration.url)) {
        errors.push('Invalid webhook URL format');
      }
      break;
  }

  if (channel.recipients && channel.recipients.length > 0) {
    channel.recipients.forEach((recipient, index) => {
      if (channel.type === 'EMAIL' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)) {
        errors.push(`Invalid email address at position ${index + 1}: ${recipient}`);
      }
      if (channel.type === 'SMS' && !/^\+?[\d\s-()]+$/.test(recipient)) {
        errors.push(`Invalid phone number at position ${index + 1}: ${recipient}`);
      }
    });
  }

  return errors;
};

// Export default API object
export default notificationsApi;