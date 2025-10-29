#!/usr/bin/env python3
"""
Multi-Environment CloudWatch Alarm Verification for LCopilot API

Comprehensive verification that environment-specific CloudWatch alarms exist and are properly configured.
Checks metric configuration, threshold settings, and SNS topic attachment.

Usage:
    python3 verify_alarm.py                   # Verify prod alarm (default)
    python3 verify_alarm.py --env staging     # Verify staging alarm
    python3 verify_alarm.py --env prod        # Verify prod alarm explicitly

Returns:
    Exit code 0 if all checks pass, 1 if any check fails
"""

import os
import sys
import argparse
import boto3
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError


class AlarmVerifier:
    """CloudWatch alarm configuration verification."""

    def __init__(self, environment: str = "prod"):
        # Environment configuration
        self.environment = environment

        # Environment-aware naming
        self.alarm_name = f"lcopilot-error-spike-{environment}"
        self.expected_config = {
            'Namespace': 'LCopilot',
            'MetricName': f'LCopilotErrorCount-{environment}',
            'Statistic': 'Sum',
            'Period': 60,
            'Threshold': 5.0,
            'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
            'EvaluationPeriods': 1,
            'TreatMissingData': 'notBreaching'
        }
        self.sns_topic_name = f"lcopilot-alerts-{environment}"

        # AWS clients
        self.cloudwatch = None
        self.region = None
        self.alarm_data = None

    def load_environment(self) -> bool:
        """Load environment configuration."""
        env_file = '.env.production'
        if os.path.exists(env_file):
            load_dotenv(env_file)

        self.region = os.getenv('AWS_REGION', 'eu-north-1')
        return True

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
            # Test connection
            self.cloudwatch.describe_alarms(MaxRecords=1)
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def fetch_alarm_data(self) -> bool:
        """Fetch alarm data from CloudWatch."""
        try:
            response = self.cloudwatch.describe_alarms(AlarmNames=[self.alarm_name])
            alarms = response.get('MetricAlarms', [])

            if not alarms:
                print(f"❌ Alarm '{self.alarm_name}' not found")
                print(f"   Run: python3 setup_alarm.py to create it")
                return False

            self.alarm_data = alarms[0]
            return True

        except ClientError as e:
            print(f"❌ Error fetching alarm data: {e}")
            return False

    def verify_basic_info(self) -> dict:
        """Verify basic alarm information."""
        checks = {}

        # Alarm exists
        checks['alarm_exists'] = self.alarm_data is not None

        if not checks['alarm_exists']:
            return checks

        # Basic properties
        checks['name_correct'] = self.alarm_data.get('AlarmName') == self.alarm_name
        checks['actions_enabled'] = self.alarm_data.get('ActionsEnabled', False)
        checks['has_description'] = bool(self.alarm_data.get('AlarmDescription', ''))

        return checks

    def verify_metric_configuration(self) -> dict:
        """Verify metric-related configuration."""
        checks = {}

        if not self.alarm_data:
            return checks

        for key, expected_value in self.expected_config.items():
            actual_value = self.alarm_data.get(key)
            check_name = f'metric_{key.lower()}'
            checks[check_name] = actual_value == expected_value

        return checks

    def verify_sns_configuration(self) -> dict:
        """Verify SNS topic configuration."""
        checks = {}

        if not self.alarm_data:
            return checks

        # Check alarm actions
        alarm_actions = self.alarm_data.get('AlarmActions', [])
        ok_actions = self.alarm_data.get('OKActions', [])

        checks['has_alarm_actions'] = len(alarm_actions) > 0
        checks['has_ok_actions'] = len(ok_actions) > 0

        # Verify SNS topic name in actions
        sns_topic_found = False
        if alarm_actions:
            for action_arn in alarm_actions:
                if action_arn.startswith('arn:aws:sns:') and action_arn.endswith(f':{self.sns_topic_name}'):
                    sns_topic_found = True
                    break

        checks['correct_sns_topic'] = sns_topic_found

        return checks

    def print_detailed_status(self, all_checks: dict):
        """Print detailed verification status."""
        print(f"🔍 LCopilot CloudWatch Alarm Verification [{self.environment.upper()}]")
        print("=" * 60)
        print(f"Environment: {self.environment}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Region: {self.region}")
        print("=" * 60)

        # Basic Information
        print("\n📋 BASIC INFORMATION")
        print("-" * 30)
        self._print_check("Alarm exists", all_checks.get('alarm_exists', False))
        self._print_check("Name correct", all_checks.get('name_correct', False))
        self._print_check("Actions enabled", all_checks.get('actions_enabled', False))
        self._print_check("Has description", all_checks.get('has_description', False))

        if self.alarm_data:
            print(f"   Current state: {self.alarm_data.get('StateValue', 'Unknown')}")
            print(f"   State reason: {self.alarm_data.get('StateReason', 'No reason')}")

        # Metric Configuration
        print("\n📊 METRIC CONFIGURATION")
        print("-" * 30)
        metric_checks = [k for k in all_checks.keys() if k.startswith('metric_')]
        for check in sorted(metric_checks):
            display_name = check.replace('metric_', '').replace('_', ' ').title()
            self._print_check(display_name, all_checks.get(check, False))

        # Show expected vs actual for failed metric checks
        if self.alarm_data and any(not all_checks.get(check, True) for check in metric_checks):
            print("\n   Expected vs Actual:")
            for key, expected_value in self.expected_config.items():
                actual_value = self.alarm_data.get(key)
                if actual_value != expected_value:
                    print(f"   ❌ {key}: expected {expected_value}, got {actual_value}")

        # SNS Configuration
        print("\n📧 SNS CONFIGURATION")
        print("-" * 30)
        self._print_check("Has alarm actions", all_checks.get('has_alarm_actions', False))
        self._print_check("Has OK actions", all_checks.get('has_ok_actions', False))
        self._print_check("Correct SNS topic", all_checks.get('correct_sns_topic', False))

        if self.alarm_data:
            alarm_actions = self.alarm_data.get('AlarmActions', [])
            if alarm_actions:
                print(f"   SNS Actions ({len(alarm_actions)}):")
                for action in alarm_actions:
                    topic_name = action.split(':')[-1] if ':' in action else action
                    status = "✅" if topic_name == self.sns_topic_name else "❌"
                    print(f"     {status} {topic_name}")

    def _print_check(self, name: str, passed: bool):
        """Print a single check result."""
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")

    def print_summary(self, all_checks: dict) -> bool:
        """Print verification summary."""
        passed_checks = sum(1 for check in all_checks.values() if check)
        total_checks = len(all_checks)
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Checks Passed: {passed_checks}/{total_checks} ({success_rate:.1f}%)")

        if passed_checks == total_checks:
            print("🎉 All checks passed! Alarm is properly configured.")
            print("✅ Ready for production monitoring")

            print(f"\n🧪 Test the alarm:")
            print(f"   curl 'http://localhost:8000/debug/spam-errors?count=6'")
            print(f"\n📧 Monitor for SNS notifications when alarm triggers")
            print(f"\n🔄 Run other environment checks:")
            if self.environment == 'prod':
                print(f"   python3 verify_alarm.py --env staging")
            else:
                print(f"   python3 verify_alarm.py --env prod")

            return True
        else:
            failed_checks = total_checks - passed_checks
            print(f"❌ {failed_checks} checks failed - alarm needs attention")
            print("💡 Run: python3 setup_alarm.py to fix configuration")
            return False

    def verify_alarm(self) -> bool:
        """Main verification workflow."""
        print("Starting CloudWatch alarm verification...")

        # Initialize
        if not self.load_environment():
            return False

        if not self.initialize_aws_clients():
            return False

        if not self.fetch_alarm_data():
            return False

        # Run all verification checks
        all_checks = {}

        # Basic info checks
        basic_checks = self.verify_basic_info()
        all_checks.update(basic_checks)

        # Metric configuration checks
        metric_checks = self.verify_metric_configuration()
        all_checks.update(metric_checks)

        # SNS configuration checks
        sns_checks = self.verify_sns_configuration()
        all_checks.update(sns_checks)

        # Print detailed results
        self.print_detailed_status(all_checks)

        # Print summary and return result
        return self.print_summary(all_checks)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Multi-Environment CloudWatch Alarm Verification for LCopilot API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 verify_alarm.py                   # Verify prod alarm (default)
  python3 verify_alarm.py --env staging     # Verify staging alarm
  python3 verify_alarm.py --env prod        # Verify prod alarm explicitly
        """
    )

    parser.add_argument(
        '--env', '--environment',
        choices=['staging', 'prod'],
        default='prod',
        help='Environment to verify alarm for (default: prod)'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        verifier = AlarmVerifier(environment=args.env)
        success = verifier.verify_alarm()

        if success:
            print(f"\n✅ Verification completed successfully for {args.env}")
            sys.exit(0)
        else:
            print(f"\n❌ Verification failed for {args.env} - check configuration")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()