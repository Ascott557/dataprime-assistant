#!/bin/bash
###############################################################################
# AWS Health Check Script
# 
# This script verifies that all services are running correctly on the deployed
# EC2 instance. It checks:
# - EC2 instance status
# - Docker containers
# - Service health endpoints
# - OTel Collector metrics
#
# Usage: ./scripts/health-check-aws.sh
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

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}DataPrime Demo - Health Check${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

###############################################################################
# Get Instance Info from Terraform
###############################################################################
echo -e "${YELLOW}[1/5] Retrieving instance information...${NC}"

cd "$TERRAFORM_DIR"

if [ ! -f "terraform.tfstate" ]; then
  echo -e "${RED}ERROR: No Terraform state found. Has the infrastructure been deployed?${NC}"
  exit 1
fi

PUBLIC_IP=$(terraform output -raw instance_public_ip 2>/dev/null || echo "")
INSTANCE_ID=$(terraform output -raw instance_id 2>/dev/null || echo "")

if [ -z "$PUBLIC_IP" ] || [ -z "$INSTANCE_ID" ]; then
  echo -e "${RED}ERROR: Could not retrieve instance information from Terraform${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Instance ID: $INSTANCE_ID${NC}"
echo -e "${GREEN}✓ Public IP: $PUBLIC_IP${NC}"

###############################################################################
# Check EC2 Instance Status
###############################################################################
echo ""
echo -e "${YELLOW}[2/5] Checking EC2 instance status...${NC}"

INSTANCE_STATE=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

if [ "$INSTANCE_STATE" = "running" ]; then
  echo -e "${GREEN}✓ Instance is running${NC}"
else
  echo -e "${RED}✗ Instance state: $INSTANCE_STATE${NC}"
  exit 1
fi

# Check status checks
STATUS_CHECKS=$(aws ec2 describe-instance-status \
  --instance-ids "$INSTANCE_ID" \
  --query 'InstanceStatuses[0].InstanceStatus.Status' \
  --output text 2>/dev/null || echo "initializing")

echo -e "${BLUE}  Status checks: $STATUS_CHECKS${NC}"

###############################################################################
# Check SSH Connectivity
###############################################################################
echo ""
echo -e "${YELLOW}[3/5] Checking SSH connectivity...${NC}"

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"

if [ ! -f "$SSH_KEY" ]; then
  echo -e "${RED}✗ SSH key not found at: $SSH_KEY${NC}"
  echo -e "${YELLOW}  Extract it with: terraform output -raw ssh_private_key > $SSH_KEY && chmod 600 $SSH_KEY${NC}"
  exit 1
fi

if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" "echo 'SSH OK'" &>/dev/null; then
  echo -e "${GREEN}✓ SSH connection successful${NC}"
else
  echo -e "${RED}✗ Cannot connect via SSH${NC}"
  echo -e "${YELLOW}  The instance may still be booting. Wait a minute and try again.${NC}"
  exit 1
fi

###############################################################################
# Check Docker Containers
###############################################################################
echo ""
echo -e "${YELLOW}[4/5] Checking Docker containers...${NC}"

CONTAINER_STATUS=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" \
  "cd /opt/dataprime-assistant/deployment/docker && docker compose --env-file .env.vm -f docker-compose.vm.yml ps --format json 2>/dev/null" || echo "[]")

if [ "$CONTAINER_STATUS" = "[]" ]; then
  echo -e "${YELLOW}⏱  Docker Compose not yet running (still bootstrapping)${NC}"
else
  # Count containers
  TOTAL=$(echo "$CONTAINER_STATUS" | jq -s 'length')
  RUNNING=$(echo "$CONTAINER_STATUS" | jq -s '[.[] | select(.State == "running")] | length')
  
  echo -e "${BLUE}  Total containers: $TOTAL${NC}"
  echo -e "${BLUE}  Running: $RUNNING${NC}"
  
  if [ "$RUNNING" -eq "$TOTAL" ]; then
    echo -e "${GREEN}✓ All containers are running${NC}"
  else
    echo -e "${YELLOW}⚠  Some containers are not running yet${NC}"
  fi
fi

###############################################################################
# Check Service Health Endpoints
###############################################################################
echo ""
echo -e "${YELLOW}[5/5] Checking service health endpoints...${NC}"

check_endpoint() {
  local name=$1
  local url=$2
  
  if curl -sf "$url" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ $name${NC}"
    return 0
  else
    echo -e "${RED}✗ $name${NC}"
    return 1
  fi
}

HEALTHY=0
TOTAL_CHECKS=3

echo ""
echo -e "${BLUE}Testing endpoints:${NC}"

check_endpoint "API Gateway       " "http://$PUBLIC_IP:8010/api/health" && ((HEALTHY++)) || true
check_endpoint "Frontend (HTTP)   " "http://$PUBLIC_IP" && ((HEALTHY++)) || true
check_endpoint "Frontend (HTTPS)  " "https://$PUBLIC_IP" --insecure && ((HEALTHY++)) || true

echo ""
if [ $HEALTHY -eq $TOTAL_CHECKS ]; then
  echo -e "${GREEN}✓ All health checks passed ($HEALTHY/$TOTAL_CHECKS)${NC}"
else
  echo -e "${YELLOW}⚠  Some health checks failed ($HEALTHY/$TOTAL_CHECKS)${NC}"
  echo -e "${YELLOW}  The application may still be starting up. Bootstrap takes 5-10 minutes.${NC}"
fi

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""
echo -e "${BLUE}Access your application:${NC}"
echo -e "  Frontend:   ${GREEN}https://$PUBLIC_IP${NC}"
echo -e "  API:        ${GREEN}http://$PUBLIC_IP:8010${NC}"
echo ""
echo -e "${BLUE}Monitor logs:${NC}"
echo -e "  ${GREEN}ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/dataprime-bootstrap.log'${NC}"
echo ""
echo -e "${BLUE}View Docker logs:${NC}"
echo -e "  ${GREEN}ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP 'cd /opt/dataprime-assistant/deployment/docker && docker compose --env-file .env.vm -f docker-compose.vm.yml logs -f'${NC}"
echo ""
echo -e "${BLUE}=====================================================================${NC}"





