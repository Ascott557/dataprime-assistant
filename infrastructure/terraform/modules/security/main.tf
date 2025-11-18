/**
 * Security Module
 * 
 * Creates:
 * - Security Group with minimal required ports
 * - IAM Role for Coralogix Infrastructure Explorer integration
 * - SSH Key Pair via Terraform
 */

# Security Group
resource "aws_security_group" "main" {
  name        = "${var.project_name}-sg"
  description = "Security group for DataPrime Demo application"
  vpc_id      = var.vpc_id

  # SSH - Only from your IP
  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # HTTP - Public access
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS - Public access
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # API Gateway - Public access (for testing)
  ingress {
    description = "API Gateway from internet"
    from_port   = 8010
    to_port     = 8010
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - API Gateway HTTP (30010)
  ingress {
    description = "K3s API Gateway HTTP"
    from_port   = 30010
    to_port     = 30010
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - Frontend HTTPS (30443)
  ingress {
    description = "K3s Frontend HTTPS"
    from_port   = 30443
    to_port     = 30443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - API Gateway HTTPS (30444)
  ingress {
    description = "K3s API Gateway HTTPS"
    from_port   = 30444
    to_port     = 30444
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - Inventory Service (30015)
  ingress {
    description = "K3s Inventory Service"
    from_port   = 30015
    to_port     = 30015
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - Order Service (30016)
  ingress {
    description = "K3s Order Service"
    from_port   = 30016
    to_port     = 30016
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s NodePort - Demo Frontend (30017)
  ingress {
    description = "K3s Demo Frontend"
    from_port   = 30017
    to_port     = 30017
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# Generate SSH Key Pair
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "deployer" {
  key_name   = "${var.project_name}-key"
  public_key = tls_private_key.ssh_key.public_key_openssh

  tags = {
    Name = "${var.project_name}-ssh-key"
  }
}

# IAM Role for Coralogix Infrastructure Explorer
resource "aws_iam_role" "coralogix_integration" {
  name               = "${var.project_name}-coralogix-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
      {
        # Trust relationship with Coralogix AWS account
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.coralogix_aws_account_id}:root"
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

  tags = {
    Name = "${var.project_name}-coralogix-role"
  }
}

# IAM Policy for EC2 Read-Only (Infrastructure Explorer)
resource "aws_iam_role_policy" "coralogix_ec2_readonly" {
  name = "${var.project_name}-ec2-readonly"
  role = aws_iam_role.coralogix_integration.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ec2:Get*",
          "ec2:List*"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "main" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.coralogix_integration.name

  tags = {
    Name = "${var.project_name}-instance-profile"
  }
}
