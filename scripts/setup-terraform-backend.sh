#!/bin/bash
###############################################################################
# Terraform Backend Setup Script
# 
# This script creates the S3 bucket and DynamoDB table for Terraform state.
# This is a one-time setup that must be run before deploying the main infrastructure.
#
# Usage: ./scripts/setup-terraform-backend.sh
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/infrastructure/terraform/backend-setup"

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}DataPrime Demo - Terraform Backend Setup${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

###############################################################################
# Prerequisites Check
###############################################################################
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
  echo -e "${RED}ERROR: Terraform is not installed${NC}"
  echo "Install it from: https://www.terraform.io/downloads"
  exit 1
fi
echo -e "${GREEN}✓ Terraform installed: $(terraform version | head -n1)${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
  echo "Install it from: https://aws.amazon.com/cli/"
  exit 1
fi
echo -e "${GREEN}✓ AWS CLI installed: $(aws --version | cut -d' ' -f1)${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  echo -e "${RED}ERROR: AWS credentials not configured${NC}"
  echo "Run: aws configure"
  exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
echo -e "${GREEN}✓ AWS credentials valid${NC}"
echo -e "  Account: ${AWS_ACCOUNT}"
echo -e "  User: ${AWS_USER}"

###############################################################################
# Navigate to Backend Directory
###############################################################################
echo ""
echo -e "${YELLOW}[2/5] Navigating to backend setup directory...${NC}"

if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}ERROR: Backend directory not found: $BACKEND_DIR${NC}"
  exit 1
fi

cd "$BACKEND_DIR"
echo -e "${GREEN}✓ In directory: $(pwd)${NC}"

###############################################################################
# Initialize Terraform
###############################################################################
echo ""
echo -e "${YELLOW}[3/5] Initializing Terraform...${NC}"

terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"

###############################################################################
# Plan and Apply
###############################################################################
echo ""
echo -e "${YELLOW}[4/5] Creating backend resources...${NC}"
echo -e "${BLUE}This will create:${NC}"
echo -e "  • S3 bucket for Terraform state"
echo -e "  • DynamoDB table for state locking"
echo ""

# Run terraform plan
terraform plan -out=tfplan

echo ""
read -p "Apply this plan? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo -e "${RED}Aborted by user${NC}"
  exit 1
fi

# Apply the plan
terraform apply tfplan
rm tfplan

echo -e "${GREEN}✓ Backend resources created${NC}"

###############################################################################
# Save Outputs
###############################################################################
echo ""
echo -e "${YELLOW}[5/5] Saving outputs...${NC}"

S3_BUCKET=$(terraform output -raw s3_bucket_name)
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name)

echo ""
echo -e "${GREEN}=====================================================================${NC}"
echo -e "${GREEN}✅ Backend Setup Complete!${NC}"
echo -e "${GREEN}=====================================================================${NC}"
echo ""
echo -e "${BLUE}S3 Bucket:${NC}       $S3_BUCKET"
echo -e "${BLUE}DynamoDB Table:${NC}  $DYNAMODB_TABLE"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. Update ${BLUE}infrastructure/terraform/main.tf${NC} with backend config:"
echo ""
echo -e "   ${BLUE}terraform {${NC}"
echo -e "     ${BLUE}backend \"s3\" {${NC}"
echo -e "       ${BLUE}bucket         = \"$S3_BUCKET\"${NC}"
echo -e "       ${BLUE}key            = \"dataprime-demo/terraform.tfstate\"${NC}"
echo -e "       ${BLUE}region         = \"$(terraform output -raw s3_bucket_arn | cut -d':' -f4)\"${NC}"
echo -e "       ${BLUE}dynamodb_table = \"$DYNAMODB_TABLE\"${NC}"
echo -e "       ${BLUE}encrypt        = true${NC}"
echo -e "     ${BLUE}}${NC}"
echo -e "   ${BLUE}}${NC}"
echo ""
echo -e "2. Deploy main infrastructure:"
echo -e "   ${GREEN}./scripts/deploy-aws.sh${NC}"
echo ""
echo -e "${GREEN}=====================================================================${NC}"
