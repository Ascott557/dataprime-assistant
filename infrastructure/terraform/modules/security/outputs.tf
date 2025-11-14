output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.main.id
}

output "security_group_name" {
  description = "Name of the security group"
  value       = aws_security_group.main.name
}

output "ssh_key_name" {
  description = "Name of the SSH key pair"
  value       = aws_key_pair.deployer.key_name
}

output "ssh_private_key" {
  description = "Private SSH key for EC2 access"
  value       = tls_private_key.ssh_key.private_key_pem
  sensitive   = true
}

output "ssh_public_key" {
  description = "Public SSH key"
  value       = tls_private_key.ssh_key.public_key_openssh
}

output "iam_role_arn" {
  description = "ARN of the IAM role for Coralogix"
  value       = aws_iam_role.coralogix_integration.arn
}

output "iam_role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.coralogix_integration.name
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = aws_iam_instance_profile.main.name
}

output "iam_instance_profile_arn" {
  description = "ARN of the IAM instance profile"
  value       = aws_iam_instance_profile.main.arn
}
