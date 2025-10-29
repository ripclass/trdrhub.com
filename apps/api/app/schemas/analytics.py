"""
Analytics schemas for dashboard data models.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator


# Time range literals for analytics queries
TimeRange = Literal["7d", "30d", "90d", "180d", "365d", "custom"]
MetricType = Literal["jobs", "discrepancies", "processing_time", "user_activity"]


class DateRange(BaseModel):
    """Date range for analytics queries."""
    start_date: datetime
    end_date: datetime


class SummaryStats(BaseModel):
    """Summary statistics for jobs and processing."""
    total_jobs: int = Field(..., description="Total number of jobs submitted")
    success_count: int = Field(..., description="Number of successful jobs")
    rejection_count: int = Field(..., description="Number of rejected jobs")
    pending_count: int = Field(..., description="Number of pending jobs")
    rejection_rate: float = Field(..., description="Rejection rate as percentage")
    avg_processing_time_minutes: Optional[float] = Field(None, description="Average processing time in minutes")
    doc_distribution: Dict[str, int] = Field(..., description="Distribution by document types")

    # Time period for these stats
    time_range: str = Field(..., description="Time range for these statistics")
    start_date: datetime
    end_date: datetime


class DiscrepancyStats(BaseModel):
    """Discrepancy analysis statistics."""
    top_discrepancies: List[Dict[str, Any]] = Field(..., description="Top 10 discrepancy categories with counts")
    fatal_four_frequency: Dict[str, int] = Field(..., description="Frequency of critical discrepancy types")
    severity_distribution: Dict[str, int] = Field(..., description="Distribution by severity level")
    discrepancy_trends: List[Dict[str, Any]] = Field(..., description="Trend of discrepancies over time")

    # Summary metrics
    total_discrepancies: int = Field(..., description="Total number of discrepancies")
    avg_discrepancies_per_job: float = Field(..., description="Average discrepancies per job")

    time_range: str
    start_date: datetime
    end_date: datetime


class TrendPoint(BaseModel):
    """Single point in a trend timeline."""
    date: date
    jobs_submitted: int = 0
    jobs_completed: int = 0
    jobs_rejected: int = 0
    avg_processing_time: Optional[float] = None
    discrepancy_count: int = 0
    success_rate: float = 0.0


class TrendStats(BaseModel):
    """Trend analysis over time."""
    timeline: List[TrendPoint] = Field(..., description="Daily timeline of metrics")

    # Aggregate trends
    job_volume_trend: float = Field(..., description="Job volume trend (positive = increasing)")
    rejection_rate_trend: float = Field(..., description="Rejection rate trend (positive = worsening)")
    processing_time_trend: float = Field(..., description="Processing time trend (positive = slower)")

    time_range: str
    start_date: datetime
    end_date: datetime


class UserStats(BaseModel):
    """Statistics for individual users."""
    user_id: UUID
    user_email: str
    user_role: str

    # Job metrics
    total_jobs: int = 0
    successful_jobs: int = 0
    rejected_jobs: int = 0
    pending_jobs: int = 0
    rejection_rate: float = 0.0

    # Performance metrics
    avg_processing_time_minutes: Optional[float] = None
    avg_time_to_correction_hours: Optional[float] = None

    # Activity metrics
    most_active_day: Optional[str] = None
    most_active_hour: Optional[int] = None
    documents_uploaded: int = 0

    # Recent activity
    last_job_date: Optional[datetime] = None
    jobs_last_30_days: int = 0

    time_range: str
    start_date: datetime
    end_date: datetime


class SystemMetrics(BaseModel):
    """System-wide metrics (Bank/Admin view only)."""

    # Volume metrics
    total_system_jobs: int = Field(..., description="Total jobs across all users")
    total_active_users: int = Field(..., description="Number of active users in period")
    jobs_per_user_avg: float = Field(..., description="Average jobs per user")

    # Performance metrics
    system_rejection_rate: float = Field(..., description="System-wide rejection rate")
    avg_system_processing_time: Optional[float] = Field(None, description="Average processing time across all jobs")

    # Usage patterns
    usage_by_role: Dict[str, int] = Field(..., description="Job count by user role")
    peak_hours: List[Dict[str, Any]] = Field(..., description="Peak usage hours")
    peak_days: List[Dict[str, Any]] = Field(..., description="Peak usage days")

    # Document insights
    most_common_document_types: List[Dict[str, Any]] = Field(..., description="Most processed document types")
    document_processing_success_rates: Dict[str, float] = Field(..., description="Success rate by document type")

    time_range: str
    start_date: datetime
    end_date: datetime


class DiscrepancyDetail(BaseModel):
    """Detailed discrepancy information."""
    discrepancy_type: str
    severity: str
    rule_name: str
    field_name: Optional[str] = None
    description: str
    frequency: int = Field(..., description="How often this discrepancy occurs")
    avg_correction_time_hours: Optional[float] = None
    source_documents: List[str] = Field(default_factory=list)


class ProcessingTimeBreakdown(BaseModel):
    """Breakdown of processing times by stage."""

    # Processing stages
    avg_upload_time_seconds: Optional[float] = None
    avg_ocr_time_seconds: Optional[float] = None
    avg_validation_time_seconds: Optional[float] = None
    avg_total_time_seconds: Optional[float] = None

    # Distribution
    time_percentiles: Dict[str, float] = Field(..., description="Processing time percentiles (p50, p90, p95, p99)")

    # By document type
    by_document_type: Dict[str, float] = Field(..., description="Average processing time by document type")


class AnalyticsQuery(BaseModel):
    """Query parameters for analytics endpoints."""
    time_range: TimeRange = "30d"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[UUID] = None
    document_type: Optional[str] = None
    include_trends: bool = True
    include_discrepancies: bool = True

    @validator('time_range')
    def validate_time_range(cls, v, values):
        """Validate time range parameters."""
        if v == "custom" and ('start_date' not in values or 'end_date' not in values):
            raise ValueError("start_date and end_date required for custom time range")
        return v


class ComplianceReport(BaseModel):
    """Compliance-focused report for banks and auditors."""

    # Compliance metrics
    total_transactions_processed: int
    compliance_rate: float = Field(..., description="Percentage of transactions processed without fatal errors")
    fatal_error_rate: float = Field(..., description="Percentage with fatal discrepancies")

    # Risk indicators
    high_risk_patterns: List[Dict[str, Any]] = Field(..., description="Patterns indicating potential compliance issues")
    user_risk_scores: List[Dict[str, Any]] = Field(..., description="Risk assessment by user")

    # Audit trail summary
    audit_trail_completeness: float = Field(..., description="Percentage of actions with complete audit trails")
    data_integrity_score: float = Field(..., description="File integrity verification score")

    # Regulatory insights
    processing_time_compliance: Dict[str, bool] = Field(..., description="Meeting regulatory processing time requirements")
    documentation_completeness: Dict[str, float] = Field(..., description="Document completeness rates by type")

    report_generated_at: datetime
    report_period: DateRange
    generated_by: UUID


class AnalyticsDashboard(BaseModel):
    """Complete dashboard data for frontend."""

    summary: SummaryStats
    trends: TrendStats
    discrepancies: DiscrepancyStats
    processing_times: ProcessingTimeBreakdown

    # Role-specific data
    user_stats: Optional[UserStats] = None  # For individual users
    system_metrics: Optional[SystemMetrics] = None  # For bank/admin
    compliance_report: Optional[ComplianceReport] = None  # For bank/admin

    # Metadata
    generated_at: datetime
    user_role: str
    data_scope: str = Field(..., description="Scope of data (own, system-wide)")


class AnalyticsExport(BaseModel):
    """Export configuration for analytics data."""
    export_type: Literal["csv", "pdf", "json"] = "csv"
    include_sections: List[str] = Field(default_factory=lambda: ["summary", "trends", "discrepancies"])
    date_format: str = "%Y-%m-%d"
    timezone: str = "UTC"

    # Export metadata
    export_requested_by: UUID
    export_requested_at: datetime = Field(default_factory=datetime.utcnow)


class AnomalyAlert(BaseModel):
    """Anomaly detection alert."""
    alert_type: Literal["rejection_spike", "processing_delay", "volume_anomaly", "user_behavior"]
    severity: Literal["low", "medium", "high", "critical"]

    message: str
    details: Dict[str, Any]

    # Metrics
    current_value: float
    expected_value: float
    threshold: float
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in anomaly detection")

    # Context
    affected_users: List[UUID] = Field(default_factory=list)
    time_window: DateRange

    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics for the analytics system itself."""

    # Query performance
    avg_query_time_ms: float
    slowest_queries: List[Dict[str, Any]]
    cache_hit_rate: float = 0.0

    # Data freshness
    last_updated: datetime
    update_frequency_minutes: int
    data_lag_minutes: float = 0.0

    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Errors
    error_rate: float = 0.0
    last_error: Optional[str] = None