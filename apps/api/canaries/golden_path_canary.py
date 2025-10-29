#!/usr/bin/env python3
"""
LCopilot Golden Path Canary

Implements synthetic monitoring for the upload → validate → report flow.
This canary runs continuously to verify the complete user journey works as expected.

Test Scenarios:
1. upload_validate_report: Full golden path test (upload file, validate, generate report)
2. auth_check: Authentication validation test

Metrics Published:
- CanarySuccessRate-{env}: Overall success rate (0-100%)
- CanaryLatencyMs-{env}: End-to-end latency in milliseconds
- CanaryScenarioDuration-{env}: Individual scenario duration

Usage:
    # Run as Lambda function (deployed via Terraform/CDK)
    # Or run locally for testing:
    python3 golden_path_canary.py --env staging --scenario upload_validate_report
    python3 golden_path_canary.py --env prod --scenario all
"""

import os
import sys
import json
import time
import argparse
import requests
import tempfile
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid


@dataclass
class CanaryResult:
    """Result of a canary test scenario."""
    scenario_name: str
    success: bool
    duration_ms: int
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class GoldenPathCanary:
    """Golden path canary for LCopilot API monitoring."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        self.environment = environment
        self.aws_profile = aws_profile

        # Load configuration
        self.config = self._load_config()
        self.env_config = self.config['environments'].get(environment, {})
        self.canary_config = self.config.get('observability', {}).get('canary', {})

        # API endpoints
        self.api_base_url = self.canary_config.get('api_endpoints', {}).get(environment, 'http://localhost:8000')

        # Test scenarios configuration
        self.scenarios = self.canary_config.get('test_scenarios', [
            {
                'name': 'upload_validate_report',
                'description': 'Full golden path test',
                'timeout': 45
            },
            {
                'name': 'auth_check',
                'description': 'Authentication validation',
                'timeout': 15
            }
        ])

        # AWS clients
        self.cloudwatch_client = None
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Test data
        self.test_file_content = self._generate_test_file_content()

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
            'observability': {
                'canary': {
                    'enabled': True,
                    'api_endpoints': {
                        'staging': 'https://api-staging.company.com',
                        'prod': 'https://api.company.com'
                    },
                    'test_scenarios': [
                        {'name': 'upload_validate_report', 'timeout': 45},
                        {'name': 'auth_check', 'timeout': 15}
                    ]
                }
            }
        }

    def _generate_test_file_content(self) -> bytes:
        """Generate test file content for upload testing."""
        test_data = {
            "canary_test": True,
            "timestamp": datetime.now().isoformat(),
            "test_id": str(uuid.uuid4()),
            "environment": self.environment,
            "data": "This is a synthetic test file for canary monitoring"
        }
        return json.dumps(test_data, indent=2).encode('utf-8')

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
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS client: {e}")
            return False

    def test_auth_check(self) -> CanaryResult:
        """Test authentication endpoint."""
        start_time = time.time()
        scenario_name = "auth_check"

        try:
            # Test authentication endpoint
            auth_url = f"{self.api_base_url}/auth/validate"

            response = requests.get(
                auth_url,
                headers={
                    'User-Agent': f'LCopilot-Canary/{self.environment}',
                    'X-Canary-Test': 'true'
                },
                timeout=15
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code in [200, 401]:  # 401 is expected for auth check
                return CanaryResult(
                    scenario_name=scenario_name,
                    success=True,
                    duration_ms=duration_ms,
                    details={
                        'status_code': response.status_code,
                        'response_time_ms': duration_ms
                    }
                )
            else:
                return CanaryResult(
                    scenario_name=scenario_name,
                    success=False,
                    duration_ms=duration_ms,
                    error_message=f"Unexpected status code: {response.status_code}",
                    details={'status_code': response.status_code}
                )

        except requests.exceptions.Timeout:
            duration_ms = int((time.time() - start_time) * 1000)
            return CanaryResult(
                scenario_name=scenario_name,
                success=False,
                duration_ms=duration_ms,
                error_message="Request timeout"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return CanaryResult(
                scenario_name=scenario_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

    def test_upload_validate_report(self) -> CanaryResult:
        """Test the full upload → validate → report flow."""
        start_time = time.time()
        scenario_name = "upload_validate_report"

        try:
            # Step 1: Upload file
            upload_url = f"{self.api_base_url}/upload"

            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                temp_file.write(self.test_file_content)
                temp_file_path = temp_file.name

            try:
                with open(temp_file_path, 'rb') as f:
                    files = {'file': ('canary_test.json', f, 'application/json')}
                    headers = {
                        'User-Agent': f'LCopilot-Canary/{self.environment}',
                        'X-Canary-Test': 'true'
                    }

                    upload_response = requests.post(
                        upload_url,
                        files=files,
                        headers=headers,
                        timeout=30
                    )

                if upload_response.status_code != 200:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return CanaryResult(
                        scenario_name=scenario_name,
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Upload failed: {upload_response.status_code}",
                        details={'step': 'upload', 'status_code': upload_response.status_code}
                    )

                upload_result = upload_response.json()
                file_id = upload_result.get('file_id')

                if not file_id:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return CanaryResult(
                        scenario_name=scenario_name,
                        success=False,
                        duration_ms=duration_ms,
                        error_message="No file_id returned from upload",
                        details={'step': 'upload'}
                    )

                # Step 2: Validate file
                validate_url = f"{self.api_base_url}/validate/{file_id}"
                validate_response = requests.post(
                    validate_url,
                    headers=headers,
                    timeout=20
                )

                if validate_response.status_code != 200:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return CanaryResult(
                        scenario_name=scenario_name,
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Validation failed: {validate_response.status_code}",
                        details={'step': 'validate', 'status_code': validate_response.status_code}
                    )

                # Step 3: Generate report
                report_url = f"{self.api_base_url}/report/{file_id}"
                report_response = requests.get(
                    report_url,
                    headers=headers,
                    timeout=20
                )

                duration_ms = int((time.time() - start_time) * 1000)

                if report_response.status_code == 200:
                    return CanaryResult(
                        scenario_name=scenario_name,
                        success=True,
                        duration_ms=duration_ms,
                        details={
                            'file_id': file_id,
                            'total_duration_ms': duration_ms,
                            'steps_completed': ['upload', 'validate', 'report']
                        }
                    )
                else:
                    return CanaryResult(
                        scenario_name=scenario_name,
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Report generation failed: {report_response.status_code}",
                        details={'step': 'report', 'status_code': report_response.status_code}
                    )

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except requests.exceptions.Timeout:
            duration_ms = int((time.time() - start_time) * 1000)
            return CanaryResult(
                scenario_name=scenario_name,
                success=False,
                duration_ms=duration_ms,
                error_message="Request timeout during golden path test"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return CanaryResult(
                scenario_name=scenario_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

    def run_scenario(self, scenario_name: str) -> CanaryResult:
        """Run a specific test scenario."""
        if scenario_name == "auth_check":
            return self.test_auth_check()
        elif scenario_name == "upload_validate_report":
            return self.test_upload_validate_report()
        else:
            return CanaryResult(
                scenario_name=scenario_name,
                success=False,
                duration_ms=0,
                error_message=f"Unknown scenario: {scenario_name}"
            )

    def run_all_scenarios(self) -> List[CanaryResult]:
        """Run all configured test scenarios."""
        results = []

        for scenario_config in self.scenarios:
            scenario_name = scenario_config['name']
            print(f"🧪 Running scenario: {scenario_name}")

            result = self.run_scenario(scenario_name)
            results.append(result)

            if result.success:
                print(f"   ✅ {scenario_name}: SUCCESS ({result.duration_ms}ms)")
            else:
                print(f"   ❌ {scenario_name}: FAILED ({result.duration_ms}ms) - {result.error_message}")

        return results

    def publish_metrics(self, results: List[CanaryResult]) -> bool:
        """Publish canary metrics to CloudWatch."""
        if not self.cloudwatch_client:
            print("❌ CloudWatch client not initialized")
            return False

        try:
            metric_data = []
            timestamp = datetime.now()

            # Calculate overall success rate
            total_scenarios = len(results)
            successful_scenarios = sum(1 for r in results if r.success)
            success_rate = (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

            # Overall success rate metric
            metric_data.append({
                'MetricName': f'CanarySuccessRate-{self.environment}',
                'Value': success_rate,
                'Unit': 'Percent',
                'Timestamp': timestamp
            })

            # Individual scenario metrics
            for result in results:
                # Scenario duration
                metric_data.append({
                    'MetricName': f'CanaryScenarioDuration-{self.environment}',
                    'Dimensions': [
                        {'Name': 'Scenario', 'Value': result.scenario_name}
                    ],
                    'Value': result.duration_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': timestamp
                })

                # Scenario success (1 or 0)
                metric_data.append({
                    'MetricName': f'CanaryScenarioSuccess-{self.environment}',
                    'Dimensions': [
                        {'Name': 'Scenario', 'Value': result.scenario_name}
                    ],
                    'Value': 1 if result.success else 0,
                    'Unit': 'Count',
                    'Timestamp': timestamp
                })

            # Overall latency (average of all scenarios)
            avg_latency = sum(r.duration_ms for r in results) / len(results) if results else 0
            metric_data.append({
                'MetricName': f'CanaryLatencyMs-{self.environment}',
                'Value': avg_latency,
                'Unit': 'Milliseconds',
                'Timestamp': timestamp
            })

            # Publish metrics in batches (CloudWatch limit is 20 per request)
            batch_size = 20
            for i in range(0, len(metric_data), batch_size):
                batch = metric_data[i:i + batch_size]

                self.cloudwatch_client.put_metric_data(
                    Namespace='LCopilot',
                    MetricData=batch
                )

            print(f"✅ Published {len(metric_data)} metrics to CloudWatch")
            print(f"   Success rate: {success_rate:.1f}%")
            print(f"   Average latency: {avg_latency:.0f}ms")

            return True

        except Exception as e:
            print(f"❌ Failed to publish metrics: {e}")
            return False

    def generate_summary_report(self, results: List[CanaryResult]) -> Dict[str, Any]:
        """Generate a summary report of canary results."""
        total_scenarios = len(results)
        successful_scenarios = sum(1 for r in results if r.success)
        failed_scenarios = total_scenarios - successful_scenarios

        summary = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment,
            'total_scenarios': total_scenarios,
            'successful_scenarios': successful_scenarios,
            'failed_scenarios': failed_scenarios,
            'success_rate_percent': (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
            'average_duration_ms': sum(r.duration_ms for r in results) / len(results) if results else 0,
            'scenarios': []
        }

        for result in results:
            summary['scenarios'].append({
                'name': result.scenario_name,
                'success': result.success,
                'duration_ms': result.duration_ms,
                'error_message': result.error_message,
                'details': result.details
            })

        return summary


def lambda_handler(event, context):
    """AWS Lambda handler for canary execution."""
    # Get environment from event or Lambda environment variable
    environment = event.get('environment', os.environ.get('ENVIRONMENT', 'prod'))

    canary = GoldenPathCanary(environment=environment)

    if not canary.initialize_aws_client():
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to initialize AWS client'})
        }

    # Run all scenarios
    results = canary.run_all_scenarios()

    # Publish metrics
    canary.publish_metrics(results)

    # Generate summary
    summary = canary.generate_summary_report(results)

    return {
        'statusCode': 200,
        'body': json.dumps(summary, indent=2)
    }


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='LCopilot Golden Path Canary',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 golden_path_canary.py --env staging --scenario auth_check
  python3 golden_path_canary.py --env prod --scenario upload_validate_report
  python3 golden_path_canary.py --env staging --scenario all --publish-metrics
        """
    )

    parser.add_argument('--env', '--environment', choices=['staging', 'prod'],
                       default='prod', help='Environment (default: prod)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--scenario', default='all',
                       help='Scenario to run (auth_check, upload_validate_report, all)')
    parser.add_argument('--publish-metrics', action='store_true',
                       help='Publish metrics to CloudWatch')
    parser.add_argument('--api-url', help='Override API base URL')
    parser.add_argument('--output', help='Save results to JSON file')

    args = parser.parse_args()

    # Initialize canary
    canary = GoldenPathCanary(environment=args.env, aws_profile=args.profile)

    # Override API URL if specified
    if args.api_url:
        canary.api_base_url = args.api_url

    print(f"🚀 LCopilot Golden Path Canary")
    print(f"   Environment: {args.env}")
    print(f"   API URL: {canary.api_base_url}")
    print(f"   Scenario: {args.scenario}")

    # Initialize AWS client if metrics publishing is requested
    if args.publish_metrics:
        if not canary.initialize_aws_client():
            sys.exit(1)

    # Run scenarios
    if args.scenario == 'all':
        results = canary.run_all_scenarios()
    else:
        result = canary.run_scenario(args.scenario)
        results = [result]

    # Publish metrics if requested
    if args.publish_metrics:
        canary.publish_metrics(results)

    # Generate and display summary
    summary = canary.generate_summary_report(results)

    print(f"\n📊 Canary Results Summary:")
    print(f"   Success rate: {summary['success_rate_percent']:.1f}%")
    print(f"   Average duration: {summary['average_duration_ms']:.0f}ms")
    print(f"   Failed scenarios: {summary['failed_scenarios']}")

    # Save to file if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"✅ Results saved to {args.output}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

    # Exit with error code if any scenarios failed
    if summary['failed_scenarios'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()