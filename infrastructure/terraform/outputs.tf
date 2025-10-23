# DataPrime Assistant - Terraform Outputs

# EC2 Instance Information
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = module.ec2.instance_id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = module.ec2.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = module.ec2.private_ip
}

output "elastic_ip" {
  description = "Elastic IP address (if enabled)"
  value       = module.ec2.elastic_ip
}

# Network Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = module.vpc.public_subnet_ids[0]
}

# Security Information
output "security_group_id" {
  description = "ID of the instance security group"
  value       = module.security.instance_security_group_id
}

output "ssh_key_name" {
  description = "Name of the SSH key pair"
  value       = module.security.key_pair_name
}

output "ssh_private_key" {
  description = "SSH private key (sensitive - save to file)"
  value       = module.security.private_key_pem
  sensitive   = true
}

# Application Access Information
output "application_url" {
  description = "URL to access the DataPrime Assistant application"
  value       = var.create_elastic_ip ? "https://${module.ec2.elastic_ip}" : "https://${module.ec2.public_ip}"
}

output "api_gateway_url" {
  description = "URL to access the API Gateway directly"
  value       = var.create_elastic_ip ? "http://${module.ec2.elastic_ip}:8010" : "http://${module.ec2.public_ip}:8010"
}

# SSH Connection
output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = var.create_elastic_ip ? "ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.elastic_ip}" : "ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.public_ip}"
}

# Coralogix Integration
output "coralogix_integration_status" {
  description = "Coralogix integration information"
  value = {
    company_id       = var.coralogix_company_id
    domain           = var.coralogix_domain
    application_name = var.coralogix_application_name
    iam_role_arn     = module.security.coralogix_role_arn
  }
}

# Cost Information
output "estimated_monthly_cost" {
  description = "Estimated monthly AWS cost (USD)"
  value = {
    ec2_instance = var.instance_type == "t3.small" ? "~$15.18" : "varies"
    ebs_storage  = "${var.root_volume_size * 0.08}"
    elastic_ip   = var.create_elastic_ip ? "$0 (attached)" : "N/A"
    data_transfer = "~$1"
    total_estimate = var.instance_type == "t3.small" ? "~$18/month" : "varies"
  }
}

# Deployment Instructions
output "next_steps" {
  description = "Next steps after Terraform apply"
  value = <<-EOT
  
  ✅ Infrastructure deployed successfully!
  
  📝 Next Steps:
  
  1. Save SSH private key:
     terraform output -raw ssh_private_key > ~/.ssh/${var.project_name}-key.pem
     chmod 600 ~/.ssh/${var.project_name}-key.pem
  
  2. Wait for instance initialization (~5 minutes):
     The bootstrap script is installing Docker, services, and starting the application.
  
  3. Check instance status:
     ${var.create_elastic_ip ? "ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.elastic_ip}" : "ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.public_ip}"}
     
  4. Monitor bootstrap progress:
     tail -f /var/log/cloud-init-output.log
  
  5. Access the application:
     Frontend:  ${var.create_elastic_ip ? "https://${module.ec2.elastic_ip}" : "https://${module.ec2.public_ip}"}
     API:       ${var.create_elastic_ip ? "http://${module.ec2.elastic_ip}:8010/api/health" : "http://${module.ec2.public_ip}:8010/api/health"}
  
  6. View in Coralogix:
     - Infrastructure Explorer: https://coralogix.com/infrastructure
     - APM Traces: https://coralogix.com/apm
     - Logs: https://coralogix.com/logs
  
  ⚠️  Note: SSL certificate is self-signed. Accept browser warning for demo purposes.
  
  💰 Estimated Cost: ~$18/month
  
  EOT
}

