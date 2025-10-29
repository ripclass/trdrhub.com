#!/usr/bin/env python3
"""
Enterprise Multi-Environment CloudWatch Monitoring Stack for LCopilot API

Enhanced AWS CDK (Python) implementation with enterprise features:
- Cross-account deployment support
- Cost controls with S3 archival and lifecycle management
- Escalation routing with Lambda
- Future-proofing hooks for anomaly detection and log insights
- Compliance and security controls

Usage:
    cdk deploy --context env=prod --context enable_future_features=true
    cdk deploy --context env=staging --context enable_cost_controls=true
    cdk destroy --context env=staging

Requirements:
    pip install aws-cdk-lib constructs
"""

import json
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_iam as iam,
    aws_lambda as aws_lambda,
    aws_s3 as s3,
    aws_kms as kms,
    aws_glue as glue,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct
from typing import Optional, Dict, Any, List


class EnterpriseMonitoringStack(Stack):
    """Enterprise multi-environment CloudWatch monitoring stack for LCopilot API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str = "prod",
        enable_cost_controls: bool = True,
        enable_escalation_routing: bool = True,
        enable_future_features: bool = False,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load enterprise configuration
        self.config = self._load_enterprise_config()
        self.env_name = env_name
        self.env_config = self.config['environments'].get(env_name, {})
        self.global_config = self.config['global_settings']
        self.future_config = self.config['future_features']

        # Feature flags
        self.enable_cost_controls = enable_cost_controls
        self.enable_escalation_routing = enable_escalation_routing
        self.enable_future_features = enable_future_features

        # Validate account deployment
        self._validate_account()

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
            "ManagedBy": "AWS-CDK-Enterprise",
            "Purpose": "Enterprise-ErrorMonitoring",
            "Account": self.env_config.get('aws_account_id', 'unknown'),
        }

        # Create resources
        self.kms_key = self._create_kms_key()
        self.log_archive_bucket = self._create_log_archive_bucket() if enable_cost_controls else None
        self.log_group = self._create_log_group()
        self.metric_filter = self._create_metric_filter()
        self.sns_topic = self._create_sns_topic()
        self.escalation_lambda = self._create_escalation_lambda() if enable_escalation_routing else None
        self.email_sns_topic = self._create_email_sns_topic() if enable_escalation_routing else None
        self.alarm = self._create_cloudwatch_alarm()

        # Future features (optional)
        if enable_future_features:
            self.anomaly_detector = self._create_anomaly_detector()
            self.log_insights_queries = self._create_log_insights_queries()
            self.compliance_checker = self._create_compliance_checker()

        # Cost control features
        if enable_cost_controls:
            self.log_export_task = self._create_log_export_task()
            self.athena_table = self._create_athena_table()

        # Create outputs
        self._create_outputs()

    def _load_enterprise_config(self) -> Dict[str, Any]:
        """Load enterprise configuration from JSON file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'enterprise_config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback configuration
            return {
                'environments': {
                    'staging': {'alarm_threshold': 3, 'aws_account_id': '111111111111'},
                    'prod': {'alarm_threshold': 5, 'aws_account_id': '222222222222'}
                },
                'global_settings': {
                    'metric_namespace': 'LCopilot',
                    'alarm_period_seconds': 60,
                    'evaluation_periods': 1,
                    'treat_missing_data': 'notBreaching'
                },
                'future_features': {
                    'anomaly_detection': {'enabled': False},
                    'log_insights': {'enabled': True, 'queries': []},
                    'compliance': {'enabled': True}
                }
            }

    def _validate_account(self):
        """Validate deployment is in correct AWS account."""
        expected_account = self.env_config.get('aws_account_id')
        if expected_account and cdk.Aws.ACCOUNT_ID != expected_account:
            print(f"⚠️ Account validation: Expected {expected_account}, deploying to {cdk.Aws.ACCOUNT_ID}")

    def _create_kms_key(self) -> kms.Key:
        """Create KMS key for encryption."""
        key = kms.Key(
            self,
            f"{self.name_prefix}-encryption-key",
            description=f"LCopilot {self.env_name} encryption key",
            enable_key_rotation=True,
            removal_policy=cdk.RemovalPolicy.RETAIN if self.env_name == 'prod' else cdk.RemovalPolicy.DESTROY,
        )

        kms.Alias(
            self,
            f"{self.name_prefix}-key-alias",
            alias_name=f"alias/{self.name_prefix}-monitoring",
            target_key=key,
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(key).add(key_name, value)

        return key

    def _create_log_archive_bucket(self) -> Optional[s3.Bucket]:
        """Create S3 bucket for log archival (cost control)."""
        if not self.enable_cost_controls:
            return None

        bucket_name = self.env_config.get('cost_controls', {}).get('s3_bucket', f"{self.name_prefix}-logs-archive")

        bucket = s3.Bucket(
            self,
            f"{self.name_prefix}-log-archive",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="log-lifecycle",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        ),
                    ],
                    expiration=Duration.days(2555 if self.env_name == 'prod' else 365)  # 7 years prod, 1 year staging
                )
            ],
            removal_policy=cdk.RemovalPolicy.RETAIN if self.env_name == 'prod' else cdk.RemovalPolicy.DESTROY,
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(bucket).add(key_name, value)

        cdk.Tags.of(bucket).add("Purpose", "Log-Archival-Cost-Control")

        return bucket

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch Log Group with enhanced configuration."""
        retention_days = self.env_config.get('log_retention_days', 30)
        retention_setting = logs.RetentionDays.ONE_MONTH if retention_days >= 30 else logs.RetentionDays.ONE_WEEK

        log_group = logs.LogGroup(
            self,
            f"{self.name_prefix}-logs",
            log_group_name=self.log_group_name,
            retention=retention_setting,
            encryption_key=self.kms_key,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(log_group).add(key_name, value)

        return log_group

    def _create_metric_filter(self) -> logs.MetricFilter:
        """Create CloudWatch Metric Filter with cost controls."""
        cost_controls = self.env_config.get('cost_controls', {})

        # Enhanced filter pattern for cost control
        if self.enable_cost_controls and cost_controls.get('filter_debug_logs', False):
            filter_pattern = logs.FilterPattern.any_term("ERROR", "WARN", "FATAL")
        else:
            filter_pattern = logs.FilterPattern.string_value("$.level", "=", "ERROR")

        metric_filter = logs.MetricFilter(
            self,
            f"{self.name_prefix}-error-filter",
            log_group=self.log_group,
            metric_namespace=self.global_config['metric_namespace'],
            metric_name=self.metric_name,
            metric_value="1",
            default_value=0,
            filter_pattern=filter_pattern,
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(metric_filter).add(key_name, value)

        return metric_filter

    def _create_sns_topic(self) -> sns.Topic:
        """Create SNS Topic for primary alerts."""
        topic = sns.Topic(
            self,
            f"{self.name_prefix}-alerts",
            topic_name=self.sns_topic_name,
            display_name=f"LCopilot {self.env_name.upper()} Alerts",
            master_key=self.kms_key,
        )

        # Allow CloudWatch to publish
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
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(topic).add(key_name, value)

        return topic

    def _create_escalation_lambda(self) -> Optional[aws_lambda.Function]:
        """Create Lambda function for escalation routing."""
        if not self.enable_escalation_routing:
            return None

        # IAM role for Lambda
        lambda_role = iam.Role(
            self,
            f"{self.name_prefix}-escalation-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )

        # Add SNS publish permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=[f"arn:aws:sns:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:{self.sns_topic_name}-email"]
            )
        )

        # Lambda function
        escalation_function = aws_lambda.Function(
            self,
            f"{self.name_prefix}-escalation-router",
            function_name=f"{self.name_prefix}-escalation-router",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="escalation_router.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            environment={
                "ENVIRONMENT": self.env_name,
                "SLACK_WEBHOOK_URL": self.env_config.get('escalation', {}).get('slack_webhook', ''),
                "PAGERDUTY_INTEGRATION_KEY": self.env_config.get('escalation', {}).get('pagerduty_integration_key', ''),
                "EMAIL_SNS_TOPIC_ARN": f"arn:aws:sns:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:{self.sns_topic_name}-email",
            }
        )

        # Grant SNS permission to invoke Lambda
        escalation_function.add_permission(
            "AllowSNSInvoke",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            source_arn=self.sns_topic.topic_arn,
        )

        # Subscribe Lambda to SNS topic
        sns.Subscription(
            self,
            f"{self.name_prefix}-escalation-subscription",
            topic=self.sns_topic,
            endpoint=escalation_function.function_arn,
            protocol=sns.SubscriptionProtocol.LAMBDA,
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(escalation_function).add(key_name, value)

        return escalation_function

    def _create_email_sns_topic(self) -> Optional[sns.Topic]:
        """Create SNS topic for email notifications."""
        if not self.enable_escalation_routing:
            return None

        email_topic = sns.Topic(
            self,
            f"{self.name_prefix}-email-alerts",
            topic_name=f"{self.sns_topic_name}-email",
            display_name=f"LCopilot {self.env_name.upper()} Email Alerts",
        )

        # Add email subscriptions
        email_addresses = self.env_config.get('escalation', {}).get('email_addresses', [])
        for i, email in enumerate(email_addresses):
            sns.Subscription(
                self,
                f"{self.name_prefix}-email-sub-{i}",
                topic=email_topic,
                endpoint=email,
                protocol=sns.SubscriptionProtocol.EMAIL,
            )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(email_topic).add(key_name, value)

        return email_topic

    def _create_cloudwatch_alarm(self) -> cloudwatch.Alarm:
        """Create CloudWatch Alarm with enhanced configuration."""
        # Create metric
        metric = cloudwatch.Metric(
            namespace=self.global_config['metric_namespace'],
            metric_name=self.metric_name,
            statistic=cloudwatch.Statistic.SUM,
            period=Duration.seconds(self.global_config['alarm_period_seconds']),
        )

        # Create alarm
        alarm = cloudwatch.Alarm(
            self,
            f"{self.name_prefix}-error-alarm",
            alarm_name=self.alarm_name,
            alarm_description=f"[{self.env_name.upper()}] Triggers when ≥{self.env_config.get('alarm_threshold', 5)} errors occur within {self.global_config['alarm_period_seconds']} seconds",
            metric=metric,
            threshold=self.env_config.get('alarm_threshold', 5),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=self.global_config['evaluation_periods'],
            datapoints_to_alarm=self.global_config['evaluation_periods'],
            treat_missing_data=getattr(cloudwatch.TreatMissingData, self.global_config['treat_missing_data'].upper()),
            actions_enabled=True,
        )

        # Add SNS actions
        alarm.add_alarm_action(cloudwatch.SnsAction(self.sns_topic))
        alarm.add_ok_action(cloudwatch.SnsAction(self.sns_topic))

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(alarm).add(key_name, value)

        return alarm

    def _create_anomaly_detector(self) -> Optional[cloudwatch.CfnAnomalyDetector]:
        """Create CloudWatch Anomaly Detector (future feature)."""
        if not self.enable_future_features or not self.future_config.get('anomaly_detection', {}).get('enabled', False):
            return None

        anomaly_detector = cloudwatch.CfnAnomalyDetector(
            self,
            f"{self.name_prefix}-anomaly-detector",
            namespace=self.global_config['metric_namespace'],
            metric_name=self.metric_name,
            stat="Average",
        )

        # Create anomaly alarm
        cloudwatch.CfnAlarm(
            self,
            f"{self.name_prefix}-anomaly-alarm",
            alarm_name=f"{self.alarm_name}-anomaly",
            alarm_description=f"[{self.env_name.upper()}] Anomaly detection for error rate - triggers on >3σ deviation",
            comparison_operator="LessThanLowerOrGreaterThanUpperThreshold",
            evaluation_periods=2,
            metrics=[
                cloudwatch.CfnAlarm.MetricDataQueryProperty(
                    id="m1",
                    return_data=True,
                    metric_stat=cloudwatch.CfnAlarm.MetricStatProperty(
                        metric=cloudwatch.CfnAlarm.MetricProperty(
                            namespace=self.global_config['metric_namespace'],
                            metric_name=self.metric_name,
                        ),
                        period=300,
                        stat="Average",
                    ),
                ),
                cloudwatch.CfnAlarm.MetricDataQueryProperty(
                    id="ad1",
                    anomaly_detector=cloudwatch.CfnAlarm.AnomalyDetectorProperty(
                        namespace=self.global_config['metric_namespace'],
                        metric_name=self.metric_name,
                        stat="Average",
                    ),
                ),
            ],
            threshold_metric_id="ad1",
            actions_enabled=True,
            alarm_actions=[self.sns_topic.topic_arn],
            ok_actions=[self.sns_topic.topic_arn],
        )

        return anomaly_detector

    def _create_log_insights_queries(self) -> List[logs.CfnQueryDefinition]:
        """Create CloudWatch Logs Insights queries (future feature)."""
        if not self.enable_future_features or not self.future_config.get('log_insights', {}).get('enabled', True):
            return []

        queries = []
        query_definitions = self.future_config.get('log_insights', {}).get('queries', [])

        for i, query_def in enumerate(query_definitions):
            query = logs.CfnQueryDefinition(
                self,
                f"{self.name_prefix}-query-{i}",
                name=f"{self.name_prefix}-{query_def['name']}",
                log_group_names=[self.log_group.log_group_name],
                query_string=query_def['query'],
            )
            queries.append(query)

        return queries

    def _create_compliance_checker(self) -> Optional[aws_lambda.Function]:
        """Create compliance checker Lambda (future feature)."""
        if not self.enable_future_features or not self.future_config.get('compliance', {}).get('enabled', True):
            return None

        # IAM role for compliance checker
        compliance_role = iam.Role(
            self,
            f"{self.name_prefix}-compliance-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )

        # Add CloudWatch and Config permissions
        compliance_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:DescribeAlarms",
                    "logs:DescribeLogGroups",
                    "sns:ListTopics",
                    "config:PutEvaluations"
                ],
                resources=["*"]
            )
        )

        # Lambda function for compliance checks
        compliance_function = aws_lambda.Function(
            self,
            f"{self.name_prefix}-compliance-checker",
            function_name=f"{self.name_prefix}-compliance-checker",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=aws_lambda.Code.from_inline("""
