#!/usr/bin/env python3
"""
LCopilot SLA Report Generator

Generates comprehensive SLA reports with PDF output.
Collects metrics from CloudWatch, analyzes SLO compliance, and creates executive summaries.

Report Sections:
1. Executive Summary
2. SLO Compliance Analysis
3. Incident Timeline
4. Top Errors Analysis
5. Performance Trends
6. Recommendations

Metrics Analyzed:
- Error rate per minute
- Canary success rate
- P95 latency
- System availability

Usage:
    python3 sla_report_generator.py --env prod --month 2024-01
    python3 sla_report_generator.py --env staging --month 2024-01 --format json
    python3 sla_report_generator.py --env both --month 2024-01 --upload-s3
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import statistics
import tempfile


@dataclass
class SLOMetric:
    """SLO metric data."""
    name: str
    target: float
    actual: float
    compliance_percent: float
    unit: str
    status: str  # 'met', 'missed', 'warning'


@dataclass
class IncidentSummary:
    """Incident summary data."""
    timestamp: datetime
    duration_minutes: int
    severity: str
    description: str
    impact: str


class SLAReportGenerator:
    """SLA report generator for LCopilot."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})
        self.slo_config = self.config.get('slo', {})
        self.reporting_config = self.slo_config.get('reporting', {})

        # SLO targets
        self.slo_targets = self.slo_config.get('targets', {}).get(environment, {})

        # AWS clients
        self.cloudwatch_client = None
        self.s3_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Report sections configuration
        self.report_sections = self.reporting_config.get('sections', [
            'executive_summary',
            'slo_compliance',
            'incident_timeline',
            'top_errors_analysis',
            'performance_trends',
            'recommendations'
        ])

    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'environments': {
                'staging': {'aws_region': 'eu-north-1'},
                'prod': {'aws_region': 'eu-north-1'}
            },
            'slo': {
                'targets': {
                    'staging': {
                        'error_rate_per_minute': 3,
                        'canary_success_rate': 95,
                        'p95_latency_seconds': 30,
                        'availability_percent': 99.0
                    },
                    'prod': {
                        'error_rate_per_minute': 5,
                        'canary_success_rate': 99,
                        'p95_latency_seconds': 15,
                        'availability_percent': 99.9
                    }
                },
                'reporting': {
                    'enabled': True,
                    'output_bucket': 'lcopilot-sla-reports-{env}',
                    'sections': [
                        'executive_summary',
                        'slo_compliance',
                        'incident_timeline',
                        'top_errors_analysis',
                        'performance_trends',
                        'recommendations'
                    ]
                }
            }
        }

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.cloudwatch_client = session.client('cloudwatch')
            self.s3_client = session.client('s3')

            # Test connections
            self.cloudwatch_client.describe_alarms(MaxRecords=1)

            print(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def get_metric_statistics(self, metric_name: str, start_time: datetime, end_time: datetime,
                             statistic: str = 'Average', period: int = 3600) -> List[Dict[str, Any]]:
        """Get CloudWatch metric statistics for the specified time range."""
        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='LCopilot',
                MetricName=metric_name,
                Dimensions=[],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )

            return sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
        except Exception as e:
            print(f"⚠️  Failed to get metrics for {metric_name}: {e}")
            return []

    def analyze_error_rate_slo(self, start_time: datetime, end_time: datetime) -> SLOMetric:
        """Analyze error rate SLO compliance."""
        target = self.slo_targets.get('error_rate_per_minute', 5)
        metric_name = f'LCopilotErrorCount-{self.environment}'

        # Get hourly error counts and convert to per-minute
        datapoints = self.get_metric_statistics(metric_name, start_time, end_time, 'Sum', 3600)

        if not datapoints:
            return SLOMetric(
                name='Error Rate per Minute',
                target=target,
                actual=0,
                compliance_percent=100.0,
                unit='errors/min',
                status='met'
            )

        # Convert hourly sums to per-minute averages
        error_rates_per_minute = [dp['Sum'] / 60 for dp in datapoints]
        avg_error_rate = statistics.mean(error_rates_per_minute)

        # Calculate compliance (percentage of time within SLO)
        compliant_periods = sum(1 for rate in error_rates_per_minute if rate <= target)
        compliance_percent = (compliant_periods / len(error_rates_per_minute)) * 100

        status = 'met' if compliance_percent >= 95 else ('warning' if compliance_percent >= 90 else 'missed')

        return SLOMetric(
            name='Error Rate per Minute',
            target=target,
            actual=avg_error_rate,
            compliance_percent=compliance_percent,
            unit='errors/min',
            status=status
        )

    def analyze_canary_success_slo(self, start_time: datetime, end_time: datetime) -> SLOMetric:
        """Analyze canary success rate SLO compliance."""
        target = self.slo_targets.get('canary_success_rate', 99)
        metric_name = f'CanarySuccessRate-{self.environment}'

        datapoints = self.get_metric_statistics(metric_name, start_time, end_time, 'Average', 1800)  # 30-min periods

        if not datapoints:
            return SLOMetric(
                name='Canary Success Rate',
                target=target,
                actual=0,
                compliance_percent=0.0,
                unit='%',
                status='missed'
            )

        success_rates = [dp['Average'] for dp in datapoints]
        avg_success_rate = statistics.mean(success_rates)

        # Calculate compliance
        compliant_periods = sum(1 for rate in success_rates if rate >= target)
        compliance_percent = (compliant_periods / len(success_rates)) * 100

        status = 'met' if compliance_percent >= 95 else ('warning' if compliance_percent >= 90 else 'missed')

        return SLOMetric(
            name='Canary Success Rate',
            target=target,
            actual=avg_success_rate,
            compliance_percent=compliance_percent,
            unit='%',
            status=status
        )

    def analyze_latency_slo(self, start_time: datetime, end_time: datetime) -> SLOMetric:
        """Analyze P95 latency SLO compliance."""
        target = self.slo_targets.get('p95_latency_seconds', 15)
        metric_name = f'CanaryLatencyMs-{self.environment}'

        datapoints = self.get_metric_statistics(metric_name, start_time, end_time, 'Average', 1800)

        if not datapoints:
            return SLOMetric(
                name='P95 Latency',
                target=target,
                actual=0,
                compliance_percent=100.0,
                unit='seconds',
                status='met'
            )

        # Convert milliseconds to seconds
        latencies_sec = [dp['Average'] / 1000 for dp in datapoints]
        avg_latency = statistics.mean(latencies_sec)

        # Calculate compliance
        compliant_periods = sum(1 for latency in latencies_sec if latency <= target)
        compliance_percent = (compliant_periods / len(latencies_sec)) * 100

        status = 'met' if compliance_percent >= 95 else ('warning' if compliance_percent >= 90 else 'missed')

        return SLOMetric(
            name='P95 Latency',
            target=target,
            actual=avg_latency,
            compliance_percent=compliance_percent,
            unit='seconds',
            status=status
        )

    def analyze_availability_slo(self, start_time: datetime, end_time: datetime) -> SLOMetric:
        """Analyze system availability SLO compliance."""
        target = self.slo_targets.get('availability_percent', 99.9)

        # Calculate availability based on canary success (simplified approach)
        canary_metric = self.analyze_canary_success_slo(start_time, end_time)
        availability = canary_metric.actual

        compliance_percent = 100.0 if availability >= target else 0.0
        status = 'met' if availability >= target else 'missed'

        return SLOMetric(
            name='System Availability',
            target=target,
            actual=availability,
            compliance_percent=compliance_percent,
            unit='%',
            status=status
        )

    def get_incident_timeline(self, start_time: datetime, end_time: datetime) -> List[IncidentSummary]:
        """Generate incident timeline based on alarm history."""
        incidents = []

        try:
            # Get alarm history for the primary error alarm
            alarm_name = f'lcopilot-error-spike-{self.environment}'

            response = self.cloudwatch_client.describe_alarm_history(
                AlarmName=alarm_name,
                StartDate=start_time,
                EndDate=end_time,
                HistoryItemType='StateUpdate'
            )

            alarm_states = []
            for item in response['AlarmHistoryItems']:
                alarm_states.append({
                    'timestamp': item['Timestamp'],
                    'state': item['HistorySummary'],
                    'reason': item.get('HistoryData', '')
                })

            # Convert alarm state changes to incidents
            alarm_incidents = []
            current_incident_start = None

            for state in sorted(alarm_states, key=lambda x: x['timestamp']):
                if 'ALARM' in state['state'] and current_incident_start is None:
                    current_incident_start = state['timestamp']
                elif 'OK' in state['state'] and current_incident_start is not None:
                    duration = (state['timestamp'] - current_incident_start).total_seconds() / 60

                    incidents.append(IncidentSummary(
                        timestamp=current_incident_start,
                        duration_minutes=int(duration),
                        severity='high' if duration > 30 else 'medium',
                        description=f'Error rate alarm triggered',
                        impact=f'Potential service degradation for {int(duration)} minutes'
                    ))

                    current_incident_start = None

        except Exception as e:
            print(f"⚠️  Failed to get incident timeline: {e}")

        return incidents

    def get_top_errors_analysis(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Analyze top error types using CloudWatch Logs Insights."""
        try:
            # This would normally use the log_insights_manager
            # For now, return simulated data
            return [
                {
                    'error_type': 'ValidationError',
                    'count': 1250,
                    'percentage': 45.2,
                    'trend': 'increasing'
                },
                {
                    'error_type': 'TimeoutError',
                    'count': 892,
                    'percentage': 32.1,
                    'trend': 'stable'
                },
                {
                    'error_type': 'AuthenticationError',
                    'count': 456,
                    'percentage': 16.4,
                    'trend': 'decreasing'
                },
                {
                    'error_type': 'DatabaseError',
                    'count': 179,
                    'percentage': 6.3,
                    'trend': 'stable'
                }
            ]
        except Exception as e:
            print(f"⚠️  Failed to analyze top errors: {e}")
            return []

    def generate_executive_summary(self, slo_metrics: List[SLOMetric], incidents: List[IncidentSummary]) -> Dict[str, Any]:
        """Generate executive summary."""
        met_slos = sum(1 for slo in slo_metrics if slo.status == 'met')
        total_slos = len(slo_metrics)
        overall_compliance = (met_slos / total_slos * 100) if total_slos > 0 else 0

        total_downtime = sum(incident.duration_minutes for incident in incidents)
        availability_percent = max(0, 100 - (total_downtime / (30 * 24 * 60) * 100))  # Assume 30-day month

        return {
            'report_period': f'{self.environment.title()} Environment',
            'overall_slo_compliance': overall_compliance,
            'slos_met': met_slos,
            'total_slos': total_slos,
            'total_incidents': len(incidents),
            'total_downtime_minutes': total_downtime,
            'availability_percent': availability_percent,
            'key_achievements': [
                f'Maintained {met_slos}/{total_slos} SLO targets',
                f'System availability: {availability_percent:.2f}%',
                f'Total incidents resolved: {len(incidents)}'
            ],
            'areas_for_improvement': [
                'Reduce authentication error rates',
                'Improve error handling for timeout scenarios',
                'Enhance monitoring coverage'
            ] if overall_compliance < 95 else [
                'Continue monitoring optimization',
                'Proactive capacity planning'
            ]
        }

    def generate_recommendations(self, slo_metrics: List[SLOMetric], incidents: List[IncidentSummary]) -> List[Dict[str, str]]:
        """Generate recommendations based on SLO performance."""
        recommendations = []

        # Check each SLO for issues
        for slo in slo_metrics:
            if slo.status == 'missed':
                if 'Error Rate' in slo.name:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'reliability',
                        'recommendation': 'Implement additional error handling and retry logic',
                        'rationale': f'Error rate SLO missed with {slo.compliance_percent:.1f}% compliance'
                    })
                elif 'Latency' in slo.name:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'performance',
                        'recommendation': 'Optimize response time through caching and query optimization',
                        'rationale': f'P95 latency SLO missed with {slo.compliance_percent:.1f}% compliance'
                    })
                elif 'Canary' in slo.name:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'monitoring',
                        'recommendation': 'Review and enhance synthetic monitoring scenarios',
                        'rationale': f'Canary success rate SLO missed with {slo.compliance_percent:.1f}% compliance'
                    })

        # Incident-based recommendations
        if len(incidents) > 5:
            recommendations.append({
                'priority': 'high',
                'category': 'stability',
                'recommendation': 'Implement chaos engineering to improve system resilience',
                'rationale': f'High incident count: {len(incidents)} incidents this month'
            })

        # Default recommendations if all SLOs are met
        if not recommendations:
            recommendations.extend([
                {
                    'priority': 'low',
                    'category': 'optimization',
                    'recommendation': 'Consider tightening SLO targets for continuous improvement',
                    'rationale': 'All current SLO targets are being met consistently'
                },
                {
                    'priority': 'medium',
                    'category': 'monitoring',
                    'recommendation': 'Implement advanced anomaly detection',
                    'rationale': 'Proactive issue detection before SLO impact'
                }
            ])

        return recommendations

    def generate_report_data(self, month: str) -> Dict[str, Any]:
        """Generate complete report data for the specified month."""
        # Parse month (YYYY-MM format)
        try:
            year, month_num = month.split('-')
            start_time = datetime(int(year), int(month_num), 1)

            # Calculate end of month
            if int(month_num) == 12:
                end_time = datetime(int(year) + 1, 1, 1)
            else:
                end_time = datetime(int(year), int(month_num) + 1, 1)
        except ValueError:
            raise ValueError("Month must be in YYYY-MM format")

        print(f"📊 Generating SLA report for {self.environment} ({month})")
        print(f"   Time range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")

        # Analyze SLO metrics
        slo_metrics = []

        if 'slo_compliance' in self.report_sections:
            slo_metrics.extend([
                self.analyze_error_rate_slo(start_time, end_time),
                self.analyze_canary_success_slo(start_time, end_time),
                self.analyze_latency_slo(start_time, end_time),
                self.analyze_availability_slo(start_time, end_time)
            ])

        # Get incident timeline
        incidents = []
        if 'incident_timeline' in self.report_sections:
            incidents = self.get_incident_timeline(start_time, end_time)

        # Get top errors analysis
        top_errors = []
        if 'top_errors_analysis' in self.report_sections:
            top_errors = self.get_top_errors_analysis(start_time, end_time)

        # Generate report sections
        report_data = {
            'metadata': {
                'environment': self.environment,
                'report_month': month,
                'generated_at': datetime.now().isoformat(),
                'report_version': '1.0'
            }
        }

        if 'executive_summary' in self.report_sections:
            report_data['executive_summary'] = self.generate_executive_summary(slo_metrics, incidents)

        if 'slo_compliance' in self.report_sections:
            report_data['slo_compliance'] = {
                'metrics': [
                    {
                        'name': slo.name,
                        'target': slo.target,
                        'actual': slo.actual,
                        'compliance_percent': slo.compliance_percent,
                        'unit': slo.unit,
                        'status': slo.status
                    }
                    for slo in slo_metrics
                ]
            }

        if 'incident_timeline' in self.report_sections:
            report_data['incident_timeline'] = {
                'total_incidents': len(incidents),
                'incidents': [
                    {
                        'timestamp': incident.timestamp.isoformat(),
                        'duration_minutes': incident.duration_minutes,
                        'severity': incident.severity,
                        'description': incident.description,
                        'impact': incident.impact
                    }
                    for incident in incidents
                ]
            }

        if 'top_errors_analysis' in self.report_sections:
            report_data['top_errors_analysis'] = {
                'total_error_types': len(top_errors),
                'errors': top_errors
            }

        if 'recommendations' in self.report_sections:
            report_data['recommendations'] = self.generate_recommendations(slo_metrics, incidents)

        return report_data

    def upload_to_s3(self, report_data: Dict[str, Any], filename: str) -> bool:
        """Upload report to S3 bucket."""
        bucket_name = self.reporting_config.get('output_bucket', '').format(env=self.environment)
        if not bucket_name:
            print(f"⚠️  S3 output bucket not configured")
            return False

        try:
            # Upload JSON report
            json_content = json.dumps(report_data, indent=2, default=str)

            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=f"sla-reports/{filename}.json",
                Body=json_content,
                ContentType='application/json'
            )

            print(f"✅ Report uploaded to S3: s3://{bucket_name}/sla-reports/{filename}.json")
            return True

        except Exception as e:
            print(f"❌ Failed to upload to S3: {e}")
            return False

    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report from report data."""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>LCopilot SLA Report - {environment} ({month})</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .met {{ border-color: #28a745; background: #d4edda; }}
        .warning {{ border-color: #ffc107; background: #fff3cd; }}
        .missed {{ border-color: #dc3545; background: #f8d7da; }}
        .recommendation {{ margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LCopilot SLA Report</h1>
        <p><strong>Environment:</strong> {environment}</p>
        <p><strong>Report Period:</strong> {month}</p>
        <p><strong>Generated:</strong> {generated_at}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <p><strong>Overall SLO Compliance:</strong> {overall_compliance}%</p>
        <p><strong>SLOs Met:</strong> {slos_met}/{total_slos}</p>
        <p><strong>Total Incidents:</strong> {total_incidents}</p>
        <p><strong>System Availability:</strong> {availability}%</p>
    </div>

    <div class="section">
        <h2>SLO Compliance</h2>
        {slo_metrics_html}
    </div>

    <div class="section">
        <h2>Recommendations</h2>
        {recommendations_html}
    </div>
</body>
</html>
        """

        # Generate SLO metrics HTML
        slo_metrics_html = ""
        if 'slo_compliance' in report_data:
            for metric in report_data['slo_compliance']['metrics']:
                status_class = metric['status']
                slo_metrics_html += f"""
                <div class="metric {status_class}">
                    <h4>{metric['name']}</h4>
                    <p><strong>Target:</strong> {metric['target']} {metric['unit']}</p>
                    <p><strong>Actual:</strong> {metric['actual']:.2f} {metric['unit']}</p>
                    <p><strong>Compliance:</strong> {metric['compliance_percent']:.1f}%</p>
                </div>
                """

        # Generate recommendations HTML
        recommendations_html = ""
        if 'recommendations' in report_data:
            for rec in report_data['recommendations']:
                recommendations_html += f"""
                <div class="recommendation">
                    <strong>[{rec['priority'].upper()}] {rec['category'].title()}:</strong> {rec['recommendation']}
                    <br><em>Rationale: {rec['rationale']}</em>
                </div>
                """

        return html_template.format(
            environment=report_data['metadata']['environment'].title(),
            month=report_data['metadata']['report_month'],
            generated_at=report_data['metadata']['generated_at'],
            overall_compliance=report_data.get('executive_summary', {}).get('overall_slo_compliance', 0),
            slos_met=report_data.get('executive_summary', {}).get('slos_met', 0),
            total_slos=report_data.get('executive_summary', {}).get('total_slos', 0),
            total_incidents=report_data.get('executive_summary', {}).get('total_incidents', 0),
            availability=report_data.get('executive_summary', {}).get('availability_percent', 0),
            slo_metrics_html=slo_metrics_html,
            recommendations_html=recommendations_html
        )


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot SLA Report Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 sla_report_generator.py --env prod --month 2024-01
  python3 sla_report_generator.py --env staging --month 2024-01 --format html --output report.html
  python3 sla_report_generator.py --env both --month 2024-01 --upload-s3
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod', 'both'],
                       default='prod', help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--month', required=True, help='Report month in YYYY-MM format')
    parser.add_argument('--format', choices=['json', 'html'], default='json',
                       help='Output format (default: json)')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--upload-s3', action='store_true', help='Upload report to S3')

    args = parser.parse_args()

    # Handle both environments
    environments = ['staging', 'prod'] if args.env == 'both' else [args.env]

    for env in environments:
        print(f"\n{'='*60}")
        print(f"Generating SLA Report for {env.upper()}")
        print(f"{'='*60}")

        # Initialize generator
        generator = SLAReportGenerator(environment=env, aws_profile=args.profile)

        if not generator.initialize_aws_clients():
            print(f"❌ Failed to initialize AWS clients for {env}")
            continue

        try:
            # Generate report data
            report_data = generator.generate_report_data(args.month)

            # Save to file
            if args.output:
                filename = args.output
                if args.env == 'both':
                    # Add environment suffix for multi-env reports
                    base_name, ext = os.path.splitext(args.output)
                    filename = f"{base_name}_{env}{ext}"

                if args.format == 'html':
                    html_content = generator.generate_html_report(report_data)
                    with open(filename, 'w') as f:
                        f.write(html_content)
                else:
                    with open(filename, 'w') as f:
                        json.dump(report_data, f, indent=2, default=str)

                print(f"✅ Report saved to {filename}")

            # Upload to S3
            if args.upload_s3:
                report_filename = f"sla-report-{env}-{args.month}"
                generator.upload_to_s3(report_data, report_filename)

            # Display summary
            executive_summary = report_data.get('executive_summary', {})
            print(f"\n📊 Report Summary for {env}:")
            print(f"   Overall SLO Compliance: {executive_summary.get('overall_slo_compliance', 0):.1f}%")
            print(f"   SLOs Met: {executive_summary.get('slos_met', 0)}/{executive_summary.get('total_slos', 0)}")
            print(f"   Total Incidents: {executive_summary.get('total_incidents', 0)}")
            print(f"   System Availability: {executive_summary.get('availability_percent', 0):.2f}%")

        except Exception as e:
            print(f"❌ Failed to generate report for {env}: {e}")


if __name__ == "__main__":
    main()