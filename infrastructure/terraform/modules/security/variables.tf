variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where security group will be created"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH (your IP/32)"
  type        = string
}

variable "coralogix_company_id" {
  description = "Coralogix company ID for IAM role trust"
  type        = string
}

variable "coralogix_aws_account_id" {
  description = "Coralogix AWS account ID for cross-account access"
  type        = string
  default     = "625240141681" # Coralogix production AWS account
}
