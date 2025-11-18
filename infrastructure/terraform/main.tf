/**
 * DataPrime Demo - Main Terraform Configuration
 * 
 * This configuration creates all AWS infrastructure for the DataPrime Demo:
 * - VPC with public subnet
 * - Security group, IAM roles, SSH key
 * - EC2 t3.small instance with bootstrapping
 * - Elastic IP for stable access
 * 
 * Prerequisites:
 * 1. Run backend-setup first to create S3/DynamoDB
 * 2. Update backend configuration below with your bucket name
 * 3. Create terraform.tfvars with required variables
 * 
 * Usage:
 *   terraform init
 *   terraform plan
 *   terraform apply
 */

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Backend configuration - S3 state storage
  backend "s3" {
    bucket         = "dataprime-demo-terraform-state-ffa1bc17"
    key            = "ecommerce-demo/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "dataprime-demo-terraform-locks"
    encrypt        = true
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "dataprime-assistant"
    }
  }
}

# Get current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Availability zone selection
data "aws_availability_zones" "available" {
  state = "available"
}

###############################################################################
# VPC Module
###############################################################################
module "vpc" {
  source = "./modules/vpc"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  availability_zone   = data.aws_availability_zones.available.names[0]
}

###############################################################################
# Security Module
###############################################################################
module "security" {
  source = "./modules/security"

  project_name           = var.project_name
  vpc_id                 = module.vpc.vpc_id
  allowed_ssh_cidr       = var.allowed_ssh_cidr
  coralogix_company_id   = var.coralogix_company_id
  coralogix_aws_account_id = var.coralogix_aws_account_id

  depends_on = [module.vpc]
}

###############################################################################
# EC2 Module
###############################################################################
module "ec2" {
  source = "./modules/ec2"

  project_name              = var.project_name
  environment               = var.environment
  instance_type             = var.instance_type
  root_volume_size          = var.root_volume_size
  
  # Network configuration
  subnet_id                 = module.vpc.public_subnet_id
  security_group_id         = module.security.security_group_id
  key_name                  = module.security.ssh_key_name
  iam_instance_profile_name = module.security.iam_instance_profile_name

  # Application configuration
  coralogix_token      = var.coralogix_token
  coralogix_domain     = var.coralogix_domain
  coralogix_app_name   = var.coralogix_app_name
  coralogix_subsystem  = var.coralogix_subsystem
  openai_api_key       = var.openai_api_key
  redis_url            = var.redis_url
  otel_endpoint        = var.otel_endpoint
  repository_url       = var.repository_url
  cx_rum_public_key    = var.cx_rum_public_key
  db_password          = var.db_password

  depends_on = [module.vpc, module.security]
}
