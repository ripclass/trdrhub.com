"""
Prometheus monitoring and health checks for integration platform.
Tracks API usage, performance, billing events, and system health.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from prometheus_client import Counter, Histogram, Gauge, Enum, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
from fastapi import Response

from ..models.integrations import (
    IntegrationSubmission, IntegrationBillingEvent, IntegrationHealthCheck,
    Integration, CompanyIntegration, BillingEventType
)
from ..models import User
from ..database import get_db

logger = logging.getLogger(__name__)

# Prometheus Metrics Definitions

# API Request Metrics
integration_requests_total = Counter(
    'lcopilot_integration_requests_total',
    'Total integration API requests',
    ['integration_type', 'operation', 'user_role', 'status']
)

integration_request_duration = Histogram(
    'lcopilot_integration_request_duration_seconds',
    'Integration API request duration',
    ['integration_type', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# Billing Metrics
billing_events_total = Counter(
    'lcopilot_billing_events_total',
    'Total billing events recorded',
    ['event_type', 'billing_tier', 'company_id']
)

billing_revenue_total = Counter(
    'lcopilot_billing_revenue_total',
    'Total billing revenue',
    ['event_type', 'billing_tier', 'currency']
)

# Integration Health Metrics
integration_health_status = Gauge(
    'lcopilot_integration_health_status',
    'Integration health status (1=healthy, 0=unhealthy)',
    ['integration_id', 'integration_name', 'integration_type']
)

integration_response_time = Gauge(
    'lcopilot_integration_response_time_ms',
    'Integration API response time in milliseconds',
    ['integration_id', 'integration_name']
)

# Submission Metrics
submission_status = Counter(
    'lcopilot_submissions_total',
    'Total submissions by status',
    ['integration_type', 'submission_type', 'status', 'company_id']
)

submission_retry_count = Counter(
    'lcopilot_submission_retries_total',
    'Total submission retries',
    ['integration_type', 'submission_type', 'company_id']
)

# User Activity Metrics
active_users = Gauge(
    'lcopilot_active_users',
    'Number of active users',
    ['user_role', 'time_window']
)

company_usage = Gauge(
    'lcopilot_company_usage',
    'Company usage statistics',
    ['company_id', 'integration_type', 'metric_type']
)

# System Resource Metrics
database_connections = Gauge(
    'lcopilot_database_connections',
    'Number of active database connections'
)

# Authentication Metrics
auth_attempts = Counter(
    'lcopilot_auth_attempts_total',
    'Authentication attempts',
    ['auth_type', 'integration_type', 'status']
)

# Rate Limiting Metrics
rate_limit_hits = Counter(
    'lcopilot_rate_limit_hits_total',
    'Rate limit hits',
    ['integration_type', 'company_id', 'limit_type']
)


class IntegrationMetricsCollector:
    """Collects and exposes integration platform metrics."""

    def __init__(self):
        self.db = None

    def set_database(self, db: Session):
        """Set database session for metrics collection."""
        self.db = db

    def record_api_request(
        self,
        integration_type: str,
        operation: str,
        user_role: str,
        status: str,
        duration: float
    ) -> None:
        """Record API request metrics."""
        integration_requests_total.labels(
            integration_type=integration_type,
            operation=operation,
            user_role=user_role,
            status=status
        ).inc()

        integration_request_duration.labels(
            integration_type=integration_type,
            operation=operation
        ).observe(duration)

    def record_billing_event(
        self,
        event_type: str,
        billing_tier: str,
        company_id: str,
        amount: float,
        currency: str = 'USD'
    ) -> None:
        """Record billing event metrics."""
        billing_events_total.labels(
            event_type=event_type,
            billing_tier=billing_tier,
            company_id=company_id
        ).inc()

        billing_revenue_total.labels(
            event_type=event_type,
            billing_tier=billing_tier,
            currency=currency
        ).inc(amount)

    def record_submission_status(
        self,
        integration_type: str,
        submission_type: str,
        status: str,
        company_id: str
    ) -> None:
        """Record submission status metrics."""
        submission_status.labels(
            integration_type=integration_type,
            submission_type=submission_type,
            status=status,
            company_id=company_id
        ).inc()

    def record_submission_retry(
        self,
        integration_type: str,
        submission_type: str,
        company_id: str
    ) -> None:
        """Record submission retry metrics."""
        submission_retry_count.labels(
            integration_type=integration_type,
            submission_type=submission_type,
            company_id=company_id
        ).inc()

    def record_auth_attempt(
        self,
        auth_type: str,
        integration_type: str,
        status: str
    ) -> None:
        """Record authentication attempt metrics."""
        auth_attempts.labels(
            auth_type=auth_type,
            integration_type=integration_type,
            status=status
        ).inc()

    def record_rate_limit_hit(
        self,
        integration_type: str,
        company_id: str,
        limit_type: str
    ) -> None:
        """Record rate limit hit metrics."""
        rate_limit_hits.labels(
            integration_type=integration_type,
            company_id=company_id,
            limit_type=limit_type
        ).inc()

    def update_integration_health(
        self,
        integration_id: str,
        integration_name: str,
        integration_type: str,
        is_healthy: bool,
        response_time_ms: Optional[int] = None
    ) -> None:
        """Update integration health metrics."""
        integration_health_status.labels(
            integration_id=integration_id,
            integration_name=integration_name,
            integration_type=integration_type
        ).set(1 if is_healthy else 0)

        if response_time_ms is not None:
            integration_response_time.labels(
                integration_id=integration_id,
                integration_name=integration_name
            ).set(response_time_ms)

    def update_user_activity_metrics(self) -> None:
        """Update user activity metrics from database."""
        if not self.db:
            return

        try:
            # Active users in last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            # Count active users by role
            for role in ['exporter', 'importer', 'bank', 'admin']:
                count = self.db.query(User).filter(
                    User.role == role,
                    User.last_login_at >= one_hour_ago
                ).count()

                active_users.labels(
                    user_role=role,
                    time_window='1h'
                ).set(count)

            # Active users in last day
            one_day_ago = datetime.utcnow() - timedelta(days=1)

            for role in ['exporter', 'importer', 'bank', 'admin']:
                count = self.db.query(User).filter(
                    User.role == role,
                    User.last_login_at >= one_day_ago
                ).count()

                active_users.labels(
                    user_role=role,
                    time_window='24h'
                ).set(count)

        except Exception as e:
            logger.error(f"Failed to update user activity metrics: {str(e)}")

    def update_company_usage_metrics(self) -> None:
        """Update company usage metrics from database."""
        if not self.db:
            return

        try:
            # Get usage by company and integration type
            companies = self.db.query(CompanyIntegration).all()

            for company_integration in companies:
                company_id = str(company_integration.company_id)
                integration_type = company_integration.integration.type.value

                # Usage count
                company_usage.labels(
                    company_id=company_id,
                    integration_type=integration_type,
                    metric_type='usage_count'
                ).set(company_integration.usage_count)

                # Quota remaining
                if company_integration.monthly_quota:
                    remaining = company_integration.monthly_quota - company_integration.usage_count
                    company_usage.labels(
                        company_id=company_id,
                        integration_type=integration_type,
                        metric_type='quota_remaining'
                    ).set(max(0, remaining))

        except Exception as e:
            logger.error(f"Failed to update company usage metrics: {str(e)}")

    def update_database_metrics(self) -> None:
        """Update database connection metrics."""
        try:
            # This would need to be implemented based on your connection pool
            # For now, we'll use a placeholder
            database_connections.set(10)  # Placeholder value
        except Exception as e:
            logger.error(f"Failed to update database metrics: {str(e)}")

    def collect_all_metrics(self) -> None:
        """Collect all metrics from database."""
        self.update_user_activity_metrics()
        self.update_company_usage_metrics()
        self.update_database_metrics()


class IntegrationHealthChecker:
    """Performs health checks for integrations."""

    def __init__(self, db: Session):
        self.db = db
        self.metrics_collector = IntegrationMetricsCollector()
        self.metrics_collector.set_database(db)

    async def check_integration_health(self, integration_id: str) -> Dict[str, Any]:
        """Perform health check for specific integration."""
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id
        ).first()

        if not integration:
            return {'error': 'Integration not found'}

        start_time = time.time()

        try:
            # Perform basic connectivity check
            health_status = await self._perform_health_check(integration)

            response_time_ms = int((time.time() - start_time) * 1000)

            # Record health check in database
            health_check = IntegrationHealthCheck(
                integration_id=integration_id,
                endpoint=integration.base_url,
                status_code=health_status.get('status_code'),
                response_time_ms=response_time_ms,
                error_message=health_status.get('error'),
                is_healthy=health_status.get('healthy', False)
            )

            self.db.add(health_check)
            self.db.commit()

            # Update Prometheus metrics
            self.metrics_collector.update_integration_health(
                integration_id=str(integration_id),
                integration_name=integration.name,
                integration_type=integration.type.value,
                is_healthy=health_status.get('healthy', False),
                response_time_ms=response_time_ms
            )

            return {
                'integration_id': str(integration_id),
                'name': integration.name,
                'type': integration.type.value,
                'healthy': health_status.get('healthy', False),
                'response_time_ms': response_time_ms,
                'status_code': health_status.get('status_code'),
                'error': health_status.get('error'),
                'checked_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed for integration {integration_id}: {str(e)}")

            # Record failed health check
            health_check = IntegrationHealthCheck(
                integration_id=integration_id,
                endpoint=integration.base_url,
                status_code=None,
                response_time_ms=None,
                error_message=str(e),
                is_healthy=False
            )

            self.db.add(health_check)
            self.db.commit()

            return {
                'integration_id': str(integration_id),
                'name': integration.name,
                'healthy': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }

    async def _perform_health_check(self, integration: Integration) -> Dict[str, Any]:
        """Perform actual health check."""
        import httpx

        # Use sandbox for health checks if enabled
        from ..config import settings
        api_url = integration.get_api_url(use_sandbox=settings.USE_SANDBOX)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{api_url}/health")

                return {
                    'healthy': response.status_code == 200,
                    'status_code': response.status_code,
                    'error': None if response.status_code == 200 else response.text
                }

        except httpx.TimeoutException:
            return {
                'healthy': False,
                'status_code': None,
                'error': 'Health check timeout'
            }
        except Exception as e:
            return {
                'healthy': False,
                'status_code': None,
                'error': str(e)
            }

    async def check_all_integrations(self) -> List[Dict[str, Any]]:
        """Perform health checks for all active integrations."""
        integrations = self.db.query(Integration).filter(
            Integration.status == 'active'
        ).all()

        results = []
        for integration in integrations:
            result = await self.check_integration_health(str(integration.id))
            results.append(result)

        return results


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response."""
    # Collect latest metrics
    db = next(get_db())
    collector = IntegrationMetricsCollector()
    collector.set_database(db)
    collector.collect_all_metrics()
    db.close()

    # Generate Prometheus format
    metrics_data = generate_latest()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


