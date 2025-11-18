#!/bin/bash
###############################################################################
# AWS Teardown Script
# 
# This script destroys all AWS infrastructure created by Terraform.
# WARNING: This will delete all resources and data!
#
# Usage: ./scripts/teardown-aws.sh
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
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"

echo -e "${RED}=====================================================================${NC}"
echo -e "${RED}E-commerce Demo - Teardown${NC}"
echo -e "${RED}=====================================================================${NC}"
echo ""

###############################################################################
# Warning and Confirmation
###############################################################################
echo -e "${RED}⚠️  WARNING: This will destroy all AWS infrastructure!${NC}"
echo ""
echo -e "${YELLOW}Resources to be destroyed:${NC}"
echo -e "  • EC2 instance and Elastic IP"
echo -e "  • EBS volumes (all data will be lost)"
echo -e "  • Security groups and IAM roles"
echo -e "  • VPC and networking components"
echo -e "  • K3s cluster and all applications"
echo ""

read -p "Are you sure you want to destroy everything? (yes/no): " CONFIRM1

if [ "$CONFIRM1" != "yes" ]; then
  echo -e "${GREEN}Aborted${NC}"
  exit 0
fi

echo ""
echo -e "${RED}This action cannot be undone!${NC}"
read -p "Type 'destroy' to confirm: " CONFIRM2

if [ "$CONFIRM2" != "destroy" ]; then
  echo -e "${GREEN}Aborted${NC}"
  exit 0
fi

###############################################################################
# Navigate to Terraform Directory
###############################################################################
echo ""
echo -e "${YELLOW}[1/6] Navigating to Terraform directory...${NC}"

cd "$TERRAFORM_DIR"

if [ ! -f "terraform.tfstate" ]; then
  echo -e "${YELLOW}No Terraform state found. Nothing to destroy.${NC}"
  exit 0
fi

echo -e "${GREEN}✓ Terraform state found${NC}"

###############################################################################
# Get Instance Information (before destruction)
###############################################################################
echo ""
echo -e "${YELLOW}[2/6] Retrieving instance information...${NC}"

PUBLIC_IP=$(terraform output -raw instance_public_ip 2>/dev/null || echo "N/A")
INSTANCE_ID=$(terraform output -raw instance_id 2>/dev/null || echo "N/A")
SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"

echo -e "${BLUE}  Instance ID: $INSTANCE_ID${NC}"
echo -e "${BLUE}  Public IP: $PUBLIC_IP${NC}"

###############################################################################
# Cleanup K3s Resources
###############################################################################
echo ""
echo -e "${YELLOW}[3/6] Cleaning up Kubernetes resources...${NC}"

if [ "$PUBLIC_IP" != "N/A" ] && [ -f "$SSH_KEY" ]; then
  echo -e "${BLUE}Attempting to cleanup K3s resources...${NC}"
  
  ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" bash <<'REMOTE_CLEANUP' || true
    # Uninstall Helm releases
    helm uninstall coralogix-otel -n dataprime-demo 2>/dev/null || true
    
    # Delete namespace (cascades to all resources)
    kubectl delete namespace dataprime-demo --timeout=120s 2>/dev/null || true
    
    echo "✓ Kubernetes resources cleaned up"
REMOTE_CLEANUP
  
  echo -e "${GREEN}✓ K3s resources cleaned up${NC}"
else
  echo -e "${YELLOW}⚠  Skipping K3s cleanup (instance not accessible)${NC}"
fi

###############################################################################
# Terraform Destroy
###############################################################################
echo ""
echo -e "${YELLOW}[4/6] Destroying infrastructure...${NC}"
echo -e "${BLUE}This will take 2-3 minutes...${NC}"
echo ""

terraform destroy -auto-approve

echo -e "${GREEN}✓ Infrastructure destroyed${NC}"

###############################################################################
# Cleanup Local Files
###############################################################################
echo ""
echo -e "${YELLOW}[5/6] Cleaning up local files...${NC}"

# Remove SSH key
if [ -f "$SSH_KEY" ]; then
  rm "$SSH_KEY"
  echo -e "${GREEN}✓ Removed SSH key: $SSH_KEY${NC}"
fi

# Remove Terraform lock file (optional)
if [ -f ".terraform.lock.hcl" ]; then
  echo -e "${BLUE}  Keeping .terraform.lock.hcl (run 'rm .terraform.lock.hcl' to remove)${NC}"
fi

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${YELLOW}[6/6] Teardown complete${NC}"
echo ""
echo -e "${GREEN}=====================================================================${NC}"
echo -e "${GREEN}✅ Teardown Complete${NC}"
echo -e "${GREEN}=====================================================================${NC}"
echo ""
echo -e "${BLUE}All AWS resources have been destroyed.${NC}"
echo ""
echo -e "${YELLOW}Note: The following were NOT destroyed (manual cleanup if desired):${NC}"
echo -e "  • Terraform backend (S3 bucket and DynamoDB table)"
echo -e "  • CloudWatch logs (if any)"
echo ""
echo -e "${BLUE}To destroy the Terraform backend:${NC}"
echo -e "  cd infrastructure/terraform/backend-setup"
echo -e "  terraform destroy"
echo ""
echo -e "${GREEN}=====================================================================${NC}"
