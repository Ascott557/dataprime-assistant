# DataPrime Assistant - Main Terraform Configuration
# Cost-optimized AWS infrastructure for demo purposes (~$18/month)

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

  # Backend configuration (populated after running backend-setup)
  # Uncomment and update after creating backend resources
  # backend "s3" {
  #   bucket         = "dataprime-demo-terraform-state-us-east-1"
  #   key            = "dataprime-assistant/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "dataprime-demo-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Local variables for common configuration
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "Coralogix DataPrime Demo"
    CostCenter  = "demo"
  }
}

# VPC Module - Minimal single-AZ setup
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  aws_region   = var.aws_region
  
  tags = local.common_tags
}

# Security Module - Security groups and IAM roles
module "security" {
  source = "./modules/security"

  project_name         = var.project_name
  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  allowed_ssh_cidr     = var.allowed_ssh_cidr
  coralogix_company_id = var.coralogix_company_id
  
  tags = local.common_tags
}

# EC2 Module - t3.small instance for cost optimization
module "ec2" {
  source = "./modules/ec2"

  project_name          = var.project_name
  environment           = var.environment
  instance_type         = var.instance_type
  root_volume_size      = var.root_volume_size
  subnet_id             = module.vpc.public_subnet_ids[0]
  security_group_id     = module.security.instance_security_group_id
  iam_instance_profile  = module.security.instance_profile_name
  key_name              = module.security.key_pair_name
  
  # User data for bootstrapping
  user_data = templatefile("${path.module}/user-data/bootstrap.sh.tpl", {
    coralogix_token    = var.coralogix_token
    coralogix_domain   = var.coralogix_domain
    coralogix_app_name = var.coralogix_application_name
    openai_api_key     = var.openai_api_key
    postgres_password  = var.postgres_password
    environment        = var.environment
    project_name       = var.project_name
  })
  
  tags = local.common_tags
}

