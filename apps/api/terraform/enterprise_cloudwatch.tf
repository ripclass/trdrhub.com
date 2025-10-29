# Enterprise Multi-Environment CloudWatch Monitoring for LCopilot API
# Supports cross-account deployment with escalation routing and cost controls
#
# Usage:
#   terraform apply -var="environment=prod" -var="aws_profile=lcopilot-production"
#   terraform apply -var="environment=staging" -var="aws_profile=lcopilot-staging"

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# Load enterprise configuration
locals {
  config_file = file("${path.module}/../config/enterprise_config.json")
  config      = jsondecode(local.config_file)

  env_config     = local.config.environments[var.environment]
  global_config  = local.config.global_settings
  future_config  = local.config.future_features

  # Resource naming
  name_prefix = "lcopilot-${var.environment}"

  # Resource names following the naming convention
  log_group_name       = "/aws/lambda/lcopilot-${var.environment}"
  metric_filter_name   = "LCopilotErrorCount-${var.environment}"
  metric_name         = "LCopilotErrorCount-${var.environment}"
  alarm_name          = "lcopilot-error-spike-${var.environment}"
  sns_topic_name      = "lcopilot-alerts-${var.environment}"

  # Cost control settings
  cost_controls = local.env_config.cost_controls

  # Common tags
  common_tags = {
    Application = "LCopilot"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Enterprise-ErrorMonitoring"
    Account     = local.env_config.aws_account_id
  }
}

# Variables
variable "environment" {
  description = "Environment name (staging or prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be either 'staging' or 'prod'."
  }
}

variable "aws_profile" {
  description = "AWS profile for cross-account deployment"
  type        = string
  default     = null
}

variable "enable_cross_account_validation" {
  description = "Validate deployment is in correct AWS account"
  type        = bool
  default     = true
}

variable "enable_cost_controls" {
  description = "Enable cost control features (log filtering, S3 archival)"
  type        = bool
  default     = true
}

variable "enable_escalation_routing" {
  description = "Enable Lambda-based escalation routing"
  type        = bool
  default     = true
}

variable "enable_future_features" {
  description = "Enable future-proofing features (anomaly detection, log insights)"
  type        = bool
  default     = false
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Validate account ID if cross-account validation is enabled
resource "null_resource" "account_validation" {
  count = var.enable_cross_account_validation ? 1 : 0

  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == local.env_config.aws_account_id
      error_message = "Deployment account ${data.aws_caller_identity.current.account_id} does not match expected account ${local.env_config.aws_account_id} for ${var.environment} environment."
    }
  }
}

# S3 Bucket for Log Archival (Cost Control)
resource "aws_s3_bucket" "log_archive" {
  count  = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  bucket = local.cost_controls.s3_bucket

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-log-archive"
    Purpose = "Log-Archival-Cost-Control"
  })
}

resource "aws_s3_bucket_versioning" "log_archive" {
  count  = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  bucket = aws_s3_bucket.log_archive[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "log_archive" {
  count  = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  bucket = aws_s3_bucket.log_archive[0].id

  rule {
    id     = "log_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.environment == "prod" ? 2555 : 365  # 7 years for prod, 1 year for staging
    }
  }
}

# CloudWatch Log Group with enhanced configuration
resource "aws_cloudwatch_log_group" "lcopilot" {
  name              = local.log_group_name
  retention_in_days = local.env_config.log_retention_days
  kms_key_id       = aws_kms_key.logs.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs"
  })
}

# KMS Key for Log Encryption
resource "aws_kms_key" "logs" {
  description             = "LCopilot ${var.environment} log encryption key"
  deletion_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs-key"
  })
}

resource "aws_kms_alias" "logs" {
  name          = "alias/${local.name_prefix}-logs"
  target_key_id = aws_kms_key.logs.key_id
}

