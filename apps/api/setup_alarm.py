#!/usr/bin/env python3
"""
Multi-Environment CloudWatch Alarm Setup for LCopilot API

Creates/updates environment-specific CloudWatch alarms that trigger on ≥5 errors within 1 minute.
Automatically connects to environment-specific SNS topics for notifications.

Usage:
    python3 setup_alarm.py                    # Creates prod alarm (default)
    python3 setup_alarm.py --env staging      # Creates staging alarm
    python3 setup_alarm.py --env prod         # Creates prod alarm explicitly

Requirements:
    - .env.production with AWS credentials
    - SNS topic 'lcopilot-alerts-{env}' must exist
    - CloudWatch permissions for alarm creation
"""

import os
import sys
import json
import argparse
import boto3
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional


class CloudWatchAlarmSetup:
    """Production CloudWatch alarm setup and management."""

    def __init__(self, environment: str = "prod", aws_profile: Optional[str] = None):
        # Environment configuration
        self.environment = environment
        self.aws_profile = aws_profile

        # Load enterprise configuration
        self.config = self.load_enterprise_config()
        self.env_config = self.config['environments'].get(environment, {})

        # Environment-aware naming
        threshold = self.env_config.get('alarm_threshold', 5)
        self.alarm_name = f"lcopilot-error-spike-{environment}"
        self.alarm_description = f"[{environment.upper()}] Triggers when ≥{threshold} errors occur within 1 minute"
        self.metric_namespace = self.config['global_settings']['metric_namespace']
        self.metric_name = f"LCopilotErrorCount-{environment}"
        self.sns_topic_name = f"lcopilot-alerts-{environment}"
        self.log_group_name = f"/aws/lambda/lcopilot-{environment}"
        self.region = self.env_config.get('aws_region', 'eu-north-1')

        # Expected account ID for validation
        self.expected_account_id = self.env_config.get('aws_account_id')

        # AWS clients
        self.cloudwatch = None
        self.sns = None
        self.logs = None
        self.account_id = None

    def load_enterprise_config(self) -> Dict[str, Any]:
        """Load enterprise configuration from JSON file."""
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'enterprise_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Enterprise config not found at {config_path}")
            print("   Using default configuration")
            return {
                'environments': {
                    'staging': {'alarm_threshold': 3, 'aws_region': 'eu-north-1'},
                    'prod': {'alarm_threshold': 5, 'aws_region': 'eu-north-1'}
                },
                'global_settings': {'metric_namespace': 'LCopilot'}
            }
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in enterprise config: {e}")
            sys.exit(1)

    def load_environment(self) -> bool:
        """Load environment variables and validate cross-account setup."""
        print("🔧 Loading environment configuration...")
        print(f"   Target Environment: {self.environment}")
        print(f"   Expected Account: {self.expected_account_id or 'Not specified'}")
        if self.aws_profile:
            print(f"   AWS Profile: {self.aws_profile}")

        # Load .env.production for fallback credentials
        env_file = '.env.production'
        if os.path.exists(env_file):
            load_dotenv(env_file)

        # Override region from enterprise config
        os.environ['AWS_REGION'] = self.region

        print(f"✅ Environment configuration loaded")
        print(f"   Target Region: {self.region}")
        return True

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS clients with cross-account support."""
        print("☁️  Initializing AWS clients...")

        try:
            # Create session with profile if specified
            session_kwargs = {'region_name': self.region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile
                print(f"   Using AWS profile: {self.aws_profile}")

            session = boto3.Session(**session_kwargs)

            # Create clients from session
            self.cloudwatch = session.client('cloudwatch')
            self.sns = session.client('sns')
            self.logs = session.client('logs')

            # Test credentials and get account info
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            self.account_id = identity['Account']

            # Validate account ID if specified
            if self.expected_account_id and self.account_id != self.expected_account_id:
                print(f"⚠️  Account ID mismatch!")
                print(f"   Expected: {self.expected_account_id}")
                print(f"   Actual: {self.account_id}")
                print(f"   Continuing anyway...")

            print(f"✅ AWS clients initialized")
            print(f"   Account ID: {self.account_id}")
            print(f"   Region: {self.region}")
            print(f"   Identity: {identity.get('Arn', 'unknown').split('/')[-1]}")

            return True

        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            if self.aws_profile:
                print(f"   Check AWS profile '{self.aws_profile}' configuration")
            else:
                print("   Check AWS credentials and configuration")
            return False

    def find_sns_topic_arn(self) -> str:
        """Discover SNS topic ARN by name."""
        print(f"🔍 Discovering SNS topic: {self.sns_topic_name}")

        try:
            # List all topics and find ours
            paginator = self.sns.get_paginator('list_topics')

            for page in paginator.paginate():
                for topic in page.get('Topics', []):
                    topic_arn = topic['TopicArn']
                    topic_name = topic_arn.split(':')[-1]

                    if topic_name == self.sns_topic_name:
                        print(f"✅ Found SNS topic")
                        print(f"   ARN: {topic_arn}")
                        return topic_arn

            # Topic not found
            print(f"❌ SNS topic '{self.sns_topic_name}' not found in region {self.region}")

            # Show available topics for debugging
            all_topics = []
            for page in paginator.paginate():
                for topic in page.get('Topics', []):
                    topic_name = topic['TopicArn'].split(':')[-1]
                    all_topics.append(topic_name)

            if all_topics:
                print(f"   Available topics: {', '.join(sorted(all_topics))}")
            else:
                print(f"   No SNS topics found in region")

            print(f"\n💡 Create the topic with:")
            print(f"   aws sns create-topic --name {self.sns_topic_name} --region {self.region}")

            return None

        except ClientError as e:
            print(f"❌ Error accessing SNS: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error finding SNS topic: {e}")
            return None

    def create_or_update_alarm(self, sns_topic_arn: str) -> bool:
        """Create or update the CloudWatch alarm."""
        print(f"🚨 Setting up alarm: {self.alarm_name}")

        try:
            # Comprehensive alarm configuration
            alarm_params = {
                'AlarmName': self.alarm_name,
                'AlarmDescription': self.alarm_description,
                'ActionsEnabled': True,

                # Actions
                'AlarmActions': [sns_topic_arn],
                'OKActions': [sns_topic_arn],
                'InsufficientDataActions': [],

                # Metric configuration
                'MetricName': self.metric_name,
                'Namespace': self.metric_namespace,
                'Statistic': 'Sum',
                'Dimensions': [],

                # Threshold settings from config
                'Period': self.config['global_settings']['alarm_period_seconds'],
                'EvaluationPeriods': self.config['global_settings']['evaluation_periods'],
                'DatapointsToAlarm': self.config['global_settings']['evaluation_periods'],
                'Threshold': float(self.env_config.get('alarm_threshold', 5)),
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'TreatMissingData': self.config['global_settings']['treat_missing_data'],

                # Tags
                'Tags': [
                    {'Key': 'Application', 'Value': 'LCopilot'},
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Purpose', 'Value': 'ErrorRateMonitoring'},
                    {'Key': 'CreatedBy', 'Value': 'setup_alarm.py'},
                    {'Key': 'CreatedAt', 'Value': datetime.now().isoformat()}
                ]
            }

            # Create/update alarm
            self.cloudwatch.put_metric_alarm(**alarm_params)

            print(f"✅ Alarm created/updated successfully: {self.alarm_name}")

            # Generate alarm ARN
            alarm_arn = f"arn:aws:cloudwatch:{self.region}:{self.account_id}:alarm:{self.alarm_name}"
            print(f"   Alarm ARN: {alarm_arn}")

            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            print(f"❌ Failed to create alarm: {error_code}")
            print(f"   {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error creating alarm: {e}")
            return False

    def verify_alarm_configuration(self) -> bool:
        """Verify the alarm was created with correct configuration."""
        print(f"✅ Verifying alarm configuration...")

        try:
            response = self.cloudwatch.describe_alarms(AlarmNames=[self.alarm_name])
            alarms = response.get('MetricAlarms', [])

            if not alarms:
                print(f"❌ Alarm not found after creation")
                return False

            alarm = alarms[0]

            print(f"✅ Alarm verification successful")
            print(f"   Name: {alarm['AlarmName']}")
            print(f"   State: {alarm['StateValue']} ({alarm.get('StateReason', 'No reason')})")
            print(f"   Metric: {alarm['Namespace']}/{alarm['MetricName']}")
            print(f"   Threshold: {alarm['ComparisonOperator']} {alarm['Threshold']}")
            print(f"   Period: {alarm['Period']} seconds")
            print(f"   Evaluation Periods: {alarm['EvaluationPeriods']}")
            print(f"   Actions: {len(alarm.get('AlarmActions', []))} configured")

            # Verify configuration matches expectations
            expected = {
                'Namespace': self.metric_namespace,
                'MetricName': self.metric_name,
                'Statistic': 'Sum',
                'Period': 60,
                'Threshold': 5.0,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 1,
                'TreatMissingData': 'notBreaching'
            }

            mismatches = []
            for key, expected_value in expected.items():
                actual_value = alarm.get(key)
                if actual_value != expected_value:
                    mismatches.append(f"{key}: expected {expected_value}, got {actual_value}")

            if mismatches:
                print(f"⚠️  Configuration mismatches:")
                for mismatch in mismatches:
                    print(f"   - {mismatch}")
                return False

            return True

        except Exception as e:
            print(f"❌ Error verifying alarm: {e}")
            return False

    def setup_alarm(self) -> bool:
        """Main setup workflow."""
        print(f"🚀 LCopilot CloudWatch Alarm Setup [{self.environment.upper()}]")
        print("=" * 60)
        print(f"Environment: {self.environment}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Step 1: Load environment
        if not self.load_environment():
            return False
        print()

        # Step 2: Initialize AWS clients
        if not self.initialize_aws_clients():
            return False
        print()

        # Step 3: Find SNS topic
        sns_topic_arn = self.find_sns_topic_arn()
        if not sns_topic_arn:
            return False
        print()

        # Step 4: Create/update alarm
        if not self.create_or_update_alarm(sns_topic_arn):
            return False
        print()

        # Step 5: Verify configuration
        if not self.verify_alarm_configuration():
            print("⚠️  Alarm created but verification failed")
            return False

        # Success summary
        print("\n" + "=" * 60)
        print("🎉 CLOUDWATCH ALARM SETUP COMPLETE")
        print("=" * 60)
        print(f"✅ Alarm Name: {self.alarm_name}")
        print(f"✅ Metric: {self.metric_namespace}/{self.metric_name}")
        print(f"✅ Threshold: ≥5 errors in 1 minute")
        print(f"✅ SNS Topic: {self.sns_topic_name}")
        print(f"✅ Region: {self.region}")

        print(f"\n🧪 Testing Commands:")
        print(f"   # Test alarm with API")
        print(f"   curl 'http://localhost:8000/debug/spam-errors?count=6'")
        print(f"   ")
        print(f"   # Verify alarm setup")
        print(f"   python3 verify_alarm.py --env {self.environment}")
        print(f"   ")
        print(f"   # Full end-to-end test")
        print(f"   python3 cloudwatch_alert_test.py --env {self.environment}")

        print(f"\n📧 Check your email/Slack for SNS notifications when alarm triggers!")

        return True


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Enterprise Multi-Environment CloudWatch Alarm Setup for LCopilot API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 setup_alarm.py                               # Create prod alarm (default)
  python3 setup_alarm.py --env staging                 # Create staging alarm
  python3 setup_alarm.py --env prod --profile prod-profile  # Cross-account with profile
  python3 setup_alarm.py --env staging --profile staging   # Staging account with profile
        """
    )

    parser.add_argument(
        '--env', '--environment',
        choices=['staging', 'prod'],
        default='prod',
        help='Environment to create alarm for (default: prod)'
    )

    parser.add_argument(
        '--profile',
        help='AWS profile to use for cross-account deployment'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        # Auto-detect profile from enterprise config if not provided
        profile = args.profile
        if not profile:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'enterprise_config.json')
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    env_config = config['environments'].get(args.env, {})
                    profile = env_config.get('aws_profile')
                    if profile:
                        print(f"🔧 Auto-detected AWS profile from config: {profile}")
            except:
                pass

        setup = CloudWatchAlarmSetup(environment=args.env, aws_profile=profile)
        success = setup.setup_alarm()

        if success:
            print(f"\n✅ Enterprise setup completed successfully for {args.env}")
            if setup.expected_account_id:
                print(f"   Deployed to account: {setup.account_id}")
            sys.exit(0)
        else:
            print(f"\n❌ Setup failed for {args.env} - check errors above")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()