# LCopilot Reliability-as-a-Service Terraform Infrastructure
# Provisions tier-based reliability infrastructure with consistent naming

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "tier" {
  description = "Reliability tier (free, pro, enterprise)"
  type        = string
  default     = "enterprise"

  validation {
    condition     = contains(["free", "pro", "enterprise"], var.tier)
    error_message = "Tier must be one of: free, pro, enterprise."
  }
}

variable "customer_id" {
  description = "Customer ID for enterprise customers"
  type        = string
  default     = ""
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "white_label_domain" {
  description = "Custom domain for white-label enterprise customers"
  type        = string
  default     = ""
}

# Local values for resource naming
locals {
  name_prefix = var.customer_id != "" ? "lcopilot-reliability-${var.tier}-${var.customer_id}" : "lcopilot-reliability-${var.tier}"

  common_tags = {
    Environment    = var.environment
    Tier          = var.tier
    Project       = "LCopilot"
    Component     = "Reliability"
    CustomerID    = var.customer_id
    ManagedBy     = "terraform"
  }

  # Tier-based configuration
  tier_config = {
    free = {
      lambda_memory         = 256
      lambda_timeout        = 30
      cloudwatch_retention  = 7
      s3_versioning        = false
      backup_enabled       = false
      multi_az             = false
      auto_scaling_enabled = false
    }
    pro = {
      lambda_memory         = 512
      lambda_timeout        = 60
      cloudwatch_retention  = 30
      s3_versioning        = true
      backup_enabled       = true
      multi_az             = false
      auto_scaling_enabled = true
    }
    enterprise = {
      lambda_memory         = 1024
      lambda_timeout        = 300
      cloudwatch_retention  = 90
      s3_versioning        = true
      backup_enabled       = true
      multi_az             = true
      auto_scaling_enabled = true
    }
  }

  config = local.tier_config[var.tier]
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# S3 Buckets for Reliability Components
resource "aws_s3_bucket" "status_page_assets" {
  bucket = "${local.name_prefix}-status-page-${var.environment}"
  tags   = merge(local.common_tags, { Component = "StatusPage" })
}

resource "aws_s3_bucket_versioning" "status_page_assets" {
  bucket = aws_s3_bucket.status_page_assets.id
  versioning_configuration {
    status = local.config.s3_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_public_access_block" "status_page_assets" {
  bucket = aws_s3_bucket.status_page_assets.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket" "sla_reports" {
  bucket = "${local.name_prefix}-sla-reports-${var.environment}"
  tags   = merge(local.common_tags, { Component = "SLAReporting" })
}

resource "aws_s3_bucket_versioning" "sla_reports" {
  bucket = aws_s3_bucket.sla_reports.id
  versioning_configuration {
    status = local.config.s3_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket" "analytics_data" {
  count  = var.tier != "free" ? 1 : 0
  bucket = "${local.name_prefix}-analytics-${var.environment}"
  tags   = merge(local.common_tags, { Component = "Analytics" })
}

resource "aws_s3_bucket" "ml_models" {
  count  = var.tier == "enterprise" ? 1 : 0
  bucket = "${local.name_prefix}-ml-models-${var.environment}"
  tags   = merge(local.common_tags, { Component = "Predictive" })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "reliability_logs" {
  name              = "/aws/lambda/${local.name_prefix}-${var.environment}"
  retention_in_days = local.config.cloudwatch_retention
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${local.name_prefix}-api-${var.environment}"
  retention_in_days = local.config.cloudwatch_retention
  tags              = local.common_tags
}

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${local.name_prefix}-lambda-role-${var.environment}"
  tags = local.common_tags

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
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.status_page_assets.arn}/*",
          "${aws_s3_bucket.sla_reports.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Enhanced permissions for Pro and Enterprise tiers
resource "aws_iam_role_policy" "enhanced_lambda_policy" {
  count = var.tier != "free" ? 1 : 0
  name  = "${local.name_prefix}-enhanced-lambda-policy-${var.environment}"
  role  = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = var.tier != "free" ? [
          "${aws_s3_bucket.analytics_data[0].arn}/*"
        ] : []
      },
      {
        Effect = "Allow"
        Action = [
          "cognito-identity:*",
          "cognito-idp:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Enterprise-specific permissions
resource "aws_iam_role_policy" "enterprise_lambda_policy" {
  count = var.tier == "enterprise" ? 1 : 0
  name  = "${local.name_prefix}-enterprise-lambda-policy-${var.environment}"
  role  = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint",
          "sagemaker:CreateModel",
          "sagemaker:CreateTrainingJob"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = var.tier == "enterprise" ? [
          "${aws_s3_bucket.ml_models[0].arn}/*"
        ] : []
      }
    ]
  })
}

# Lambda Functions for Reliability Components
resource "aws_lambda_function" "status_page_generator" {
  filename         = "status_page_generator.zip"
  function_name    = "${local.name_prefix}-status-page-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "status_page_generator.handler"
  runtime         = "python3.11"
  timeout         = local.config.lambda_timeout
  memory_size     = local.config.lambda_memory
  tags            = merge(local.common_tags, { Component = "StatusPage" })

  environment {
    variables = {
      ENVIRONMENT     = var.environment
      TIER           = var.tier
      CUSTOMER_ID    = var.customer_id
      S3_BUCKET      = aws_s3_bucket.status_page_assets.bucket
      WHITE_LABEL    = var.white_label_domain != "" ? "true" : "false"
    }
  }
}

resource "aws_lambda_function" "sla_dashboard_manager" {
  filename         = "sla_dashboard_manager.zip"
  function_name    = "${local.name_prefix}-sla-dashboard-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "sla_dashboard_manager.handler"
  runtime         = "python3.11"
  timeout         = local.config.lambda_timeout
  memory_size     = local.config.lambda_memory
  tags            = merge(local.common_tags, { Component = "SLADashboard" })

  environment {
    variables = {
      ENVIRONMENT   = var.environment
      TIER         = var.tier
      CUSTOMER_ID  = var.customer_id
      REPORTS_BUCKET = aws_s3_bucket.sla_reports.bucket
    }
  }
}

resource "aws_lambda_function" "trust_portal_manager" {
  count            = var.tier != "free" ? 1 : 0
  filename         = "trust_portal_manager.zip"
  function_name    = "${local.name_prefix}-trust-portal-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "trust_portal_manager.handler"
  runtime         = "python3.11"
  timeout         = local.config.lambda_timeout
  memory_size     = local.config.lambda_memory
  tags            = merge(local.common_tags, { Component = "TrustPortal" })

  environment {
    variables = {
      ENVIRONMENT     = var.environment
      TIER           = var.tier
      CUSTOMER_ID    = var.customer_id
      WHITE_LABEL    = var.white_label_domain != "" ? "true" : "false"
    }
  }
}

resource "aws_lambda_function" "integration_api_manager" {
  count            = var.tier == "enterprise" ? 1 : 0
  filename         = "integration_api_manager.zip"
  function_name    = "${local.name_prefix}-integration-api-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "integration_api_manager.handler"
  runtime         = "python3.11"
  timeout         = local.config.lambda_timeout
  memory_size     = local.config.lambda_memory
  tags            = merge(local.common_tags, { Component = "IntegrationAPI" })

  environment {
    variables = {
      ENVIRONMENT   = var.environment
      TIER         = var.tier
      CUSTOMER_ID  = var.customer_id
    }
  }
}

resource "aws_lambda_function" "analytics_manager" {
  count            = var.tier != "free" ? 1 : 0
  filename         = "analytics_manager.zip"
  function_name    = "${local.name_prefix}-analytics-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "analytics_manager.handler"
  runtime         = "python3.11"
  timeout         = local.config.lambda_timeout
  memory_size     = local.config.lambda_memory * 2  # Analytics needs more memory
  tags            = merge(local.common_tags, { Component = "Analytics" })

  environment {
    variables = {
      ENVIRONMENT     = var.environment
      TIER           = var.tier
      CUSTOMER_ID    = var.customer_id
      ANALYTICS_BUCKET = var.tier != "free" ? aws_s3_bucket.analytics_data[0].bucket : ""
    }
  }
}

resource "aws_lambda_function" "predictive_manager" {
  count            = var.tier == "enterprise" ? 1 : 0
  filename         = "predictive_manager.zip"
  function_name    = "${local.name_prefix}-predictive-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "predictive_manager.handler"
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes for ML operations
  memory_size     = 3008  # Maximum memory for ML processing
  tags            = merge(local.common_tags, { Component = "Predictive" })

  environment {
    variables = {
      ENVIRONMENT   = var.environment
      TIER         = var.tier
      CUSTOMER_ID  = var.customer_id
      MODELS_BUCKET = var.tier == "enterprise" ? aws_s3_bucket.ml_models[0].bucket : ""
    }
  }
}

# API Gateway for Reliability Services
resource "aws_api_gateway_rest_api" "reliability_api" {
  name        = "${local.name_prefix}-api-${var.environment}"
  description = "LCopilot Reliability API for ${var.tier} tier"
  tags        = merge(local.common_tags, { Component = "API" })

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway Resources and Methods
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.reliability_api.id
  parent_id   = aws_api_gateway_rest_api.reliability_api.root_resource_id
  path_part   = "status"
}

resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.reliability_api.id
  resource_id   = aws_api_gateway_resource.status.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_integration" {
  rest_api_id = aws_api_gateway_rest_api.reliability_api.id
  resource_id = aws_api_gateway_resource.status.id
  http_method = aws_api_gateway_method.status_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.status_page_generator.invoke_arn
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_status" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_page_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.reliability_api.execution_arn}/*/*"
}

# CloudWatch Dashboard for Tier-based Monitoring
resource "aws_cloudwatch_dashboard" "reliability_dashboard" {
  dashboard_name = "${local.name_prefix}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.status_page_generator.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.status_page_generator.function_name],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.status_page_generator.function_name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "Status Page Lambda Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.reliability_api.name],
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.reliability_api.name],
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.reliability_api.name],
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.reliability_api.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "API Gateway Metrics"
          period  = 300
        }
      }
    ]
  })

  tags = local.common_tags
}

