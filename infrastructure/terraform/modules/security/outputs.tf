# Security Module Outputs

output "instance_security_group_id" {
  description = "ID of the instance security group"
  value       = aws_security_group.instance.id
}

output "instance_security_group_name" {
  description = "Name of the instance security group"
  value       = aws_security_group.instance.name
}

output "key_pair_name" {
  description = "Name of the SSH key pair"
  value       = aws_key_pair.deployer.key_name
}

output "private_key_pem" {
  description = "Private key in PEM format (sensitive)"
  value       = tls_private_key.ssh_key.private_key_pem
  sensitive   = true
}

output "public_key_openssh" {
  description = "Public key in OpenSSH format"
  value       = tls_private_key.ssh_key.public_key_openssh
}

output "instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = aws_iam_instance_profile.instance.name
}

output "instance_role_arn" {
  description = "ARN of the instance IAM role"
  value       = aws_iam_role.instance.arn
}

output "coralogix_role_arn" {
  description = "ARN of the Coralogix IAM role for Infrastructure Explorer"
  value       = aws_iam_role.coralogix.arn
}

output "coralogix_role_name" {
  description = "Name of the Coralogix IAM role"
  value       = aws_iam_role.coralogix.name
}

output "coralogix_integration_instructions" {
  description = "Instructions for setting up Coralogix Infrastructure Explorer"
  value = <<-EOT
  
  Coralogix Infrastructure Explorer Setup:
  
  1. Log in to Coralogix: https://coralogix.com
  2. Navigate to Settings → Infrastructure → AWS Integration
  3. Add New Integration
  4. Use the following details:
     - Role ARN: ${aws_iam_role.coralogix.arn}
     - External ID: ${var.coralogix_company_id}
     - Region: Your AWS region
  5. Save and verify the connection
  
  This will enable EC2 metadata enrichment in your traces and metrics!
  EOT
}