# Global metrics collector instance
metrics_collector = IntegrationMetricsCollector()


# Middleware for automatic metrics collection
class MetricsMiddleware:
    """FastAPI middleware for automatic metrics collection."""

    def __init__(self):
        self.collector = metrics_collector

    async def __call__(self, request, call_next):
        """Process request and collect metrics."""
        start_time = time.time()

        # Extract context
        path = request.url.path
        method = request.method

        # Skip non-integration endpoints
        if not self._is_integration_endpoint(path):
            return await call_next(request)

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract metrics context
        integration_type = self._extract_integration_type(path)
        operation = self._extract_operation(path, method)
        user_role = getattr(request.state, 'user_role', 'unknown')
        status = 'success' if response.status_code < 400 else 'error'

        # Record metrics
        self.collector.record_api_request(
            integration_type=integration_type,
            operation=operation,
            user_role=user_role,
            status=status,
            duration=duration
        )

        return response

    def _is_integration_endpoint(self, path: str) -> bool:
        """Check if path is an integration endpoint."""
        integration_paths = [
            '/integrations/',
            '/api/v1/integrations/',
            '/sessions/'
        ]
        return any(path.startswith(p) for p in integration_paths)

    def _extract_integration_type(self, path: str) -> str:
        """Extract integration type from path."""
        if '/bank/' in path:
            return 'bank'
        elif '/customs/' in path:
            return 'customs'
        elif '/logistics/' in path:
            return 'logistics'
        elif '/fx/' in path:
            return 'fx_provider'
        return 'unknown'

    def _extract_operation(self, path: str, method: str) -> str:
        """Extract operation from path and method."""
        if 'submit' in path or method == 'POST':
            return 'submit'
        elif 'query' in path or 'status' in path:
            return 'query'
        elif 'track' in path:
            return 'track'
        elif method == 'GET':
            return 'get'
        return 'unknown'


# Global middleware instance
metrics_middleware = MetricsMiddleware()