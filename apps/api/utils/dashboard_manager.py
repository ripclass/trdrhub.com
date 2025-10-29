#!/usr/bin/env python3
"""
CloudWatch Dashboard Manager

Manages CloudWatch dashboards for enterprise monitoring.
Provides utilities for creating, updating, and managing environment-scoped dashboards.

Features:
- Environment-specific dashboard deployment
- Template-based dashboard generation
- Cross-account dashboard management
- Dashboard verification and consistency checks

Usage:
    python3 dashboard_manager.py --env prod --deploy
    python3 dashboard_manager.py --env staging --verify
    python3 dashboard_manager.py --list-dashboards --env both
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv


class DashboardManager:
    """Manager for CloudWatch dashboards."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})

        # AWS clients
        self.cloudwatch_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Dashboard configuration
        self.dashboard_config = self.config.get('observability', {}).get('dashboards', {})

    def _load_config(self) -> Dict[str, Any]:
        """Load enterprise configuration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.yaml')
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, ImportError):
            # Fallback to JSON if YAML not available
            json_config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.json')
            try:
                with open(json_config_path, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
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
                'dashboards': {
                    'cloudwatch_enabled': True,
                    'refresh_interval': 300
                }
            },
            'slo': {
                'targets': {
                    'staging': {
                        'error_rate_per_minute': 3,
                        'canary_success_rate': 95,
                        'p95_latency_seconds': 30
                    },
                    'prod': {
                        'error_rate_per_minute': 5,
                        'canary_success_rate': 99,
                        'p95_latency_seconds': 15
                    }
                }
            },
            'security': {
                'auth_monitoring': {
                    'failure_threshold': {
                        'staging': 20,
                        'prod': 50
                    }
                }
            }
        }

    def initialize_aws_client(self) -> bool:
        """Initialize AWS CloudWatch client."""
        try:
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            self.cloudwatch_client = session.client('cloudwatch')

            # Test connection
            self.cloudwatch_client.describe_alarms(MaxRecords=1)
            print(f"✅ Connected to CloudWatch in {self.region}")

            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS client: {e}")
            return False

    def load_dashboard_template(self) -> Dict[str, Any]:
        """Load dashboard template and substitute environment variables."""
        template_path = os.path.join(os.path.dirname(__file__), '..', 'dashboards', 'lcopilot_health_template.json')

        try:
            with open(template_path, 'r') as f:
                template = json.load(f)
        except FileNotFoundError:
            print(f"❌ Dashboard template not found: {template_path}")
            return {}

        # Get environment-specific values
        env_title = self.environment.title()
        aws_account_id = self.env_config.get('aws_account_id', 'unknown')
        alarm_threshold = self.env_config.get('alarm_threshold', 5)

        # SLO targets
        slo_targets = self.config.get('slo', {}).get('targets', {}).get(self.environment, {})
        canary_success_threshold = slo_targets.get('canary_success_rate', 95)
        p95_latency_target_ms = slo_targets.get('p95_latency_seconds', 15) * 1000

        # Security thresholds
        auth_failure_threshold = self.config.get('security', {}).get('auth_monitoring', {}).get('failure_threshold', {}).get(self.environment, 20)

        # Substitute template variables
        template_str = json.dumps(template)
        template_str = template_str.replace('{env}', self.environment)
        template_str = template_str.replace('{env_title}', env_title)
        template_str = template_str.replace('{region}', self.region)
        template_str = template_str.replace('{aws_account_id}', str(aws_account_id))
        template_str = template_str.replace('{alarm_threshold}', str(alarm_threshold))
        template_str = template_str.replace('{canary_success_threshold}', str(canary_success_threshold))
        template_str = template_str.replace('{p95_latency_target_ms}', str(p95_latency_target_ms))
        template_str = template_str.replace('{auth_failure_threshold}', str(auth_failure_threshold))

        return json.loads(template_str)

    def create_dashboard(self) -> bool:
        """Create or update CloudWatch dashboard."""
        if not self.dashboard_config.get('cloudwatch_enabled', True):
            print(f"⚠️  CloudWatch dashboards disabled in configuration")
            return False

        dashboard_name = f"lcopilot-health-{self.environment}"

        # Load and process template
        dashboard_body = self.load_dashboard_template()
        if not dashboard_body:
            return False

        print(f"🚀 Deploying dashboard: {dashboard_name}")
        print(f"   Environment: {self.environment}")
        print(f"   Account: {self.env_config.get('aws_account_id', 'default')}")
        print(f"   Region: {self.region}")

        try:
            response = self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )

            print(f"✅ Dashboard deployed successfully")
            print(f"   Dashboard URL: https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}")

            return True

        except Exception as e:
            print(f"❌ Failed to deploy dashboard: {e}")
            return False

    def verify_dashboard(self) -> Dict[str, Any]:
        """Verify dashboard exists and is configured correctly."""
        dashboard_name = f"lcopilot-health-{self.environment}"

        try:
            response = self.cloudwatch_client.get_dashboard(DashboardName=dashboard_name)
            dashboard_body = json.loads(response['DashboardBody'])

            verification_results = {
                'dashboard_name': dashboard_name,
                'exists': True,
                'widget_count': len(dashboard_body.get('widgets', [])),
                'last_modified': response.get('DashboardArn', 'Unknown'),
                'widgets': [],
                'issues': []
            }

            # Verify widgets
            expected_widgets = [
                'Error Rate',
                'Error Rate (5-min)',
                'Primary Alarm Status',
                'Canary Success Rate',
                'Canary Latency',
                'Authentication Failures',
                'Top Error Types',
                'Response Time Percentiles',
                'System Availability',
                'Security Events'
            ]

            found_widgets = []
            for widget in dashboard_body.get('widgets', []):
                widget_title = widget.get('properties', {}).get('title', 'Untitled')
                found_widgets.append(widget_title)
                verification_results['widgets'].append({
                    'title': widget_title,
                    'type': widget.get('type', 'unknown'),
                    'dimensions': f"{widget.get('width', 0)}x{widget.get('height', 0)}"
                })

            # Check for missing widgets
            for expected in expected_widgets:
                if not any(expected in found for found in found_widgets):
                    verification_results['issues'].append(f"Missing widget: {expected}")

            print(f"✅ Dashboard verification completed")
            print(f"   Widgets found: {len(found_widgets)}")
            print(f"   Issues: {len(verification_results['issues'])}")

            return verification_results

        except self.cloudwatch_client.exceptions.ResourceNotFound:
            return {
                'dashboard_name': dashboard_name,
                'exists': False,
                'error': 'Dashboard not found'
            }
        except Exception as e:
            return {
                'dashboard_name': dashboard_name,
                'exists': False,
                'error': str(e)
            }

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all LCopilot dashboards."""
        try:
            response = self.cloudwatch_client.list_dashboards()

            lcopilot_dashboards = []
            for dashboard in response.get('DashboardEntries', []):
                if 'lcopilot' in dashboard['DashboardName'].lower():
                    lcopilot_dashboards.append({
                        'name': dashboard['DashboardName'],
                        'last_modified': dashboard['LastModified'].isoformat(),
                        'size': dashboard.get('Size', 0)
                    })

            return lcopilot_dashboards

        except Exception as e:
            print(f"❌ Failed to list dashboards: {e}")
            return []

    def delete_dashboard(self) -> bool:
        """Delete the dashboard for this environment."""
        dashboard_name = f"lcopilot-health-{self.environment}"

        try:
            self.cloudwatch_client.delete_dashboards(DashboardNames=[dashboard_name])
            print(f"✅ Dashboard deleted: {dashboard_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to delete dashboard: {e}")
            return False

    def create_grafana_config(self) -> Dict[str, Any]:
        """Generate Grafana dashboard configuration (JSON)."""
        if not self.dashboard_config.get('grafana_enabled', False):
            print(f"⚠️  Grafana dashboards not enabled in configuration")
            return {}

        # Basic Grafana dashboard structure
        grafana_config = {
            "dashboard": {
                "id": None,
                "title": f"LCopilot Health - {self.environment.title()}",
                "tags": ["lcopilot", self.environment, "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": f"Error Rate - {self.environment.title()}",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f'LCopilotErrorCount_{self.environment}',
                                "refId": "A"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                    },
                    {
                        "id": 2,
                        "title": f"Canary Success Rate - {self.environment.title()}",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f'CanarySuccessRate_{self.environment}',
                                "refId": "A"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                    }
                ],
                "time": {
                    "from": "now-6h",
                    "to": "now"
                },
                "refresh": f"{self.dashboard_config.get('refresh_interval', 300)}s"
            },
            "overwrite": True
        }

        return grafana_config


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='CloudWatch Dashboard Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 dashboard_manager.py --env prod --deploy
  python3 dashboard_manager.py --env staging --verify
  python3 dashboard_manager.py --list-dashboards --env both
  python3 dashboard_manager.py --env prod --delete --confirm
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod', 'both'],
                       default='prod', help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--deploy', action='store_true', help='Deploy dashboard')
    parser.add_argument('--verify', action='store_true', help='Verify dashboard')
    parser.add_argument('--list-dashboards', action='store_true', help='List all dashboards')
    parser.add_argument('--delete', action='store_true', help='Delete dashboard')
    parser.add_argument('--confirm', action='store_true', help='Confirm destructive operations')
    parser.add_argument('--export-grafana', help='Export Grafana config to file')

    args = parser.parse_args()

    # Handle both environments
    if args.env == 'both':
        environments = ['staging', 'prod']
    else:
        environments = [args.env]

    for env in environments:
        print(f"\n{'='*50}")
        print(f"Processing environment: {env.upper()}")
        print(f"{'='*50}")

        # Initialize manager
        manager = DashboardManager(environment=env, aws_profile=args.profile)

        if not manager.initialize_aws_client():
            print(f"❌ Failed to initialize AWS client for {env}")
            continue

        # List dashboards
        if args.list_dashboards:
            dashboards = manager.list_dashboards()
            if dashboards:
                print(f"📊 Found {len(dashboards)} LCopilot dashboard(s) in {env}:")
                for dashboard in dashboards:
                    print(f"   • {dashboard['name']} (modified: {dashboard['last_modified']})")
            else:
                print(f"No LCopilot dashboards found in {env}")

        # Deploy dashboard
        if args.deploy:
            success = manager.create_dashboard()
            if not success:
                sys.exit(1)

        # Verify dashboard
        if args.verify:
            results = manager.verify_dashboard()
            if results.get('exists'):
                print(f"✅ Dashboard verification passed for {env}")
                print(f"   Widget count: {results['widget_count']}")
                if results.get('issues'):
                    print(f"   Issues found: {len(results['issues'])}")
                    for issue in results['issues']:
                        print(f"     • {issue}")
            else:
                print(f"❌ Dashboard verification failed for {env}: {results.get('error', 'Unknown error')}")

        # Delete dashboard
        if args.delete:
            if not args.confirm:
                print(f"⚠️  Delete operation requires --confirm flag for safety")
                continue
            success = manager.delete_dashboard()
            if not success:
                sys.exit(1)

        # Export Grafana config
        if args.export_grafana:
            grafana_config = manager.create_grafana_config()
            if grafana_config:
                filename = args.export_grafana
                if not filename.endswith('.json'):
                    filename = f"{filename}.json"

                try:
                    with open(filename, 'w') as f:
                        json.dump(grafana_config, f, indent=2)
                    print(f"✅ Grafana config exported to {filename}")
                except Exception as e:
                    print(f"❌ Failed to export Grafana config: {e}")
            else:
                print(f"❌ Grafana not enabled or failed to generate config")

    # Show help if no action specified
    if not any([args.deploy, args.verify, args.list_dashboards, args.delete, args.export_grafana]):
        parser.print_help()


if __name__ == "__main__":
    main()