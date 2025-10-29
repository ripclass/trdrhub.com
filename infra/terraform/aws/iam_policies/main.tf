terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "lcopilot"
}

variable "kms_key_docs_arn" {
  description = "ARN of the KMS key for document encryption"
  type        = string
}

variable "kms_key_db_arn" {
  description = "ARN of the KMS key for database encryption"
  type        = string
}

variable "s3_bucket_arns" {
  description = "Map of S3 bucket ARNs by region"
  type        = map(string)
}

# Application service role
resource "aws_iam_role" "app_service" {
  name = "${var.project_name}-app-service-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "${var.project_name}-${var.environment}"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-app-service-${var.environment}"
    Environment = var.environment
    Purpose     = "application-service"
  }
}

# S3 access policy
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access-${var.environment}"
  description = "S3 access policy for LCopilot application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBuckets"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          for arn in values(var.s3_bucket_arns) : arn
        ]
      },
      {
        Sid    = "ObjectOperations"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectAttributes"
        ]
        Resource = [
          for arn in values(var.s3_bucket_arns) : "${arn}/*"
        ]
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = var.kms_key_docs_arn
          }
        }
      }
    ]
  })
}

# KMS access policy
resource "aws_iam_policy" "kms_access" {
  name        = "${var.project_name}-kms-access-${var.environment}"
  description = "KMS access policy for LCopilot application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DocumentsKMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_docs_arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.*.amazonaws.com"
          }
        }
      },
      {
        Sid    = "DatabaseKMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_db_arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "rds.*.amazonaws.com"
          }
        }
      }
    ]
  })
}

# CloudWatch logs policy
resource "aws_iam_policy" "cloudwatch_logs" {
  name        = "${var.project_name}-cloudwatch-logs-${var.environment}"
  description = "CloudWatch logs access for LCopilot application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/lcopilot/${var.environment}/*"
      }
    ]
  })
}

# SSM Parameter Store access (for secrets)
resource "aws_iam_policy" "ssm_access" {
  name        = "${var.project_name}-ssm-access-${var.environment}"
  description = "SSM Parameter Store access for LCopilot application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/${var.environment}/*"
      }
    ]
  })
}

# Attach policies to the role
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.app_service.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_role_policy_attachment" "kms_access" {
  role       = aws_iam_role.app_service.name
  policy_arn = aws_iam_policy.kms_access.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = aws_iam_role.app_service.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}

resource "aws_iam_role_policy_attachment" "ssm_access" {
  role       = aws_iam_role.app_service.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

# Instance profile for EC2 instances
resource "aws_iam_instance_profile" "app_service" {
  name = "${var.project_name}-app-service-${var.environment}"
  role = aws_iam_role.app_service.name
}

# User for backup operations
resource "aws_iam_user" "backup_user" {
  name = "${var.project_name}-backup-user-${var.environment}"
  path = "/system/"

  tags = {
    Name        = "${var.project_name}-backup-user-${var.environment}"
    Environment = var.environment
    Purpose     = "backup-operations"
  }
}

# Backup user policy
resource "aws_iam_policy" "backup_access" {
  name        = "${var.project_name}-backup-access-${var.environment}"
  description = "Backup access policy for pgBackRest and object storage backup"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BackupBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-backups-${var.environment}",
          "arn:aws:s3:::${var.project_name}-backups-${var.environment}/*"
        ]
      },
      {
        Sid    = "BackupKMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_db_arn
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "backup_access" {
  user       = aws_iam_user.backup_user.name
  policy_arn = aws_iam_policy.backup_access.arn
}

# Access keys for backup user
resource "aws_iam_access_key" "backup_user" {
  user = aws_iam_user.backup_user.name
}

data "aws_caller_identity" "current" {}

# Outputs
output "app_service_role_arn" {
  description = "ARN of the application service role"
  value       = aws_iam_role.app_service.arn
}

output "instance_profile_name" {
  description = "Name of the instance profile"
  value       = aws_iam_instance_profile.app_service.name
}

output "backup_user_access_key_id" {
  description = "Access key ID for backup user"
  value       = aws_iam_access_key.backup_user.id
  sensitive   = true
}

output "backup_user_secret_access_key" {
  description = "Secret access key for backup user"
  value       = aws_iam_access_key.backup_user.secret
  sensitive   = true
}