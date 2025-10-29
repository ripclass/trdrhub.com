"""
AWS CDK Stack for LCopilot Reliability-as-a-Service Infrastructure

Provides comprehensive infrastructure deployment with tier-based configuration.
Supports Free, Pro, and Enterprise tiers with appropriate resource allocation.
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_s3 as s3,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_certificatemanager as acm,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct
from typing import Dict, List, Optional, Any
from enum import Enum
import json

class ReliabilityTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class TierConfiguration:
    """Configuration class for tier-specific settings"""

    def __init__(self, tier: ReliabilityTier):
        self.tier = tier
        self._config = self._get_tier_config()

    def _get_tier_config(self) -> Dict[str, Any]:
        configs = {
            ReliabilityTier.FREE: {
                "lambda_memory": 256,
                "lambda_timeout": 30,
                "log_retention": logs.RetentionDays.ONE_WEEK,
                "s3_versioning": False,
                "backup_enabled": False,
                "multi_az": False,
                "auto_scaling": False,
                "reserved_concurrency": None,
                "enhanced_monitoring": False,
                "custom_domains": False,
                "white_label": False,
                "api_throttling": {"burst_limit": 100, "rate_limit": 50},
                "cloudwatch_dashboard": False,
                "predictive_analytics": False,
                "ml_features": False
            },
            ReliabilityTier.PRO: {
                "lambda_memory": 512,
                "lambda_timeout": 60,
                "log_retention": logs.RetentionDays.ONE_MONTH,
                "s3_versioning": True,
                "backup_enabled": True,
                "multi_az": False,
                "auto_scaling": True,
                "reserved_concurrency": 10,
                "enhanced_monitoring": True,
                "custom_domains": False,
                "white_label": False,
                "api_throttling": {"burst_limit": 500, "rate_limit": 250},
                "cloudwatch_dashboard": True,
                "predictive_analytics": False,
                "ml_features": False
            },
            ReliabilityTier.ENTERPRISE: {
                "lambda_memory": 1024,
                "lambda_timeout": 300,
                "log_retention": logs.RetentionDays.THREE_MONTHS,
                "s3_versioning": True,
                "backup_enabled": True,
                "multi_az": True,
                "auto_scaling": True,
                "reserved_concurrency": 50,
                "enhanced_monitoring": True,
                "custom_domains": True,
                "white_label": True,
                "api_throttling": {"burst_limit": 2000, "rate_limit": 1000},
                "cloudwatch_dashboard": True,
                "predictive_analytics": True,
                "ml_features": True
            }
        }
        return configs[self.tier]

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

class LCopilotReliabilityStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        tier: ReliabilityTier = ReliabilityTier.ENTERPRISE,
        customer_id: Optional[str] = None,
        white_label_domain: Optional[str] = None,
        alert_email: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.tier = tier
        self.customer_id = customer_id or ""
        self.white_label_domain = white_label_domain
        self.alert_email = alert_email
        self.config = TierConfiguration(tier)

        # Generate consistent resource names
        self.name_prefix = self._generate_name_prefix()

        # Common tags
        self.common_tags = {
            "Project": "LCopilot",
            "Component": "Reliability",
            "Tier": tier.value,
            "Environment": self.node.try_get_context("environment") or "production",
            "CustomerID": self.customer_id,
            "ManagedBy": "aws-cdk"
        }

        # Create infrastructure components
        self.create_storage_layer()
        self.create_execution_layer()
        self.create_api_layer()
        self.create_monitoring_layer()
        self.create_authentication_layer()
        self.create_distribution_layer()
        self.create_automation_layer()

        # Create outputs
        self.create_outputs()

    def _generate_name_prefix(self) -> str:
        """Generate consistent resource naming prefix"""
        base = f"lcopilot-reliability-{self.tier.value}"
        if self.customer_id:
            return f"{base}-{self.customer_id}"
        return base

    def create_storage_layer(self) -> None:
        """Create S3 buckets and storage resources"""

        # Status page assets bucket
        self.status_page_bucket = s3.Bucket(
            self, "StatusPageBucket",
            bucket_name=f"{self.name_prefix}-status-page-{self.node.try_get_context('environment') or 'prod'}",
            versioned=self.config.get("s3_versioning"),
            removal_policy=RemovalPolicy.RETAIN if self.tier != ReliabilityTier.FREE else RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(365 if self.tier == ReliabilityTier.ENTERPRISE else 90),
                    noncurrent_version_expiration=Duration.days(30) if self.config.get("s3_versioning") else None
                )
            ]
        )

        # SLA reports bucket
        self.sla_reports_bucket = s3.Bucket(
            self, "SLAReportsBucket",
            bucket_name=f"{self.name_prefix}-sla-reports-{self.node.try_get_context('environment') or 'prod'}",
            versioned=self.config.get("s3_versioning"),
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Analytics data bucket (Pro and Enterprise only)
        if self.tier != ReliabilityTier.FREE:
            self.analytics_bucket = s3.Bucket(
                self, "AnalyticsBucket",
                bucket_name=f"{self.name_prefix}-analytics-{self.node.try_get_context('environment') or 'prod'}",
                versioned=self.config.get("s3_versioning"),
                removal_policy=RemovalPolicy.RETAIN,
                intelligent_tiering_configurations=[
                    s3.IntelligentTieringConfiguration(
                        name="OptimizeStorage",
                        prefix="analytics/",
                        archive_access_tier_time=Duration.days(90),
                        deep_archive_access_tier_time=Duration.days(180)
                    )
                ]
            )

        # ML models bucket (Enterprise only)
        if self.tier == ReliabilityTier.ENTERPRISE:
            self.ml_models_bucket = s3.Bucket(
                self, "MLModelsBucket",
                bucket_name=f"{self.name_prefix}-ml-models-{self.node.try_get_context('environment') or 'prod'}",
                versioned=True,
                removal_policy=RemovalPolicy.RETAIN,
            )

    def create_execution_layer(self) -> None:
        """Create Lambda functions and execution resources"""

        # Create Lambda execution role with tier-appropriate permissions
        self.lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name=f"{self.name_prefix}-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add tier-specific permissions
        self._add_lambda_permissions()

        # Status Page Generator Lambda
        self.status_page_lambda = lambda_.Function(
            self, "StatusPageGenerator",
            function_name=f"{self.name_prefix}-status-page",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="status_page_generator.handler",
            code=lambda_.Code.from_asset("../status_page"),
            role=self.lambda_role,
            memory_size=self.config.get("lambda_memory"),
            timeout=Duration.seconds(self.config.get("lambda_timeout")),
            reserved_concurrent_executions=self.config.get("reserved_concurrency"),
            environment={
                "TIER": self.tier.value,
                "CUSTOMER_ID": self.customer_id,
                "S3_BUCKET": self.status_page_bucket.bucket_name,
                "WHITE_LABEL": str(self.config.get("white_label")),
                "WHITE_LABEL_DOMAIN": self.white_label_domain or ""
            },
            log_retention=self.config.get("log_retention")
        )

        # SLA Dashboard Manager Lambda
        self.sla_dashboard_lambda = lambda_.Function(
            self, "SLADashboardManager",
            function_name=f"{self.name_prefix}-sla-dashboard",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="sla_dashboard_manager.handler",
            code=lambda_.Code.from_asset("../sla_reporting"),
            role=self.lambda_role,
            memory_size=self.config.get("lambda_memory"),
            timeout=Duration.seconds(self.config.get("lambda_timeout")),
            reserved_concurrent_executions=self.config.get("reserved_concurrency"),
            environment={
                "TIER": self.tier.value,
                "CUSTOMER_ID": self.customer_id,
                "REPORTS_BUCKET": self.sla_reports_bucket.bucket_name
            },
            log_retention=self.config.get("log_retention")
        )

        # Trust Portal Manager Lambda (Pro and Enterprise)
        if self.tier != ReliabilityTier.FREE:
            self.trust_portal_lambda = lambda_.Function(
                self, "TrustPortalManager",
                function_name=f"{self.name_prefix}-trust-portal",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="trust_portal_manager.handler",
                code=lambda_.Code.from_asset("../trust_portal"),
                role=self.lambda_role,
                memory_size=self.config.get("lambda_memory"),
                timeout=Duration.seconds(self.config.get("lambda_timeout")),
                environment={
                    "TIER": self.tier.value,
                    "CUSTOMER_ID": self.customer_id,
                    "WHITE_LABEL": str(self.config.get("white_label"))
                },
                log_retention=self.config.get("log_retention")
            )

        # Integration API Manager Lambda (Enterprise only)
        if self.tier == ReliabilityTier.ENTERPRISE:
            self.integration_api_lambda = lambda_.Function(
                self, "IntegrationAPIManager",
                function_name=f"{self.name_prefix}-integration-api",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="integration_api_manager.handler",
                code=lambda_.Code.from_asset("../apis"),
                role=self.lambda_role,
                memory_size=self.config.get("lambda_memory"),
                timeout=Duration.seconds(self.config.get("lambda_timeout")),
                environment={
                    "TIER": self.tier.value,
                    "CUSTOMER_ID": self.customer_id
                },
                log_retention=self.config.get("log_retention")
            )

        # Analytics Manager Lambda (Pro and Enterprise)
        if self.tier != ReliabilityTier.FREE:
            self.analytics_lambda = lambda_.Function(
                self, "AnalyticsManager",
                function_name=f"{self.name_prefix}-analytics",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="analytics_manager.handler",
                code=lambda_.Code.from_asset("../analytics"),
                role=self.lambda_role,
                memory_size=self.config.get("lambda_memory") * 2,  # More memory for analytics
                timeout=Duration.seconds(self.config.get("lambda_timeout") * 2),
                environment={
                    "TIER": self.tier.value,
                    "CUSTOMER_ID": self.customer_id,
                    "ANALYTICS_BUCKET": self.analytics_bucket.bucket_name if hasattr(self, 'analytics_bucket') else ""
                },
                log_retention=self.config.get("log_retention")
            )

        # Predictive Manager Lambda (Enterprise only)
        if self.tier == ReliabilityTier.ENTERPRISE:
            self.predictive_lambda = lambda_.Function(
                self, "PredictiveManager",
                function_name=f"{self.name_prefix}-predictive",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="predictive_manager.handler",
                code=lambda_.Code.from_asset("../predictive"),
                role=self.lambda_role,
                memory_size=3008,  # Maximum memory for ML operations
                timeout=Duration.minutes(15),  # Extended timeout for ML
                environment={
                    "TIER": self.tier.value,
                    "CUSTOMER_ID": self.customer_id,
                    "MODELS_BUCKET": self.ml_models_bucket.bucket_name if hasattr(self, 'ml_models_bucket') else ""
                },
                log_retention=self.config.get("log_retention")
            )

    def _add_lambda_permissions(self) -> None:
        """Add tier-appropriate permissions to Lambda execution role"""

        # Basic permissions for all tiers
        basic_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            resources=[
                f"{self.status_page_bucket.bucket_arn}/*",
                f"{self.sla_reports_bucket.bucket_arn}/*"
            ]
        )

        cloudwatch_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudwatch:PutMetricData",
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:GetMetricData",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:StartQuery",
                "logs:GetQueryResults"
            ],
            resources=["*"]
        )

        self.lambda_role.add_to_policy(basic_policy)
        self.lambda_role.add_to_policy(cloudwatch_policy)

        # Enhanced permissions for Pro and Enterprise
        if self.tier != ReliabilityTier.FREE:
            enhanced_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                resources=[
                    f"{self.analytics_bucket.bucket_arn}/*" if hasattr(self, 'analytics_bucket') else ""
                ]
            )

            cognito_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-identity:*",
                    "cognito-idp:*"
                ],
                resources=["*"]
            )

            self.lambda_role.add_to_policy(enhanced_policy)
            self.lambda_role.add_to_policy(cognito_policy)

        # Enterprise-specific permissions
        if self.tier == ReliabilityTier.ENTERPRISE:
            ml_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:InvokeEndpoint",
                    "sagemaker:CreateModel",
                    "sagemaker:CreateTrainingJob",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                resources=[
                    "*",
                    f"{self.ml_models_bucket.bucket_arn}/*" if hasattr(self, 'ml_models_bucket') else ""
                ]
            )

            self.lambda_role.add_to_policy(ml_policy)

    def create_api_layer(self) -> None:
        """Create API Gateway and routing"""

        # Create API Gateway
        self.api_gateway = apigateway.RestApi(
            self, "ReliabilityAPI",
            rest_api_name=f"{self.name_prefix}-api",
            description=f"LCopilot Reliability API for {self.tier.value} tier",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ),
            deploy_options=apigateway.StageOptions(
                throttling_rate_limit=self.config.get("api_throttling")["rate_limit"],
                throttling_burst_limit=self.config.get("api_throttling")["burst_limit"],
                logging_level=apigateway.MethodLoggingLevel.INFO if self.config.get("enhanced_monitoring") else apigateway.MethodLoggingLevel.ERROR,
                data_trace_enabled=self.config.get("enhanced_monitoring"),
                metrics_enabled=True
            )
        )

        # Status endpoint
        status_resource = self.api_gateway.root.add_resource("status")
        status_integration = apigateway.LambdaIntegration(self.status_page_lambda)
        status_resource.add_method("GET", status_integration)

        # SLA endpoint
        sla_resource = self.api_gateway.root.add_resource("sla")
        sla_integration = apigateway.LambdaIntegration(self.sla_dashboard_lambda)
        sla_resource.add_method("GET", sla_integration)

        # Trust portal endpoint (Pro and Enterprise)
        if self.tier != ReliabilityTier.FREE and hasattr(self, 'trust_portal_lambda'):
            portal_resource = self.api_gateway.root.add_resource("portal")
            portal_integration = apigateway.LambdaIntegration(self.trust_portal_lambda)
            portal_resource.add_method("GET", portal_integration)
            portal_resource.add_method("POST", portal_integration)

        # Integration API endpoints (Enterprise only)
        if self.tier == ReliabilityTier.ENTERPRISE and hasattr(self, 'integration_api_lambda'):
            api_resource = self.api_gateway.root.add_resource("api")
            api_integration = apigateway.LambdaIntegration(self.integration_api_lambda)

            # Health endpoint
            health_resource = api_resource.add_resource("health")
            health_resource.add_method("GET", api_integration)

            # Reports endpoint
            reports_resource = api_resource.add_resource("reports")
            reports_resource.add_method("GET", api_integration)
            reports_resource.add_method("POST", api_integration)

    def create_monitoring_layer(self) -> None:
        """Create CloudWatch dashboards and alarms"""

        if not self.config.get("cloudwatch_dashboard"):
            return

        # Create CloudWatch dashboard
        self.dashboard = cloudwatch.Dashboard(
            self, "ReliabilityDashboard",
            dashboard_name=f"{self.name_prefix}-dashboard"
        )

        # Lambda metrics widget
        lambda_widget = cloudwatch.GraphWidget(
            title="Lambda Function Metrics",
            left=[
                self.status_page_lambda.metric_duration(),
                self.status_page_lambda.metric_errors(),
                self.status_page_lambda.metric_invocations()
            ],
            width=12,
            height=6
        )

        # API Gateway metrics widget
        api_widget = cloudwatch.GraphWidget(
            title="API Gateway Metrics",
            left=[
                self.api_gateway.metric_count(),
                self.api_gateway.metric_latency(),
                self.api_gateway.metric_client_error(),
                self.api_gateway.metric_server_error()
            ],
            width=12,
            height=6
        )

        self.dashboard.add_widgets(lambda_widget, api_widget)

        # Create alarms based on tier
        self._create_alarms()

    def _create_alarms(self) -> None:
        """Create CloudWatch alarms based on tier"""

        # SNS topic for alerts
        if self.alert_email:
            self.alert_topic = sns.Topic(
                self, "ReliabilityAlerts",
                topic_name=f"{self.name_prefix}-alerts"
            )

            self.alert_topic.add_subscription(
                subscriptions.EmailSubscription(self.alert_email)
            )

        # Lambda error alarm
        lambda_error_alarm = cloudwatch.Alarm(
            self, "LambdaErrorAlarm",
            alarm_name=f"{self.name_prefix}-lambda-errors",
            metric=self.status_page_lambda.metric_errors(period=Duration.minutes(5)),
            threshold=5 if self.tier == ReliabilityTier.FREE else 1,
            evaluation_periods=2,
            alarm_description="Lambda function error rate exceeded threshold"
        )

        if hasattr(self, 'alert_topic'):
            lambda_error_alarm.add_alarm_action(
                cdk.aws_cloudwatch_actions.SnsAction(self.alert_topic)
            )

        # API Gateway latency alarm
        api_latency_alarm = cloudwatch.Alarm(
            self, "APILatencyAlarm",
            alarm_name=f"{self.name_prefix}-api-latency",
            metric=self.api_gateway.metric_latency(period=Duration.minutes(5)),
            threshold=2000 if self.tier == ReliabilityTier.FREE else 1000,
            evaluation_periods=3,
            alarm_description="API Gateway latency exceeded threshold"
        )

        if hasattr(self, 'alert_topic'):
            api_latency_alarm.add_alarm_action(
                cdk.aws_cloudwatch_actions.SnsAction(self.alert_topic)
            )

    def create_authentication_layer(self) -> None:
        """Create Cognito User Pool for customer authentication"""

        if self.tier == ReliabilityTier.FREE:
            return

        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, "CustomerPortalUserPool",
            user_pool_name=f"{self.name_prefix}-portal",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Create User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "CustomerPortalClient",
            user_pool_client_name=f"{self.name_prefix}-portal-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            generate_secret=False
        )

    def create_distribution_layer(self) -> None:
        """Create CloudFront distribution for enterprise white-label"""

        if self.tier != ReliabilityTier.ENTERPRISE or not self.white_label_domain:
            return

        # Create Origin Access Identity
        self.oai = cloudfront.OriginAccessIdentity(
            self, "StatusPageOAI",
            comment=f"OAI for {self.white_label_domain}"
        )

        # Grant read access to OAI
        self.status_page_bucket.grant_read(self.oai)

        # Create CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self, "StatusPageDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.status_page_bucket,
                    origin_access_identity=self.oai
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            domain_names=[self.white_label_domain] if self.white_label_domain else None,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html"
                )
            ],
            comment=f"LCopilot Reliability Status Page for {self.customer_id}"
        )

    def create_automation_layer(self) -> None:
        """Create Step Functions for reliability automation"""

        if self.tier != ReliabilityTier.ENTERPRISE:
            return

        # Create Step Function for automated reliability checks
        check_status_task = sfn_tasks.LambdaInvoke(
            self, "CheckStatusTask",
            lambda_function=self.status_page_lambda,
            comment="Check service status"
        )

        analyze_metrics_task = sfn_tasks.LambdaInvoke(
            self, "AnalyzeMetricsTask",
            lambda_function=self.analytics_lambda if hasattr(self, 'analytics_lambda') else self.status_page_lambda,
            comment="Analyze reliability metrics"
        )

        # Define workflow
        definition = check_status_task.next(analyze_metrics_task)

        # Create State Machine
        self.reliability_workflow = stepfunctions.StateMachine(
            self, "ReliabilityWorkflow",
            state_machine_name=f"{self.name_prefix}-workflow",
            definition=definition,
            timeout=Duration.minutes(30)
        )

        # Create EventBridge rule to trigger workflow
        reliability_schedule = events.Rule(
            self, "ReliabilitySchedule",
            rule_name=f"{self.name_prefix}-schedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.SfnStateMachine(self.reliability_workflow)]
        )

    def create_outputs(self) -> None:
        """Create CDK outputs"""

        cdk.CfnOutput(
            self, "APIGatewayURL",
            value=self.api_gateway.url,
            description="API Gateway endpoint URL"
        )

        cdk.CfnOutput(
            self, "StatusPageBucket",
            value=self.status_page_bucket.bucket_name,
            description="S3 bucket for status page assets"
        )

        cdk.CfnOutput(
            self, "SLAReportsBucket",
            value=self.sla_reports_bucket.bucket_name,
            description="S3 bucket for SLA reports"
        )

        if hasattr(self, 'user_pool'):
            cdk.CfnOutput(
                self, "CognitoUserPoolId",
                value=self.user_pool.user_pool_id,
                description="Cognito User Pool ID"
            )

            cdk.CfnOutput(
                self, "CognitoUserPoolClientId",
                value=self.user_pool_client.user_pool_client_id,
                description="Cognito User Pool Client ID"
            )

        if hasattr(self, 'distribution'):
            cdk.CfnOutput(
                self, "CloudFrontDistributionId",
                value=self.distribution.distribution_id,
                description="CloudFront Distribution ID"
            )

            cdk.CfnOutput(
                self, "CloudFrontDomainName",
                value=self.distribution.distribution_domain_name,
                description="CloudFront Distribution Domain Name"
            )

        if hasattr(self, 'dashboard'):
            cdk.CfnOutput(
                self, "CloudWatchDashboardURL",
                value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
                description="CloudWatch Dashboard URL"
            )