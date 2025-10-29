#!/usr/bin/env python3
"""
Multi-Environment CloudWatch Monitoring Stack for LCopilot API

AWS CDK (Python) implementation that creates environment-specific:
- CloudWatch Log Groups
- Metric Filters for error counting
- CloudWatch Alarms with SNS integration
- SNS Topics for notifications

Usage:
    cdk deploy --context env=prod
    cdk deploy --context env=staging
    cdk destroy --context env=staging

Requirements:
    pip install aws-cdk-lib constructs
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_iam as iam,
)
from constructs import Construct
from typing import Optional


class LCopilotMonitoringStack(Stack):
    """Multi-environment CloudWatch monitoring stack for LCopilot API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str = "prod",
        alarm_threshold: int = 5,
        alarm_period_minutes: int = 1,
        log_retention_days: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Environment configuration
        self.env_name = env_name
        self.alarm_threshold = alarm_threshold
        self.alarm_period = Duration.minutes(alarm_period_minutes)

        # Set default log retention based on environment
        if log_retention_days is None:
            log_retention_days = 30 if env_name == "prod" else 7

        # Resource naming following the convention
        self.name_prefix = f"lcopilot-{env_name}"
        self.log_group_name = f"/aws/lambda/lcopilot-{env_name}"
        self.metric_name = f"LCopilotErrorCount-{env_name}"
        self.alarm_name = f"lcopilot-error-spike-{env_name}"
        self.sns_topic_name = f"lcopilot-alerts-{env_name}"

        # Common tags
        self.common_tags = {
            "Application": "LCopilot",
            "Environment": env_name,
            "ManagedBy": "AWS-CDK",
            "Purpose": "ErrorMonitoring",
        }

        # Create resources
        self.log_group = self._create_log_group(log_retention_days)
        self.metric_filter = self._create_metric_filter()
        self.sns_topic = self._create_sns_topic()
        self.alarm = self._create_cloudwatch_alarm()

        # Create outputs
        self._create_outputs()

    def _create_log_group(self, retention_days: int) -> logs.LogGroup:
        """Create CloudWatch Log Group for the environment."""
        log_group = logs.LogGroup(
            self,
            f"{self.name_prefix}-logs",
            log_group_name=self.log_group_name,
            retention=logs.RetentionDays(f"ONE_MONTH" if retention_days >= 30 else "ONE_WEEK"),
            removal_policy=cdk.RemovalPolicy.DESTROY,  # For non-prod environments
        )

        # Add tags
        for key, value in self.common_tags.items():
            cdk.Tags.of(log_group).add(key, value)

        return log_group

    def _create_metric_filter(self) -> logs.MetricFilter:
        """Create CloudWatch Metric Filter for error counting."""
        metric_filter = logs.MetricFilter(
            self,
            f"{self.name_prefix}-error-filter",
            log_group=self.log_group,
            metric_namespace="LCopilot",
            metric_name=self.metric_name,
            metric_value="1",
            default_value=0,
            filter_pattern=logs.FilterPattern.json_pattern(
                json_field="$.level",
                comparison="=",
                value="ERROR"
            ),
        )

        # Add tags
        for key, value in self.common_tags.items():
            cdk.Tags.of(metric_filter).add(key, value)

        return metric_filter

    def _create_sns_topic(self) -> sns.Topic:
        """Create SNS Topic for alarm notifications."""
        topic = sns.Topic(
            self,
            f"{self.name_prefix}-alerts",
            topic_name=self.sns_topic_name,
            display_name=f"LCopilot {self.env_name.upper()} Alerts",
        )

        # Allow CloudWatch to publish to this topic
        topic.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
                actions=["sns:Publish"],
                resources=[topic.topic_arn],
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": cdk.Aws.ACCOUNT_ID
                    }
                }
            )
        )

        # Add tags
        for key, value in self.common_tags.items():
            cdk.Tags.of(topic).add(key, value)

        return topic

    def _create_cloudwatch_alarm(self) -> cloudwatch.Alarm:
        """Create CloudWatch Alarm for error spike detection."""

        # Create metric
        metric = cloudwatch.Metric(
            namespace="LCopilot",
            metric_name=self.metric_name,
            statistic=cloudwatch.Statistic.SUM,
            period=self.alarm_period,
        )

        # Create alarm
        alarm = cloudwatch.Alarm(
            self,
            f"{self.name_prefix}-error-alarm",
            alarm_name=self.alarm_name,
            alarm_description=f"[{self.env_name.upper()}] Triggers when ≥{self.alarm_threshold} errors occur within {self.alarm_period.to_minutes()} minute(s)",
            metric=metric,
            threshold=self.alarm_threshold,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            actions_enabled=True,
        )

        # Add SNS actions
        alarm.add_alarm_action(
            cloudwatch.SnsAction(self.sns_topic)
        )
        alarm.add_ok_action(
            cloudwatch.SnsAction(self.sns_topic)
        )

        # Add tags
        for key, value in self.common_tags.items():
            cdk.Tags.of(alarm).add(key, value)

        return alarm

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for key resources."""

        # Log Group outputs
        cdk.CfnOutput(
            self,
            "LogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch Log Group name",
            export_name=f"{self.name_prefix}-log-group-name"
        )

        cdk.CfnOutput(
            self,
            "LogGroupArn",
            value=self.log_group.log_group_arn,
            description="CloudWatch Log Group ARN",
            export_name=f"{self.name_prefix}-log-group-arn"
        )

        # Metric outputs
        cdk.CfnOutput(
            self,
            "MetricName",
            value=self.metric_name,
            description="CloudWatch Metric name",
            export_name=f"{self.name_prefix}-metric-name"
        )

        # Alarm outputs
        cdk.CfnOutput(
            self,
            "AlarmName",
            value=self.alarm.alarm_name,
            description="CloudWatch Alarm name",
            export_name=f"{self.name_prefix}-alarm-name"
        )

        cdk.CfnOutput(
            self,
            "AlarmArn",
            value=self.alarm.alarm_arn,
            description="CloudWatch Alarm ARN",
            export_name=f"{self.name_prefix}-alarm-arn"
        )

        # SNS outputs
        cdk.CfnOutput(
            self,
            "SnsTopicName",
            value=self.sns_topic.topic_name,
            description="SNS Topic name",
            export_name=f"{self.name_prefix}-sns-topic-name"
        )

        cdk.CfnOutput(
            self,
            "SnsTopicArn",
            value=self.sns_topic.topic_arn,
            description="SNS Topic ARN",
            export_name=f"{self.name_prefix}-sns-topic-arn"
        )

        # Summary output
        cdk.CfnOutput(
            self,
            "MonitoringSummary",
            value=f"Environment: {self.env_name} | Alarm: {self.alarm_name} | Threshold: ≥{self.alarm_threshold} errors",
            description="Monitoring configuration summary",
        )


# CDK App with environment-specific stack instantiation
def create_app():
    """Create CDK app with environment-specific configuration."""
    app = cdk.App()

    # Get environment from context (default to prod)
    env_name = app.node.try_get_context("env") or "prod"

    # Validate environment
    if env_name not in ["staging", "prod"]:
        raise ValueError(f"Invalid environment '{env_name}'. Must be 'staging' or 'prod'.")

    # Environment-specific configuration
    config = {
        "staging": {
            "alarm_threshold": 3,  # Lower threshold for staging
            "log_retention_days": 7,
        },
        "prod": {
            "alarm_threshold": 5,  # Higher threshold for production
            "log_retention_days": 30,
        }
    }

    env_config = config[env_name]

    # Create stack
    LCopilotMonitoringStack(
        app,
        f"LCopilotMonitoring-{env_name.title()}",
        env_name=env_name,
        alarm_threshold=env_config["alarm_threshold"],
        log_retention_days=env_config["log_retention_days"],
        description=f"LCopilot CloudWatch monitoring stack for {env_name} environment",
        env=cdk.Environment(
            region=app.node.try_get_context("region") or "eu-north-1"
        ),
    )

    return app


if __name__ == "__main__":
    # Create and synthesize the app
    app = create_app()
    app.synth()