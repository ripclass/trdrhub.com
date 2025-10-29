#!/usr/bin/env python3
"""
CloudWatch setup script for LCopilot API monitoring.

This script creates:
- CloudWatch log group with retention policy
- Metric filters for error tracking
- CloudWatch alarms for error rate monitoring
- SNS topic for alerting
"""

import os
import sys
import boto3
from typing import Dict, Any

def setup_cloudwatch_logging():
    """Set up CloudWatch log group and retention policy."""

    print("🔧 Setting up CloudWatch logging...")

    # Get AWS region
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Create CloudWatch Logs client
    logs_client = boto3.client('logs', region_name=aws_region)

    log_group_name = "lcopilot-backend"
    retention_days = 30

    try:
        # Create log group
        try:
            logs_client.create_log_group(logGroupName=log_group_name)
            print(f"✅ Created log group: {log_group_name}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            print(f"ℹ️  Log group already exists: {log_group_name}")

        # Set retention policy
        logs_client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days
        )
        print(f"✅ Set retention policy: {retention_days} days")

        return True

    except Exception as e:
        print(f"❌ Failed to setup log group: {str(e)}")
        return False


def setup_metric_filters():
    """Set up CloudWatch metric filters for error tracking."""

    print("📊 Setting up CloudWatch metric filters...")

    # Get AWS region
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Create CloudWatch Logs client
    logs_client = boto3.client('logs', region_name=aws_region)

    log_group_name = "lcopilot-backend"

    # Metric filter configurations
    metric_filters = [
        {
            "filterName": "LCopilotErrorFilter",
            "filterPattern": '{ $.level = "ERROR" }',
            "metricTransformations": [
                {
                    "metricName": "LCopilotErrorCount",
                    "metricNamespace": "LCopilot/API",
                    "metricValue": "1",
                    "defaultValue": 0
                }
            ]
        },
        {
            "filterName": "LCopilotCriticalFilter",
            "filterPattern": '{ $.level = "CRITICAL" }',
            "metricTransformations": [
                {
                    "metricName": "LCopilotCriticalErrorCount",
                    "metricNamespace": "LCopilot/API",
                    "metricValue": "1",
                    "defaultValue": 0
                }
            ]
        },
        {
            "filterName": "LCopilot5xxErrorFilter",
            "filterPattern": '{ $.http_status_code >= 500 }',
            "metricTransformations": [
                {
                    "metricName": "LCopilot5xxErrorCount",
                    "metricNamespace": "LCopilot/API",
                    "metricValue": "1",
                    "defaultValue": 0
                }
            ]
        },
        {
            "filterName": "LCopilotSlowRequestFilter",
            "filterPattern": '{ $.request_duration_ms > 5000 }',
            "metricTransformations": [
                {
                    "metricName": "LCopilotSlowRequestCount",
                    "metricNamespace": "LCopilot/API",
                    "metricValue": "1",
                    "defaultValue": 0
                }
            ]
        }
    ]

    try:
        for metric_filter in metric_filters:
            try:
                logs_client.put_metric_filter(
                    logGroupName=log_group_name,
                    **metric_filter
                )
                print(f"✅ Created metric filter: {metric_filter['filterName']}")
            except Exception as e:
                print(f"⚠️  Failed to create metric filter {metric_filter['filterName']}: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ Failed to setup metric filters: {str(e)}")
        return False


def setup_sns_topic():
    """Set up SNS topic for alerting."""

    print("📧 Setting up SNS topic for alerts...")

    # Get AWS region
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Create SNS client
    sns_client = boto3.client('sns', region_name=aws_region)

    topic_name = "lcopilot-alerts"

    try:
        # Create SNS topic
        response = sns_client.create_topic(Name=topic_name)
        topic_arn = response['TopicArn']

        print(f"✅ Created/verified SNS topic: {topic_name}")
        print(f"   Topic ARN: {topic_arn}")

        # Set topic attributes for better delivery
        sns_client.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName='DisplayName',
            AttributeValue='LCopilot Alerts'
        )

        return topic_arn

    except Exception as e:
        print(f"❌ Failed to setup SNS topic: {str(e)}")
        return None


