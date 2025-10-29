export type Role = "exporter" | "importer" | "bank" | "admin";

export type TimeRange = "7d" | "30d" | "90d" | "180d" | "365d" | "custom";

export interface DateRange {
  from: Date;
  to: Date;
}

export interface SummaryStats {
  total_jobs: number;
  success_count: number;
  rejection_count: number;
  pending_count: number;
  rejection_rate: number;
  avg_processing_time_minutes: number | null;
  doc_distribution: Record<string, number>;
  time_range: string;
  start_date: string;
  end_date: string;
}

export interface DiscrepancyItem {
  type: string;
  rule: string;
  count: number;
  percentage: number;
}

export interface DiscrepancyStats {
  top_discrepancies: DiscrepancyItem[];
  fatal_four_frequency: Record<string, number>;
  severity_distribution: Record<string, number>;
  discrepancy_trends: Array<{
    date: string;
    count: number;
  }>;
  total_discrepancies: number;
  avg_discrepancies_per_job: number;
  time_range: string;
  start_date: string;
  end_date: string;
}

export interface TrendPoint {
  date: string;
  jobs_submitted: number;
  jobs_completed: number;
  jobs_rejected: number;
  avg_processing_time: number | null;
  discrepancy_count: number;
  success_rate: number;
}

export interface TrendStats {
  timeline: TrendPoint[];
  job_volume_trend: number;
  rejection_rate_trend: number;
  processing_time_trend: number;
  time_range: string;
  start_date: string;
  end_date: string;
}

export interface ProcessingTimeBreakdown {
  avg_upload_time_seconds?: number | null;
  avg_ocr_time_seconds?: number | null;
  avg_validation_time_seconds?: number | null;
  avg_total_time_seconds?: number | null;
  time_percentiles: {
    p50: number;
    p90: number;
    p95: number;
    p99: number;
  };
  by_document_type: Record<string, number>;
}

export interface UserStats {
  user_id: string;
  user_email: string;
  user_role: string;
  total_jobs: number;
  successful_jobs: number;
  rejected_jobs: number;
  pending_jobs: number;
  rejection_rate: number;
  avg_processing_time_minutes: number | null;
  avg_time_to_correction_hours: number | null;
  most_active_day: string | null;
  most_active_hour: number | null;
  documents_uploaded: number;
  last_job_date: string | null;
  jobs_last_30_days: number;
  time_range: string;
  start_date: string;
  end_date: string;
}

export interface SystemMetrics {
  total_system_jobs: number;
  total_active_users: number;
  jobs_per_user_avg: number;
  system_rejection_rate: number;
  avg_system_processing_time: number | null;
  usage_by_role: Record<string, number>;
  peak_hours: Array<{
    hour: number;
    job_count: number;
  }>;
  peak_days: Array<{
    day: string;
    job_count: number;
  }>;
  most_common_document_types: Array<{
    document_type: string;
    count: number;
  }>;
  document_processing_success_rates: Record<string, number>;
  time_range: string;
  start_date: string;
  end_date: string;
}

export interface AnalyticsDashboard {
  summary: SummaryStats;
  trends: TrendStats | null;
  discrepancies: DiscrepancyStats | null;
  processing_times: ProcessingTimeBreakdown;
  user_stats: UserStats | null;
  system_metrics: SystemMetrics | null;
  generated_at: string;
  user_role: Role;
  data_scope: string;
}

export interface AnomalyAlert {
  alert_type: "rejection_spike" | "processing_delay" | "volume_anomaly" | "user_behavior";
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  details: Record<string, any>;
  current_value: number;
  expected_value: number;
  threshold: number;
  confidence: number;
  time_window: {
    start_date: string;
    end_date: string;
  };
  detected_at: string;
  resolved_at: string | null;
}

export interface AnalyticsFilters {
  timeRange: TimeRange;
  startDate?: Date;
  endDate?: Date;
  documentType?: string;
  outcome?: "all" | "success" | "rejected" | "pending";
}

export interface AnalyticsQueryParams {
  time_range?: TimeRange;
  start_date?: string;
  end_date?: string;
  include_trends?: boolean;
  include_discrepancies?: boolean;
}

// Chart data types
export interface ChartDataPoint {
  date: string;
  [key: string]: string | number;
}

export interface HeatmapDataPoint {
  day: string;
  hour: number;
  value: number;
}

export interface BarChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

// API response types
export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  error: string;
  message: string;
  timestamp: string;
  path: string;
  method: string;
}

// Component prop types
export interface ChartProps {
  data: ChartDataPoint[];
  height?: number;
  className?: string;
}

export interface KpiCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeType?: "increase" | "decrease";
  description?: string;
  icon?: React.ReactNode;
  className?: string;
}

export interface FilterProps {
  filters: AnalyticsFilters;
  onFiltersChange: (filters: AnalyticsFilters) => void;
  className?: string;
}

// Store types
export interface AnalyticsStore {
  filters: AnalyticsFilters;
  role: Role | null;
  setFilters: (filters: AnalyticsFilters) => void;
  setRole: (role: Role) => void;
  resetFilters: () => void;
}