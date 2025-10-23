# DataPrime Assistant - Terraform Variables

# AWS Configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "dataprime-demo"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (your IP address/32)"
  type        = string
  
  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0))
    error_message = "Must be a valid CIDR block (e.g., 1.2.3.4/32)."
  }
}

# EC2 Configuration
variable "instance_type" {
  description = "EC2 instance type (t3.small for cost optimization)"
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Size of root EBS volume in GB"
  type        = number
  default     = 30
  
  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 100
    error_message = "Root volume size must be between 20 and 100 GB."
  }
}

# Coralogix Configuration
variable "coralogix_token" {
  description = "Coralogix Send Data API Key"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.coralogix_token) > 0
    error_message = "Coralogix token cannot be empty."
  }
}

variable "coralogix_domain" {
  description = "Coralogix domain (e.g., coralogix.com)"
  type        = string
  default     = "coralogix.com"
}

variable "coralogix_application_name" {
  description = "Coralogix application name"
  type        = string
  default     = "dataprime-demo"
}

variable "coralogix_company_id" {
  description = "Coralogix Company ID for Infrastructure Explorer integration"
  type        = string
  default     = "4015437"
}

# Application Configuration
variable "openai_api_key" {
  description = "OpenAI API Key for DataPrime query generation"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.openai_api_key) > 0
    error_message = "OpenAI API key cannot be empty."
  }
}

variable "postgres_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.postgres_password) >= 12
    error_message = "PostgreSQL password must be at least 12 characters long."
  }
}

# Optional: Advanced Configuration
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (additional cost)"
  type        = bool
  default     = false
}

variable "create_elastic_ip" {
  description = "Create Elastic IP for stable public address"
  type        = bool
  default     = true
}

