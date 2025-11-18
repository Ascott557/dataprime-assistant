###############################################################################
# Required Variables
###############################################################################

variable "coralogix_token" {
  description = "Coralogix Send-Your-Data API key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for query generation"
  type        = string
  sensitive   = true
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (your IP/32)"
  type        = string
  
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]{1,2}$", var.allowed_ssh_cidr))
    error_message = "Must be a valid CIDR block (e.g., 1.2.3.4/32)"
  }
}

###############################################################################
# AWS Configuration
###############################################################################

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "dataprime-demo"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

###############################################################################
# Instance Configuration
###############################################################################

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
  
  validation {
    condition     = can(regex("^t3\\.(small|medium)$", var.instance_type))
    error_message = "For cost optimization, only t3.small or t3.medium allowed"
  }
}

variable "root_volume_size" {
  description = "Size of root EBS volume in GB"
  type        = number
  default     = 30
  
  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 200
    error_message = "Volume size must be between 20 and 200 GB"
  }
}

###############################################################################
# Network Configuration
###############################################################################

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

###############################################################################
# Coralogix Configuration
###############################################################################

variable "coralogix_domain" {
  description = "Coralogix domain or ingress endpoint (e.g., coralogix.com, ingress.eu2.coralogix.com:443)"
  type        = string
  default     = "coralogix.com"
}

variable "coralogix_app_name" {
  description = "Coralogix application name"
  type        = string
  default     = "dataprime-demo"
}

variable "coralogix_subsystem" {
  description = "Coralogix subsystem name"
  type        = string
  default     = "vm-deployment"
}

variable "coralogix_company_id" {
  description = "Coralogix company ID for IAM role trust"
  type        = string
  default     = "4015437"
}

variable "coralogix_aws_account_id" {
  description = "Coralogix AWS account ID for cross-account access"
  type        = string
  default     = "625240141681" # Coralogix production AWS account
}

###############################################################################
# Application Configuration
###############################################################################

variable "cx_rum_public_key" {
  description = "Coralogix RUM Public Key for browser monitoring"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  default     = "demo_password"
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL (containerized)"
  type        = string
  default     = "redis://redis:6379/0"
}

variable "otel_endpoint" {
  description = "OpenTelemetry collector endpoint (containerized)"
  type        = string
  default     = "http://otel-collector:4317"
}

variable "repository_url" {
  description = "Git repository URL for application code"
  type        = string
  default     = "https://github.com/coralogix/dataprime-assistant.git"
}
