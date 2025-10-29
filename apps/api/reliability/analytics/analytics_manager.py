"""
LCopilot Reliability Analytics Manager

Commercial feature tiers:
- Free: No analytics
- Pro: Basic error trends and aggregate metrics
- Enterprise: Advanced analytics, ML insights, BI integration

Analytics collection for reliability trends, error patterns, and predictive insights.
Integrates with CloudWatch, S3, and external BI tools.
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class AnalyticsTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

@dataclass
class ErrorTrend:
    timestamp: datetime
    error_type: str
    service: str
    count: int
    severity: str
    customer_id: Optional[str] = None
    correlation_id: Optional[str] = None

@dataclass
class MetricPoint:
    timestamp: datetime
    metric_name: str
    value: float
    dimensions: Dict[str, str]
    unit: str = "Count"

@dataclass
class AnalyticsInsight:
    insight_type: str
    title: str
    description: str
    severity: str
    confidence: float
    recommended_actions: List[str]
    data_points: List[Dict[str, Any]]
    tier_access: List[str]

@dataclass
class AnalyticsConfig:
    tier: str
    customer_id: str
    retention_days: int
    data_sources: List[str]
    export_formats: List[str]
    ml_features_enabled: bool
    bi_integration_enabled: bool
    custom_dashboards: bool
    real_time_alerts: bool

class ReliabilityAnalyticsManager:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch')
        self.s3 = boto3.client('s3')
        self.logs = boto3.client('logs')

        self.config_path = Path(__file__).parent.parent / "config" / "reliability_config.yaml"
        self.reliability_config = self._load_reliability_config()

        self.analytics_bucket = f"lcopilot-analytics-{environment}"
        self.insights_bucket = f"lcopilot-insights-{environment}"

    def _load_reliability_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reliability config not found at {self.config_path}")
            return {}

    def get_analytics_config(self, tier: str, customer_id: str) -> AnalyticsConfig:
        feature_matrix = self.reliability_config.get('feature_matrix', {})
        tier_features = feature_matrix.get(tier, feature_matrix.get('free', {}))

        # Default configuration for free tier (no analytics)
        config = AnalyticsConfig(
            tier=tier,
            customer_id=customer_id,
            retention_days=0,
            data_sources=[],
            export_formats=[],
            ml_features_enabled=False,
            bi_integration_enabled=False,
            custom_dashboards=False,
            real_time_alerts=False
        )

        # Pro tier configuration
        if tier == "pro":
            config.retention_days = 90
            config.data_sources = ["cloudwatch", "application_logs"]
            config.export_formats = ["json", "csv"]
            config.real_time_alerts = True

        # Enterprise tier configuration
        elif tier == "enterprise":
            config.retention_days = 365
            config.data_sources = ["cloudwatch", "application_logs", "external_apis", "custom_metrics"]
            config.export_formats = ["json", "csv", "parquet", "excel"]
            config.ml_features_enabled = True
            config.bi_integration_enabled = True
            config.custom_dashboards = True
            config.real_time_alerts = True

        return config

    def collect_error_trends(self, config: AnalyticsConfig, hours_back: int = 24) -> List[ErrorTrend]:
        if config.tier == "free":
            logger.info("Error trend collection not available for free tier")
            return []

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        error_trends = []

        try:
            # Query CloudWatch Logs for error patterns
            log_groups = self._get_log_groups_for_customer(config.customer_id)

            for log_group in log_groups:
                query = self._build_error_query(config.tier)

                response = self.logs.start_query(
                    logGroupName=log_group,
                    startTime=int(start_time.timestamp()),
                    endTime=int(end_time.timestamp()),
                    queryString=query
                )

                query_id = response['queryId']

                # Poll for query completion
                results = self._wait_for_query_completion(query_id)

                for result in results:
                    trend = self._parse_error_log_result(result, config.customer_id)
                    if trend:
                        error_trends.append(trend)

        except Exception as e:
            logger.error(f"Failed to collect error trends: {str(e)}")

        return error_trends

    def _build_error_query(self, tier: str) -> str:
        base_query = """
        fields @timestamp, @message, @logStream
        | filter @message like /ERROR|WARN|FATAL/
        | stats count() by bin(5m)
        """

        if tier == "enterprise":
            # Enhanced query with correlation tracking
            return """
            fields @timestamp, @message, @logStream, @requestId
            | filter @message like /ERROR|WARN|FATAL|EXCEPTION/
            | parse @message /(?P<level>\w+).*(?P<service>\w+).*(?P<error_type>\w+)/
            | stats count() by bin(5m), level, service, error_type
            | sort @timestamp desc
            """

        return base_query

    def _get_log_groups_for_customer(self, customer_id: str) -> List[str]:
        customer_config = self.reliability_config.get('customers', {}).get(customer_id, {})
        tier = customer_config.get('tier', 'free')

        log_groups = [
            f"/aws/lambda/lcopilot-reliability-{tier}-{self.environment}",
            f"/aws/apigateway/lcopilot-api-{tier}-{self.environment}"
        ]

        if tier == "enterprise":
            log_groups.extend([
                f"/aws/lambda/lcopilot-custom-{customer_id}-{self.environment}",
                f"/aws/ecs/lcopilot-service-{customer_id}-{self.environment}"
            ])

        return log_groups

    def _wait_for_query_completion(self, query_id: str, max_wait: int = 60) -> List[List[Dict]]:
        for _ in range(max_wait):
            response = self.logs.get_query_results(queryId=query_id)

            if response['status'] == 'Complete':
                return response['results']
            elif response['status'] == 'Failed':
                logger.error(f"CloudWatch Logs query failed: {query_id}")
                return []

            import time
            time.sleep(1)

        logger.warning(f"Query timeout: {query_id}")
        return []

    def _parse_error_log_result(self, result: List[Dict], customer_id: str) -> Optional[ErrorTrend]:
        try:
            timestamp_field = next((r for r in result if r['field'] == '@timestamp'), None)
            message_field = next((r for r in result if r['field'] == '@message'), None)

            if not timestamp_field or not message_field:
                return None

            timestamp = datetime.fromisoformat(timestamp_field['value'].replace('Z', '+00:00'))
            message = message_field['value']

            # Parse error type and severity from message
            error_type = "Unknown"
            severity = "ERROR"
            service = "Unknown"

            if "FATAL" in message:
                severity = "FATAL"
            elif "WARN" in message:
                severity = "WARN"
            elif "ERROR" in message:
                severity = "ERROR"

            # Extract service name if available
            if "service=" in message:
                service = message.split("service=")[1].split()[0]

            return ErrorTrend(
                timestamp=timestamp,
                error_type=error_type,
                service=service,
                count=1,
                severity=severity,
                customer_id=customer_id
            )

        except Exception as e:
            logger.error(f"Failed to parse error log result: {str(e)}")
            return None

    def collect_performance_metrics(self, config: AnalyticsConfig, hours_back: int = 24) -> List[MetricPoint]:
        if config.tier == "free":
            return []

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        metrics = []

        # Base metrics for Pro tier
        metric_queries = [
            {
                'metric_name': 'ResponseTime',
                'namespace': 'AWS/ApiGateway',
                'stat': 'Average',
                'dimensions': {'ApiName': f'lcopilot-api-{config.tier}-{self.environment}'}
            },
            {
                'metric_name': 'Count',
                'namespace': 'AWS/ApiGateway',
                'stat': 'Sum',
                'dimensions': {'ApiName': f'lcopilot-api-{config.tier}-{self.environment}'}
            }
        ]

        # Enhanced metrics for Enterprise tier
        if config.tier == "enterprise":
            metric_queries.extend([
                {
                    'metric_name': 'Duration',
                    'namespace': 'AWS/Lambda',
                    'stat': 'Average',
                    'dimensions': {'FunctionName': f'lcopilot-custom-{config.customer_id}-{self.environment}'}
                },
                {
                    'metric_name': 'Errors',
                    'namespace': 'AWS/Lambda',
                    'stat': 'Sum',
                    'dimensions': {'FunctionName': f'lcopilot-custom-{config.customer_id}-{self.environment}'}
                },
                {
                    'metric_name': 'CPUUtilization',
                    'namespace': 'AWS/ECS',
                    'stat': 'Average',
                    'dimensions': {'ServiceName': f'lcopilot-service-{config.customer_id}-{self.environment}'}
                }
            ])

        for query in metric_queries:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace=query['namespace'],
                    MetricName=query['metric_name'],
                    Dimensions=[{'Name': k, 'Value': v} for k, v in query['dimensions'].items()],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,  # 5 minutes
                    Statistics=[query['stat']]
                )

                for datapoint in response['Datapoints']:
                    metrics.append(MetricPoint(
                        timestamp=datapoint['Timestamp'],
                        metric_name=query['metric_name'],
                        value=datapoint[query['stat']],
                        dimensions=query['dimensions']
                    ))

            except Exception as e:
                logger.error(f"Failed to collect metric {query['metric_name']}: {str(e)}")

        return sorted(metrics, key=lambda x: x.timestamp)

    def generate_insights(self, config: AnalyticsConfig, error_trends: List[ErrorTrend],
                         metrics: List[MetricPoint]) -> List[AnalyticsInsight]:
        insights = []

        if config.tier == "free":
            return insights

        # Pro tier: Basic trend analysis
        if config.tier in ["pro", "enterprise"]:
            insights.extend(self._analyze_error_patterns(error_trends, config.tier))
            insights.extend(self._analyze_performance_trends(metrics, config.tier))

        # Enterprise tier: Advanced ML insights
        if config.tier == "enterprise" and config.ml_features_enabled:
            insights.extend(self._generate_ml_insights(error_trends, metrics))
            insights.extend(self._predict_reliability_issues(error_trends, metrics))

        return insights

    def _analyze_error_patterns(self, error_trends: List[ErrorTrend], tier: str) -> List[AnalyticsInsight]:
        insights = []

        if not error_trends:
            return insights

        # Group errors by type and service
        error_groups = {}
        for trend in error_trends:
            key = f"{trend.service}:{trend.error_type}"
            if key not in error_groups:
                error_groups[key] = []
            error_groups[key].append(trend)

        # Analyze patterns
        for service_error, trends in error_groups.items():
            service, error_type = service_error.split(':', 1)

            if len(trends) > 10:  # Threshold for pattern detection
                severity = "HIGH" if any(t.severity == "FATAL" for t in trends) else "MEDIUM"

                insight = AnalyticsInsight(
                    insight_type="error_pattern",
                    title=f"High Error Rate in {service}",
                    description=f"Detected {len(trends)} {error_type} errors in {service} service",
                    severity=severity,
                    confidence=0.8,
                    recommended_actions=[
                        f"Review {service} service logs",
                        "Check recent deployments",
                        "Monitor resource utilization"
                    ],
                    data_points=[
                        {
                            "service": service,
                            "error_type": error_type,
                            "count": len(trends),
                            "timespan": "24h"
                        }
                    ],
                    tier_access=["pro", "enterprise"] if tier == "pro" else ["enterprise"]
                )

                insights.append(insight)

        return insights

    def _analyze_performance_trends(self, metrics: List[MetricPoint], tier: str) -> List[AnalyticsInsight]:
        insights = []

        if not metrics:
            return insights

        # Analyze response time trends
        response_time_metrics = [m for m in metrics if m.metric_name == 'ResponseTime']

        if len(response_time_metrics) > 10:
            values = [m.value for m in response_time_metrics]
            avg_response_time = np.mean(values)
            std_response_time = np.std(values)

            # Detect anomalies
            threshold = avg_response_time + (2 * std_response_time)
            anomalies = [m for m in response_time_metrics if m.value > threshold]

            if len(anomalies) > 3:
                insight = AnalyticsInsight(
                    insight_type="performance_degradation",
                    title="Response Time Anomalies Detected",
                    description=f"Found {len(anomalies)} response time spikes above normal baseline",
                    severity="MEDIUM",
                    confidence=0.75,
                    recommended_actions=[
                        "Review system capacity",
                        "Check database performance",
                        "Analyze traffic patterns"
                    ],
                    data_points=[
                        {
                            "metric": "response_time",
                            "average": avg_response_time,
                            "threshold": threshold,
                            "anomaly_count": len(anomalies)
                        }
                    ],
                    tier_access=["pro", "enterprise"] if tier == "pro" else ["enterprise"]
                )

                insights.append(insight)

        return insights

    def _generate_ml_insights(self, error_trends: List[ErrorTrend], metrics: List[MetricPoint]) -> List[AnalyticsInsight]:
        insights = []

        # Correlation analysis between errors and performance
        if error_trends and metrics:
            # Create time-series data
            df_errors = pd.DataFrame([
                {
                    'timestamp': t.timestamp,
                    'error_count': t.count,
                    'severity_score': 1 if t.severity == 'WARN' else 2 if t.severity == 'ERROR' else 3
                }
                for t in error_trends
            ])

            df_metrics = pd.DataFrame([
                {
                    'timestamp': m.timestamp,
                    'response_time': m.value if m.metric_name == 'ResponseTime' else None
                }
                for m in metrics if m.metric_name == 'ResponseTime'
            ])

            if not df_errors.empty and not df_metrics.empty:
                # Merge on timestamp (rounded to nearest 5 minutes)
                df_errors['time_bucket'] = df_errors['timestamp'].dt.floor('5min')
                df_metrics['time_bucket'] = df_metrics['timestamp'].dt.floor('5min')

                merged = pd.merge(df_errors, df_metrics, on='time_bucket', how='inner')

                if len(merged) > 5:
                    correlation = merged['error_count'].corr(merged['response_time'])

                    if abs(correlation) > 0.7:
                        insight = AnalyticsInsight(
                            insight_type="ml_correlation",
                            title="Error-Performance Correlation Detected",
                            description=f"Strong correlation ({correlation:.2f}) between errors and response time",
                            severity="HIGH" if correlation > 0.8 else "MEDIUM",
                            confidence=0.9,
                            recommended_actions=[
                                "Investigate root cause of errors",
                                "Optimize performance bottlenecks",
                                "Implement circuit breaker patterns"
                            ],
                            data_points=[
                                {
                                    "correlation_coefficient": correlation,
                                    "data_points": len(merged),
                                    "analysis_type": "pearson_correlation"
                                }
                            ],
                            tier_access=["enterprise"]
                        )

                        insights.append(insight)

        return insights

    def _predict_reliability_issues(self, error_trends: List[ErrorTrend], metrics: List[MetricPoint]) -> List[AnalyticsInsight]:
        insights = []

        # Simple predictive model based on trend analysis
        if len(error_trends) > 20:
            # Calculate error rate trend
            df = pd.DataFrame([
                {'timestamp': t.timestamp, 'error_count': t.count}
                for t in error_trends
            ])

            df = df.sort_values('timestamp')
            df['hour'] = df['timestamp'].dt.floor('H')
            hourly_errors = df.groupby('hour')['error_count'].sum().reset_index()

            if len(hourly_errors) > 6:
                # Calculate trend slope
                hours = np.arange(len(hourly_errors))
                slope, _ = np.polyfit(hours, hourly_errors['error_count'], 1)

                # Predict next 4 hours
                if slope > 1:  # Increasing error trend
                    predicted_errors = slope * (len(hourly_errors) + 4) + hourly_errors['error_count'].iloc[-1]

                    insight = AnalyticsInsight(
                        insight_type="predictive_alert",
                        title="Increasing Error Trend Detected",
                        description=f"Error rate increasing by {slope:.1f} errors/hour. Predicted {predicted_errors:.0f} errors in next 4 hours",
                        severity="HIGH",
                        confidence=0.85,
                        recommended_actions=[
                            "Prepare incident response team",
                            "Scale up monitoring",
                            "Review recent changes",
                            "Consider service degradation"
                        ],
                        data_points=[
                            {
                                "trend_slope": slope,
                                "current_rate": hourly_errors['error_count'].iloc[-1],
                                "predicted_4h": predicted_errors,
                                "confidence_interval": "85%"
                            }
                        ],
                        tier_access=["enterprise"]
                    )

                    insights.append(insight)

        return insights

    def export_analytics_data(self, config: AnalyticsConfig, data_type: str,
                             data: List[Any], format: str = "json") -> str:
        if format not in config.export_formats:
            raise ValueError(f"Export format {format} not available for tier {config.tier}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_type}_{config.customer_id}_{timestamp}.{format}"

        try:
            if format == "json":
                content = json.dumps([asdict(item) if hasattr(item, '__dict__') else item for item in data],
                                   default=str, indent=2)
            elif format == "csv":
                df = pd.DataFrame([asdict(item) if hasattr(item, '__dict__') else item for item in data])
                content = df.to_csv(index=False)
            elif format == "excel":
                df = pd.DataFrame([asdict(item) if hasattr(item, '__dict__') else item for item in data])
                content = df.to_excel(index=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # Upload to S3
            s3_key = f"analytics/{config.customer_id}/{data_type}/{filename}"

            self.s3.put_object(
                Bucket=self.analytics_bucket,
                Key=s3_key,
                Body=content,
                ContentType=self._get_content_type(format)
            )

            # Generate presigned URL for download
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.analytics_bucket, 'Key': s3_key},
                ExpiresIn=3600  # 1 hour
            )

            logger.info(f"Analytics data exported: {s3_key}")
            return url

        except Exception as e:
            logger.error(f"Failed to export analytics data: {str(e)}")
            raise

    def _get_content_type(self, format: str) -> str:
        content_types = {
            'json': 'application/json',
            'csv': 'text/csv',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'parquet': 'application/octet-stream'
        }
        return content_types.get(format, 'application/octet-stream')

    def setup_analytics_hooks(self, config: AnalyticsConfig) -> bool:
        if config.tier == "free":
            logger.info("Analytics hooks not available for free tier")
            return False

        try:
            # Create CloudWatch custom metrics
            self._setup_custom_metrics(config)

            # Setup real-time alerts
            if config.real_time_alerts:
                self._setup_cloudwatch_alarms(config)

            # Setup BI integration for enterprise
            if config.bi_integration_enabled:
                self._setup_bi_integration(config)

            logger.info(f"Analytics hooks setup completed for {config.tier} tier")
            return True

        except Exception as e:
            logger.error(f"Failed to setup analytics hooks: {str(e)}")
            return False

    def _setup_custom_metrics(self, config: AnalyticsConfig):
        namespace = f"LCopilot/Reliability/{config.tier.title()}"

        # Put sample metric to create namespace
        self.cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    'MetricName': 'AnalyticsSetup',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'CustomerId', 'Value': config.customer_id},
                        {'Name': 'Tier', 'Value': config.tier}
                    ]
                }
            ]
        )

    def _setup_cloudwatch_alarms(self, config: AnalyticsConfig):
        alarm_name = f"lcopilot-analytics-{config.tier}-{config.customer_id}-{self.environment}"

        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='Errors',
            Namespace='AWS/Lambda',
            Period=300,
            Statistic='Sum',
            Threshold=10.0,
            ActionsEnabled=True,
            AlarmActions=[
                f"arn:aws:sns:{boto3.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:lcopilot-alerts-{self.environment}"
            ],
            AlarmDescription=f'Error rate alarm for {config.customer_id}',
            Dimensions=[
                {'Name': 'FunctionName', 'Value': f'lcopilot-reliability-{config.tier}-{self.environment}'}
            ]
        )

    def _setup_bi_integration(self, config: AnalyticsConfig):
        # Create Kinesis Data Firehose for real-time streaming to BI tools
        pass  # Implementation would depend on specific BI platform

def main():
    """Demo analytics collection and insights generation"""
    manager = ReliabilityAnalyticsManager()

    # Example for enterprise customer
    config = manager.get_analytics_config("enterprise", "customer-enterprise-001")

    print(f"Analytics configuration for {config.tier} tier:")
    print(f"- Retention: {config.retention_days} days")
    print(f"- Data sources: {config.data_sources}")
    print(f"- Export formats: {config.export_formats}")
    print(f"- ML features: {config.ml_features_enabled}")
    print(f"- BI integration: {config.bi_integration_enabled}")

    # Collect analytics data
    error_trends = manager.collect_error_trends(config, hours_back=24)
    metrics = manager.collect_performance_metrics(config, hours_back=24)

    print(f"\nCollected {len(error_trends)} error trends and {len(metrics)} metrics")

    # Generate insights
    insights = manager.generate_insights(config, error_trends, metrics)

    print(f"\nGenerated {len(insights)} insights:")
    for insight in insights:
        print(f"- {insight.title} (Severity: {insight.severity}, Confidence: {insight.confidence})")

if __name__ == "__main__":
    main()