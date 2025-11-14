variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Size of root EBS volume in GB"
  type        = number
  default     = 30
}

variable "subnet_id" {
  description = "Subnet ID where instance will be launched"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID for the instance"
  type        = string
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "iam_instance_profile_name" {
  description = "IAM instance profile name"
  type        = string
}

# Application configuration variables
variable "coralogix_token" {
  description = "Coralogix Send-Your-Data API key"
  type        = string
  sensitive   = true
}

variable "coralogix_domain" {
  description = "Coralogix domain (coralogix.com, coralogix.eu, etc.)"
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

variable "openai_api_key" {
  description = "OpenAI API key for query generation"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL"
  type        = string
  default     = "redis://redis:6379/0"
}

variable "otel_endpoint" {
  description = "OpenTelemetry collector endpoint"
  type        = string
  default     = "http://otel-collector:4317"
}

variable "repository_url" {
  description = "Git repository URL for application code"
  type        = string
  default     = "https://github.com/coralogix/dataprime-assistant.git"
}