# Log Destination for S3 Export (Cost Control)
resource "aws_cloudwatch_log_destination" "s3_export" {
  count = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0

  name            = "${local.name_prefix}-s3-export"
  role_arn        = aws_iam_role.log_destination[0].arn
  target_arn      = aws_s3_bucket.log_archive[0].arn
  filter_pattern  = local.cost_controls.filter_debug_logs ? "[level != DEBUG && level != INFO]" : ""
}

# IAM Role for Log Destination
resource "aws_iam_role" "log_destination" {
  count = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  name  = "${local.name_prefix}-log-destination-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "logs.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "log_destination" {
  count = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  name  = "${local.name_prefix}-log-destination-policy"
  role  = aws_iam_role.log_destination[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketAcl",
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.log_archive[0].arn,
          "${aws_s3_bucket.log_archive[0].arn}/*"
        ]
      }
    ]
  })
}

# Enhanced Metric Filter with Cost Controls
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = local.metric_filter_name
  log_group_name = aws_cloudwatch_log_group.lcopilot.name

  # Enhanced pattern that excludes DEBUG/INFO if cost controls enabled
  pattern = local.cost_controls.enable_log_filtering && local.cost_controls.filter_debug_logs ?
    "{ $.level = \"ERROR\" || $.level = \"WARN\" || $.level = \"FATAL\" }" :
    "{ $.level = \"ERROR\" }"

  metric_transformation {
    name          = local.metric_name
    namespace     = local.global_config.metric_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# SNS Topic for Primary Alerts
resource "aws_sns_topic" "lcopilot_alerts" {
  name = local.sns_topic_name
  kms_master_key_id = "alias/aws/sns"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alerts"
  })
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "lcopilot_alerts_policy" {
  arn = aws_sns_topic.lcopilot_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchToPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.lcopilot_alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# Lambda-based Escalation Router
resource "aws_lambda_function" "escalation_router" {
  count = var.enable_escalation_routing ? 1 : 0

  filename         = data.archive_file.escalation_router[0].output_path
  function_name    = "${local.name_prefix}-escalation-router"
  role            = aws_iam_role.escalation_router[0].arn
  handler         = "escalation_router.lambda_handler"
  source_code_hash = data.archive_file.escalation_router[0].output_base64sha256
  runtime         = "python3.9"
  timeout         = 30

  environment {
    variables = {
      ENVIRONMENT = var.environment
      SLACK_WEBHOOK_URL = local.env_config.escalation.slack_webhook
      PAGERDUTY_INTEGRATION_KEY = local.env_config.escalation.pagerduty_integration_key
      EMAIL_SNS_TOPIC_ARN = aws_sns_topic.email_alerts[0].arn
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-escalation-router"
  })
}

# Archive Lambda code
data "archive_file" "escalation_router" {
  count = var.enable_escalation_routing ? 1 : 0
  type  = "zip"
  source_file = "${path.module}/../lambda/escalation_router.py"
  output_path = "${path.module}/escalation_router.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "escalation_router" {
  count = var.enable_escalation_routing ? 1 : 0
  name  = "${local.name_prefix}-escalation-router-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "escalation_router_basic" {
  count      = var.enable_escalation_routing ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.escalation_router[0].name
}

resource "aws_iam_role_policy" "escalation_router_sns" {
  count = var.enable_escalation_routing ? 1 : 0
  name  = "${local.name_prefix}-escalation-router-sns"
  role  = aws_iam_role.escalation_router[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.email_alerts[0].arn
        ]
      }
    ]
  })
}

# SNS Topic for Email Alerts
resource "aws_sns_topic" "email_alerts" {
  count = var.enable_escalation_routing ? 1 : 0
  name  = "${local.sns_topic_name}-email"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-email-alerts"
  })
}

# Email Subscriptions
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.enable_escalation_routing ? length(local.env_config.escalation.email_addresses) : 0
  topic_arn = aws_sns_topic.email_alerts[0].arn
  protocol  = "email"
  endpoint  = local.env_config.escalation.email_addresses[count.index]
}