import json
import boto3

def handler(event, context):
    # Basic compliance checks
    cloudwatch = boto3.client('cloudwatch')
    logs_client = boto3.client('logs')

    checks = []

    # Check if required alarms exist
    alarm_name = f"lcopilot-error-spike-{event.get('environment', 'unknown')}"
    try:
        response = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
        if response['MetricAlarms']:
            checks.append({"check": "alarm_exists", "status": "PASS"})
        else:
            checks.append({"check": "alarm_exists", "status": "FAIL"})
    except Exception as e:
        checks.append({"check": "alarm_exists", "status": "ERROR", "error": str(e)})

    return {
        'statusCode': 200,
        'body': json.dumps({
            'environment': event.get('environment'),
            'checks': checks,
            'compliant': all(check['status'] == 'PASS' for check in checks)
        })
    }
            """),
            role=compliance_role,
            timeout=Duration.seconds(60),
        )

        # Schedule compliance checks
        rule = events.Rule(
            self,
            f"{self.name_prefix}-compliance-schedule",
            schedule=events.Schedule.rate(Duration.hours(24)),  # Daily compliance check
        )

        rule.add_target(
            targets.LambdaFunction(
                compliance_function,
                event=events.RuleTargetInput.from_object({"environment": self.env_name})
            )
        )

        # Add tags
        for key_name, value in self.common_tags.items():
            cdk.Tags.of(compliance_function).add(key_name, value)

        cdk.Tags.of(compliance_function).add("Feature", "Future-Compliance-Checks")

        return compliance_function

    def _create_log_export_task(self) -> Optional[aws_lambda.Function]:
        """Create log export task for cost control."""
        if not self.enable_cost_controls or not self.log_archive_bucket:
            return None

        # IAM role for log export
        export_role = iam.Role(
            self,
            f"{self.name_prefix}-export-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )

        # Add permissions for log export and S3
        export_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateExportTask",
                    "logs:DescribeExportTasks",
                    "s3:PutObject",
                    "s3:GetBucketAcl"
                ],
                resources=[
                    f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group:{self.log_group_name}:*",
                    self.log_archive_bucket.bucket_arn,
                    f"{self.log_archive_bucket.bucket_arn}/*"
                ]
            )
        )

        # Lambda function for log export
        export_function = aws_lambda.Function(
            self,
            f"{self.name_prefix}-log-export",
            function_name=f"{self.name_prefix}-log-export",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=aws_lambda.Code.from_inline(f"""
