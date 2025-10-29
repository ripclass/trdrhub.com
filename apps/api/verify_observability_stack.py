#!/usr/bin/env python3
"""
LCopilot Observability Stack Verification

Comprehensive verification script for the complete observability and resilience stack.
Validates all components across environments and provides detailed health reporting.

Components Verified:
- CloudWatch Dashboards
- Synthetic Canaries
- Chaos Engineering Setup
- SLO/SLA Reporting
- Security Monitoring
- Log Insights Queries

Usage:
    python3 verify_observability_stack.py --env prod --check all
    python3 verify_observability_stack.py --env staging --check dashboards,canaries
    python3 verify_observability_stack.py --env both --verbose --output report.json
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import concurrent.futures
import threading


@dataclass
class VerificationResult:
    """Result of a verification check."""
    component: str
    check_name: str
    status: str  # 'pass', 'fail', 'warning', 'skip'
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ObservabilityStackVerifier:
    """Comprehensive observability stack verifier."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None, verbose: bool = False):
        self.environment = environment
        self.aws_profile = aws_profile
        self.verbose = verbose

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})

        # AWS clients
        self.cloudwatch_client = None
        self.logs_client = None
        self.dynamodb_client = None
        self.s3_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Verification results
        self.results: List[VerificationResult] = []
        self.lock = threading.Lock()

    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'enterprise_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no config file exists."""
        return {
            'environments': {
                'staging': {
                    'aws_region': 'eu-north-1',
                    'aws_account_id': '111111111111',
                    'alarm_threshold': 3
                },
                'prod': {
                    'aws_region': 'eu-north-1',
                    'aws_account_id': '222222222222',
                    'alarm_threshold': 5
                }
            },
            'observability': {
                'enable_dashboards': True,
                'dashboards': {'cloudwatch_enabled': True},
                'canary': {'enabled': True}
            },
            'chaos': {
                'allowed_in_staging': True,
                'allowed_in_prod': False
            },
            'slo': {
                'reporting': {'enabled': True}
            },
            'security': {
                'enable_auth_alarms': True
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
            self.logs_client = session.client('logs')
            self.dynamodb_client = session.client('dynamodb')
            self.s3_client = session.client('s3')

            # Test connections
            self.cloudwatch_client.describe_alarms(MaxRecords=1)
            self.logs_client.describe_log_groups(limit=1)

            self._log(f"✅ AWS clients initialized for {self.region}")
            return True
        except Exception as e:
            self._log(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _add_result(self, result: VerificationResult):
        """Thread-safe method to add verification result."""
        with self.lock:
            self.results.append(result)

    def verify_dashboards(self) -> List[VerificationResult]:
        """Verify CloudWatch dashboards."""
        results = []
        component = "dashboards"

        try:
            # Check if dashboards are enabled
            dashboard_config = self.config.get('observability', {}).get('dashboards', {})
            if not dashboard_config.get('cloudwatch_enabled', True):
                results.append(VerificationResult(
                    component=component,
                    check_name="dashboard_enabled",
                    status="skip",
                    message="CloudWatch dashboards disabled in configuration"
                ))
                return results

            # Check if dashboard exists
            dashboard_name = f"lcopilot-health-{self.environment}"

            try:
                response = self.cloudwatch_client.get_dashboard(DashboardName=dashboard_name)
                dashboard_body = json.loads(response['DashboardBody'])

                results.append(VerificationResult(
                    component=component,
                    check_name="dashboard_exists",
                    status="pass",
                    message=f"Dashboard exists: {dashboard_name}",
                    details={'widget_count': len(dashboard_body.get('widgets', []))}
                ))

                # Validate dashboard structure
                widgets = dashboard_body.get('widgets', [])
                expected_widget_types = ['metric', 'log', 'text']
                found_types = set(widget.get('type') for widget in widgets)

                if not found_types.intersection(expected_widget_types):
                    results.append(VerificationResult(
                        component=component,
                        check_name="dashboard_structure",
                        status="warning",
                        message="Dashboard has unusual widget types",
                        details={'found_types': list(found_types)}
                    ))
                else:
                    results.append(VerificationResult(
                        component=component,
                        check_name="dashboard_structure",
                        status="pass",
                        message=f"Dashboard structure valid ({len(widgets)} widgets)"
                    ))

                # Check for essential widgets
                widget_titles = [w.get('properties', {}).get('title', '') for w in widgets]
                essential_widgets = ['Error Rate', 'Canary Success', 'Security Events']
                missing_widgets = [w for w in essential_widgets if not any(w in title for title in widget_titles)]

                if missing_widgets:
                    results.append(VerificationResult(
                        component=component,
                        check_name="essential_widgets",
                        status="warning",
                        message=f"Missing essential widgets: {', '.join(missing_widgets)}"
                    ))
                else:
                    results.append(VerificationResult(
                        component=component,
                        check_name="essential_widgets",
                        status="pass",
                        message="All essential widgets present"
                    ))

            except self.cloudwatch_client.exceptions.ResourceNotFound:
                results.append(VerificationResult(
                    component=component,
                    check_name="dashboard_exists",
                    status="fail",
                    message=f"Dashboard not found: {dashboard_name}"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="dashboard_verification",
                status="fail",
                message=f"Dashboard verification failed: {str(e)}"
            ))

        return results

    def verify_canaries(self) -> List[VerificationResult]:
        """Verify synthetic canary setup."""
        results = []
        component = "canaries"

        try:
            canary_config = self.config.get('observability', {}).get('canary', {})
            if not canary_config.get('enabled', True):
                results.append(VerificationResult(
                    component=component,
                    check_name="canary_enabled",
                    status="skip",
                    message="Canaries disabled in configuration"
                ))
                return results

            # Check for canary metrics
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)

            canary_metrics = [
                f'CanarySuccessRate-{self.environment}',
                f'CanaryLatencyMs-{self.environment}',
                f'CanaryScenarioDuration-{self.environment}'
            ]

            metrics_found = 0
            for metric_name in canary_metrics:
                try:
                    response = self.cloudwatch_client.get_metric_statistics(
                        Namespace='LCopilot',
                        MetricName=metric_name,
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=1800,
                        Statistics=['Average']
                    )

                    if response['Datapoints']:
                        metrics_found += 1
                        latest_value = response['Datapoints'][-1]['Average']
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"metric_{metric_name}",
                            status="pass",
                            message=f"Metric active with recent data: {latest_value}",
                            details={'metric_name': metric_name, 'latest_value': latest_value}
                        ))
                    else:
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"metric_{metric_name}",
                            status="warning",
                            message=f"No recent data for metric: {metric_name}"
                        ))

                except Exception as e:
                    results.append(VerificationResult(
                        component=component,
                        check_name=f"metric_{metric_name}",
                        status="fail",
                        message=f"Failed to check metric {metric_name}: {str(e)}"
                    ))

            # Overall canary health
            if metrics_found >= len(canary_metrics) // 2:
                results.append(VerificationResult(
                    component=component,
                    check_name="canary_health",
                    status="pass",
                    message=f"Canary system healthy ({metrics_found}/{len(canary_metrics)} metrics active)"
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="canary_health",
                    status="fail",
                    message=f"Canary system unhealthy ({metrics_found}/{len(canary_metrics)} metrics active)"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="canary_verification",
                status="fail",
                message=f"Canary verification failed: {str(e)}"
            ))

        return results

    def verify_chaos_engineering(self) -> List[VerificationResult]:
        """Verify chaos engineering setup."""
        results = []
        component = "chaos"

        try:
            chaos_config = self.config.get('chaos', {})

            # Check environment permissions
            if self.environment == 'prod':
                allowed = chaos_config.get('allowed_in_prod', False)
            else:
                allowed = chaos_config.get('allowed_in_staging', True)

            results.append(VerificationResult(
                component=component,
                check_name="environment_permissions",
                status="pass" if allowed else "warning",
                message=f"Chaos testing {'allowed' if allowed else 'restricted'} in {self.environment}"
            ))

            # Check fault type definitions
            fault_types = chaos_config.get('fault_types', {})
            enabled_faults = [name for name, config in fault_types.items() if config.get('enabled', False)]

            if enabled_faults:
                results.append(VerificationResult(
                    component=component,
                    check_name="fault_types",
                    status="pass",
                    message=f"Enabled fault types: {', '.join(enabled_faults)}",
                    details={'enabled_faults': enabled_faults}
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="fault_types",
                    status="warning",
                    message="No fault types enabled"
                ))

            # Check feature flags table (if configured)
            ff_config = chaos_config.get('feature_flags', {})
            table_name = ff_config.get('table_name', '').format(env=self.environment)

            if table_name:
                try:
                    response = self.dynamodb_client.describe_table(TableName=table_name)
                    results.append(VerificationResult(
                        component=component,
                        check_name="feature_flags_table",
                        status="pass",
                        message=f"Feature flags table exists: {table_name}",
                        details={'table_status': response['Table']['TableStatus']}
                    ))
                except self.dynamodb_client.exceptions.ResourceNotFoundException:
                    results.append(VerificationResult(
                        component=component,
                        check_name="feature_flags_table",
                        status="warning",
                        message=f"Feature flags table not found: {table_name}"
                    ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="feature_flags_table",
                    status="skip",
                    message="Feature flags table not configured"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="chaos_verification",
                status="fail",
                message=f"Chaos engineering verification failed: {str(e)}"
            ))

        return results

    def verify_slo_reporting(self) -> List[VerificationResult]:
        """Verify SLO/SLA reporting setup."""
        results = []
        component = "slo_reporting"

        try:
            slo_config = self.config.get('slo', {})
            reporting_config = slo_config.get('reporting', {})

            if not reporting_config.get('enabled', True):
                results.append(VerificationResult(
                    component=component,
                    check_name="slo_reporting_enabled",
                    status="skip",
                    message="SLO reporting disabled in configuration"
                ))
                return results

            # Check SLO targets
            targets = slo_config.get('targets', {}).get(self.environment, {})
            required_targets = ['error_rate_per_minute', 'canary_success_rate', 'p95_latency_seconds', 'availability_percent']

            missing_targets = [t for t in required_targets if t not in targets]
            if missing_targets:
                results.append(VerificationResult(
                    component=component,
                    check_name="slo_targets",
                    status="warning",
                    message=f"Missing SLO targets: {', '.join(missing_targets)}"
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="slo_targets",
                    status="pass",
                    message="All required SLO targets configured"
                ))

            # Check output bucket (if configured)
            bucket_name = reporting_config.get('output_bucket', '').format(env=self.environment)
            if bucket_name:
                try:
                    self.s3_client.head_bucket(Bucket=bucket_name)
                    results.append(VerificationResult(
                        component=component,
                        check_name="output_bucket",
                        status="pass",
                        message=f"Output bucket exists: {bucket_name}"
                    ))
                except Exception as e:
                    results.append(VerificationResult(
                        component=component,
                        check_name="output_bucket",
                        status="warning",
                        message=f"Output bucket issue: {str(e)}"
                    ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="output_bucket",
                    status="skip",
                    message="Output bucket not configured"
                ))

            # Check report sections
            sections = reporting_config.get('sections', [])
            essential_sections = ['executive_summary', 'slo_compliance']
            missing_sections = [s for s in essential_sections if s not in sections]

            if missing_sections:
                results.append(VerificationResult(
                    component=component,
                    check_name="report_sections",
                    status="warning",
                    message=f"Missing essential report sections: {', '.join(missing_sections)}"
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="report_sections",
                    status="pass",
                    message=f"Report sections configured ({len(sections)} sections)"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="slo_reporting_verification",
                status="fail",
                message=f"SLO reporting verification failed: {str(e)}"
            ))

        return results

    def verify_security_monitoring(self) -> List[VerificationResult]:
        """Verify security monitoring setup."""
        results = []
        component = "security"

        try:
            security_config = self.config.get('security', {})

            if not security_config.get('enable_auth_alarms', True):
                results.append(VerificationResult(
                    component=component,
                    check_name="security_monitoring_enabled",
                    status="skip",
                    message="Security monitoring disabled in configuration"
                ))
                return results

            # Check security alarms
            security_alarms = [
                f'lcopilot-auth-failures-{self.environment}',
                f'lcopilot-suspicious-ips-{self.environment}',
                f'lcopilot-high-risk-security-{self.environment}'
            ]

            alarms_found = 0
            for alarm_name in security_alarms:
                try:
                    response = self.cloudwatch_client.describe_alarms(AlarmNames=[alarm_name])
                    if response['MetricAlarms']:
                        alarm = response['MetricAlarms'][0]
                        alarms_found += 1
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"alarm_{alarm_name}",
                            status="pass",
                            message=f"Security alarm exists: {alarm_name}",
                            details={'state': alarm['StateValue'], 'threshold': alarm['Threshold']}
                        ))
                    else:
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"alarm_{alarm_name}",
                            status="warning",
                            message=f"Security alarm not found: {alarm_name}"
                        ))
                except Exception as e:
                    results.append(VerificationResult(
                        component=component,
                        check_name=f"alarm_{alarm_name}",
                        status="fail",
                        message=f"Failed to check alarm {alarm_name}: {str(e)}"
                    ))

            # Overall security monitoring health
            if alarms_found >= len(security_alarms) // 2:
                results.append(VerificationResult(
                    component=component,
                    check_name="security_monitoring_health",
                    status="pass",
                    message=f"Security monitoring healthy ({alarms_found}/{len(security_alarms)} alarms active)"
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="security_monitoring_health",
                    status="warning",
                    message=f"Security monitoring incomplete ({alarms_found}/{len(security_alarms)} alarms active)"
                ))

            # Check auth monitoring configuration
            auth_config = security_config.get('auth_monitoring', {})
            failure_threshold = auth_config.get('failure_threshold', {}).get(self.environment)

            if failure_threshold:
                results.append(VerificationResult(
                    component=component,
                    check_name="auth_threshold",
                    status="pass",
                    message=f"Auth failure threshold configured: {failure_threshold}",
                    details={'threshold': failure_threshold}
                ))
            else:
                results.append(VerificationResult(
                    component=component,
                    check_name="auth_threshold",
                    status="warning",
                    message="Auth failure threshold not configured"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="security_verification",
                status="fail",
                message=f"Security monitoring verification failed: {str(e)}"
            ))

        return results

    def verify_log_insights(self) -> List[VerificationResult]:
        """Verify log insights queries setup."""
        results = []
        component = "log_insights"

        try:
            # Check log groups exist
            expected_log_groups = [
                f'/aws/lambda/lcopilot-{self.environment}',
                f'/aws/apigateway/lcopilot-{self.environment}'
            ]

            log_groups_found = 0
            for log_group_name in expected_log_groups:
                try:
                    response = self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name,
                        limit=1
                    )
                    if response['logGroups']:
                        log_group = response['logGroups'][0]
                        log_groups_found += 1
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"log_group_{log_group_name}",
                            status="pass",
                            message=f"Log group exists: {log_group_name}",
                            details={'retention_days': log_group.get('retentionInDays', 'never_expire')}
                        ))
                    else:
                        results.append(VerificationResult(
                            component=component,
                            check_name=f"log_group_{log_group_name}",
                            status="warning",
                            message=f"Log group not found: {log_group_name}"
                        ))
                except Exception as e:
                    results.append(VerificationResult(
                        component=component,
                        check_name=f"log_group_{log_group_name}",
                        status="fail",
                        message=f"Failed to check log group {log_group_name}: {str(e)}"
                    ))

            # Check saved queries
            try:
                response = self.logs_client.describe_query_definitions(
                    queryDefinitionNamePrefix=f'lcopilot-{self.environment}-'
                )
                saved_queries = response.get('queryDefinitions', [])

                if saved_queries:
                    results.append(VerificationResult(
                        component=component,
                        check_name="saved_queries",
                        status="pass",
                        message=f"Found {len(saved_queries)} saved queries"
                    ))
                else:
                    results.append(VerificationResult(
                        component=component,
                        check_name="saved_queries",
                        status="warning",
                        message="No saved queries found"
                    ))

            except Exception as e:
                results.append(VerificationResult(
                    component=component,
                    check_name="saved_queries",
                    status="fail",
                    message=f"Failed to check saved queries: {str(e)}"
                ))

        except Exception as e:
            results.append(VerificationResult(
                component=component,
                check_name="log_insights_verification",
                status="fail",
                message=f"Log insights verification failed: {str(e)}"
            ))

        return results

    def run_verification(self, components: List[str]) -> List[VerificationResult]:
        """Run verification for specified components."""
        self.results = []

        verification_methods = {
            'dashboards': self.verify_dashboards,
            'canaries': self.verify_canaries,
            'chaos': self.verify_chaos_engineering,
            'slo_reporting': self.verify_slo_reporting,
            'security': self.verify_security_monitoring,
            'log_insights': self.verify_log_insights
        }

        # Run verifications in parallel for better performance
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_component = {}

            for component in components:
                if component in verification_methods:
                    future = executor.submit(verification_methods[component])
                    future_to_component[future] = component

            for future in concurrent.futures.as_completed(future_to_component):
                component = future_to_component[future]
                try:
                    component_results = future.result()
                    for result in component_results:
                        self._add_result(result)
                    self._log(f"✅ {component.title()} verification completed ({len(component_results)} checks)")
                except Exception as e:
                    error_result = VerificationResult(
                        component=component,
                        check_name="component_verification",
                        status="fail",
                        message=f"Component verification failed: {str(e)}"
                    )
                    self._add_result(error_result)
                    self._log(f"❌ {component.title()} verification failed: {e}")

        return self.results

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        if not self.results:
            return {'error': 'No verification results available'}

        # Count results by status
        status_counts = {'pass': 0, 'fail': 0, 'warning': 0, 'skip': 0}
        component_results = {}

        for result in self.results:
            status_counts[result.status] += 1

            if result.component not in component_results:
                component_results[result.component] = {'pass': 0, 'fail': 0, 'warning': 0, 'skip': 0}
            component_results[result.component][result.status] += 1

        # Calculate overall health score
        total_checks = len(self.results)
        health_score = 0
        if total_checks > 0:
            health_score = (
                (status_counts['pass'] * 1.0) +
                (status_counts['warning'] * 0.5) +
                (status_counts['skip'] * 0.3)
            ) / total_checks * 100

        # Determine overall status
        if status_counts['fail'] > 0:
            overall_status = 'unhealthy'
        elif status_counts['warning'] > total_checks // 2:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'

        return {
            'environment': self.environment,
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'health_score': round(health_score, 1),
            'total_checks': total_checks,
            'status_summary': status_counts,
            'component_summary': {
                component: {
                    'total_checks': sum(counts.values()),
                    'status_counts': counts,
                    'health_score': round(
                        (counts['pass'] * 1.0 + counts['warning'] * 0.5 + counts['skip'] * 0.3) /
                        max(1, sum(counts.values())) * 100, 1
                    )
                }
                for component, counts in component_results.items()
            },
            'detailed_results': [asdict(result) for result in self.results],
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on verification results."""
        recommendations = []

        # Analyze failures and warnings
        failed_components = set()
        warning_components = set()

        for result in self.results:
            if result.status == 'fail':
                failed_components.add(result.component)
            elif result.status == 'warning':
                warning_components.add(result.component)

        # Generate component-specific recommendations
        if 'dashboards' in failed_components:
            recommendations.append({
                'priority': 'high',
                'category': 'observability',
                'recommendation': 'Deploy CloudWatch dashboards using dashboard_manager.py',
                'command': f'python3 utils/dashboard_manager.py --env {self.environment} --deploy'
            })

        if 'canaries' in failed_components or 'canaries' in warning_components:
            recommendations.append({
                'priority': 'high',
                'category': 'monitoring',
                'recommendation': 'Set up synthetic canaries for golden path monitoring',
                'command': f'python3 canaries/golden_path_canary.py --env {self.environment} --scenario all --publish-metrics'
            })

        if 'security' in failed_components:
            recommendations.append({
                'priority': 'high',
                'category': 'security',
                'recommendation': 'Create security monitoring alarms',
                'command': f'python3 security/security_monitor.py --env {self.environment} --create-alarms'
            })

        if 'chaos' in warning_components:
            recommendations.append({
                'priority': 'medium',
                'category': 'resilience',
                'recommendation': 'Review chaos engineering configuration and enable fault types',
                'command': f'python3 chaos/chaos_controller.py --env {self.environment} --fault error_spike --duration 120'
            })

        # General recommendations if no specific issues
        if not failed_components and not warning_components:
            recommendations.append({
                'priority': 'low',
                'category': 'optimization',
                'recommendation': 'All systems healthy - consider running end-to-end validation tests',
                'command': 'make test-staging'  # or test-prod
            })

        return recommendations


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot Observability Stack Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 verify_observability_stack.py --env prod --check all
  python3 verify_observability_stack.py --env staging --check dashboards,canaries --verbose
  python3 verify_observability_stack.py --env both --output report.json
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod', 'both'],
                       default='prod', help='Environment to verify (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--check', default='all',
                       help='Components to check (all, dashboards, canaries, chaos, slo_reporting, security, log_insights)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--output', help='Save report to JSON file')

    args = parser.parse_args()

    # Parse components to check
    if args.check == 'all':
        components = ['dashboards', 'canaries', 'chaos', 'slo_reporting', 'security', 'log_insights']
    else:
        components = [c.strip() for c in args.check.split(',')]

    # Handle both environments
    environments = ['staging', 'prod'] if args.env == 'both' else [args.env]

    all_reports = {}

    for env in environments:
        print(f"\n{'='*70}")
        print(f"🔍 OBSERVABILITY STACK VERIFICATION - {env.upper()}")
        print(f"{'='*70}")

        # Initialize verifier
        verifier = ObservabilityStackVerifier(environment=env, aws_profile=args.profile, verbose=args.verbose)

        if not verifier.initialize_aws_clients():
            print(f"❌ Failed to initialize AWS clients for {env}")
            continue

        print(f"🚀 Running verification for components: {', '.join(components)}")

        # Run verification
        results = verifier.run_verification(components)

        # Generate summary report
        report = verifier.generate_summary_report()
        all_reports[env] = report

        # Display results
        print(f"\n📊 VERIFICATION RESULTS - {env.upper()}")
        print(f"Overall Status: {report['overall_status'].upper()}")
        print(f"Health Score: {report['health_score']}%")
        print(f"Total Checks: {report['total_checks']}")
        print(f"✅ Passed: {report['status_summary']['pass']}")
        print(f"⚠️  Warnings: {report['status_summary']['warning']}")
        print(f"❌ Failed: {report['status_summary']['fail']}")
        print(f"⏭️ Skipped: {report['status_summary']['skip']}")

        # Component breakdown
        print(f"\n📋 COMPONENT BREAKDOWN:")
        for component, summary in report['component_summary'].items():
            status_icon = "✅" if summary['health_score'] > 80 else ("⚠️" if summary['health_score'] > 50 else "❌")
            print(f"  {status_icon} {component.title()}: {summary['health_score']}% ({summary['total_checks']} checks)")

        # Recommendations
        if report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. [{rec['priority'].upper()}] {rec['recommendation']}")
                if 'command' in rec:
                    print(f"     Command: {rec['command']}")

        # Show detailed results if verbose
        if args.verbose:
            print(f"\n📝 DETAILED RESULTS:")
            for result in results:
                status_icon = {"pass": "✅", "fail": "❌", "warning": "⚠️", "skip": "⏭️"}[result.status]
                print(f"  {status_icon} [{result.component}] {result.check_name}: {result.message}")

    # Save report if requested
    if args.output:
        try:
            output_data = all_reports if len(all_reports) > 1 else list(all_reports.values())[0]
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"\n✅ Verification report saved to {args.output}")
        except Exception as e:
            print(f"\n❌ Failed to save report: {e}")

    # Exit with appropriate code
    exit_code = 0
    for env_report in all_reports.values():
        if env_report['overall_status'] == 'unhealthy':
            exit_code = 1
        elif env_report['overall_status'] == 'degraded' and exit_code == 0:
            exit_code = 2

    print(f"\n🎯 VERIFICATION COMPLETE")
    if exit_code == 0:
        print("🎉 All systems healthy!")
    elif exit_code == 1:
        print("❌ Critical issues found - immediate attention required")
    else:
        print("⚠️ Some issues detected - review and address when convenient")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()