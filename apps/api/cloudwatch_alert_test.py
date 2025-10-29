#!/usr/bin/env python3
"""
Multi-Environment CloudWatch Alert Chain Test for LCopilot API

End-to-end test that validates the complete monitoring pipeline:
API → CloudWatch Logs → Metric Filter → Alarm → SNS Notification

This script:
1. Loads .env.production for AWS credentials
2. Triggers API errors via debug endpoint
3. Polls CloudWatch for environment-specific metric datapoints
4. Monitors environment-specific alarm state changes
5. Confirms SNS notification path

Usage:
    python3 cloudwatch_alert_test.py                           # Test prod (default)
    python3 cloudwatch_alert_test.py --env staging             # Test staging
    python3 cloudwatch_alert_test.py --env prod --count 8      # Test prod with 8 errors

Requirements:
    - API server running on localhost:8000
    - .env.production with AWS credentials
    - CloudWatch log group and metric filter configured for environment
    - CloudWatch alarm and SNS topic set up for environment
"""

import os
import sys
import time
import argparse
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError


class CloudWatchAlertTester:
    """End-to-end CloudWatch monitoring pipeline test."""

    def __init__(self, environment: str = "prod", api_base_url: str = "http://localhost:8000",
                 error_count: int = 6, metric_timeout: int = 300,
                 alarm_reset_timeout: int = 600):
        # Environment configuration
        self.environment = environment

        # Configuration
        self.api_base_url = api_base_url
        self.error_count = error_count
        self.metric_timeout = metric_timeout
        self.alarm_reset_timeout = alarm_reset_timeout

        # Environment-aware CloudWatch configuration
        self.metric_namespace = "LCopilot"
        self.metric_name = f"LCopilotErrorCount-{environment}"
        self.alarm_name = f"lcopilot-error-spike-{environment}"
        self.log_group_name = f"/aws/lambda/lcopilot-{environment}"

        # AWS clients
        self.cloudwatch = None
        self.logs_client = None
        self.region = None

        # Test state
        self.start_time = datetime.now(timezone.utc)
        self.test_results = {}

    def load_environment(self) -> bool:
        """Load environment variables from .env.production."""
        print("🔧 Loading environment from .env.production...")

        env_file = '.env.production'
        if not os.path.exists(env_file):
            print(f"❌ Environment file {env_file} not found")
            print("   Create .env.production with AWS credentials")
            return False

        load_dotenv(env_file)

        # Verify required environment variables
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False

        self.region = os.getenv('AWS_REGION', 'eu-north-1')
        print(f"✅ Environment loaded successfully")
        print(f"   Region: {self.region}")
        return True

    def initialize_aws_clients(self) -> bool:
        """Initialize AWS CloudWatch clients with retry logic."""
        print("☁️  Initializing AWS clients...")

        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
            self.logs_client = boto3.client('logs', region_name=self.region)

            # Test credentials
            sts = boto3.client('sts', region_name=self.region)
            identity = sts.get_caller_identity()

            print(f"✅ AWS clients initialized")
            print(f"   Account: {identity.get('Account')}")
            print(f"   Region: {self.region}")
            print(f"   Identity: {identity.get('Arn', 'unknown').split('/')[-1]}")

            return True

        except NoCredentialsError:
            print("❌ AWS credentials not found")
            print("   Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env.production")
            return False
        except ClientError as e:
            print(f"❌ AWS authentication failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error initializing AWS clients: {e}")
            return False

    def trigger_api_errors(self) -> bool:
        """Trigger errors in the API using debug endpoint."""
        print(f"🚨 Triggering {self.error_count} errors via API...")

        try:
            url = f"{self.api_base_url}/debug/spam-errors"
            params = {'count': self.error_count}

            print(f"   Calling: {url}?count={self.error_count}")

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 500:
                print(f"✅ API errors triggered successfully")
                print(f"   Response: {response.json().get('detail', 'No detail')}")
                self.test_results['api_errors_triggered'] = True
                return True
            else:
                print(f"❌ Unexpected API response: {response.status_code}")
                print(f"   Content: {response.text}")
                self.test_results['api_errors_triggered'] = False
                return False

        except requests.exceptions.ConnectionError:
            print(f"❌ Failed to connect to API at {self.api_base_url}")
            print("   Make sure the API server is running:")
            print("   ENVIRONMENT=production python3 main.py")
            self.test_results['api_errors_triggered'] = False
            return False
        except requests.exceptions.Timeout:
            print(f"❌ API request timed out")
            self.test_results['api_errors_triggered'] = False
            return False
        except Exception as e:
            print(f"❌ Error triggering API errors: {e}")
            self.test_results['api_errors_triggered'] = False
            return False

    def wait_for_metric_datapoints(self) -> Optional[Dict[str, Any]]:
        """Wait for CloudWatch metric datapoints with intelligent polling."""
        print(f"⏳ Waiting for metric datapoints ({self.metric_name})...")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=10)  # Look back 10 minutes
        timeout_end = time.time() + self.metric_timeout

        attempt = 0
        while time.time() < timeout_end:
            attempt += 1
            print(f"   Attempt {attempt}: Checking for metric datapoints...")

            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace=self.metric_namespace,
                    MetricName=self.metric_name,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=60,  # 1-minute periods
                    Statistics=['Sum', 'Maximum', 'Average']
                )

                datapoints = response.get('Datapoints', [])
                if datapoints:
                    # Sort by timestamp and get the latest
                    latest_datapoint = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]

                    print(f"✅ Metric datapoints detected!")
                    print(f"   Metric: {self.metric_namespace}/{self.metric_name}")
                    print(f"   Latest value: {latest_datapoint.get('Sum', 'N/A')}")
                    print(f"   Timestamp: {latest_datapoint['Timestamp'].isoformat()}")
                    print(f"   Total datapoints: {len(datapoints)}")

                    self.test_results['metric_datapoints_found'] = True
                    self.test_results['metric_value'] = latest_datapoint.get('Sum', 0)
                    return latest_datapoint

                # Update end time for next check
                end_time = datetime.now(timezone.utc)

                # Rate limiting - wait before next attempt
                if time.time() < timeout_end:
                    wait_time = min(15, max(5, attempt))  # 5-15 second backoff
                    print(f"   No datapoints yet, waiting {wait_time}s...")
                    time.sleep(wait_time)

            except ClientError as e:
                print(f"   AWS error checking metrics: {e}")
                time.sleep(10)
            except Exception as e:
                print(f"   Error checking metrics: {e}")
                time.sleep(10)

        print(f"❌ No metric datapoints found within {self.metric_timeout} seconds")
        print(f"   This might indicate:")
        print(f"   1. Metric filter not configured correctly")
        print(f"   2. CloudWatch logs not flowing from API")
        print(f"   3. Metric namespace/name mismatch")

        self.test_results['metric_datapoints_found'] = False
        return None

    def wait_for_alarm_trigger(self) -> bool:
        """Wait for CloudWatch alarm to trigger with detailed monitoring."""
        print(f"⏳ Monitoring alarm state: {self.alarm_name}")

        timeout_end = time.time() + self.metric_timeout
        last_state = None
        attempt = 0

        while time.time() < timeout_end:
            attempt += 1

            try:
                response = self.cloudwatch.describe_alarms(AlarmNames=[self.alarm_name])
                alarms = response.get('MetricAlarms', [])

                if not alarms:
                    print(f"❌ Alarm '{self.alarm_name}' not found")
                    print("   Run: python3 setup_alarm.py to create it")
                    self.test_results['alarm_triggered'] = False
                    return False

                alarm = alarms[0]
                current_state = alarm['StateValue']
                state_reason = alarm.get('StateReason', 'No reason provided')
                state_updated = alarm.get('StateUpdatedTimestamp', 'Unknown')

                # Log state changes
                if current_state != last_state:
                    print(f"   State change: {last_state or 'Unknown'} → {current_state}")
                    print(f"   Reason: {state_reason}")
                    print(f"   Updated: {state_updated}")
                    last_state = current_state

                # Check if alarm triggered
                if current_state == 'ALARM':
                    print(f"✅ Alarm triggered successfully!")
                    print(f"   Alarm: {self.alarm_name}")
                    print(f"   State: {current_state}")
                    print(f"   Reason: {state_reason}")
                    print(f"   Time to trigger: {attempt * 15} seconds")

                    self.test_results['alarm_triggered'] = True
                    self.test_results['alarm_trigger_time'] = attempt * 15
                    return True

                # Progress indicator
                if attempt % 4 == 0:  # Every minute
                    print(f"   Still monitoring... (attempt {attempt}, state: {current_state})")

                # Rate limiting
                time.sleep(15)

            except Exception as e:
                print(f"   Error checking alarm: {e}")
                time.sleep(10)

        print(f"❌ Alarm did not trigger within {self.metric_timeout} seconds")
        print(f"   Current state: {last_state}")
        print(f"   This might indicate:")
        print(f"   1. Threshold not met (need ≥5 errors)")
        print(f"   2. Metric filter not working")
        print(f"   3. Alarm evaluation period issues")

        self.test_results['alarm_triggered'] = False
        return False

    def wait_for_alarm_reset(self) -> bool:
        """Wait for CloudWatch alarm to reset to OK state."""
        print(f"⏳ Waiting for alarm to reset to OK...")

        timeout_end = time.time() + self.alarm_reset_timeout
        attempt = 0

        while time.time() < timeout_end:
            attempt += 1

            try:
                response = self.cloudwatch.describe_alarms(AlarmNames=[self.alarm_name])
                alarms = response.get('MetricAlarms', [])

                if not alarms:
                    print(f"❌ Alarm not found during reset monitoring")
                    return False

                alarm = alarms[0]
                current_state = alarm['StateValue']
                state_reason = alarm.get('StateReason', 'No reason')
                state_updated = alarm.get('StateUpdatedTimestamp', 'Unknown')

                if current_state == 'OK':
                    print(f"✅ Alarm reset to OK!")
                    print(f"   Reset reason: {state_reason}")
                    print(f"   Reset time: {state_updated}")
                    print(f"   Time to reset: {attempt * 30} seconds")

                    self.test_results['alarm_reset'] = True
                    return True

                # Progress indicator
                if attempt % 2 == 0:  # Every minute
                    print(f"   Still waiting for reset... (state: {current_state})")

                time.sleep(30)  # Longer interval for reset monitoring

            except Exception as e:
                print(f"   Error monitoring alarm reset: {e}")
                time.sleep(30)

        print(f"⚠️  Alarm did not reset within {self.alarm_reset_timeout} seconds")
        print("   This is often normal - alarms may take time to reset")
        print("   Manual check: aws cloudwatch describe-alarms --alarm-names lcopilot-error-spike")

        self.test_results['alarm_reset'] = False
        return False

    def print_sns_notification_info(self):
        """Print SNS notification verification instructions."""
        print("\n📧 SNS NOTIFICATION VERIFICATION")
        print("-" * 40)
        print("Check your notification channels for alarm alerts:")
        print("   📧 Email: Look for subject containing 'lcopilot-error-spike'")
        print("   💬 Slack: Check configured channel for CloudWatch alerts")
        print("   📱 SMS: Check for text message (if configured)")
        print()
        print("Expected notification content:")
        print("   - Alarm name: lcopilot-error-spike")
        print("   - State change: OK → ALARM")
        print("   - Threshold: ≥5 errors")
        print("   - Metric: LCopilot/LCopilotErrorCount")
        print()
        print("If no notification received:")
        print("   1. Check SNS topic subscriptions are confirmed")
        print("   2. Verify email/phone number is correct")
        print("   3. Check spam/junk folders")
        print("   4. Verify SNS topic permissions")

    def print_test_summary(self):
        """Print comprehensive test results summary."""
        print("\n" + "=" * 70)
        print("📊 CLOUDWATCH ALERT TEST RESULTS")
        print("=" * 70)

        # Test results overview
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"Test Duration: {time.time() - time.mktime(self.start_time.timetuple()):.1f} seconds")

        # Individual test results
        print("\nDetailed Results:")
        result_descriptions = {
            'api_errors_triggered': 'API error injection',
            'metric_datapoints_found': 'CloudWatch metric datapoints',
            'alarm_triggered': 'Alarm state change to ALARM',
            'alarm_reset': 'Alarm state reset to OK'
        }

        for test_key, description in result_descriptions.items():
            result = self.test_results.get(test_key, False)
            status = "✅" if result else "❌"
            print(f"   {status} {description}")

        # Additional metrics
        if 'metric_value' in self.test_results:
            print(f"   📊 Metric value detected: {self.test_results['metric_value']}")

        if 'alarm_trigger_time' in self.test_results:
            print(f"   ⏱️  Alarm trigger time: {self.test_results['alarm_trigger_time']} seconds")

        # Overall assessment
        critical_tests = ['api_errors_triggered', 'metric_datapoints_found', 'alarm_triggered']
        critical_passed = all(self.test_results.get(test, False) for test in critical_tests)

        if critical_passed:
            print("\n🎉 CRITICAL MONITORING PATH VERIFIED!")
            print("✅ Your CloudWatch monitoring pipeline is working correctly")
            print("✅ Errors flow from API → Metrics → Alarms")
            print("📧 SNS notifications should be delivered")
        else:
            print("\n⚠️  MONITORING PIPELINE ISSUES DETECTED")
            failed_critical = [test for test in critical_tests if not self.test_results.get(test, False)]
            print(f"❌ Failed critical tests: {', '.join(failed_critical)}")
            print("💡 Review configuration and run setup scripts")

        # Next steps
        print(f"\n🔧 Next Steps:")
        if critical_passed:
            print("   1. Verify SNS notifications arrived")
            print("   2. Set up monitoring dashboards")
            print("   3. Document incident response procedures")
            print("   4. Schedule regular monitoring tests")
        else:
            print("   1. Check CloudWatch log group exists: lcopilot-backend")
            print("   2. Verify metric filter configuration: LCopilotErrorCount")
            print("   3. Confirm alarm setup: python3 setup_alarm.py")
            print("   4. Test individual components separately")

    def run_complete_test(self) -> bool:
        """Execute the complete end-to-end monitoring test."""
        print(f"🚀 LCopilot CloudWatch Alert Chain Test [{self.environment.upper()}]")
        print("=" * 70)
        print(f"Environment: {self.environment}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Parameters: {self.error_count} errors, {self.metric_timeout}s timeout")
        print("=" * 70)

        # Step 1: Environment setup
        if not self.load_environment():
            return False
        print()

        # Step 2: AWS client initialization
        if not self.initialize_aws_clients():
            return False
        print()

        # Step 3: Trigger API errors
        if not self.trigger_api_errors():
            return False
        print()

        # Step 4: Wait for metric datapoints
        datapoint = self.wait_for_metric_datapoints()
        if not datapoint:
            print("⚠️  Continuing test despite missing metrics...")
        print()

        # Step 5: Wait for alarm trigger
        alarm_triggered = self.wait_for_alarm_trigger()
        print()

        # Step 6: SNS notification info
        if alarm_triggered:
            self.print_sns_notification_info()
            print()

        # Step 7: Wait for alarm reset (optional)
        print("🔄 Monitoring alarm reset (optional)...")
        self.wait_for_alarm_reset()
        print()

        # Step 8: Print comprehensive results
        self.print_test_summary()

        # Return success if critical path works
        critical_success = (self.test_results.get('api_errors_triggered', False) and
                          (self.test_results.get('metric_datapoints_found', False) or
                           self.test_results.get('alarm_triggered', False)))

        return critical_success


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Multi-Environment CloudWatch monitoring pipeline test for LCopilot API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 cloudwatch_alert_test.py                          # Test prod (default)
  python3 cloudwatch_alert_test.py --env staging            # Test staging
  python3 cloudwatch_alert_test.py --env prod --count 8     # Test prod with 8 errors
  python3 cloudwatch_alert_test.py --timeout 600            # 10-minute timeout
  python3 cloudwatch_alert_test.py --api-url http://prod-api.com  # Remote API

