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

output "instance_private_ip" {
  description = "Private IP address of the instance"
  value       = aws_instance.main.private_ip
}

output "instance_public_ip" {
  description = "Public IP address (via Elastic IP)"
  value       = aws_eip.main.public_ip
}

output "elastic_ip_id" {
  description = "ID of the Elastic IP"
  value       = aws_eip.main.id
}

output "ami_id" {
  description = "AMI ID used for the instance"
  value       = aws_instance.main.ami
}
