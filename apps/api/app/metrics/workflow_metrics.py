"""
Workflow metrics for Prometheus monitoring.
"""

try:
    from prometheus_client import Counter, Histogram, Gauge
except ImportError:
    # Fallback if prometheus_client is not available
    class _MockMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, value=1):
            pass
        def observe(self, value):
            pass
        def set(self, value):
            pass
    
    Counter = Histogram = Gauge = _MockMetric


# Bulk processing metrics
bulk_metrics = type('BulkMetrics', (), {
    'jobs_created_total': Counter(
        'bulk_jobs_created_total',
        'Total number of bulk jobs created',
        ['tenant', 'job_type']
    ),
    'job_duration_seconds': Histogram(
        'bulk_job_duration_seconds',
        'Duration of bulk job processing in seconds',
        ['tenant', 'job_type', 'status']
    ),
    'items_processed_total': Counter(
        'bulk_items_processed_total',
        'Total number of items processed in bulk jobs',
        ['tenant', 'job_type', 'status']
    ),
})()