Note: Ensure API server is running and .env.production is configured.
        """
    )

    parser.add_argument(
        '--env', '--environment',
        choices=['staging', 'prod'],
        default='prod',
        help='Environment to test alarm for (default: prod)'
    )
    parser.add_argument(
        '--count', type=int, default=6,
        help='Number of errors to trigger (default: 6)'
    )
    parser.add_argument(
        '--timeout', type=int, default=300,
        help='Timeout in seconds for metric/alarm checks (default: 300)'
    )
    parser.add_argument(
        '--alarm-reset-timeout', type=int, default=600,
        help='Timeout in seconds for alarm reset (default: 600)'
    )
    parser.add_argument(
        '--api-url', default="http://localhost:8000",
        help='API base URL (default: http://localhost:8000)'
    )

    args = parser.parse_args()

    # Validation
    if args.count < 5:
        print("⚠️  Warning: Error count < 5 may not trigger alarm (threshold: ≥5 errors)")

    # Run test
    try:
        tester = CloudWatchAlertTester(
            environment=args.env,
            api_base_url=args.api_url,
            error_count=args.count,
            metric_timeout=args.timeout,
            alarm_reset_timeout=args.alarm_reset_timeout
        )

        success = tester.run_complete_test()

        if success:
            print(f"\n✅ Test completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ Test failed - check results above")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()