import json
import boto3
from datetime import datetime, timedelta

def handler(event, context):
    logs_client = boto3.client('logs')

    # Export logs older than retention period
    end_time = datetime.now() - timedelta(days={self.env_config.get('log_retention_days', 30)})
    start_time = end_time - timedelta(days=1)

    try:
        response = logs_client.create_export_task(
            logGroupName='{self.log_group_name}',
            fromTime=int(start_time.timestamp() * 1000),
            to=int(end_time.timestamp() * 1000),
            destination='{self.log_archive_bucket.bucket_name}',
            destinationPrefix='year={{end_time.year}}/month={{end_time.month}}/day={{end_time.day}}/'
        )

        return {{
            'statusCode': 200,
            'body': json.dumps({{
                'taskId': response['taskId'],
                'message': 'Log export task created successfully'
            }})
        }}
    except Exception as e:
        return {{
            'statusCode': 500,
            'body': json.dumps({{'error': str(e)}})
        }}
            """),
            role=export_role,
            timeout=Duration.seconds(60),
        )

        # Schedule log export
        export_rule = events.Rule(
            self,
            f"{self.name_prefix}-export-schedule",
            schedule=events.Schedule.rate(Duration.days(1)),  # Daily export
        )

        export_rule.add_target(targets.LambdaFunction(export_function))

        return export_function

    def _create_athena_table(self) -> Optional[glue.CfnTable]:
        """Create Athena table for querying archived logs."""
        if not self.enable_cost_controls or not self.log_archive_bucket:
            return None

        # Create Glue database
        database = glue.CfnDatabase(
            self,
            f"{self.name_prefix}-logs-db",
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{self.name_prefix.replace('-', '_')}_logs_db",
                description=f"Database for {self.env_name} archived logs",
            ),
        )

        # Create Athena table
        table = glue.CfnTable(
            self,
            f"{self.name_prefix}-archived-logs-table",
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_name=database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name=f"{self.name_prefix.replace('-', '_')}_archived_logs",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "projection.enabled": "true",
                    "projection.year.type": "integer",
                    "projection.year.range": "2024,2030",
                    "projection.month.type": "integer",
                    "projection.month.range": "1,12",
                    "projection.day.type": "integer",
                    "projection.day.range": "1,31",
                    "storage.location.template": f"s3://{self.log_archive_bucket.bucket_name}/year=${{year}}/month=${{month}}/day=${{day}}/"
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    location=f"s3://{self.log_archive_bucket.bucket_name}/",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
                    ),
                    columns=[
                        glue.CfnTable.ColumnProperty(name="timestamp", type="string"),
                        glue.CfnTable.ColumnProperty(name="level", type="string"),
                        glue.CfnTable.ColumnProperty(name="message", type="string"),
                        glue.CfnTable.ColumnProperty(name="service", type="string"),
                    ],
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(name="year", type="string"),
                    glue.CfnTable.ColumnProperty(name="month", type="string"),
                    glue.CfnTable.ColumnProperty(name="day", type="string"),
                ],
            ),
        )

        return table

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for key resources."""

        # Environment and validation outputs
        cdk.CfnOutput(
            self,
            "Environment",
            value=self.env_name,
            description="Environment name",
        )

        cdk.CfnOutput(
            self,
            "DeployedAccountId",
            value=cdk.Aws.ACCOUNT_ID,
            description="AWS Account ID where resources were deployed",
        )

        cdk.CfnOutput(
            self,
            "ExpectedAccountId",
            value=self.env_config.get('aws_account_id', 'Not specified'),
            description="Expected AWS Account ID from configuration",
        )

        # Core resource outputs
        cdk.CfnOutput(
            self,
            "LogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch Log Group name",
            export_name=f"{self.name_prefix}-log-group-name"
        )

        cdk.CfnOutput(
            self,
            "MetricName",
            value=self.metric_name,
            description="CloudWatch Metric name",
        )

        cdk.CfnOutput(
            self,
            "AlarmName",
            value=self.alarm.alarm_name,
            description="CloudWatch Alarm name",
            export_name=f"{self.name_prefix}-alarm-name"
        )

        cdk.CfnOutput(
            self,
            "SnsTopicArn",
            value=self.sns_topic.topic_arn,
            description="SNS Topic ARN",
            export_name=f"{self.name_prefix}-sns-topic-arn"
        )

        # Feature-specific outputs
        if self.escalation_lambda:
            cdk.CfnOutput(
                self,
                "EscalationLambdaArn",
                value=self.escalation_lambda.function_arn,
                description="Escalation Router Lambda ARN",
            )

        if self.log_archive_bucket:
            cdk.CfnOutput(
                self,
                "LogArchiveBucket",
                value=self.log_archive_bucket.bucket_name,
                description="S3 bucket for log archival",
            )

        # Summary output
        cdk.CfnOutput(
            self,
            "MonitoringSummary",
            value=f"Environment: {self.env_name} | Alarm: {self.alarm.alarm_name} | Threshold: ≥{self.env_config.get('alarm_threshold', 5)} errors | Features: Cost={self.enable_cost_controls}, Escalation={self.enable_escalation_routing}, Future={self.enable_future_features}",
            description="Enterprise monitoring configuration summary",
        )