# Lambda Permission for SNS
resource "aws_lambda_permission" "allow_sns" {
  count         = var.enable_escalation_routing ? 1 : 0
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.escalation_router[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.lcopilot_alerts.arn
}

# SNS Subscription to Lambda
resource "aws_sns_topic_subscription" "escalation_router" {
  count     = var.enable_escalation_routing ? 1 : 0
  topic_arn = aws_sns_topic.lcopilot_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.escalation_router[0].arn
}

# CloudWatch Alarm with Enhanced Configuration
resource "aws_cloudwatch_metric_alarm" "error_spike" {
  alarm_name        = local.alarm_name
  alarm_description = "[${upper(var.environment)}] Triggers when ≥${local.env_config.alarm_threshold} errors occur within ${local.global_config.alarm_period_seconds} seconds"

  # Metric configuration
  namespace   = local.global_config.metric_namespace
  metric_name = local.metric_name
  statistic   = "Sum"

  # Threshold settings from config
  period                    = local.global_config.alarm_period_seconds
  evaluation_periods        = local.global_config.evaluation_periods
  datapoints_to_alarm      = local.global_config.evaluation_periods
  threshold                = local.env_config.alarm_threshold
  comparison_operator      = "GreaterThanOrEqualToThreshold"
  treat_missing_data       = local.global_config.treat_missing_data

  # Enable actions
  actions_enabled = true

  # SNS notifications
  alarm_actions             = [aws_sns_topic.lcopilot_alerts.arn]
  ok_actions               = [aws_sns_topic.lcopilot_alerts.arn]
  insufficient_data_actions = []

  tags = merge(local.common_tags, {
    Name = local.alarm_name
  })

  depends_on = [
    aws_cloudwatch_log_metric_filter.error_count,
    aws_sns_topic.lcopilot_alerts,
    aws_sns_topic_policy.lcopilot_alerts_policy
  ]
}

# Future Feature: Anomaly Detection (Optional)
resource "aws_cloudwatch_anomaly_detector" "error_anomaly" {
  count = var.enable_future_features && local.future_config.anomaly_detection.enabled ? 1 : 0

  namespace   = local.global_config.metric_namespace
  metric_name = local.metric_name
  stat        = local.future_config.anomaly_detection.stat

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-anomaly-detector"
    Feature = "Future-Anomaly-Detection"
  })
}

resource "aws_cloudwatch_metric_alarm" "anomaly_alarm" {
  count = var.enable_future_features && local.future_config.anomaly_detection.enabled ? 1 : 0

  alarm_name          = "${local.alarm_name}-anomaly"
  alarm_description   = "[${upper(var.environment)}] Anomaly detection for error rate - triggers on >3σ deviation"
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = "2"
  threshold_metric_id = "e1"
  actions_enabled     = true

  alarm_actions = [aws_sns_topic.lcopilot_alerts.arn]
  ok_actions    = [aws_sns_topic.lcopilot_alerts.arn]

  metric_query {
    id = "e1"

    return_data = true
    metric {
      metric_name = local.metric_name
      namespace   = local.global_config.metric_namespace
      period      = 300
      stat        = "Average"
    }
  }

  metric_query {
    id = "ad1"

    anomaly_detector {
      namespace   = local.global_config.metric_namespace
      metric_name = local.metric_name
      stat        = "Average"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.alarm_name}-anomaly"
    Feature = "Future-Anomaly-Detection"
  })
}

# Future Feature: Saved Log Insights Queries (Optional)
resource "aws_logs_query_definition" "log_insights_queries" {
  count = var.enable_future_features && local.future_config.log_insights.enabled ? length(local.future_config.log_insights.queries) : 0

  name = "${local.name_prefix}-${local.future_config.log_insights.queries[count.index].name}"

  log_group_names = [
    aws_cloudwatch_log_group.lcopilot.name
  ]

  query_string = local.future_config.log_insights.queries[count.index].query
}

