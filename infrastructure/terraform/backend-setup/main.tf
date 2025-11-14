/**
 * Terraform Backend Setup
 * 
 * Creates S3 bucket and DynamoDB table for Terraform state management.
 * This is a one-time setup that runs independently before the main infrastructure.
 * 
 * Usage:
 *   cd infrastructure/terraform/backend-setup
 *   terraform init
 *   terraform apply
 *   # Note the outputs for use in main Terraform config
 */

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "dataprime-demo"
      ManagedBy   = "terraform"
      Purpose     = "backend-setup"
      Environment = "infrastructure"
    }
  }
}

# Random suffix for globally unique S3 bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-terraform-state-${random_id.bucket_suffix.hex}"

  # Prevent accidental deletion of this bucket
  lifecycle {
    prevent_destroy = false # Set to true in production
  }

  tags = {
    Name        = "Terraform State Bucket"
    Description = "Stores Terraform state for DataPrime Demo"
  }
}

# Enable versioning for state history
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "${var.project_name}-terraform-locks"
  billing_mode = "PAY_PER_REQUEST" # Cost-effective for low usage
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform State Locks"
    Description = "Prevents concurrent Terraform runs"
  }
}
