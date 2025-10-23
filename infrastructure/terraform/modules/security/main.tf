# Security Module - Security groups, SSH keys, and IAM roles
# Includes Coralogix Infrastructure Explorer integration

# Generate SSH Key Pair
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "deployer" {
  key_name   = "${var.project_name}-key-${var.environment}"
  public_key = tls_private_key.ssh_key.public_key_openssh

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-key-${var.environment}"
    }
  )
}

# Security Group for EC2 Instance
resource "aws_security_group" "instance" {
  name_description = "${var.project_name}-instance-sg-${var.environment}"
  description = "Security group for DataPrime Assistant EC2 instance"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-instance-sg-${var.environment}"
    }
  )
}

# SSH Access (restricted to specific IP)
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.instance.id
  description       = "SSH access from allowed CIDR"
  
  from_port   = 22
  to_port     = 22
  ip_protocol = "tcp"
  cidr_ipv4   = var.allowed_ssh_cidr
  
  tags = {
    Name = "ssh-access"
  }
}

# HTTP Access (for NGINX)
resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.instance.id
  description       = "HTTP access from anywhere"
  
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"
  
  tags = {
    Name = "http-access"
  }
}

# HTTPS Access (for NGINX with SSL)
resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.instance.id
  description       = "HTTPS access from anywhere"
  
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"
  
  tags = {
    Name = "https-access"
  }
}

# API Gateway Direct Access (optional, for testing)
resource "aws_vpc_security_group_ingress_rule" "api_gateway" {
  security_group_id = aws_security_group.instance.id
  description       = "Direct API Gateway access for testing"
  
  from_port   = 8010
  to_port     = 8010
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"
  
  tags = {
    Name = "api-gateway-access"
  }
}

# OpenTelemetry Collector (OTLP gRPC - VPC only for security)
resource "aws_vpc_security_group_ingress_rule" "otlp_grpc" {
  security_group_id = aws_security_group.instance.id
  description       = "OTLP gRPC from within VPC"
  
  from_port   = 4317
  to_port     = 4317
  ip_protocol = "tcp"
  cidr_ipv4   = "10.0.0.0/16"
  
  tags = {
    Name = "otlp-grpc"
  }
}

# OpenTelemetry Collector (OTLP HTTP - VPC only)
resource "aws_vpc_security_group_ingress_rule" "otlp_http" {
  security_group_id = aws_security_group.instance.id
  description       = "OTLP HTTP from within VPC"
  
  from_port   = 4318
  to_port     = 4318
  ip_protocol = "tcp"
  cidr_ipv4   = "10.0.0.0/16"
  
  tags = {
    Name = "otlp-http"
  }
}

# Egress - Allow all outbound traffic
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.instance.id
  description       = "Allow all outbound traffic"
  
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"
  
  tags = {
    Name = "all-outbound"
  }
}

# IAM Role for EC2 Instance (Coralogix Infrastructure Explorer integration)
resource "aws_iam_role" "instance" {
  name = "${var.project_name}-instance-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-instance-role-${var.environment}"
    }
  )
}

# IAM Policy for basic EC2 operations
resource "aws_iam_role_policy" "instance_policy" {
  name = "${var.project_name}-instance-policy-${var.environment}"
  role = aws_iam_role.instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeNetworkInterfaces"
        ]
        Resource = "*"
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "instance" {
  name = "${var.project_name}-instance-profile-${var.environment}"
  role = aws_iam_role.instance.name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-instance-profile-${var.environment}"
    }
  )
}

# IAM Role for Coralogix Infrastructure Explorer (cross-account access)
# This allows Coralogix to read EC2 metadata for enrichment
resource "aws_iam_role" "coralogix" {
  name = "${var.project_name}-coralogix-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::625240141681:root"  # Coralogix AWS account
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.coralogix_company_id
          }
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-coralogix-role-${var.environment}"
      Purpose     = "Coralogix Infrastructure Explorer Integration"
      CompanyID   = var.coralogix_company_id
    }
  )
}

# IAM Policy for Coralogix (read-only EC2 permissions)
resource "aws_iam_role_policy" "coralogix_policy" {
  name = "${var.project_name}-coralogix-policy-${var.environment}"
  role = aws_iam_role.coralogix.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs"
        ]
        Resource = "*"
      }
    ]
  })
}

