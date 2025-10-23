# Development Environment Variables
# DataPrime Assistant - AWS Deployment

# Basic Configuration
environment = "dev"
project_name = "dataprime-demo"
aws_region = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
# IMPORTANT: Update this with your actual IP address for SSH access
# Find your IP: curl ifconfig.me
allowed_ssh_cidr = "0.0.0.0/0"  # CHANGE THIS! Use your IP/32 for security

# EC2 Configuration (Cost Optimized)
instance_type = "t3.small"  # ~$15/month
root_volume_size = 30  # GB

# Coralogix Configuration
coralogix_domain = "coralogix.com"
coralogix_application_name = "dataprime-demo"
coralogix_company_id = "4015437"

# Optional Features (disabled for cost savings)
enable_detailed_monitoring = false
create_elastic_ip = true

# ==============================================================================
# SENSITIVE VARIABLES - Set via environment variables or terraform.tfvars
# ==============================================================================
# DO NOT commit actual values to git!
# 
# Set these via environment variables:
# export TF_VAR_coralogix_token="your_coralogix_token"
# export TF_VAR_openai_api_key="your_openai_key"
# export TF_VAR_postgres_password="your_secure_password"
#
# Or create a terraform.tfvars file (add to .gitignore):
# coralogix_token = "your_coralogix_token"
# openai_api_key = "your_openai_key"
# postgres_password = "your_secure_password"
# ==============================================================================

