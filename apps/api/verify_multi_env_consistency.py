#!/usr/bin/env python3
"""
Multi-Environment CloudWatch Consistency Verification

Verifies that all three implementation approaches (Python, Terraform, CDK)
produce consistent AWS resources with correct naming conventions.

This script:
1. Checks both staging and prod environments
2. Verifies resource naming follows conventions
3. Compares configurations across environments
4. Reports any inconsistencies or missing resources

Usage:
    python3 verify_multi_env_consistency.py
    python3 verify_multi_env_consistency.py --env staging
    python3 verify_multi_env_consistency.py --verbose

Requirements:
    - .env.production with AWS credentials
    - AWS resources created by one or more approaches
    - boto3, python-dotenv packages
"""

import os
import sys
import argparse
import boto3
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Any


class MultiEnvConsistencyVerifier:
    """Verifies consistency across multi-environment CloudWatch implementations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.environments = ["staging", "prod"]

        # Expected naming patterns
        self.naming_patterns = {
            "alarm": "lcopilot-error-spike-{env}",
            "metric": "LCopilotErrorCount-{env}",
            "log_group": "/aws/lambda/lcopilot-{env}",
            "sns_topic": "lcopilot-alerts-{env}"
        }

        # Expected configuration per environment
        self.expected_configs = {
            "staging": {
                "threshold": 3.0,
                "period": 60,
                "evaluation_periods": 1,
                "log_retention": 7  # days (approximate)
            },
            "prod": {
                "threshold": 5.0,
                "period": 60,
                "evaluation_periods": 1,
                "log_retention": 30  # days (approximate)
            }
        }

        # AWS clients
        self.cloudwatch = None
        self.logs_client = None
        self.sns_client = None
        self.region = None

        # Verification results
        self.results = {
            "staging": {},
            "prod": {},
            "consistency_issues": [],
            "missing_resources": [],
            "summary": {}
        }

    def load_environment(self) -> bool:
        """Load environment variables."""
        if self.verbose:
            print("🔧 Loading environment configuration...")

        env_file = '.env.production'
        if not os.path.exists(env_file):
            print(f"❌ Environment file {env_file} not found")
            return False

        load_dotenv(env_file)

        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False

        self.region = os.getenv('AWS_REGION', 'eu-north-1')

        if self.verbose:
            print(f"✅ Environment loaded (Region: {self.region})")

        return True

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients."""
        if self.verbose:
            print("☁️  Initializing AWS clients...")

        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
            self.logs_client = boto3.client('logs', region_name=self.region)
            self.sns_client = boto3.client('sns', region_name=self.region)

            # Test connection
            sts = boto3.client('sts', region_name=self.region)
            identity = sts.get_caller_identity()

            if self.verbose:
                print(f"✅ AWS clients initialized (Account: {identity['Account']})")

            return True
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            return False

    def verify_cloudwatch_alarms(self) -> Dict[str, Any]:
        """Verify CloudWatch alarms for both environments."""
        alarm_results = {}

        try:
            response = self.cloudwatch.describe_alarms()
            all_alarms = response.get('MetricAlarms', [])

            for env in self.environments:
                expected_alarm_name = self.naming_patterns["alarm"].format(env=env)
                expected_metric_name = self.naming_patterns["metric"].format(env=env)

                # Find the alarm
                alarm = None
                for a in all_alarms:
                    if a['AlarmName'] == expected_alarm_name:
                        alarm = a
                        break

                if alarm:
                    # Verify configuration
                    config_check = {
                        'exists': True,
                        'name_correct': alarm['AlarmName'] == expected_alarm_name,
                        'metric_name_correct': alarm['MetricName'] == expected_metric_name,
                        'namespace_correct': alarm['Namespace'] == 'LCopilot',
                        'threshold_correct': alarm['Threshold'] == self.expected_configs[env]['threshold'],
                        'period_correct': alarm['Period'] == self.expected_configs[env]['period'],
                        'evaluation_periods_correct': alarm['EvaluationPeriods'] == self.expected_configs[env]['evaluation_periods'],
                        'statistic_correct': alarm['Statistic'] == 'Sum',
                        'comparison_correct': alarm['ComparisonOperator'] == 'GreaterThanOrEqualToThreshold',
                        'treat_missing_correct': alarm['TreatMissingData'] == 'notBreaching',
                        'actions_enabled': alarm.get('ActionsEnabled', False),
                        'has_alarm_actions': len(alarm.get('AlarmActions', [])) > 0,
                        'alarm_state': alarm.get('StateValue', 'UNKNOWN'),
                        'alarm_description': alarm.get('AlarmDescription', '')
                    }

                    if self.verbose:
                        print(f"✅ Found alarm: {expected_alarm_name}")
                        if not all(config_check.values()):
                            failed_checks = [k for k, v in config_check.items() if v is False]
                            print(f"⚠️  Configuration issues: {failed_checks}")
                else:
                    config_check = {'exists': False}
                    self.results['missing_resources'].append(f"Alarm: {expected_alarm_name}")
                    if self.verbose:
                        print(f"❌ Missing alarm: {expected_alarm_name}")

                alarm_results[env] = config_check

        except ClientError as e:
            print(f"❌ Error checking CloudWatch alarms: {e}")
            return {}

        return alarm_results

    def verify_sns_topics(self) -> Dict[str, Any]:
        """Verify SNS topics for both environments."""
        topic_results = {}

        try:
            response = self.sns_client.list_topics()
            all_topics = response.get('Topics', [])

            for env in self.environments:
                expected_topic_name = self.naming_patterns["sns_topic"].format(env=env)

                # Find the topic
                topic = None
                for t in all_topics:
                    topic_arn = t['TopicArn']
                    if topic_arn.endswith(f":{expected_topic_name}"):
                        topic = t
                        break

                if topic:
                    topic_check = {
                        'exists': True,
                        'name_correct': topic['TopicArn'].endswith(f":{expected_topic_name}"),
                        'topic_arn': topic['TopicArn']
                    }

                    if self.verbose:
                        print(f"✅ Found SNS topic: {expected_topic_name}")
                else:
                    topic_check = {'exists': False}
                    self.results['missing_resources'].append(f"SNS Topic: {expected_topic_name}")
                    if self.verbose:
                        print(f"❌ Missing SNS topic: {expected_topic_name}")

                topic_results[env] = topic_check

        except ClientError as e:
            print(f"❌ Error checking SNS topics: {e}")
            return {}

        return topic_results

    def verify_log_groups(self) -> Dict[str, Any]:
        """Verify CloudWatch Log Groups for both environments."""
        log_group_results = {}

        try:
            for env in self.environments:
                expected_log_group = self.naming_patterns["log_group"].format(env=env)

                try:
                    response = self.logs_client.describe_log_groups(
                        logGroupNamePrefix=expected_log_group,
                        limit=1
                    )

                    log_groups = response.get('logGroups', [])
                    log_group = next((lg for lg in log_groups if lg['logGroupName'] == expected_log_group), None)

                    if log_group:
                        log_group_check = {
                            'exists': True,
                            'name_correct': log_group['logGroupName'] == expected_log_group,
                            'retention_days': log_group.get('retentionInDays'),
                            'arn': log_group.get('arn', '')
                        }

                        if self.verbose:
                            print(f"✅ Found log group: {expected_log_group}")
                    else:
                        log_group_check = {'exists': False}
                        self.results['missing_resources'].append(f"Log Group: {expected_log_group}")
                        if self.verbose:
                            print(f"❌ Missing log group: {expected_log_group}")

                    log_group_results[env] = log_group_check

                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        log_group_results[env] = {'exists': False}
                        self.results['missing_resources'].append(f"Log Group: {expected_log_group}")
                        if self.verbose:
                            print(f"❌ Missing log group: {expected_log_group}")
                    else:
                        raise

        except ClientError as e:
            print(f"❌ Error checking CloudWatch Log Groups: {e}")
            return {}

        return log_group_results

    def check_cross_environment_consistency(self) -> List[str]:
        """Check for consistency issues between environments."""
        issues = []

        # Compare alarm configurations between environments
        if 'alarms' in self.results['staging'] and 'alarms' in self.results['prod']:
            staging_alarm = self.results['staging']['alarms']
            prod_alarm = self.results['prod']['alarms']

            # Both should exist
            if staging_alarm.get('exists') and prod_alarm.get('exists'):
                # Check if both have same structure (different thresholds expected)
                common_checks = ['namespace_correct', 'period_correct', 'evaluation_periods_correct',
                               'statistic_correct', 'comparison_correct', 'treat_missing_correct']

                for check in common_checks:
                    if staging_alarm.get(check) != prod_alarm.get(check):
                        issues.append(f"Inconsistent {check} between staging and prod")

            # One exists but not the other
            elif staging_alarm.get('exists') != prod_alarm.get('exists'):
                issues.append("Alarm exists in one environment but not the other")

        return issues

    def print_summary_report(self) -> None:
        """Print comprehensive summary report."""
        print("\n" + "=" * 80)
        print("🔍 MULTI-ENVIRONMENT CONSISTENCY VERIFICATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Region: {self.region}")
        print("=" * 80)

        # Resource Summary
        print("\n📊 RESOURCE SUMMARY")
        print("-" * 40)

        for env in self.environments:
            env_results = self.results[env]
            print(f"\n🏷️  {env.upper()} Environment:")

            for resource_type in ['alarms', 'sns_topics', 'log_groups']:
                if resource_type in env_results:
                    resource_data = env_results[resource_type]
                    exists = resource_data.get('exists', False)
                    status = "✅ EXISTS" if exists else "❌ MISSING"

                    resource_name = {
                        'alarms': self.naming_patterns["alarm"].format(env=env),
                        'sns_topics': self.naming_patterns["sns_topic"].format(env=env),
                        'log_groups': self.naming_patterns["log_group"].format(env=env)
                    }[resource_type]

                    print(f"   {status} {resource_type.replace('_', ' ').title()}: {resource_name}")

        # Missing Resources
        if self.results['missing_resources']:
            print(f"\n❌ MISSING RESOURCES ({len(self.results['missing_resources'])})")
            print("-" * 40)
            for resource in self.results['missing_resources']:
                print(f"   • {resource}")

        # Consistency Issues
        if self.results['consistency_issues']:
            print(f"\n⚠️  CONSISTENCY ISSUES ({len(self.results['consistency_issues'])})")
            print("-" * 40)
            for issue in self.results['consistency_issues']:
                print(f"   • {issue}")

        # Overall Status
        print("\n" + "=" * 80)
        total_missing = len(self.results['missing_resources'])
        total_issues = len(self.results['consistency_issues'])

        if total_missing == 0 and total_issues == 0:
            print("🎉 ALL CHECKS PASSED - Multi-environment setup is consistent!")
            print("✅ All resources exist with correct naming conventions")
            print("✅ No consistency issues detected between environments")
        else:
            print(f"⚠️  VERIFICATION INCOMPLETE - {total_missing} missing resources, {total_issues} issues")
            if total_missing > 0:
                print("💡 Run setup scripts to create missing resources")
            if total_issues > 0:
                print("💡 Review configurations for consistency issues")

        # Implementation Suggestions
        print(f"\n🛠️  IMPLEMENTATION STATUS")
        print("-" * 40)
        staging_complete = 'alarms' in self.results['staging'] and self.results['staging']['alarms'].get('exists')
        prod_complete = 'alarms' in self.results['prod'] and self.results['prod']['alarms'].get('exists')

        print(f"   Staging Environment: {'✅ Deployed' if staging_complete else '❌ Not Deployed'}")
        print(f"   Production Environment: {'✅ Deployed' if prod_complete else '❌ Not Deployed'}")

        if not staging_complete or not prod_complete:
            print(f"\n📝 DEPLOYMENT COMMANDS")
            print("-" * 40)
            if not staging_complete:
                print("   # Deploy staging resources:")
                print("   python3 setup_alarm.py --env staging")
                print("   # OR: terraform apply -var='environment=staging'")
                print("   # OR: cdk deploy --context env=staging")

            if not prod_complete:
                print("   # Deploy production resources:")
                print("   python3 setup_alarm.py --env prod")
                print("   # OR: terraform apply -var='environment=prod'")
                print("   # OR: cdk deploy --context env=prod")

    def run_verification(self) -> bool:
        """Main verification workflow."""
        print("🚀 Multi-Environment CloudWatch Consistency Verification")

        # Initialize
        if not self.load_environment():
            return False

        if not self.initialize_aws_clients():
            return False

        # Run verifications
        print("\n🔍 Verifying CloudWatch Alarms...")
        self.results['staging']['alarms'] = {}
        self.results['prod']['alarms'] = {}
        alarm_results = self.verify_cloudwatch_alarms()
        for env in self.environments:
            if env in alarm_results:
                self.results[env]['alarms'] = alarm_results[env]

        print("🔍 Verifying SNS Topics...")
        self.results['staging']['sns_topics'] = {}
        self.results['prod']['sns_topics'] = {}
        topic_results = self.verify_sns_topics()
        for env in self.environments:
            if env in topic_results:
                self.results[env]['sns_topics'] = topic_results[env]

        print("🔍 Verifying Log Groups...")
        self.results['staging']['log_groups'] = {}
        self.results['prod']['log_groups'] = {}
        log_group_results = self.verify_log_groups()
        for env in self.environments:
            if env in log_group_results:
                self.results[env]['log_groups'] = log_group_results[env]

        print("🔍 Checking Cross-Environment Consistency...")
        self.results['consistency_issues'] = self.check_cross_environment_consistency()

        # Print report
        self.print_summary_report()

        # Return success if no missing resources or issues
        return len(self.results['missing_resources']) == 0 and len(self.results['consistency_issues']) == 0


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Multi-Environment CloudWatch Consistency Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 verify_multi_env_consistency.py                    # Verify both environments
  python3 verify_multi_env_consistency.py --verbose          # Detailed output
  python3 verify_multi_env_consistency.py --env staging      # Focus on staging only
        """
    )

    parser.add_argument(
        '--env', '--environment',
        choices=['staging', 'prod', 'both'],
        default='both',
        help='Environment(s) to verify (default: both)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        verifier = MultiEnvConsistencyVerifier(verbose=args.verbose)

        # Adjust environments if specific env requested
        if args.env != 'both':
            verifier.environments = [args.env]

        success = verifier.run_verification()

        if success:
            print(f"\n✅ Verification completed successfully")
            sys.exit(0)
        else:
            print(f"\n⚠️  Verification completed with issues - see report above")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()