###############################################################################
# Instance Outputs
###############################################################################

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = module.ec2.instance_id
}

output "instance_public_ip" {
  description = "Public IP address of the instance (Elastic IP)"
  value       = module.ec2.instance_public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the instance"
  value       = module.ec2.instance_private_ip
}

###############################################################################
# Access Information
###############################################################################

output "application_url" {
  description = "URL to access the application"
  value       = "https://${module.ec2.instance_public_ip}"
}

output "api_gateway_url" {
  description = "URL to access the API Gateway directly"
  value       = "http://${module.ec2.instance_public_ip}:8010"
}

output "ssh_command" {
  description = "SSH command to access the instance"
  value       = "ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.instance_public_ip}"
}

###############################################################################
# SSH Key (Sensitive)
###############################################################################

output "ssh_private_key" {
  description = "Private SSH key for EC2 access (save to ~/.ssh/)"
  value       = module.security.ssh_private_key
  sensitive   = true
}

output "ssh_private_key_instructions" {
  description = "Instructions to save SSH key"
  value = <<-EOT
    To save the SSH private key, run:
    
    terraform output -raw ssh_private_key > ~/.ssh/${var.project_name}-key.pem
    chmod 600 ~/.ssh/${var.project_name}-key.pem
  EOT
}

###############################################################################
# Network Outputs
###############################################################################

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "security_group_id" {
  description = "ID of the security group"
  value       = module.security.security_group_id
}

###############################################################################
# IAM Outputs
###############################################################################

output "iam_role_arn" {
  description = "ARN of the IAM role for Coralogix integration"
  value       = module.security.iam_role_arn
}

output "iam_role_name" {
  description = "Name of the IAM role"
  value       = module.security.iam_role_name
}

###############################################################################
# Deployment Information
###############################################################################

output "deployment_complete" {
  description = "Deployment information and next steps"
  value = <<-EOT
    ====================================================================
    🎉 DataPrime Demo - Deployment Complete!
    ====================================================================
    
    Instance ID:     ${module.ec2.instance_id}
    Public IP:       ${module.ec2.instance_public_ip}
    Region:          ${var.aws_region}
    Instance Type:   ${var.instance_type}
    
    📡 Access Points:
    ----------------
    Frontend (HTTPS): https://${module.ec2.instance_public_ip}
    API Gateway:      http://${module.ec2.instance_public_ip}:8010
    
    🔑 SSH Access:
    --------------
    1. Save SSH key:
       terraform output -raw ssh_private_key > ~/.ssh/${var.project_name}-key.pem
       chmod 600 ~/.ssh/${var.project_name}-key.pem
    
    2. Connect:
       ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.instance_public_ip}
    
    ⏱️  Bootstrap Status:
    --------------------
    The instance is currently bootstrapping (installing Docker, starting services).
    This takes approximately 5-10 minutes.
    
    Check bootstrap progress:
      ssh -i ~/.ssh/${var.project_name}-key.pem ubuntu@${module.ec2.instance_public_ip} \
        "tail -f /var/log/dataprime-bootstrap.log"
    
    📊 Coralogix Integration:
    -------------------------
    Application: ${var.coralogix_app_name}
    Subsystem:   ${var.coralogix_subsystem}
    Domain:      ${var.coralogix_domain}
    
    View metrics in Coralogix Infrastructure Explorer:
      https://${var.coralogix_domain}/infrastructure
    
    IAM Role ARN (for Infrastructure Explorer):
      ${module.security.iam_role_arn}
    
    💰 Estimated Monthly Cost:
    --------------------------
    EC2 t3.small:    ~$15/month
    EBS 30GB gp3:    ~$2.40/month
    Data Transfer:   ~$1/month
    Total:           ~$18.40/month
    
    🧹 Cleanup:
    -----------
    When done testing, destroy resources:
      terraform destroy
    
    ====================================================================
  EOT
}