def setup_cloudwatch_alarms(topic_arn: str):
    """Set up CloudWatch alarms."""

    print("🚨 Setting up CloudWatch alarms...")

    # Get AWS region
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Create CloudWatch client
    cloudwatch_client = boto3.client('cloudwatch', region_name=aws_region)

    # Alarm configurations
    alarms = [
        {
            "AlarmName": "LCopilot-HighErrorRate",
            "AlarmDescription": "LCopilot API high error rate",
            "MetricName": "LCopilotErrorCount",
            "Namespace": "LCopilot/API",
            "Statistic": "Sum",
            "Period": 60,  # 1 minute
            "EvaluationPeriods": 1,
            "Threshold": 5.0,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "AlarmActions": [topic_arn],
            "OKActions": [topic_arn],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": "LCopilot-CriticalErrors",
            "AlarmDescription": "LCopilot API critical errors detected",
            "MetricName": "LCopilotCriticalErrorCount",
            "Namespace": "LCopilot/API",
            "Statistic": "Sum",
            "Period": 60,  # 1 minute
            "EvaluationPeriods": 1,
            "Threshold": 1.0,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "AlarmActions": [topic_arn],
            "OKActions": [topic_arn],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": "LCopilot-High5xxErrors",
            "AlarmDescription": "LCopilot API high 5xx error rate",
            "MetricName": "LCopilot5xxErrorCount",
            "Namespace": "LCopilot/API",
            "Statistic": "Sum",
            "Period": 300,  # 5 minutes
            "EvaluationPeriods": 2,
            "Threshold": 10.0,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "AlarmActions": [topic_arn],
            "OKActions": [topic_arn],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": "LCopilot-SlowRequests",
            "AlarmDescription": "LCopilot API slow requests detected",
            "MetricName": "LCopilotSlowRequestCount",
            "Namespace": "LCopilot/API",
            "Statistic": "Sum",
            "Period": 300,  # 5 minutes
            "EvaluationPeriods": 2,
            "Threshold": 5.0,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "AlarmActions": [topic_arn],
            "TreatMissingData": "notBreaching"
        }
    ]

    try:
        for alarm in alarms:
            cloudwatch_client.put_metric_alarm(**alarm)
            print(f"✅ Created alarm: {alarm['AlarmName']}")

        return True

    except Exception as e:
        print(f"❌ Failed to setup alarms: {str(e)}")
        return False


def verify_setup():
    """Verify the CloudWatch setup."""

    print("🔍 Verifying CloudWatch setup...")

    # Get AWS region
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Create clients
    logs_client = boto3.client('logs', region_name=aws_region)
    cloudwatch_client = boto3.client('cloudwatch', region_name=aws_region)
    sns_client = boto3.client('sns', region_name=aws_region)

    try:
        # Check log group
        log_groups = logs_client.describe_log_groups(
            logGroupNamePrefix="lcopilot-backend"
        )

        if log_groups['logGroups']:
            log_group = log_groups['logGroups'][0]
            print(f"✅ Log group exists: {log_group['logGroupName']}")
            print(f"   Retention: {log_group.get('retentionInDays', 'Never expire')} days")
        else:
            print("❌ Log group not found")
            return False

        # Check metric filters
        metric_filters = logs_client.describe_metric_filters(
            logGroupName="lcopilot-backend"
        )

        print(f"✅ Metric filters: {len(metric_filters['metricFilters'])} configured")
        for mf in metric_filters['metricFilters']:
            print(f"   - {mf['filterName']}")

        # Check alarms
        alarms = cloudwatch_client.describe_alarms(
            AlarmNamePrefix="LCopilot-"
        )

        print(f"✅ CloudWatch alarms: {len(alarms['MetricAlarms'])} configured")
        for alarm in alarms['MetricAlarms']:
            print(f"   - {alarm['AlarmName']} ({alarm['StateValue']})")

        # Check SNS topic
        topics = sns_client.list_topics()
        lcopilot_topics = [t for t in topics['Topics'] if 'lcopilot-alerts' in t['TopicArn']]

        if lcopilot_topics:
            print(f"✅ SNS topic exists: {lcopilot_topics[0]['TopicArn']}")
        else:
            print("❌ SNS topic not found")

        return True

    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False


def main():
    """Main setup function."""

    print("🚀 LCopilot CloudWatch Setup")
    print("=" * 40)

    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
        print("✅ AWS credentials configured")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {str(e)}")
        print("Please configure AWS credentials using aws configure or environment variables")
        sys.exit(1)

    # Setup components
    success = True

    # 1. CloudWatch logging
    if not setup_cloudwatch_logging():
        success = False

    # 2. Metric filters
    if not setup_metric_filters():
        success = False

    # 3. SNS topic
    topic_arn = setup_sns_topic()
    if not topic_arn:
        success = False

    # 4. CloudWatch alarms
    if topic_arn and not setup_cloudwatch_alarms(topic_arn):
        success = False

    # 5. Verification
    if success:
        print("\n" + "=" * 40)
        verify_setup()

        print("\n🎉 CloudWatch setup completed successfully!")
        print("\n📝 Next steps:")
        print(f"   1. Subscribe to SNS topic for alerts: {topic_arn}")
        print("   2. Test logging by running the API")
        print("   3. Trigger test alarms to verify alerting")
        print("\n💡 To subscribe to SNS alerts:")
        print(f"   aws sns subscribe --topic-arn {topic_arn} --protocol email --notification-endpoint your-email@domain.com")
    else:
        print("\n❌ CloudWatch setup completed with errors")
        print("Please check the error messages above and retry")
        sys.exit(1)


if __name__ == "__main__":
    main()