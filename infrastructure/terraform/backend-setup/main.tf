# Terraform Backend Setup for DataPrime Assistant
# This creates the S3 bucket and DynamoDB table for Terraform state management
# Run this ONCE before deploying the main infrastructure

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for Terraform State
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-terraform-state-${var.aws_region}"

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-terraform-state"
    Purpose     = "Terraform state storage"
    Project     = var.project_name
    Environment = "infrastructure"
    ManagedBy   = "terraform"
  }
}

# Enable versioning for state file history
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

# Block all public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB Table for State Locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "${var.project_name}-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"  # Cost-effective for low usage
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-terraform-locks"
    Purpose     = "Terraform state locking"
    Project     = var.project_name
    Environment = "infrastructure"
    ManagedBy   = "terraform"
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for backend resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "dataprime-demo"
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for Terraform locks"
  value       = aws_dynamodb_table.terraform_locks.id
}

output "backend_config" {
  description = "Backend configuration to use in main Terraform"
  value = <<-EOT
  
  Add this to your main Terraform configuration:
  
  terraform {
    backend "s3" {
      bucket         = "${aws_s3_bucket.terraform_state.id}"
      key            = "dataprime-assistant/terraform.tfstate"
      region         = "${var.aws_region}"
      dynamodb_table = "${aws_dynamodb_table.terraform_locks.id}"
      encrypt        = true
    }
  }
  EOT
}

output "next_steps" {
  description = "Instructions for next steps"
  value = <<-EOT
  
  ✅ Backend resources created successfully!
  
  Next steps:
  1. Copy the backend configuration above to infrastructure/terraform/backend.tf
  2. Run: cd ../infrastructure/terraform
  3. Run: terraform init
  4. Run: terraform plan -var-file=environments/dev.tfvars
  5. Run: terraform apply -var-file=environments/dev.tfvars
  
  Note: You only need to run this backend setup once per AWS account/region.
  EOT
}

