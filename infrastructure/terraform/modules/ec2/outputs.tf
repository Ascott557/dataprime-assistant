# EC2 Module Outputs

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.main.id
}

output "instance_arn" {
  description = "ARN of the EC2 instance"
  value       = aws_instance.main.arn
}

output "instance_state" {
  description = "State of the EC2 instance"
  value       = aws_instance.main.instance_state
}

output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_instance.main.public_ip
}

output "private_ip" {
  description = "Private IP address of the instance"
  value       = aws_instance.main.private_ip
}

output "elastic_ip" {
  description = "Elastic IP address (if enabled)"
  value       = var.create_elastic_ip ? aws_eip.main[0].public_ip : null
}

output "elastic_ip_id" {
  description = "ID of the Elastic IP (if enabled)"
  value       = var.create_elastic_ip ? aws_eip.main[0].id : null
}

output "ami_id" {
  description = "AMI ID used for the instance"
  value       = aws_instance.main.ami
}

output "availability_zone" {
  description = "Availability zone of the instance"
  value       = aws_instance.main.availability_zone
}

output "instance_type" {
  description = "Instance type"
  value       = aws_instance.main.instance_type
}

output "root_volume_id" {
  description = "ID of the root EBS volume"
  value       = aws_instance.main.root_block_device[0].volume_id
}