# CloudWatch Alarms for Reliability Monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name_prefix}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.tier == "enterprise" ? "1" : "5"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = []  # Would include SNS topic ARN

  dimensions = {
    FunctionName = aws_lambda_function.status_page_generator.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${local.name_prefix}-api-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = var.tier == "enterprise" ? "1000" : "2000"  # ms
  alarm_description   = "This metric monitors API Gateway latency"
  alarm_actions       = []

  dimensions = {
    ApiName = aws_api_gateway_rest_api.reliability_api.name
  }

  tags = local.common_tags
}

# Cognito User Pool for Customer Portal (Pro and Enterprise)
resource "aws_cognito_user_pool" "customer_portal" {
  count = var.tier != "free" ? 1 : 0
  name  = "${local.name_prefix}-portal-${var.environment}"
  tags  = merge(local.common_tags, { Component = "Authentication" })

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  auto_verified_attributes = ["email"]

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }
}

resource "aws_cognito_user_pool_client" "customer_portal_client" {
  count        = var.tier != "free" ? 1 : 0
  name         = "${local.name_prefix}-portal-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.customer_portal[0].id

  generate_secret = false

  explicit_auth_flows = [
    "ADMIN_NO_SRP_AUTH",
    "USER_PASSWORD_AUTH"
  ]
}

