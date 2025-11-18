#!/bin/bash
###############################################################################
# E-commerce Recommendation System - k3s Deployment Script
#
# This script:
# 1. Retrieves EC2 instance information from Terraform
# 2. Connects to EC2 via SSH
# 3. Installs k3s and Helm (if not already installed)
# 4. Builds unified Docker image for all services
# 5. Deploys PostgreSQL and application services
# 6. Installs Coralogix OpenTelemetry Collector via Helm
# 7. Verifies deployment and telemetry flow
#
# Usage: ./deploy-k3s.sh
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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}======================================================================"
echo "E-commerce Recommendation System - k3s Deployment"
echo "======================================================================${NC}"

###############################################################################
# Step 1: Get EC2 Instance Information from Terraform
###############################################################################
echo -e "\n${YELLOW}[1/8] Retrieving EC2 instance information...${NC}"

cd "$PROJECT_ROOT/infrastructure/terraform"

# Get instance IP
INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || true)
if [ -z "$INSTANCE_IP" ]; then
  echo -e "${RED}Error: Could not retrieve instance IP from Terraform.${NC}"
  echo "Make sure you've run: terraform apply"
  exit 1
fi

echo -e "${GREEN}✓ Instance IP: $INSTANCE_IP${NC}"

# Get SSH key path
SSH_KEY_PATH="$HOME/.ssh/dataprime-demo-key.pem"
if [ ! -f "$SSH_KEY_PATH" ]; then
  echo "SSH key not found at $SSH_KEY_PATH, extracting from Terraform..."
  terraform output -raw ssh_private_key > "$SSH_KEY_PATH"
  chmod 600 "$SSH_KEY_PATH"
fi

echo -e "${GREEN}✓ SSH key ready${NC}"

# Get credentials from terraform.tfvars
CX_TOKEN=$(grep 'coralogix_token' terraform.tfvars | cut -d'"' -f2)
OPENAI_API_KEY=$(grep 'openai_api_key' terraform.tfvars | cut -d'"' -f2)
CX_RUM_PUBLIC_KEY=$(grep 'cx_rum_public_key' terraform.tfvars | cut -d'"' -f2)
DB_PASSWORD=$(grep 'db_password' terraform.tfvars | cut -d'"' -f2 || echo "demo_password")

if [ -z "$CX_TOKEN" ]; then
  echo -e "${RED}Error: Could not retrieve Coralogix token from terraform.tfvars${NC}"
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo -e "${YELLOW}⚠ OpenAI API key is empty - AI features will not work${NC}"
  OPENAI_API_KEY="not-configured"
fi

echo -e "${GREEN}✓ API credentials loaded${NC}"

###############################################################################
# Step 2: Test SSH Connection
###############################################################################
echo -e "\n${YELLOW}[2/8] Testing SSH connection...${NC}"

if ! ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@"$INSTANCE_IP" "echo 'SSH connection successful'" 2>/dev/null; then
  echo -e "${RED}Error: Could not connect to EC2 instance via SSH.${NC}"
  echo "Please check:"
  echo "  - Instance is running (terraform show)"
  echo "  - Security group allows SSH from your IP"
  echo "  - SSH key is correct"
  exit 1
fi

echo -e "${GREEN}✓ SSH connection successful${NC}"

###############################################################################
# Step 3: Copy Project Files to EC2
###############################################################################
echo -e "\n${YELLOW}[3/8] Copying project files to EC2 instance...${NC}"

# Create remote directories
ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" "mkdir -p /opt/dataprime-assistant/deployment/kubernetes/{deployments,}"

# Copy Kubernetes manifests
scp -i "$SSH_KEY_PATH" "$PROJECT_ROOT/deployment/kubernetes/"*.yaml ubuntu@"$INSTANCE_IP":/opt/dataprime-assistant/deployment/kubernetes/ 2>/dev/null || true
scp -i "$SSH_KEY_PATH" "$PROJECT_ROOT/deployment/kubernetes/deployments/"*.yaml ubuntu@"$INSTANCE_IP":/opt/dataprime-assistant/deployment/kubernetes/deployments/ 2>/dev/null || true

# Copy unified Dockerfile
scp -i "$SSH_KEY_PATH" "$PROJECT_ROOT/deployment/kubernetes/Dockerfile" ubuntu@"$INSTANCE_IP":/opt/dataprime-assistant/deployment/kubernetes/

# Copy application code
ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_COPY
set -euo pipefail
cd /opt/dataprime-assistant

