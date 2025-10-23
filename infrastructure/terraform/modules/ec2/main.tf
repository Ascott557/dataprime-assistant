# EC2 Module - t3.small instance for cost optimization
# ~$15/month for demo purposes

# Data source for latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 Instance
resource "aws_instance" "main" {
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = var.iam_instance_profile
  key_name               = var.key_name
  
  # User data for bootstrapping
  user_data = var.user_data
  
  # Root volume configuration
  root_block_device {
    volume_type           = "gp3"  # Cheaper and faster than gp2
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true
    
    tags = merge(
      var.tags,
      {
        Name = "${var.project_name}-root-volume-${var.environment}"
      }
    )
  }
  
  # Disable detailed monitoring to save costs
  monitoring = var.enable_detailed_monitoring
  
  # Enable termination protection for production
  disable_api_termination = var.environment == "prod" ? true : false
  
  # Instance metadata options (IMDSv2)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Enforce IMDSv2
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }
  
  # Credit specification for t3 instances
  credit_specification {
    cpu_credits = "standard"  # Use "unlimited" if you need burst performance
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-instance-${var.environment}"
      Type = "application-server"
    }
  )
  
  volume_tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-volume-${var.environment}"
    }
  )
  
  lifecycle {
    ignore_changes = [
      user_data,  # Prevent recreation on user_data changes
      ami         # Prevent recreation on AMI updates
    ]
  }
}

# Elastic IP for stable public address
resource "aws_eip" "main" {
  count    = var.create_elastic_ip ? 1 : 0
  instance = aws_instance.main.id
  domain   = "vpc"
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-eip-${var.environment}"
    }
  )
  
  depends_on = [aws_instance.main]
}

# CloudWatch Alarm for high CPU (optional, disabled by default for cost)
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count               = var.enable_cpu_alarm ? 1 : 0
  alarm_name          = "${var.project_name}-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EC2 CPU utilization"
  alarm_actions       = []  # Add SNS topic ARN if you want notifications
  
  dimensions = {
    InstanceId = aws_instance.main.id
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-high-cpu-alarm-${var.environment}"
    }
  )
}

