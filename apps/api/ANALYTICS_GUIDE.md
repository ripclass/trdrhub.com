# LCopilot Analytics Dashboard Guide

This document provides a comprehensive guide to LCopilot's analytics dashboard system, which delivers meaningful insights about job processing, rejection rates, discrepancy patterns, and system usage across all user roles.

## Overview

The analytics dashboard provides role-based insights with the following key features:

- **Real-time Metrics**: Job success rates, processing times, and discrepancy analysis
- **Trend Analysis**: Historical patterns and performance trends over time
- **Role-Based Access**: Exporters/importers see their own data; banks/admins see system-wide data
- **Export Capabilities**: CSV export functionality for reporting
- **Performance Optimized**: Sub-500ms query performance with database indexing

## Architecture

### 🗄️ **Database Layer**
- **Performance Indexes**: Optimized indexes on `validation_sessions.status`, `audit_log.timestamp`, etc.
- **No Schema Changes**: Uses existing `jobs`, `audit_log`, `users` tables
- **Query Optimization**: Materialized views and strategic indexing for fast analytics

### 📊 **Analytics Service**
- **`AnalyticsService`**: Core service for computing all metrics
- **Role-Based Filtering**: Automatic data filtering based on user permissions
- **Time Range Support**: Flexible time ranges (7d, 30d, 90d, custom)
- **Caching Ready**: Structured for future Redis caching implementation

### 🔐 **RBAC Integration**
- **Exporter/Importer**: View only their own statistics and trends
- **Bank**: System-wide read access for compliance monitoring
- **Admin**: Full system access including user-specific drill-downs

## API Endpoints

### Authentication Required
All endpoints require valid JWT authentication with appropriate role permissions.

```bash
Authorization: Bearer <jwt_token>
```

### Core Analytics Endpoints

#### 1. Summary Statistics
```http
GET /analytics/summary?time_range=30d
```

**Parameters:**
- `time_range`: `7d` | `30d` | `90d` | `180d` | `365d` | `custom`
- `start_date`: ISO datetime (required if time_range=custom)
- `end_date`: ISO datetime (required if time_range=custom)

**Response:**
```json
{
  "total_jobs": 156,
  "success_count": 134,
  "rejection_count": 22,
  "pending_count": 0,
  "rejection_rate": 14.1,
  "avg_processing_time_minutes": 45.3,
  "doc_distribution": {
    "letter_of_credit": 78,
    "commercial_invoice": 45,
    "bill_of_lading": 33
  },
  "time_range": "30d",
  "start_date": "2025-08-17T00:00:00Z",
  "end_date": "2025-09-16T23:59:59Z"
}
```

#### 2. Discrepancy Analysis
```http
GET /analytics/discrepancies?time_range=30d
```

**Response:**
```json
{
  "top_discrepancies": [
    {
      "type": "field_mismatch",
      "rule": "currency_mismatch",
      "count": 15,
      "percentage": 25.4
    }
  ],
  "fatal_four_frequency": {
    "currency_mismatch": 15,
    "missing_bill_of_lading": 8,
    "amount_discrepancy": 12,
    "date_inconsistency": 5
  },
  "severity_distribution": {
    "critical": 18,
    "major": 12,
    "minor": 8
  },
  "total_discrepancies": 38,
  "avg_discrepancies_per_job": 1.7
}
```

#### 3. Trend Analysis
```http
GET /analytics/trends?time_range=30d
```

**Response:**
```json
{
  "timeline": [
    {
      "date": "2025-09-01",
      "jobs_submitted": 8,
      "jobs_completed": 6,
      "jobs_rejected": 2,
      "avg_processing_time": 42.5,
      "discrepancy_count": 3,
      "success_rate": 75.0
    }
  ],
  "job_volume_trend": 0.0234,
  "rejection_rate_trend": -0.0156,
  "processing_time_trend": 0.0089
}
```

#### 4. Processing Time Breakdown
```http
GET /analytics/processing-times?time_range=30d
```

