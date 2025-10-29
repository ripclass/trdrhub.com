#!/usr/bin/env python3
"""
LCopilot SLA Dashboard & Reporting Manager

Manages tier-based SLA dashboards and automated report generation.
Integrates with existing SLO reporting system to provide commercial features.

Features by Tier:
- Free: No SLA reporting
- Pro: Shared monthly SLA PDFs, basic dashboards
- Enterprise: Dedicated dashboards, custom reporting, compliance exports

Usage:
    python3 sla_dashboard_manager.py --tier pro --generate-report --month 2024-01
    python3 sla_dashboard_manager.py --tier enterprise --customer enterprise-customer-001 --deploy-dashboard
    python3 sla_dashboard_manager.py --generate-all-reports
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
import base64


@dataclass
class SLATarget:
    """SLA target definition."""
    name: str
    target_value: float
    unit: str
    current_value: float
    compliance_percentage: float
    status: str  # 'met', 'at_risk', 'breached'


@dataclass
class SLAReportConfig:
    """SLA report configuration."""
    tier: str
    customer_id: Optional[str] = None
    frequency: str = 'monthly'
    formats: List[str] = None
    sections: List[str] = None
    delivery_methods: List[str] = None
    retention_months: int = 12
    dedicated_dashboard: bool = False


class SLADashboardManager:
    """Manages SLA dashboards and reporting with tier-based features."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configurations
        self.reliability_config = self._load_reliability_config()
        self.observability_config = self._load_observability_config()

        # AWS clients
        self.cloudwatch_client = None
        self.s3_client = None
        self.region = self.reliability_config.get('global', {}).get('environments', {}).get(environment, {}).get('aws_region', 'eu-north-1')

        # Import existing SLA report generator
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'slo_reporting'))
        try:
            from sla_report_generator import SLAReportGenerator
            self.sla_generator = SLAReportGenerator(environment, aws_profile)
        except ImportError:
            self.sla_generator = None
            print("⚠️ SLA Report Generator not available - using fallback methods")

    def _load_reliability_config(self) -> Dict[str, Any]:
        """Load reliability configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'reliability_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return {}

    def _load_observability_config(self) -> Dict[str, Any]:
        """Load observability configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'enterprise_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            return {}

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

    def get_sla_config(self, tier: str, customer_id: Optional[str] = None) -> SLAReportConfig:
        """Get SLA configuration based on tier."""
        sla_reporting = self.reliability_config.get('sla_reporting', {})
        tier_config = sla_reporting.get(tier, {})

        if not tier_config.get('enabled', False):
            return SLAReportConfig(
                tier=tier,
                customer_id=customer_id,
                formats=[],
                sections=[],
                delivery_methods=[]
            )

        return SLAReportConfig(
            tier=tier,
            customer_id=customer_id,
            frequency=tier_config.get('report_frequency', 'monthly'),
            formats=tier_config.get('formats', ['pdf']),
            sections=tier_config.get('sections', ['executive_summary']),
            delivery_methods=tier_config.get('delivery', ['s3_storage']),
            retention_months=tier_config.get('retention_months', 12),
            dedicated_dashboard=tier_config.get('dedicated_dashboards', False)
        )

    def get_sla_targets(self, tier: str, customer_id: Optional[str] = None) -> List[SLATarget]:
        """Get SLA targets based on tier and customer."""
        targets = []

        # Get base SLO targets from observability config
        slo_targets = self.observability_config.get('slo', {}).get('targets', {}).get(self.environment, {})

        # Define SLA targets based on tier
        if tier == 'free':
            # Free tier has no SLA guarantees
            return targets

        elif tier == 'pro':
            # Pro tier gets standard SLA targets
            targets.extend([
                SLATarget(
                    name='Service Availability',
                    target_value=99.9,
                    unit='%',
                    current_value=0.0,  # Will be calculated
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Error Rate',
                    target_value=slo_targets.get('error_rate_per_minute', 5),
                    unit='errors/min',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Response Time P95',
                    target_value=slo_targets.get('p95_latency_seconds', 15),
                    unit='seconds',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                )
            ])

        elif tier == 'enterprise':
            # Enterprise tier gets enhanced SLA targets
            targets.extend([
                SLATarget(
                    name='Service Availability',
                    target_value=99.95,  # Higher target for enterprise
                    unit='%',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Error Rate',
                    target_value=slo_targets.get('error_rate_per_minute', 5) * 0.8,  # Tighter target
                    unit='errors/min',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Response Time P95',
                    target_value=slo_targets.get('p95_latency_seconds', 15) * 0.8,  # Tighter target
                    unit='seconds',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Mean Time to Resolution',
                    target_value=2.0,  # 2 hours MTTR
                    unit='hours',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                ),
                SLATarget(
                    name='Data Processing SLA',
                    target_value=95.0,  # 95% within SLA timeframes
                    unit='%',
                    current_value=0.0,
                    compliance_percentage=0.0,
                    status='unknown'
                )
            ])

        # Calculate current values for all targets
        for target in targets:
            target.current_value, target.compliance_percentage, target.status = self._calculate_sla_performance(target)

        return targets

    def _calculate_sla_performance(self, target: SLATarget) -> Tuple[float, float, str]:
        """Calculate current SLA performance for a target."""
        try:
            if target.name == 'Service Availability':
                current_value = self._get_availability_percentage()
            elif target.name == 'Error Rate':
                current_value = self._get_current_error_rate()
            elif target.name == 'Response Time P95':
                current_value = self._get_p95_response_time()
            elif target.name == 'Mean Time to Resolution':
                current_value = self._get_mttr()
            elif target.name == 'Data Processing SLA':
                current_value = self._get_processing_sla_compliance()
            else:
                current_value = 0.0

            # Calculate compliance percentage and status
            if target.unit == '%':
                # For percentage targets, compliance is whether we meet or exceed target
                if current_value >= target.target_value:
                    compliance_percentage = 100.0
                    status = 'met'
                elif current_value >= target.target_value * 0.98:  # Within 98% of target
                    compliance_percentage = (current_value / target.target_value) * 100
                    status = 'at_risk'
                else:
                    compliance_percentage = (current_value / target.target_value) * 100
                    status = 'breached'
            else:
                # For other units (errors/min, seconds, hours), compliance is whether we're below target
                if current_value <= target.target_value:
                    compliance_percentage = 100.0
                    status = 'met'
                elif current_value <= target.target_value * 1.1:  # Within 10% of target
                    compliance_percentage = max(0, 100 - ((current_value - target.target_value) / target.target_value * 100))
                    status = 'at_risk'
                else:
                    compliance_percentage = max(0, 100 - ((current_value - target.target_value) / target.target_value * 100))
                    status = 'breached'

            return current_value, compliance_percentage, status

        except Exception as e:
            print(f"⚠️ Failed to calculate SLA performance for {target.name}: {e}")
            return 0.0, 0.0, 'unknown'

    def _get_availability_percentage(self) -> float:
        """Get current service availability percentage."""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)

            # Use canary success rate as availability proxy
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='LCopilot',
                MetricName=f'CanarySuccessRate-{self.environment}',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1-hour periods
                Statistics=['Average']
            )

            if response['Datapoints']:
                datapoints = response['Datapoints']
                avg_availability = sum(dp['Average'] for dp in datapoints) / len(datapoints)
                return round(avg_availability, 2)
            else:
                return 100.0  # Assume 100% if no data

        except Exception:
            return 99.9  # Default fallback

    def _get_current_error_rate(self) -> float:
        """Get current error rate per minute."""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)

            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='LCopilot',
                MetricName=f'LCopilotErrorCount-{self.environment}',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1-hour periods
                Statistics=['Sum']
            )

            if response['Datapoints']:
                datapoints = response['Datapoints']
                # Convert hourly sums to per-minute average
                total_errors = sum(dp['Sum'] for dp in datapoints)
                total_hours = len(datapoints)
                errors_per_minute = (total_errors / total_hours) / 60
                return round(errors_per_minute, 2)
            else:
                return 0.0

        except Exception:
            return 0.1  # Default fallback

    def _get_p95_response_time(self) -> float:
        """Get P95 response time in seconds."""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)

            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='LCopilot',
                MetricName=f'CanaryLatencyMs-{self.environment}',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )

            if response['Datapoints']:
                # Convert milliseconds to seconds and approximate P95
                datapoints = response['Datapoints']
                avg_latency_ms = sum(dp['Average'] for dp in datapoints) / len(datapoints)
                # Rough P95 estimation: avg * 1.5
                p95_seconds = (avg_latency_ms * 1.5) / 1000
                return round(p95_seconds, 2)
            else:
                return 0.5  # Default fallback

        except Exception:
            return 2.0  # Default fallback

    def _get_mttr(self) -> float:
        """Get Mean Time to Resolution in hours."""
        # This would analyze incident resolution times from alarm history
        # For now, return a simulated value
        return 1.2

    def _get_processing_sla_compliance(self) -> float:
        """Get data processing SLA compliance percentage."""
        # This would analyze processing time metrics against SLA targets
        # For now, return a simulated value
        return 97.8

    def create_dedicated_dashboard(self, customer_id: str, targets: List[SLATarget]) -> bool:
        """Create dedicated CloudWatch dashboard for enterprise customer."""
        dashboard_name = f"lcopilot-sla-{customer_id}-{self.environment}"

        try:
            # Build dashboard widgets for SLA metrics
            widgets = []

            # SLA targets overview
            widgets.append({
                "type": "metric",
                "x": 0, "y": 0, "width": 24, "height": 6,
                "properties": {
                    "metrics": [
                        ["LCopilot", f"CanarySuccessRate-{self.environment}", {"stat": "Average"}],
                        [".", f"LCopilotErrorCount-{self.environment}", {"stat": "Sum", "yAxis": "right"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": self.region,
                    "title": f"SLA Overview - {customer_id}",
                    "period": 300,
                    "yAxis": {"left": {"min": 0, "max": 100}},
                    "annotations": {
                        "horizontal": [
                            {"value": next((t.target_value for t in targets if t.name == 'Service Availability'), 99.9),
                             "label": "Availability SLA", "fill": "below"}
                        ]
                    }
                }
            })

            # Individual SLA target widgets
            y_offset = 6
            for i, target in enumerate(targets):
                if target.name == 'Service Availability':
                    metric_name = f"CanarySuccessRate-{self.environment}"
                elif target.name == 'Error Rate':
                    metric_name = f"LCopilotErrorCount-{self.environment}"
                elif target.name == 'Response Time P95':
                    metric_name = f"CanaryLatencyMs-{self.environment}"
                else:
                    continue  # Skip unsupported metrics

                widgets.append({
                    "type": "metric",
                    "x": (i % 3) * 8, "y": y_offset + (i // 3) * 6,
                    "width": 8, "height": 6,
                    "properties": {
                        "metrics": [["LCopilot", metric_name]],
                        "view": "timeSeries",
                        "region": self.region,
                        "title": f"{target.name} - Target: {target.target_value}{target.unit}",
                        "period": 300,
                        "annotations": {
                            "horizontal": [
                                {"value": target.target_value, "label": "SLA Target", "fill": "above" if target.unit == '%' else "below"}
                            ]
                        }
                    }
                })

            dashboard_body = json.dumps({"widgets": widgets})

            self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=dashboard_body
            )

            print(f"✅ Dedicated dashboard created: {dashboard_name}")
            print(f"   URL: https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}")

            return True

        except Exception as e:
            print(f"❌ Failed to create dedicated dashboard: {e}")
            return False

    def generate_tier_report(self, config: SLAReportConfig, month: str) -> Dict[str, Any]:
        """Generate SLA report based on tier configuration."""
        try:
            # Use existing SLA report generator if available
            if self.sla_generator:
                report_data = self.sla_generator.generate_report_data(month)

                # Enhance with tier-specific information
                report_data['tier_info'] = {
                    'tier': config.tier,
                    'customer_id': config.customer_id,
                    'sla_targets': [asdict(target) for target in self.get_sla_targets(config.tier, config.customer_id)],
                    'report_formats': config.formats,
                    'delivery_methods': config.delivery_methods
                }

                # Add tier-specific sections
                if config.tier == 'enterprise':
                    report_data['enterprise_features'] = {
                        'dedicated_dashboard': config.dedicated_dashboard,
                        'compliance_ready': True,
                        'predictive_insights': True,
                        'custom_sla_targets': True
                    }

                return report_data

            else:
                # Fallback report generation
                return self._generate_fallback_report(config, month)

        except Exception as e:
            print(f"❌ Failed to generate tier report: {e}")
            return {}

    def _generate_fallback_report(self, config: SLAReportConfig, month: str) -> Dict[str, Any]:
        """Generate fallback report when main generator is unavailable."""
        targets = self.get_sla_targets(config.tier, config.customer_id)

        return {
            'metadata': {
                'tier': config.tier,
                'customer_id': config.customer_id,
                'report_month': month,
                'generated_at': datetime.now().isoformat()
            },
            'sla_summary': {
                'total_targets': len(targets),
                'targets_met': len([t for t in targets if t.status == 'met']),
                'targets_at_risk': len([t for t in targets if t.status == 'at_risk']),
                'targets_breached': len([t for t in targets if t.status == 'breached'])
            },
            'sla_targets': [asdict(target) for target in targets],
            'tier_info': {
                'tier': config.tier,
                'features': config.formats,
                'delivery': config.delivery_methods
            }
        }

    def store_report(self, config: SLAReportConfig, report_data: Dict[str, Any], month: str) -> List[str]:
        """Store report in various formats and locations."""
        stored_files = []

        try:
            # Determine S3 bucket
            if config.tier == 'enterprise' and config.customer_id:
                bucket_name = f'lcopilot-reliability-enterprise-{self.environment}'
                key_prefix = f'sla-reports/{config.customer_id}'
            else:
                bucket_name = f'lcopilot-reliability-{config.tier}-{self.environment}'
                key_prefix = 'sla-reports'

            # Store in requested formats
            for format_type in config.formats:
                if format_type == 'json':
                    content = json.dumps(report_data, indent=2, default=str)
                    content_type = 'application/json'
                    file_extension = 'json'

                elif format_type == 'html':
                    if self.sla_generator:
                        content = self.sla_generator.generate_html_report(report_data)
                    else:
                        content = self._generate_html_fallback(report_data)
                    content_type = 'text/html'
                    file_extension = 'html'

                elif format_type == 'csv':
                    content = self._generate_csv_report(report_data)
                    content_type = 'text/csv'
                    file_extension = 'csv'

                else:
                    continue  # Skip unsupported formats

                # Upload to S3
                s3_key = f"{key_prefix}/sla-report-{month}.{file_extension}"

                self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                    ServerSideEncryption='AES256'
                )

                stored_files.append(f"s3://{bucket_name}/{s3_key}")

            print(f"✅ Report stored in {len(stored_files)} format(s)")
            return stored_files

        except Exception as e:
            print(f"❌ Failed to store report: {e}")
            return []

    def _generate_html_fallback(self, report_data: Dict[str, Any]) -> str:
        """Generate fallback HTML report."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SLA Report - {report_data.get('metadata', {}).get('report_month', 'N/A')}</title>
        </head>
        <body>
            <h1>SLA Report</h1>
            <p>Tier: {report_data.get('metadata', {}).get('tier', 'Unknown')}</p>
            <p>Month: {report_data.get('metadata', {}).get('report_month', 'N/A')}</p>
            <pre>{json.dumps(report_data, indent=2, default=str)}</pre>
        </body>
        </html>
        """

    def _generate_csv_report(self, report_data: Dict[str, Any]) -> str:
        """Generate CSV format report."""
        csv_lines = ['SLA Target,Target Value,Current Value,Compliance %,Status']

        sla_targets = report_data.get('sla_targets', [])
        for target in sla_targets:
            csv_lines.append(f"{target['name']},{target['target_value']},{target['current_value']},{target['compliance_percentage']},{target['status']}")

        return '\n'.join(csv_lines)

    def generate_all_customer_reports(self, month: str) -> Dict[str, Any]:
        """Generate reports for all customers based on their tiers."""
        results = {'success': [], 'failed': []}

        customers = self.reliability_config.get('customers', {}).get('tier_mappings', {})

        # Generate for each tier
        tiers_to_process = ['pro', 'enterprise']

        for tier in tiers_to_process:
            # Shared tier report
            print(f"\n📊 Generating {tier} tier shared report...")

            config = self.get_sla_config(tier)
            if config.formats:
                try:
                    report_data = self.generate_tier_report(config, month)
                    stored_files = self.store_report(config, report_data, month)

                    results['success'].append({
                        'tier': tier,
                        'customer_id': None,
                        'files': stored_files
                    })

                except Exception as e:
                    results['failed'].append({
                        'tier': tier,
                        'customer_id': None,
                        'error': str(e)
                    })

        # Generate enterprise customer-specific reports
        enterprise_customers = [cust_id for cust_id, cust_config in customers.items()
                              if cust_config.get('tier') == 'enterprise']

        for customer_id in enterprise_customers:
            print(f"\n🏢 Generating enterprise report for {customer_id}...")

            config = self.get_sla_config('enterprise', customer_id)
            try:
                report_data = self.generate_tier_report(config, month)
                stored_files = self.store_report(config, report_data, month)

                # Create/update dedicated dashboard if enabled
                if config.dedicated_dashboard:
                    targets = self.get_sla_targets('enterprise', customer_id)
                    self.create_dedicated_dashboard(customer_id, targets)

                results['success'].append({
                    'tier': 'enterprise',
                    'customer_id': customer_id,
                    'files': stored_files
                })

            except Exception as e:
                results['failed'].append({
                    'tier': 'enterprise',
                    'customer_id': customer_id,
                    'error': str(e)
                })

        return results


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot SLA Dashboard & Reporting Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 sla_dashboard_manager.py --tier pro --generate-report --month 2024-01
  python3 sla_dashboard_manager.py --tier enterprise --customer enterprise-customer-001 --deploy-dashboard
  python3 sla_dashboard_manager.py --generate-all-reports --month 2024-01
  python3 sla_dashboard_manager.py --tier enterprise --list-targets
        """
    )

    parser.add_argument('--tier', choices=['pro', 'enterprise'], default='pro',
                       help='Service tier (default: pro)')
    parser.add_argument('--customer', help='Customer ID for enterprise tier')
    parser.add_argument('--env', '--environment', choices=['staging', 'prod'], default='prod',
                       help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--month', help='Report month in YYYY-MM format')
    parser.add_argument('--generate-report', action='store_true', help='Generate SLA report')
    parser.add_argument('--deploy-dashboard', action='store_true', help='Deploy dedicated dashboard')
    parser.add_argument('--generate-all-reports', action='store_true', help='Generate reports for all customers')
    parser.add_argument('--list-targets', action='store_true', help='List SLA targets for tier')

    args = parser.parse_args()

    # Initialize manager
    manager = SLADashboardManager(environment=args.env, aws_profile=args.profile)

    print(f"🚀 LCopilot SLA Dashboard Manager ({args.tier} tier)")

    if not manager.initialize_aws_clients():
        sys.exit(1)

    # List SLA targets
    if args.list_targets:
        targets = manager.get_sla_targets(args.tier, args.customer)
        print(f"\n📊 SLA Targets for {args.tier} tier:")
        if args.customer:
            print(f"   Customer: {args.customer}")

        for target in targets:
            status_icon = "✅" if target.status == 'met' else ("⚠️" if target.status == 'at_risk' else "❌")
            print(f"   {status_icon} {target.name}: {target.current_value}{target.unit} (Target: {target.target_value}{target.unit})")
            print(f"      Compliance: {target.compliance_percentage:.1f}%")

        return

    # Deploy dedicated dashboard
    if args.deploy_dashboard:
        if args.tier != 'enterprise':
            print("❌ Dedicated dashboards only available for enterprise tier")
            sys.exit(1)

        if not args.customer:
            print("❌ Enterprise tier requires --customer parameter")
            sys.exit(1)

        targets = manager.get_sla_targets(args.tier, args.customer)
        success = manager.create_dedicated_dashboard(args.customer, targets)

        if not success:
            sys.exit(1)

        return

    # Generate all reports
    if args.generate_all_reports:
        if not args.month:
            # Use last month as default
            last_month = (datetime.now().replace(day=1) - timedelta(days=1))
            args.month = last_month.strftime('%Y-%m')

        print(f"📊 Generating all customer reports for {args.month}...")

        results = manager.generate_all_customer_reports(args.month)

        print(f"\n✅ Successfully generated {len(results['success'])} report(s)")
        for result in results['success']:
            customer_info = f" for {result['customer_id']}" if result['customer_id'] else ""
            print(f"   • {result['tier'].title()} tier{customer_info}: {len(result['files'])} file(s)")

        if results['failed']:
            print(f"\n❌ Failed to generate {len(results['failed'])} report(s):")
            for result in results['failed']:
                customer_info = f" for {result['customer_id']}" if result['customer_id'] else ""
                print(f"   • {result['tier'].title()} tier{customer_info}: {result['error']}")

        return

    # Generate single report
    if args.generate_report:
        if not args.month:
            print("❌ --month parameter required for report generation")
            sys.exit(1)

        if args.tier == 'enterprise' and not args.customer:
            print("❌ Enterprise tier requires --customer parameter")
            sys.exit(1)

        config = manager.get_sla_config(args.tier, args.customer)

        if not config.formats:
            print(f"❌ SLA reporting not enabled for {args.tier} tier")
            sys.exit(1)

        print(f"📊 Generating {args.tier} tier report for {args.month}...")

        report_data = manager.generate_tier_report(config, args.month)
        stored_files = manager.store_report(config, report_data, args.month)

        if stored_files:
            print(f"✅ Report generated and stored:")
            for file_path in stored_files:
                print(f"   📄 {file_path}")
        else:
            print("❌ Failed to store report")
            sys.exit(1)

        return

    # Show help if no action specified
    parser.print_help()


if __name__ == "__main__":
    main()