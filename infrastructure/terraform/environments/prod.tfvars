# Production Environment Variables
# DataPrime Assistant - AWS Deployment

# Basic Configuration
environment = "prod"
project_name = "dataprime-demo"
aws_region = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
# IMPORTANT: Restrict SSH access to specific IPs
allowed_ssh_cidr = "YOUR_OFFICE_IP/32"  # UPDATE THIS!

# EC2 Configuration
instance_type = "t3.medium"  # Upgrade for production (~$30/month)
root_volume_size = 50  # More storage for production

# Coralogix Configuration
coralogix_domain = "coralogix.com"
coralogix_application_name = "dataprime-demo-prod"
coralogix_company_id = "4015437"

# Optional Features
enable_detailed_monitoring = true  # Enable for production monitoring
create_elastic_ip = true

# ==============================================================================
# SENSITIVE VARIABLES - Use AWS Secrets Manager or Parameter Store
# ==============================================================================
# For production, integrate with AWS Secrets Manager:
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_version
# ==============================================================================