**Response:**
```json
{
  "avg_total_time_seconds": 2715.0,
  "time_percentiles": {
    "p50": 1800.0,
    "p90": 4200.0,
    "p95": 5400.0,
    "p99": 7200.0
  },
  "by_document_type": {
    "letter_of_credit": 2850.0,
    "commercial_invoice": 2250.0,
    "bill_of_lading": 3150.0
  }
}
```

### Role-Specific Endpoints

#### 5. User Statistics (Bank/Admin Only)
```http
GET /analytics/user/{user_id}?time_range=30d
```

**Response:**
```json
{
  "user_id": "uuid-here",
  "user_email": "trader@company.com",
  "user_role": "exporter",
  "total_jobs": 45,
  "successful_jobs": 38,
  "rejected_jobs": 7,
  "rejection_rate": 15.6,
  "avg_processing_time_minutes": 43.2,
  "most_active_day": "Tuesday",
  "most_active_hour": 14,
  "documents_uploaded": 135,
  "jobs_last_30_days": 45
}
```

#### 6. System Metrics (Bank/Admin Only)
```http
GET /analytics/system?time_range=30d
```

**Response:**
```json
{
  "total_system_jobs": 1247,
  "total_active_users": 23,
  "jobs_per_user_avg": 54.2,
  "system_rejection_rate": 12.8,
  "avg_system_processing_time": 41.7,
  "usage_by_role": {
    "exporter": 678,
    "importer": 445,
    "bank": 124
  },
  "peak_hours": [
    {"hour": 14, "job_count": 156},
    {"hour": 10, "job_count": 134}
  ],
  "peak_days": [
    {"day": "Tuesday", "job_count": 203},
    {"day": "Wednesday", "job_count": 189}
  ]
}
```

### Utility Endpoints

#### 7. Complete Dashboard
```http
GET /analytics/dashboard?time_range=30d&include_trends=true&include_discrepancies=true
```

**Response:**
```json
{
  "summary": { /* SummaryStats */ },
  "trends": { /* TrendStats */ },
  "discrepancies": { /* DiscrepancyStats */ },
  "processing_times": { /* ProcessingTimeBreakdown */ },
  "user_stats": { /* UserStats - for individual users */ },
  "system_metrics": { /* SystemMetrics - for bank/admin */ },
  "generated_at": "2025-09-16T10:30:00Z",
  "user_role": "exporter",
  "data_scope": "own"
}
```

#### 8. Anomaly Detection (Bank/Admin Only)
```http
GET /analytics/anomalies?time_range=7d
```

**Response:**
```json
[
  {
    "alert_type": "rejection_spike",
    "severity": "high",
    "message": "Rejection rate increased by 45.2%",
    "current_value": 23.5,
    "expected_value": 16.2,
    "confidence": 0.89,
    "detected_at": "2025-09-16T08:15:00Z"
  }
]
```

#### 9. CSV Export
```http
GET /analytics/export/csv?time_range=30d
```

**Response:** CSV file download with comprehensive analytics data.

