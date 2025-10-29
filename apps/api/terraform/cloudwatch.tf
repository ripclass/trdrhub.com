# Multi-Environment CloudWatch Monitoring for LCopilot API
# Creates environment-specific log groups, metric filters, alarms, and SNS topics
#
# Usage:
#   terraform apply -var="environment=prod"
#   terraform apply -var="environment=staging"

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
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

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-north-1"
}

variable "alarm_threshold" {
  description = "Error count threshold for alarm trigger"
  type        = number
  default     = 5
}

variable "alarm_period" {
  description = "Period in seconds for alarm evaluation"
  type        = number
  default     = 60
}

variable "alarm_evaluation_periods" {
  description = "Number of periods for alarm evaluation"
  type        = number
  default     = 1
}

# Local values for consistent naming
locals {
  name_prefix = "lcopilot-${var.environment}"

  # Resource names following the naming convention
  log_group_name       = "/aws/lambda/lcopilot-${var.environment}"
  metric_filter_name   = "LCopilotErrorCount-${var.environment}"
  metric_name         = "LCopilotErrorCount-${var.environment}"
  alarm_name          = "lcopilot-error-spike-${var.environment}"
  sns_topic_name      = "lcopilot-alerts-${var.environment}"

  # Common tags
  common_tags = {
    Application = "LCopilot"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "ErrorMonitoring"
  }
}

# Data source for current AWS caller identity
data "aws_caller_identity" "current" {}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lcopilot" {
  name              = local.log_group_name
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-logs"
  })
}

# CloudWatch Metric Filter for Error Count
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = local.metric_filter_name
  log_group_name = aws_cloudwatch_log_group.lcopilot.name
  pattern        = "{ $.level = \"ERROR\" }"

  metric_transformation {
    name          = local.metric_name
    namespace     = "LCopilot"
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# SNS Topic for Alarm Notifications
resource "aws_sns_topic" "lcopilot_alerts" {
  name = local.sns_topic_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alerts"
  })
}

# SNS Topic Policy (allows CloudWatch to publish)
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

# CloudWatch Alarm for Error Spike Detection
resource "aws_cloudwatch_metric_alarm" "error_spike" {
  alarm_name        = local.alarm_name
  alarm_description = "[${upper(var.environment)}] Triggers when ≥${var.alarm_threshold} errors occur within ${var.alarm_period} seconds"

  # Metric configuration
  namespace   = "LCopilot"
  metric_name = local.metric_name
  statistic   = "Sum"

  # Threshold settings
  period                    = var.alarm_period
  evaluation_periods        = var.alarm_evaluation_periods
  datapoints_to_alarm      = var.alarm_evaluation_periods
  threshold                = var.alarm_threshold
  comparison_operator      = "GreaterThanOrEqualToThreshold"
  treat_missing_data       = "notBreaching"

  # Enable actions
  actions_enabled = true

  # SNS notifications
  alarm_actions             = [aws_sns_topic.lcopilot_alerts.arn]
  ok_actions               = [aws_sns_topic.lcopilot_alerts.arn]
  insufficient_data_actions = []

  tags = merge(local.common_tags, {
    Name = local.alarm_name
  })

  # Ensure dependencies are created first
  depends_on = [
    aws_cloudwatch_log_metric_filter.error_count,
    aws_sns_topic.lcopilot_alerts,
    aws_sns_topic_policy.lcopilot_alerts_policy
  ]
}

# Optional: SNS Subscription for Email Notifications
# Uncomment and set email address to enable email alerts
#
# resource "aws_sns_topic_subscription" "email" {
#   topic_arn = aws_sns_topic.lcopilot_alerts.arn
#   protocol  = "email"
#   endpoint  = "your-email@example.com"  # Replace with your email
# }

# Optional: SNS Subscription for Slack Notifications
# Uncomment and configure webhook URL for Slack integration
#
# resource "aws_sns_topic_subscription" "slack" {
#   topic_arn = aws_sns_topic.lcopilot_alerts.arn
#   protocol  = "https"
#   endpoint  = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"  # Replace with your webhook
# }

# Outputs
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

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Output summary for verification
output "monitoring_summary" {
  description = "Summary of created monitoring resources"
  value = {
    environment      = var.environment
    log_group       = aws_cloudwatch_log_group.lcopilot.name
    metric_filter   = aws_cloudwatch_log_metric_filter.error_count.name
    metric_name     = local.metric_name
    alarm_name      = aws_cloudwatch_metric_alarm.error_spike.alarm_name
    sns_topic       = aws_sns_topic.lcopilot_alerts.name
    threshold       = var.alarm_threshold
    period_seconds  = var.alarm_period
  }
}