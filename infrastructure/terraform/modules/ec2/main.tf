/**
 * EC2 Module - Cost-Optimized Instance
 * 
 * Creates:
 * - t3.small EC2 instance (2 vCPU, 2GB RAM)
 * - 30GB gp3 root volume
 * - Elastic IP for stable public access
 * - Bootstrap script via user_data
 */

# Data source to get latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Render bootstrap script template using templatefile function
locals {
  bootstrap_script = templatefile("${path.module}/../../user-data/bootstrap.sh.tpl", {
    coralogix_token        = var.coralogix_token
    coralogix_domain       = var.coralogix_domain
    coralogix_app_name     = var.coralogix_app_name
    coralogix_subsystem    = var.coralogix_subsystem
    openai_api_key         = var.openai_api_key
    redis_url              = var.redis_url
    otel_endpoint          = var.otel_endpoint
    project_name           = var.project_name
    environment            = var.environment
    repository_url         = var.repository_url
  })
}

# EC2 Instance
resource "aws_instance" "main" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  key_name               = var.key_name
  iam_instance_profile   = var.iam_instance_profile_name

  # Root volume configuration
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  # User data for bootstrapping
  user_data = local.bootstrap_script

  # Disable detailed monitoring (cost savings)
  monitoring = false

  # Enable termination protection in production
  disable_api_termination = false

  tags = {
    Name        = "${var.project_name}-instance"
    Environment = var.environment
    Application = "dataprime-demo"
    ManagedBy   = "terraform"
    
    # Coralogix metadata enrichment tags
    CX_Application = var.coralogix_app_name
    CX_Subsystem   = var.coralogix_subsystem
  }

  # Wait for instance to be ready before considering it created
  lifecycle {
    create_before_destroy = false
  }
}

# Elastic IP for stable public access
resource "aws_eip" "main" {
  domain   = "vpc"
  instance = aws_instance.main.id

  tags = {
    Name = "${var.project_name}-eip"
  }

  # Ensure instance is created first
  depends_on = [aws_instance.main]
}