# Athena Table for Archived Logs (Cost Control)
resource "aws_glue_catalog_table" "archived_logs" {
  count         = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  name          = replace("${local.name_prefix}_archived_logs", "-", "_")
  database_name = aws_glue_catalog_database.logs[0].name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "projection.enabled"  = "true"
    "projection.year.type" = "integer"
    "projection.year.range" = "2024,2030"
    "projection.month.type" = "integer"
    "projection.month.range" = "1,12"
    "projection.day.type" = "integer"
    "projection.day.range" = "1,31"
    "storage.location.template" = "s3://${aws_s3_bucket.log_archive[0].bucket}/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.log_archive[0].bucket}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
    }

    columns {
      name = "timestamp"
      type = "string"
    }
    columns {
      name = "level"
      type = "string"
    }
    columns {
      name = "message"
      type = "string"
    }
    columns {
      name = "service"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}

resource "aws_glue_catalog_database" "logs" {
  count = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? 1 : 0
  name  = replace("${local.name_prefix}_logs_db", "-", "_")
}

# Outputs
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "deployed_account_id" {
  description = "AWS Account ID where resources were deployed"
  value       = data.aws_caller_identity.current.account_id
}

output "expected_account_id" {
  description = "Expected AWS Account ID from configuration"
  value       = local.env_config.aws_account_id
}

output "account_match" {
  description = "Whether deployment account matches expected account"
  value       = data.aws_caller_identity.current.account_id == local.env_config.aws_account_id
}

output "log_group_name" {
  description = "CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.lcopilot.name
}

output "log_group_arn" {
  description = "CloudWatch Log Group ARN"
  value       = aws_cloudwatch_log_group.lcopilot.arn
}

output "metric_filter_name" {
  description = "CloudWatch Metric Filter name"
  value       = aws_cloudwatch_log_metric_filter.error_count.name
}

output "metric_name" {
  description = "CloudWatch Metric name"
  value       = local.metric_name
}

output "alarm_name" {
  description = "CloudWatch Alarm name"
  value       = aws_cloudwatch_metric_alarm.error_spike.alarm_name
}

output "alarm_arn" {
  description = "CloudWatch Alarm ARN"
  value       = aws_cloudwatch_metric_alarm.error_spike.arn
}

output "sns_topic_name" {
  description = "SNS Topic name"
  value       = aws_sns_topic.lcopilot_alerts.name
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = aws_sns_topic.lcopilot_alerts.arn
}

output "escalation_lambda_arn" {
  description = "Escalation Router Lambda ARN"
  value       = var.enable_escalation_routing ? aws_lambda_function.escalation_router[0].arn : null
}

output "log_archive_bucket" {
  description = "S3 bucket for log archival"
  value       = var.enable_cost_controls && local.cost_controls.s3_archive_enabled ? aws_s3_bucket.log_archive[0].bucket : null
}

output "monitoring_summary" {
  description = "Summary of created monitoring resources"
  value = {
    environment             = var.environment
    deployed_account       = data.aws_caller_identity.current.account_id
    expected_account       = local.env_config.aws_account_id
    account_match          = data.aws_caller_identity.current.account_id == local.env_config.aws_account_id
    log_group             = aws_cloudwatch_log_group.lcopilot.name
    metric_filter         = aws_cloudwatch_log_metric_filter.error_count.name
    metric_name           = local.metric_name
    alarm_name            = aws_cloudwatch_metric_alarm.error_spike.alarm_name
    sns_topic             = aws_sns_topic.lcopilot_alerts.name
    threshold             = local.env_config.alarm_threshold
    period_seconds        = local.global_config.alarm_period_seconds
    escalation_enabled    = var.enable_escalation_routing
    cost_controls_enabled = var.enable_cost_controls
    future_features_enabled = var.enable_future_features
  }
}