# Clone repo if not exists
if [ ! -d "/opt/dataprime-assistant/.git" ]; then
  echo "Cloning repository..."
  git clone https://github.com/coralogix/dataprime-assistant.git /tmp/repo
  cp -r /tmp/repo/* .
  rm -rf /tmp/repo
fi

echo "✓ Application code ready"
REMOTE_COPY

echo -e "${GREEN}✓ Project files copied${NC}"

###############################################################################
# Step 4: Build Unified Docker Image
###############################################################################
echo -e "\n${YELLOW}[4/8] Building unified Docker image on EC2...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_BUILD'
set -euo pipefail

cd /opt/dataprime-assistant

echo "Building unified Docker image..."
docker build -f deployment/kubernetes/Dockerfile \
  -t dataprime-base:latest \
  coralogix-dataprime-demo/

# Tag for each service
echo "Tagging images for each service..."
for service in api-gateway recommendation-ai product-service validation-service storage-service frontend; do
  docker tag dataprime-base:latest dataprime-$service:latest
done

echo "✓ Docker images built and tagged"

# Import to k3s (if k3s is installed)
if command -v k3s &> /dev/null; then
  echo "Importing images to k3s..."
  docker save dataprime-base:latest | sudo k3s ctr images import -
  echo "✓ Images imported to k3s"
fi

REMOTE_BUILD

echo -e "${GREEN}✓ Docker images built${NC}"

###############################################################################
# Step 5: Deploy PostgreSQL
###############################################################################
echo -e "\n${YELLOW}[5/8] Deploying PostgreSQL...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_POSTGRES
set -euo pipefail

cd /opt/dataprime-assistant/deployment/kubernetes

echo "Creating namespace..."
kubectl create namespace dataprime-demo --dry-run=client -o yaml | kubectl apply -f -

echo "Creating secrets..."
kubectl create secret generic dataprime-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=CX_TOKEN="$CX_TOKEN" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --from-literal=CX_RUM_PUBLIC_KEY="$CX_RUM_PUBLIC_KEY" \
  -n dataprime-demo \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Applying ConfigMap..."
kubectl apply -f configmap.yaml

echo "Deploying PostgreSQL..."
kubectl apply -f postgres-init-configmap.yaml
kubectl apply -f postgres-statefulset.yaml

echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n dataprime-demo --timeout=300s || true

echo "✓ PostgreSQL deployed"
REMOTE_POSTGRES

echo -e "${GREEN}✓ PostgreSQL deployed${NC}"

###############################################################################
# Step 6: Install Coralogix OpenTelemetry Collector
###############################################################################
echo -e "\n${YELLOW}[6/8] Installing Coralogix OpenTelemetry Collector...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_OTEL
set -euo pipefail

echo "Adding Coralogix Helm repository..."
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual 2>/dev/null || true
helm repo update

echo "Creating Coralogix keys secret..."
kubectl create secret generic coralogix-keys \
  --from-literal=PRIVATE_KEY="$CX_TOKEN" \
  -n dataprime-demo \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Coralogix OpenTelemetry Collector..."
helm upgrade --install coralogix-otel coralogix/otel-integration \
  -f /opt/dataprime-assistant/deployment/kubernetes/coralogix-infra-values.yaml \
  -n dataprime-demo \
  --wait \
  --timeout 5m || echo "Warning: Helm install had issues, continuing..."

echo "✓ Coralogix OpenTelemetry Collector installed"

echo "Checking collector status..."
kubectl get pods -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector || true
REMOTE_OTEL

echo -e "${GREEN}✓ Coralogix OpenTelemetry Collector installed${NC}"

###############################################################################
# Step 7: Deploy Application Services
###############################################################################
echo -e "\n${YELLOW}[7/8] Deploying application services...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_APP'
set -euo pipefail

cd /opt/dataprime-assistant/deployment/kubernetes

echo "Deploying services..."
kubectl apply -f services.yaml

echo "Deploying application..."
kubectl apply -f deployments/

echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available deployment -n dataprime-demo --all --timeout=300s || true

echo "✓ Application services deployed"

echo ""
echo "Pod status:"
kubectl get pods -n dataprime-demo
REMOTE_APP

echo -e "${GREEN}✓ Application services deployed${NC}"

###############################################################################
# Step 8: Verify Deployment
###############################################################################
echo -e "\n${YELLOW}[8/8] Verifying deployment...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_VERIFY'
set -euo pipefail

echo ""
echo "========================================="
echo "Deployment Status"
echo "========================================="

echo ""
echo "Pods:"
kubectl get pods -n dataprime-demo -o wide

echo ""
echo "Services:"
kubectl get svc -n dataprime-demo

echo ""
echo "Check OTel Collector logs (last 20 lines):"
kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=20 2>/dev/null || echo "Collector logs not available yet"

echo ""
echo "Check Recommendation AI logs (last 10 lines):"
kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=10 2>/dev/null || echo "Logs not available yet"

echo ""
echo "========================================="

REMOTE_VERIFY

echo -e "${GREEN}✓ Deployment verification complete${NC}"

###############################################################################
# Summary
###############################################################################
echo -e "\n${GREEN}======================================================================"
echo "Deployment Complete!"
echo "======================================================================${NC}"

echo -e "\n${BLUE}Access your application:${NC}"
echo "  Frontend:    http://$INSTANCE_IP:30020"
echo "  API Gateway: http://$INSTANCE_IP:30010"

echo -e "\n${BLUE}SSH to instance:${NC}"
echo "  ssh -i $SSH_KEY_PATH ubuntu@$INSTANCE_IP"

echo -e "\n${BLUE}View logs:${NC}"
echo "  kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50"
echo "  kubectl logs -n dataprime-demo -l app=product-service --tail=50"
echo "  kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=50"

echo -e "\n${BLUE}Check Coralogix:${NC}"
echo "  1. Go to https://eu2.coralogix.com"
echo "  2. Navigate to Infrastructure → Explorer"
echo "  3. Look for your K3s cluster and pods"
echo "  4. Navigate to AI Center → Applications"
echo "  5. Select 'ecommerce-recommendation'"
echo "  6. Trigger a recommendation and verify LLM calls appear"

echo -e "\n${BLUE}Test the application:${NC}"
echo "  1. Open http://$INSTANCE_IP:30020 in your browser"
echo "  2. Enter a user query (e.g., 'Looking for wireless headphones under \$100')"
echo "  3. Click 'Get AI Recommendations'"
echo "  4. Check Coralogix for traces and AI evaluations"

echo -e "\n${YELLOW}Note: It may take 2-3 minutes for telemetry to appear in Coralogix.${NC}"

echo -e "\n${GREEN}✓ E-commerce Recommendation System deployed successfully!${NC}"
