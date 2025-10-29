# Terraform Variables for LCopilot Reliability Infrastructure

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "tier" {
  description = "Reliability service tier"
  type        = string
  default     = "enterprise"

  validation {
    condition     = contains(["free", "pro", "enterprise"], var.tier)
    error_message = "Tier must be one of: free, pro, enterprise."
  }
}

variable "customer_id" {
  description = "Customer ID for enterprise customers (optional for free/pro)"
  type        = string
  default     = ""

  validation {
    condition = var.customer_id == "" || can(regex("^[a-zA-Z0-9-]+$", var.customer_id))
    error_message = "Customer ID must contain only alphanumeric characters and hyphens."
  }
}

variable "region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "white_label_domain" {
  description = "Custom domain for enterprise white-label customers"
  type        = string
  default     = ""

  validation {
    condition = var.white_label_domain == "" || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\\.[a-zA-Z]{2,}$", var.white_label_domain))
    error_message = "White label domain must be a valid domain name."
  }
}

variable "enable_monitoring" {
  description = "Enable enhanced monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups (Pro and Enterprise only)"
  type        = bool
  default     = true
}

variable "retention_days" {
  description = "Data retention period in days"
  type        = number
  default     = 90

  validation {
    condition     = var.retention_days >= 7 && var.retention_days <= 2555
    error_message = "Retention days must be between 7 and 2555."
  }
}

variable "alert_email" {
  description = "Email address for reliability alerts"
  type        = string
  default     = ""

  validation {
    condition = var.alert_email == "" || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Alert email must be a valid email address."
  }
}

variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for custom domains (Enterprise)"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "VPC ID for network resources (optional)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for multi-AZ deployment (Enterprise)"
  type        = list(string)
  default     = []
}

variable "enable_waf" {
  description = "Enable Web Application Firewall (Enterprise)"
  type        = bool
  default     = false
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins for API Gateway"
  type        = list(string)
  default     = ["*"]
}

variable "lambda_layers" {
  description = "Lambda layers for shared dependencies"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}