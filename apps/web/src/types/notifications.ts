/**
 * TypeScript types for notifications system
 */

// Notification types
export enum NotificationType {
  EMAIL = 'EMAIL',
  SLACK = 'SLACK',
  SMS = 'SMS',
  WEBHOOK = 'WEBHOOK',
  IN_APP = 'IN_APP'
}

export enum NotificationStatus {
  PENDING = 'PENDING',
  SENT = 'SENT',
  DELIVERED = 'DELIVERED',
  FAILED = 'FAILED',
  RETRYING = 'RETRYING'
}

export enum NotificationPriority {
  LOW = 'LOW',
  NORMAL = 'NORMAL',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum NotificationTrigger {
  ALERT_CREATED = 'ALERT_CREATED',
  QUOTA_BREACH = 'QUOTA_BREACH',
  PAYMENT_FAILED = 'PAYMENT_FAILED',
  WEBHOOK_ERROR = 'WEBHOOK_ERROR',
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  MAINTENANCE = 'MAINTENANCE',
  CUSTOM = 'CUSTOM'
}

// Core notification interfaces
export interface Notification {
  id: string;
  type: NotificationType;
  status: NotificationStatus;
  priority: NotificationPriority;
  trigger: NotificationTrigger;
  title: string;
  message: string;
  recipient: string;
  metadata?: Record<string, any>;
  created_at: string;
  sent_at?: string;
  delivered_at?: string;
  failed_at?: string;
  retry_count: number;
  max_retries: number;
  error_message?: string;
  company_id?: string;
  user_id?: string;
  alert_id?: string;
}

export interface NotificationList {
  notifications: Notification[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Channel configuration
export interface NotificationChannel {
  id: string;
  name: string;
  type: NotificationType;
  enabled: boolean;
  configuration: ChannelConfiguration;
  triggers: NotificationTrigger[];
  priority_filter: NotificationPriority[];
  recipients: string[];
  rate_limit?: RateLimit;
  created_at: string;
  updated_at: string;
}

export interface ChannelConfiguration {
  // Email configuration
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  from_email?: string;
  from_name?: string;
  use_tls?: boolean;

  // Slack configuration
  webhook_url?: string;
  channel?: string;
  username?: string;
  icon_emoji?: string;
  icon_url?: string;

  // SMS configuration
  provider?: string;
  api_key?: string;
  from_number?: string;

  // Webhook configuration
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  auth_type?: 'none' | 'basic' | 'bearer' | 'api_key';
  auth_config?: Record<string, string>;

  // Common settings
  template?: string;
  timeout?: number;
  verify_ssl?: boolean;
}

export interface RateLimit {
  max_notifications: number;
  time_window: number; // in seconds
  burst_limit?: number;
}

// Templates
export interface NotificationTemplate {
  id: string;
  name: string;
  type: NotificationType;
  trigger: NotificationTrigger;
  subject_template: string;
  body_template: string;
  variables: TemplateVariable[];
  created_at: string;
  updated_at: string;
}

export interface TemplateVariable {
  name: string;
  description: string;
  required: boolean;
  default_value?: string;
}

// Delivery rules
export interface DeliveryRule {
  id: string;
  name: string;
  enabled: boolean;
  conditions: RuleCondition[];
  actions: RuleAction[];
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface RuleCondition {
  field: string;
  operator: 'equals' | 'contains' | 'greater_than' | 'less_than' | 'in' | 'not_in';
  value: any;
}

export interface RuleAction {
  type: 'send_notification' | 'escalate' | 'suppress' | 'route';
  channel_id?: string;
  delay?: number; // in seconds
  escalation_level?: number;
  recipients?: string[];
}

// Statistics and analytics
export interface NotificationStats {
  total_sent: number;
  total_delivered: number;
  total_failed: number;
  delivery_rate: number;
  avg_delivery_time: number;
  by_type: Record<NotificationType, number>;
  by_status: Record<NotificationStatus, number>;
  by_trigger: Record<NotificationTrigger, number>;
  recent_activity: NotificationActivity[];
}

export interface NotificationActivity {
  timestamp: string;
  type: NotificationType;
  status: NotificationStatus;
  count: number;
}

// Settings and preferences
export interface NotificationSettings {
  enabled: boolean;
  default_channels: string[];
  escalation_timeout: number; // in minutes
  max_retries: number;
  retry_intervals: number[]; // in seconds
  quiet_hours: QuietHours;
  global_rate_limit: RateLimit;
  maintenance_mode: boolean;
}

export interface QuietHours {
  enabled: boolean;
  start_time: string; // HH:MM format
  end_time: string; // HH:MM format
  timezone: string;
  emergency_override: boolean;
}

// API request/response types
export interface CreateNotificationRequest {
  type: NotificationType;
  priority: NotificationPriority;
  trigger: NotificationTrigger;
  title: string;
  message: string;
  recipients: string[];
  channel_ids?: string[];
  metadata?: Record<string, any>;
  scheduled_at?: string;
}

export interface CreateChannelRequest {
  name: string;
  type: NotificationType;
  configuration: ChannelConfiguration;
  triggers?: NotificationTrigger[];
  priority_filter?: NotificationPriority[];
  recipients?: string[];
  rate_limit?: RateLimit;
}

export interface UpdateChannelRequest extends Partial<CreateChannelRequest> {
  id: string;
}

export interface TestChannelRequest {
  channel_id: string;
  message?: string;
  recipients?: string[];
}

export interface NotificationFilters {
  type?: NotificationType;
  status?: NotificationStatus;
  priority?: NotificationPriority;
  trigger?: NotificationTrigger;
  recipient?: string;
  company_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

export interface BulkNotificationRequest {
  notifications: CreateNotificationRequest[];
  batch_size?: number;
  delay_between_batches?: number; // in seconds
}

// Webhook payload for notifications
export interface NotificationWebhookPayload {
  notification_id: string;
  type: NotificationType;
  status: NotificationStatus;
  trigger: NotificationTrigger;
  title: string;
  message: string;
  recipient: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// Integration-specific types
export interface SlackAttachment {
  fallback: string;
  color: string;
  title?: string;
  title_link?: string;
  text?: string;
  fields?: SlackField[];
  footer?: string;
  footer_icon?: string;
  ts?: number;
}

export interface SlackField {
  title: string;
  value: string;
  short?: boolean;
}

export interface EmailContent {
  subject: string;
  html_body?: string;
  text_body?: string;
  attachments?: EmailAttachment[];
}

export interface EmailAttachment {
  filename: string;
  content: string; // base64 encoded
  content_type: string;
}

// Utility functions
export function getNotificationStatusColor(status: NotificationStatus): string {
  switch (status) {
    case NotificationStatus.SENT:
    case NotificationStatus.DELIVERED:
      return 'bg-green-100 text-green-800 border-green-200';
    case NotificationStatus.PENDING:
    case NotificationStatus.RETRYING:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case NotificationStatus.FAILED:
      return 'bg-red-100 text-red-800 border-red-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getNotificationPriorityColor(priority: NotificationPriority): string {
  switch (priority) {
    case NotificationPriority.CRITICAL:
      return 'bg-red-100 text-red-800 border-red-200';
    case NotificationPriority.HIGH:
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case NotificationPriority.NORMAL:
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case NotificationPriority.LOW:
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getNotificationTypeIcon(type: NotificationType): string {
  switch (type) {
    case NotificationType.EMAIL: return '📧';
    case NotificationType.SLACK: return '💬';
    case NotificationType.SMS: return '📱';
    case NotificationType.WEBHOOK: return '🔗';
    case NotificationType.IN_APP: return '🔔';
    default: return '📄';
  }
}

export function formatNotificationTrigger(trigger: NotificationTrigger): string {
  switch (trigger) {
    case NotificationTrigger.ALERT_CREATED: return 'Alert Created';
    case NotificationTrigger.QUOTA_BREACH: return 'Quota Breach';
    case NotificationTrigger.PAYMENT_FAILED: return 'Payment Failed';
    case NotificationTrigger.WEBHOOK_ERROR: return 'Webhook Error';
    case NotificationTrigger.SYSTEM_ERROR: return 'System Error';
    case NotificationTrigger.MAINTENANCE: return 'Maintenance';
    case NotificationTrigger.CUSTOM: return 'Custom';
    default: return trigger;
  }
}

export function calculateDeliveryRate(notifications: Notification[]): number {
  if (notifications.length === 0) return 0;

  const delivered = notifications.filter(n =>
    n.status === NotificationStatus.DELIVERED ||
    n.status === NotificationStatus.SENT
  ).length;

  return (delivered / notifications.length) * 100;
}

export function getAverageDeliveryTime(notifications: Notification[]): number {
  const deliveredNotifications = notifications.filter(n =>
    n.sent_at && n.delivered_at
  );

  if (deliveredNotifications.length === 0) return 0;

  const totalTime = deliveredNotifications.reduce((sum, n) => {
    const sentTime = new Date(n.sent_at!).getTime();
    const deliveredTime = new Date(n.delivered_at!).getTime();
    return sum + (deliveredTime - sentTime);
  }, 0);

  return totalTime / deliveredNotifications.length / 1000; // return in seconds
}

export function shouldRetryNotification(notification: Notification): boolean {
  return notification.status === NotificationStatus.FAILED &&
         notification.retry_count < notification.max_retries;
}

export function getNextRetryTime(notification: Notification, retryIntervals: number[]): Date {
  const retryIndex = Math.min(notification.retry_count, retryIntervals.length - 1);
  const retryDelay = retryIntervals[retryIndex] * 1000; // convert to milliseconds

  const lastAttempt = notification.failed_at || notification.created_at;
  return new Date(new Date(lastAttempt).getTime() + retryDelay);
}

export function isInQuietHours(quietHours: QuietHours): boolean {
  if (!quietHours.enabled) return false;

  const now = new Date();
  const currentTime = now.toLocaleTimeString('en-GB', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit'
  });

  return currentTime >= quietHours.start_time && currentTime <= quietHours.end_time;
}

export function validateSlackWebhookUrl(url: string): boolean {
  const slackWebhookPattern = /^https:\/\/hooks\.slack\.com\/services\/[A-Z0-9]+\/[A-Z0-9]+\/[a-zA-Z0-9]+$/;
  return slackWebhookPattern.test(url);
}

export function validateEmailAddress(email: string): boolean {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailPattern.test(email);
}

export function sanitizeSlackMessage(message: string): string {
  // Escape special Slack characters
  return message
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}