#### 10. System Health (Admin Only)
```http
GET /analytics/health
```

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "query_performance_ms": 145.7,
  "recent_jobs_24h": 89,
  "last_checked": "2025-09-16T10:30:00Z"
}
```

## Metrics Explained

### Job-Level Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **Total Jobs** | Number of validation sessions submitted | Count of all sessions in time range |
| **Success Count** | Jobs completed successfully | Sessions with status='completed' |
| **Rejection Count** | Jobs that failed validation | Sessions with status='failed' |
| **Rejection Rate** | Percentage of jobs rejected | (Rejected / Total) × 100 |
| **Avg Processing Time** | Average time from start to completion | Mean of (completed_at - started_at) |

### Discrepancy Metrics

| Metric | Description |
|--------|-------------|
| **Top Discrepancies** | Most common validation issues |
| **Fatal Four** | Critical issues: currency mismatch, missing BL, amount discrepancy, date inconsistency |
| **Severity Distribution** | Breakdown by critical/major/minor severity |
| **Discrepancy Trends** | Daily/weekly patterns in validation issues |

### Trend Analysis

| Metric | Description |
|--------|-------------|
| **Job Volume Trend** | Whether submission volume is increasing/decreasing |
| **Rejection Rate Trend** | Whether rejection rate is improving/worsening |
| **Processing Time Trend** | Whether processing is getting faster/slower |

### System Metrics (Bank/Admin Only)

| Metric | Description |
|--------|-------------|
| **Total System Jobs** | All jobs across all users |
| **Active Users** | Users with jobs in the time period |
| **Usage by Role** | Job distribution across user roles |
| **Peak Hours/Days** | When the system is most heavily used |

## Role-Based Access Control

### 🔸 **Exporter Role**
- **Data Scope**: Own jobs and documents only
- **Available Metrics**: All personal metrics and trends
- **Restrictions**: Cannot view other users' or system-wide data

```bash
# Accessible endpoints
GET /analytics/summary          # Own data only
GET /analytics/discrepancies    # Own discrepancies
GET /analytics/trends           # Own trends
GET /analytics/processing-times # Own processing times
GET /analytics/dashboard        # Personal dashboard
GET /analytics/export/csv       # Own data export
```

### 🔸 **Importer Role**
- **Data Scope**: Same as Exporter
- **Available Metrics**: All personal metrics and trends
- **Restrictions**: Same as Exporter

### 🔸 **Bank Role**
- **Data Scope**: System-wide read access
- **Available Metrics**: All system metrics for compliance monitoring
- **Special Access**: System-wide analytics, user statistics, anomaly detection

```bash
# Additional accessible endpoints
GET /analytics/user/{user_id}   # Any user's statistics
GET /analytics/system           # System-wide metrics
GET /analytics/anomalies        # Anomaly detection
```

### 🔸 **Admin Role**
- **Data Scope**: Full system access
- **Available Metrics**: All metrics including system health
- **Special Access**: Same as Bank + system administration

```bash
# Additional accessible endpoints
GET /analytics/health           # System health monitoring
```

## Usage Examples

### Frontend Integration

#### 1. Dashboard Widget - Summary Cards
```javascript
// Fetch summary for current user
const response = await fetch('/analytics/summary?time_range=30d', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const summary = await response.json();

// Display summary cards
<SummaryCard title="Total Jobs" value={summary.total_jobs} />
<SummaryCard title="Success Rate" value={`${100-summary.rejection_rate}%`} />
<SummaryCard title="Avg Processing" value={`${summary.avg_processing_time_minutes}m`} />
```

#### 2. Trend Chart
```javascript
// Fetch trend data
const response = await fetch('/analytics/trends?time_range=90d', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const trends = await response.json();

// Render chart
<LineChart
  data={trends.timeline}
  xKey="date"
  yKey="success_rate"
  title="Success Rate Trend"
/>
```

#### 3. Discrepancy Analysis
```javascript
// Fetch discrepancy data
const response = await fetch('/analytics/discrepancies?time_range=30d', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const discrepancies = await response.json();

// Display top issues
<DiscrepancyChart
  data={discrepancies.top_discrepancies}
  title="Top Validation Issues"
/>
```

#### 4. Role-Based Dashboard
```javascript
// Fetch complete dashboard
const response = await fetch('/analytics/dashboard?time_range=30d', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const dashboard = await response.json();

// Render based on user role
if (dashboard.user_role === 'bank' || dashboard.user_role === 'admin') {
  // Show system-wide metrics
  return <SystemDashboard data={dashboard} />;
} else {
  // Show personal metrics
  return <PersonalDashboard data={dashboard} />;
}
```

### Business Intelligence Integration

#### PowerBI/Tableau Export
```bash
# Schedule daily export for BI tools
curl -X GET "https://api.lcopilot.com/analytics/export/csv?time_range=7d" \
  -H "Authorization: Bearer $API_TOKEN" \
  -o "lcopilot_analytics_$(date +%Y%m%d).csv"
```

#### Compliance Reporting
```javascript
// Generate compliance report for regulators
const systemMetrics = await fetch('/analytics/system?time_range=365d', {
  headers: { 'Authorization': `Bearer ${bankToken}` }
});

const complianceReport = {
  reportPeriod: "2025-01-01 to 2025-12-31",
  totalTransactions: systemMetrics.total_system_jobs,
  systemReliability: 100 - systemMetrics.system_rejection_rate,
  averageProcessingTime: systemMetrics.avg_system_processing_time,
  userActivity: systemMetrics.usage_by_role
};
```

## Performance Considerations

### Database Optimization
- **Indexes**: Strategic indexes on frequently queried columns
- **Query Performance**: All queries optimized for <500ms response time
- **Pagination**: Large result sets are automatically paginated
- **Caching**: Ready for Redis implementation for frequently accessed data

### API Performance
- **Response Times**: Target <500ms for all analytics queries
- **Concurrent Users**: Supports multiple simultaneous dashboard users
- **Data Freshness**: Real-time data with minimal lag
- **Export Limits**: CSV exports limited to reasonable data sizes

## Monitoring and Alerting

### System Health Monitoring
```bash
# Check analytics system health
GET /analytics/health

# Response includes:
# - Database connectivity
# - Query performance metrics
# - Recent data availability
# - System warnings
```

### Anomaly Detection
The system automatically detects anomalies in:
- Sudden spikes in rejection rates
- Processing time degradation
- Volume anomalies (unusually high/low activity)
- User behavior patterns

### Performance Monitoring
- Query execution times are logged
- Slow query alerts for queries >1 second
- Database index usage monitoring
- Memory and CPU usage tracking

## Troubleshooting

### Common Issues

#### 1. No Data Returned
**Problem**: API returns empty results
**Causes**:
- No jobs in selected time range
- Role-based filtering excludes data
- Database connectivity issues

**Solutions**:
```bash
# Check if user has any jobs
GET /analytics/summary?time_range=365d

# Verify time range
GET /analytics/summary?time_range=custom&start_date=2025-01-01T00:00:00Z&end_date=2025-12-31T23:59:59Z
```

#### 2. Slow Performance
**Problem**: Analytics queries taking >2 seconds
**Causes**:
- Missing database indexes
- Large dataset without pagination
- Complex trend calculations

**Solutions**:
- Run database migration to add analytics indexes
- Use shorter time ranges for initial testing
- Check system health endpoint

#### 3. Access Denied
**Problem**: 403 Forbidden errors
**Causes**:
- Insufficient role permissions
- Token expired or invalid
- Trying to access other user's data

**Solutions**:
- Verify user role with `/auth/me`
- Check JWT token validity
- Use role-appropriate endpoints

### Debug Endpoints

#### Analytics Health Check
```bash
GET /analytics/health
# Returns system status and performance metrics
```

#### Query Performance Debugging
```javascript
// Measure query performance
const start = Date.now();
const response = await fetch('/analytics/summary');
const duration = Date.now() - start;
console.log(`Query took ${duration}ms`);
```

## Future Enhancements

### Planned Features
1. **Dashboard Caching**: Redis implementation for faster repeated queries
2. **Real-time Updates**: WebSocket support for live dashboard updates
3. **Advanced Analytics**: Machine learning for predictive insights
4. **Custom Dashboards**: User-configurable dashboard widgets
5. **Automated Reports**: Scheduled email reports for banks and admins
6. **Data Warehouse**: Integration with data warehouse for historical analysis

### ML/AI Integration
- **Predictive Analytics**: Predict likely rejection before processing
- **Anomaly Detection**: Advanced pattern recognition for unusual behavior
- **Recommendation Engine**: Suggest process improvements based on patterns
- **Risk Scoring**: Calculate risk scores for transactions and users

### BI Tool Integration
- **Power BI Connector**: Direct connection to Power BI
- **Tableau Integration**: Custom Tableau connector
- **Grafana Dashboards**: Operational monitoring dashboards
- **API Webhooks**: Real-time data push to external systems

## Security and Compliance

### Data Privacy
- Role-based data isolation ensures users only see appropriate data
- No PII in analytics data (user IDs are UUIDs)
- All analytics access is audited in the audit log

### Compliance Features
- Complete audit trail of all analytics access
- Data export capabilities for regulatory reporting
- Anomaly detection for compliance monitoring
- System-wide metrics for oversight

### Security Measures
- JWT-based authentication required for all endpoints
- Role-based access control strictly enforced
- Request rate limiting to prevent abuse
- All analytics queries logged for security monitoring

---

For technical support or questions about the analytics system, please refer to the development team or create an issue in the project repository.