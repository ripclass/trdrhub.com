#!/usr/bin/env python3
"""
CloudWatch smoke test script for LCopilot API.

This script verifies that AWS CloudWatch logging works with your current
environment configuration by creating a test log group and sending a test message.
"""

import os
import sys
import boto3
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError


def load_environment():
    """Load environment variables from .env file if it exists."""
    env_file = '.env.production'
    if os.path.exists(env_file):
        print(f"📄 Loading environment from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment loaded successfully")
    else:
        print("ℹ️  No .env.production file found, using system environment")


def verify_aws_credentials():
    """Verify AWS credentials are configured."""
    print("\n🔐 Verifying AWS credentials...")

    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()

        print("✅ AWS credentials verified")
        print(f"   Account ID: {identity.get('Account', 'unknown')}")
        print(f"   User/Role: {identity.get('Arn', 'unknown').split('/')[-1]}")
        return True

    except Exception as e:
        print(f"❌ AWS credentials verification failed: {str(e)}")
        print("💡 Make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set")
        return False


def test_cloudwatch_logging():
    """Test CloudWatch logging functionality."""
    print("\n☁️ Testing CloudWatch Logs...")

    # Get configuration from environment
    aws_region = os.getenv('AWS_REGION', 'eu-north-1')
    print(f"   Region: {aws_region}")

    # Create CloudWatch Logs client
    try:
        logs_client = boto3.client('logs', region_name=aws_region)
        print("✅ CloudWatch Logs client created")
    except Exception as e:
        print(f"❌ Failed to create CloudWatch client: {str(e)}")
        return False

    # Test log group names
    test_log_group = "lcopilot-smoketest"
    production_log_group = "lcopilot-backend"

    # Create timestamp for unique log stream
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    test_log_stream = f"test-stream-{timestamp}"

    success = True

    # Test 1: Create test log group
    print(f"\n📝 Step 1: Creating test log group '{test_log_group}'...")
    try:
        logs_client.create_log_group(logGroupName=test_log_group)
        print("✅ Test log group created successfully")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print("ℹ️  Test log group already exists (that's fine)")
    except Exception as e:
        print(f"❌ Failed to create test log group: {str(e)}")
        success = False

    # Test 2: Create log stream
    print(f"\n📝 Step 2: Creating log stream '{test_log_stream}'...")
    try:
        logs_client.create_log_stream(
            logGroupName=test_log_group,
            logStreamName=test_log_stream
        )
        print("✅ Log stream created successfully")
    except Exception as e:
        print(f"❌ Failed to create log stream: {str(e)}")
        success = False

    # Test 3: Send test log event
    print(f"\n📝 Step 3: Sending test log event...")
    try:
        # Create test log message
        test_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "service": "lcopilot-api",
            "environment": "smoketest",
            "message": "🚀 CloudWatch smoke test successful!",
            "test_type": "cloudwatch_connectivity",
            "aws_region": aws_region
        }

        response = logs_client.put_log_events(
            logGroupName=test_log_group,
            logStreamName=test_log_stream,
            logEvents=[
                {
                    'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                    'message': json.dumps(test_message)
                }
            ]
        )

        print("✅ Test log event sent successfully")
        print(f"   Next sequence token: {response.get('nextSequenceToken', 'none')}")

    except Exception as e:
        print(f"❌ Failed to send log event: {str(e)}")
        success = False

    # Test 4: Check production log group exists
    print(f"\n📝 Step 4: Checking production log group '{production_log_group}'...")
    try:
        response = logs_client.describe_log_groups(
            logGroupNamePrefix=production_log_group
        )

        if response['logGroups']:
            log_group = response['logGroups'][0]
            print("✅ Production log group exists")
            print(f"   Creation time: {datetime.fromtimestamp(log_group['creationTime']/1000, timezone.utc)}")
            print(f"   Retention: {log_group.get('retentionInDays', 'Never expire')} days")

            # Check for log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=production_log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=3
            )

            if streams_response['logStreams']:
                print(f"   Recent log streams ({len(streams_response['logStreams'])}):")
                for stream in streams_response['logStreams']:
                    last_event = datetime.fromtimestamp(stream.get('lastEventTime', 0)/1000, timezone.utc)
                    print(f"     - {stream['logStreamName']} (last: {last_event})")
            else:
                print("   No log streams found (app hasn't written logs yet)")

        else:
            print("⚠️  Production log group not found")
            print("💡 Run: python setup_cloudwatch.py to create it")

    except Exception as e:
        print(f"❌ Failed to check production log group: {str(e)}")

    return success


