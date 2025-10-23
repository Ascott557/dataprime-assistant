# VPC Module - Minimal single-AZ setup for cost optimization
# No NAT Gateway = $32/month savings

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-vpc-${var.environment}"
    }
  )
}

# Single Public Subnet (us-east-1a for cost optimization)
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 1)  # 10.0.1.0/24
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-public-subnet-${var.environment}"
      Type = "public"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-igw-${var.environment}"
    }
  )
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-public-rt-${var.environment}"
      Type = "public"
    }
  )
}

# Route Table Association
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# VPC Flow Logs (Optional - disabled by default for cost savings)
# Uncomment if you need VPC traffic monitoring
# resource "aws_flow_log" "main" {
#   count                = var.enable_flow_logs ? 1 : 0
#   iam_role_arn         = aws_iam_role.flow_logs[0].arn
#   log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn
#   traffic_type         = "ALL"
#   vpc_id               = aws_vpc.main.id
#
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-flow-logs-${var.environment}"
#     }
#   )
# }