# CDK App with enterprise configuration
def create_enterprise_app():
    """Create CDK app with enterprise configuration."""
    app = cdk.App()

    # Get context parameters
    env_name = app.node.try_get_context("env") or "prod"
    enable_cost_controls = app.node.try_get_context("enable_cost_controls")
    enable_escalation_routing = app.node.try_get_context("enable_escalation_routing")
    enable_future_features = app.node.try_get_context("enable_future_features")

    # Set defaults based on environment
    if enable_cost_controls is None:
        enable_cost_controls = True  # Default enabled
    if enable_escalation_routing is None:
        enable_escalation_routing = True  # Default enabled
    if enable_future_features is None:
        enable_future_features = env_name == 'prod'  # Only enable in prod by default

    # Validate environment
    if env_name not in ["staging", "prod"]:
        raise ValueError(f"Invalid environment '{env_name}'. Must be 'staging' or 'prod'.")

    # Create stack
    EnterpriseMonitoringStack(
        app,
        f"LCopilotEnterpriseMonitoring-{env_name.title()}",
        env_name=env_name,
        enable_cost_controls=enable_cost_controls,
        enable_escalation_routing=enable_escalation_routing,
        enable_future_features=enable_future_features,
        description=f"LCopilot enterprise CloudWatch monitoring stack for {env_name} environment",
        env=cdk.Environment(
            region=app.node.try_get_context("region") or "eu-north-1"
        ),
    )

    return app


if __name__ == "__main__":
    # Create and synthesize the enterprise app
    app = create_enterprise_app()
    app.synth()