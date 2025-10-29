import axios from 'axios';
import type {
  SummaryStats,
  DiscrepancyStats,
  TrendStats,
  UserStats,
  SystemMetrics,
  ProcessingTimeBreakdown,
  AnalyticsDashboard,
  AnomalyAlert,
  AnalyticsQueryParams,
  TimeRange
} from '@/types/analytics';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Add auth interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const analyticsApi = {
  // Summary statistics
  getSummary: async (params: AnalyticsQueryParams = {}): Promise<SummaryStats> => {
    const { data } = await api.get('/analytics/summary', { params });
    return data;
  },

  // Discrepancy analysis
  getDiscrepancies: async (params: AnalyticsQueryParams = {}): Promise<DiscrepancyStats> => {
    const { data } = await api.get('/analytics/discrepancies', { params });
    return data;
  },

  // Trend analysis
  getTrends: async (params: AnalyticsQueryParams = {}): Promise<TrendStats> => {
    const { data } = await api.get('/analytics/trends', { params });
    return data;
  },

  // Processing time breakdown
  getProcessingTimes: async (params: AnalyticsQueryParams = {}): Promise<ProcessingTimeBreakdown> => {
    const { data } = await api.get('/analytics/processing-times', { params });
    return data;
  },

  // User statistics (Bank/Admin only)
  getUserStats: async (
    userId: string,
    params: AnalyticsQueryParams = {}
  ): Promise<UserStats> => {
    const { data } = await api.get(`/analytics/user/${userId}`, { params });
    return data;
  },

  // System metrics (Bank/Admin only)
  getSystemMetrics: async (params: AnalyticsQueryParams = {}): Promise<SystemMetrics> => {
    const { data } = await api.get('/analytics/system', { params });
    return data;
  },

  // Complete dashboard (single request)
  getDashboard: async (params: AnalyticsQueryParams = {}): Promise<AnalyticsDashboard> => {
    const { data } = await api.get('/analytics/dashboard', {
      params: {
        include_trends: true,
        include_discrepancies: true,
        ...params
      }
    });
    return data;
  },

  // Anomaly alerts (Bank/Admin only)
  getAnomalies: async (timeRange: TimeRange = '7d'): Promise<AnomalyAlert[]> => {
    const { data } = await api.get('/analytics/anomalies', {
      params: { time_range: timeRange }
    });
    return data;
  },

  // Export CSV
  exportCsv: async (params: AnalyticsQueryParams = {}): Promise<Blob> => {
    const response = await api.get('/analytics/export/csv', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // User list (Bank/Admin only) - alias for getUserStats for multiple users
  getUsers: async (params: AnalyticsQueryParams = {}): Promise<UserStats[]> => {
    const { data } = await api.get('/analytics/users', { params });
    return data;
  },

  // System metrics - alias for getSystemMetrics
  getSystem: async (params: AnalyticsQueryParams = {}): Promise<SystemMetrics> => {
    return analyticsApi.getSystemMetrics(params);
  },

  // User analytics - alias for getUserStats
  getUserAnalytics: async (userId: number, params: AnalyticsQueryParams = {}): Promise<UserStats> => {
    return analyticsApi.getUserStats(userId.toString(), params);
  },

  // Export PDF
  exportPdf: async (params: AnalyticsQueryParams = {}): Promise<Blob> => {
    const response = await api.get('/analytics/export/pdf', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // Analytics health (Admin only)
  getHealth: async () => {
    const { data } = await api.get('/analytics/health');
    return data;
  },
};

// Helper functions for data transformation
export const transformTrendsForChart = (trends: TrendStats) => {
  return trends.timeline.map(point => ({
    date: new Date(point.date).toLocaleDateString(),
    'Jobs Submitted': point.jobs_submitted,
    'Jobs Completed': point.jobs_completed,
    'Jobs Rejected': point.jobs_rejected,
    'Success Rate': point.success_rate,
    'Processing Time': point.avg_processing_time || 0,
  }));
};

export const transformDiscrepanciesForChart = (discrepancies: DiscrepancyStats) => {
  return discrepancies.top_discrepancies.slice(0, 10).map(item => ({
    name: item.rule.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: item.count,
    percentage: item.percentage,
  }));
};

export const transformProcessingTimesForChart = (processingTimes: ProcessingTimeBreakdown) => {
  return Object.entries(processingTimes.by_document_type).map(([docType, time]) => ({
    name: docType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: Math.round(time / 60), // Convert to minutes
    seconds: time,
  }));
};

export const transformPeakHoursForChart = (systemMetrics: SystemMetrics) => {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const peakData = systemMetrics.peak_hours.reduce((acc, peak) => {
    acc[peak.hour] = peak.job_count;
    return acc;
  }, {} as Record<number, number>);

  return hours.map(hour => ({
    hour: hour.toString().padStart(2, '0') + ':00',
    jobs: peakData[hour] || 0,
  }));
};

export const formatProcessingTime = (seconds: number | null): string => {
  if (!seconds) return 'N/A';

  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else if (seconds < 3600) {
    return `${Math.round(seconds / 60)}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }
};

export const formatPercentage = (value: number, decimals = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

export const formatNumber = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toString();
};

// Date helper functions
export const getDateRangeFromTimeRange = (timeRange: TimeRange): [Date, Date] => {
  const now = new Date();
  const end = new Date(now);

  let start: Date;
  switch (timeRange) {
    case '7d':
      start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      break;
    case '30d':
      start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      break;
    case '90d':
      start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      break;
    case '180d':
      start = new Date(now.getTime() - 180 * 24 * 60 * 60 * 1000);
      break;
    case '365d':
      start = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
      break;
    default:
      start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  }

  return [start, end];
};

export const formatDateForApi = (date: Date): string => {
  return date.toISOString();
};

// Error handling
export const isAnalyticsError = (error: any): boolean => {
  return error.response?.status === 403 || error.response?.status === 401;
};

export const getErrorMessage = (error: any): string => {
  if (error.response?.status === 403) {
    return 'You do not have permission to view this data';
  } else if (error.response?.status === 401) {
    return 'Please log in to view analytics';
  } else if (error.response?.data?.message) {
    return error.response.data.message;
  }
  return 'An error occurred while loading analytics data';
};