def test_production_logging():
    """Test production-style logging to the actual production log group."""
    print("\n🏭 Testing production log group...")

    aws_region = os.getenv('AWS_REGION', 'eu-north-1')
    logs_client = boto3.client('logs', region_name=aws_region)

    production_log_group = "lcopilot-backend"
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    test_log_stream = f"smoketest-{timestamp}"

    try:
        # Create log stream in production log group
        logs_client.create_log_stream(
            logGroupName=production_log_group,
            logStreamName=test_log_stream
        )
        print(f"✅ Created log stream in production log group: {test_log_stream}")

        # Send production-style log message
        production_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "service": "lcopilot-api",
            "environment": "production",
            "hostname": "smoketest-client",
            "version": "2.0.0",
            "message": "🧪 Production CloudWatch smoke test successful!",
            "test_type": "production_logging_verification",
            "aws_region": aws_region,
            "log_group": production_log_group
        }

        logs_client.put_log_events(
            logGroupName=production_log_group,
            logStreamName=test_log_stream,
            logEvents=[
                {
                    'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                    'message': json.dumps(production_message)
                }
            ]
        )

        print("✅ Production-style log event sent successfully")
        print(f"   Log group: {production_log_group}")
        print(f"   Log stream: {test_log_stream}")
        return True

    except logs_client.exceptions.ResourceNotFoundException:
        print(f"⚠️  Production log group '{production_log_group}' not found")
        print("💡 Run: python setup_cloudwatch.py to create it")
        return False

    except Exception as e:
        print(f"❌ Production logging test failed: {str(e)}")
        return False


def print_results(test_success, prod_success):
    """Print final test results and next steps."""
    print("\n" + "="*60)
    print("📊 CLOUDWATCH SMOKE TEST RESULTS")
    print("="*60)

    if test_success:
        print("✅ CloudWatch connectivity: PASSED")
        print("   ✓ AWS credentials working")
        print("   ✓ CloudWatch Logs client functional")
        print("   ✓ Log group creation working")
        print("   ✓ Log event sending working")
    else:
        print("❌ CloudWatch connectivity: FAILED")
        print("   Check AWS credentials and permissions")

    if prod_success:
        print("✅ Production logging: PASSED")
        print("   ✓ Production log group accessible")
        print("   ✓ Production-style logging working")
    else:
        print("⚠️  Production logging: NEEDS SETUP")
        print("   Run setup_cloudwatch.py first")

    print(f"\n🔍 View results in AWS Console:")
    region = os.getenv('AWS_REGION', 'eu-north-1')
    print(f"   https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups")

    if test_success or prod_success:
        print(f"\n🎉 CloudWatch logging is working!")
        print(f"   Your LCopilot API logs will flow to CloudWatch in production")
        print(f"\n🚀 Next steps:")
        print(f"   1. Start your API: python main.py")
        print(f"   2. Test debug endpoints: curl http://localhost:8000/debug/error")
        print(f"   3. Check CloudWatch for logs from your running application")

        if not prod_success:
            print(f"   4. Set up production infrastructure: python setup_cloudwatch.py")
    else:
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Verify AWS credentials in .env.production")
        print(f"   2. Check IAM permissions for CloudWatch Logs")
        print(f"   3. Ensure correct AWS region is set")


def main():
    """Main smoke test function."""
    print("🚀 LCopilot CloudWatch Smoke Test")
    print("="*50)

    # Load environment
    load_environment()

    # Verify AWS credentials
    if not verify_aws_credentials():
        print("\n❌ Cannot proceed without valid AWS credentials")
        sys.exit(1)

    # Run tests
    test_success = test_cloudwatch_logging()
    prod_success = test_production_logging()

    # Print results
    print_results(test_success, prod_success)

    # Exit with appropriate code
    if test_success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()