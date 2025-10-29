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

variable "regions" {
  description = "Regions for data residency buckets"
  type        = list(string)
  default     = ["bd", "eu", "sg"]
}

# KMS Keys for encryption
resource "aws_kms_key" "docs_encryption" {
  description             = "LCopilot Documents Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for S3"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-docs-kms-${var.environment}"
    Environment = var.environment
    Purpose     = "document-encryption"
  }
}

resource "aws_kms_alias" "docs_encryption" {
  name          = "alias/${var.project_name}-docs-${var.environment}"
  target_key_id = aws_kms_key.docs_encryption.key_id
}

resource "aws_kms_key" "db_encryption" {
  description             = "LCopilot Database Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for RDS"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-db-kms-${var.environment}"
    Environment = var.environment
    Purpose     = "database-encryption"
  }
}

resource "aws_kms_alias" "db_encryption" {
  name          = "alias/${var.project_name}-db-${var.environment}"
  target_key_id = aws_kms_key.db_encryption.key_id
}

# S3 Buckets for each region
resource "aws_s3_bucket" "docs" {
  for_each = toset(var.regions)
  bucket   = "${var.project_name}-docs-${each.key}-${var.environment}"

  tags = {
    Name        = "${var.project_name}-docs-${each.key}-${var.environment}"
    Environment = var.environment
    Region      = each.key
    Purpose     = "document-storage"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "docs" {
  for_each = aws_s3_bucket.docs
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  for_each = aws_s3_bucket.docs
  bucket   = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.docs_encryption.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "docs" {
  for_each = aws_s3_bucket.docs
  bucket   = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy to enforce encryption and TLS
resource "aws_s3_bucket_policy" "docs" {
  for_each = aws_s3_bucket.docs
  bucket   = each.value.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          each.value.arn,
          "${each.value.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${each.value.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })
}

# Lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "docs" {
  for_each = aws_s3_bucket.docs
  bucket   = each.value.id

  rule {
    id     = "transition_to_ia"
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

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Cross-region replication (optional for prod)
resource "aws_s3_bucket_replication_configuration" "docs" {
  for_each   = var.environment == "prod" ? aws_s3_bucket.docs : {}
  role       = aws_iam_role.replication[each.key].arn
  bucket     = each.value.id
  depends_on = [aws_s3_bucket_versioning.docs]

  rule {
    id     = "replicate_to_backup"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.docs_backup[each.key].arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.docs_encryption.arn
      }
    }
  }
}

# Backup buckets for replication (prod only)
resource "aws_s3_bucket" "docs_backup" {
  for_each = var.environment == "prod" ? toset(var.regions) : toset([])
  bucket   = "${var.project_name}-docs-${each.key}-backup-${var.environment}"

  tags = {
    Name        = "${var.project_name}-docs-${each.key}-backup-${var.environment}"
    Environment = var.environment
    Region      = each.key
    Purpose     = "document-backup"
  }
}

# IAM role for replication
resource "aws_iam_role" "replication" {
  for_each = var.environment == "prod" ? toset(var.regions) : toset([])
  name     = "${var.project_name}-s3-replication-${each.key}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

# Outputs
output "kms_key_docs_arn" {
  description = "ARN of the KMS key for document encryption"
  value       = aws_kms_key.docs_encryption.arn
}

output "kms_key_db_arn" {
  description = "ARN of the KMS key for database encryption"
  value       = aws_kms_key.db_encryption.arn
}

output "s3_buckets" {
  description = "Map of S3 bucket names by region"
  value = {
    for k, v in aws_s3_bucket.docs : k => v.bucket
  }
}

output "s3_bucket_arns" {
  description = "Map of S3 bucket ARNs by region"
  value = {
    for k, v in aws_s3_bucket.docs : k => v.arn
  }
}