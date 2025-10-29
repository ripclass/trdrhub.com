/**
 * TypeScript types for monitoring system
 */

// System KPIs
export interface SystemKPIs {
  payment_success_rate: number;
  webhook_error_rate: number;
  quota_breach_count: number;
  avg_response_time: number;
  system_uptime: number;
  active_sessions: number;
  failed_payments_24h: number;
  api_calls_per_minute: number;
  timestamp: string;
}

// Alert types
export enum AlertType {
  QUOTA_BREACH = 'QUOTA_BREACH',
  PAYMENT_FAILURE = 'PAYMENT_FAILURE',
  WEBHOOK_ERROR = 'WEBHOOK_ERROR',
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  PERFORMANCE_DEGRADATION = 'PERFORMANCE_DEGRADATION',
  HIGH_USAGE = 'HIGH_USAGE',
  ANOMALY_DETECTED = 'ANOMALY_DETECTED'
}

export enum AlertSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum AlertStatus {
  UNACKNOWLEDGED = 'UNACKNOWLEDGED',
  ACKNOWLEDGED = 'ACKNOWLEDGED',
  RESOLVED = 'RESOLVED',
  DISMISSED = 'DISMISSED'
}

export interface SystemAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  description?: string;
  timestamp: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  metadata?: Record<string, any>;
  company_id?: string;
  user_id?: string;
  session_id?: string;
}

export interface AlertList {
  alerts: SystemAlert[];
  total: number;
  unacknowledged_count: number;
  critical_count: number;
}

// Anomaly detection
export interface AnomalyData {
  timestamp: string;
  quota_breaches: number;
  payment_failures: number;
  response_time: number;
  usage_spike: number;
  webhook_errors: number;
  api_errors: number;
}

export interface AnomalyThresholds {
  quota_breach_threshold: number;
  payment_failure_threshold: number;
  response_time_threshold: number;
  usage_spike_threshold: number;
  webhook_error_threshold: number;
}

// Performance metrics
export interface PerformanceMetrics {
  timestamp: string;
  response_time_p50: number;
  response_time_p95: number;
  response_time_p99: number;
  throughput: number;
  error_rate: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
}

// System health
export interface SystemHealth {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  services: ServiceHealth[];
  last_updated: string;
}

export interface ServiceHealth {
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  response_time?: number;
  error_rate?: number;
  last_check: string;
  message?: string;
}

// Monitoring filters
export interface MonitoringFilters {
  time_range?: '1h' | '6h' | '24h' | '7d' | '30d';
  start_date?: string;
  end_date?: string;
}

export interface AlertFilters {
  status?: AlertStatus;
  severity?: AlertSeverity;
  type?: AlertType;
  company_id?: string;
  limit?: number;
  offset?: number;
  start_date?: string;
  end_date?: string;
}

// API request/response types
export interface AcknowledgeAlertRequest {
  alertId: string;
  message?: string;
}

export interface ResolveAlertRequest {
  alertId: string;
  resolution?: string;
}

export interface ExportMonitoringRequest {
  time_range: string;
  include_alerts?: boolean;
  include_kpis?: boolean;
  include_anomalies?: boolean;
  format?: 'csv' | 'xlsx' | 'pdf';
}

// Chart data types
export interface KPITrendData {
  timestamp: string;
  payment_success_rate: number;
  webhook_error_rate: number;
  avg_response_time: number;
  active_sessions: number;
}

export interface AlertSummaryData {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
}

// Notification settings for monitoring
export interface MonitoringNotificationSettings {
  email_alerts: boolean;
  slack_alerts: boolean;
  sms_alerts: boolean;
  alert_threshold: AlertSeverity;
  escalation_timeout: number; // minutes
  notification_channels: NotificationChannel[];
}

export interface NotificationChannel {
  id: string;
  type: 'email' | 'slack' | 'sms' | 'webhook';
  destination: string;
  enabled: boolean;
  alert_types: AlertType[];
  severity_filter: AlertSeverity[];
}

// Dashboard widgets
export interface MonitoringWidget {
  id: string;
  type: 'kpi_card' | 'chart' | 'alert_list' | 'service_status';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config: Record<string, any>;
  visible: boolean;
}

export interface MonitoringDashboard {
  id: string;
  name: string;
  description?: string;
  widgets: MonitoringWidget[];
  created_at: string;
  updated_at: string;
  is_default: boolean;
}

// Utility functions
export function getAlertSeverityColor(severity: AlertSeverity): string {
  switch (severity) {
    case AlertSeverity.CRITICAL:
      return 'bg-red-100 text-red-800 border-red-200';
    case AlertSeverity.HIGH:
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case AlertSeverity.MEDIUM:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case AlertSeverity.LOW:
      return 'bg-blue-100 text-blue-800 border-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getAlertStatusColor(status: AlertStatus): string {
  switch (status) {
    case AlertStatus.UNACKNOWLEDGED:
      return 'bg-red-100 text-red-800 border-red-200';
    case AlertStatus.ACKNOWLEDGED:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case AlertStatus.RESOLVED:
      return 'bg-green-100 text-green-800 border-green-200';
    case AlertStatus.DISMISSED:
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getServiceStatusIcon(status: 'HEALTHY' | 'DEGRADED' | 'DOWN'): string {
  switch (status) {
    case 'HEALTHY': return '🟢';
    case 'DEGRADED': return '🟡';
    case 'DOWN': return '🔴';
    default: return '⚪';
  }
}

export function formatAlertType(type: AlertType): string {
  switch (type) {
    case AlertType.QUOTA_BREACH: return 'Quota Breach';
    case AlertType.PAYMENT_FAILURE: return 'Payment Failure';
    case AlertType.WEBHOOK_ERROR: return 'Webhook Error';
    case AlertType.SYSTEM_ERROR: return 'System Error';
    case AlertType.PERFORMANCE_DEGRADATION: return 'Performance Issue';
    case AlertType.HIGH_USAGE: return 'High Usage';
    case AlertType.ANOMALY_DETECTED: return 'Anomaly Detected';
    default: return type;
  }
}

export function isAlertCritical(alert: SystemAlert): boolean {
  return alert.severity === AlertSeverity.CRITICAL ||
         (alert.severity === AlertSeverity.HIGH &&
          alert.type === AlertType.SYSTEM_ERROR);
}

export function getAlertAge(timestamp: string): string {
  const now = new Date();
  const alertTime = new Date(timestamp);
  const diffMs = now.getTime() - alertTime.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays}d ago`;
  } else if (diffHours > 0) {
    return `${diffHours}h ago`;
  } else if (diffMinutes > 0) {
    return `${diffMinutes}m ago`;
  } else {
    return 'Just now';
  }
}

export function shouldEscalateAlert(alert: SystemAlert, escalationTimeoutMinutes: number): boolean {
  if (alert.status !== AlertStatus.UNACKNOWLEDGED) {
    return false;
  }

  const alertTime = new Date(alert.timestamp);
  const now = new Date();
  const diffMinutes = (now.getTime() - alertTime.getTime()) / (1000 * 60);

  return diffMinutes >= escalationTimeoutMinutes;
}