# CloudFront Distribution for Status Page (Enterprise white-label support)
resource "aws_cloudfront_distribution" "status_page" {
  count = var.tier == "enterprise" && var.white_label_domain != "" ? 1 : 0

  origin {
    domain_name = aws_s3_bucket.status_page_assets.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.status_page_assets.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.status_page[0].cloudfront_access_identity_path
    }
  }

  enabled             = true
  default_root_object = "index.html"

  aliases = [var.white_label_domain]

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.status_page_assets.id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(local.common_tags, { Component = "CDN" })
}

resource "aws_cloudfront_origin_access_identity" "status_page" {
  count   = var.tier == "enterprise" && var.white_label_domain != "" ? 1 : 0
  comment = "OAI for ${var.white_label_domain}"
}

# Auto Scaling for Enterprise tier
resource "aws_application_autoscaling_target" "lambda_target" {
  count          = var.tier == "enterprise" && local.config.auto_scaling_enabled ? 1 : 0
  max_capacity   = 100
  min_capacity   = 1
  resource_id    = "function:${aws_lambda_function.status_page_generator.function_name}:provisioned"
  scalable_dimension = "lambda:function:ProvisionedConcurrencyUtilization"
  service_namespace  = "lambda"
}

# Outputs
output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_api_gateway_rest_api.reliability_api.execution_arn
}

output "status_page_bucket" {
  description = "S3 bucket for status page assets"
  value       = aws_s3_bucket.status_page_assets.bucket
}

output "sla_reports_bucket" {
  description = "S3 bucket for SLA reports"
  value       = aws_s3_bucket.sla_reports.bucket
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = var.tier != "free" ? aws_cognito_user_pool.customer_portal[0].id : null
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.reliability_dashboard.dashboard_name}"
}

output "lambda_functions" {
  description = "Created Lambda functions"
  value = {
    status_page_generator = aws_lambda_function.status_page_generator.function_name
    sla_dashboard_manager = aws_lambda_function.sla_dashboard_manager.function_name
    trust_portal_manager  = var.tier != "free" ? aws_lambda_function.trust_portal_manager[0].function_name : null
    integration_api       = var.tier == "enterprise" ? aws_lambda_function.integration_api_manager[0].function_name : null
    analytics_manager     = var.tier != "free" ? aws_lambda_function.analytics_manager[0].function_name : null
    predictive_manager    = var.tier == "enterprise" ? aws_lambda_function.predictive_manager[0].function_name : null
  }
}