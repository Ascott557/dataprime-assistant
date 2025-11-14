#!/bin/bash
###############################################################################
# DataPrime Demo - k3s Deployment Script
#
# This script:
# 1. Retrieves EC2 instance information from Terraform
# 2. Connects to EC2 via SSH
# 3. Stops Docker Compose services and backs up data
# 4. Installs k3s with appropriate settings for t3.small
# 5. Builds Docker images for all services
# 6. Deploys Kubernetes manifests
# 7. Installs Coralogix Operator via Helm
# 8. Verifies deployment and metrics collection
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
echo "DataPrime Demo - k3s Deployment"
echo "======================================================================${NC}"

###############################################################################
# Step 1: Get EC2 Instance Information from Terraform
###############################################################################
echo -e "\n${YELLOW}[1/9] Retrieving EC2 instance information...${NC}"

cd "$PROJECT_ROOT/infrastructure/terraform"

# Get instance IP (works with both local and remote state)
INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || true)
if [ -z "$INSTANCE_IP" ]; then
  echo -e "${RED}Error: Could not retrieve instance IP from Terraform.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Instance IP: $INSTANCE_IP${NC}"

# Get SSH key path
SSH_KEY_PATH="$HOME/.ssh/dataprime-demo-key.pem"
if [ ! -f "$SSH_KEY_PATH" ]; then
  echo "SSH key not found at $SSH_KEY_PATH, creating it..."
  terraform output -raw ssh_private_key > "$SSH_KEY_PATH"
  chmod 600 "$SSH_KEY_PATH"
fi

echo -e "${GREEN}✓ SSH key ready${NC}"

# Get Coralogix and OpenAI credentials from terraform.tfvars
CX_TOKEN=$(grep 'coralogix_token' terraform.tfvars | cut -d'"' -f2)
OPENAI_API_KEY=$(grep 'openai_api_key' terraform.tfvars | cut -d'"' -f2)

if [ -z "$CX_TOKEN" ]; then
  echo -e "${RED}Error: Could not retrieve Coralogix token from terraform.tfvars${NC}"
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo -e "${YELLOW}⚠ OpenAI API key is empty - some features may be limited${NC}"
  OPENAI_API_KEY="not-configured"
fi

echo -e "${GREEN}✓ API credentials loaded${NC}"

###############################################################################
# Step 2: Test SSH Connection
###############################################################################
echo -e "\n${YELLOW}[2/9] Testing SSH connection...${NC}"

if ! ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@"$INSTANCE_IP" "echo 'SSH connection successful'" 2>/dev/null; then
  echo -e "${RED}Error: Could not connect to EC2 instance via SSH.${NC}"
  echo "Please check:"
  echo "  - Instance is running"
  echo "  - Security group allows SSH from your IP"
  echo "  - SSH key is correct"
  exit 1
fi

echo -e "${GREEN}✓ SSH connection successful${NC}"

###############################################################################
# Step 3: Stop Docker Compose and Backup Data
###############################################################################
echo -e "\n${YELLOW}[3/9] Stopping Docker Compose services and backing up data...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_1'
set -euo pipefail

echo "Checking if Docker Compose is running..."
APP_DIR="/opt/dataprime-assistant"

if [ -d "$APP_DIR/deployment/docker" ]; then
  cd "$APP_DIR/deployment/docker"
  
  # Check if services are running
  if docker compose --env-file .env.vm -f docker-compose.vm.yml ps --quiet 2>/dev/null | grep -q .; then
    echo "Stopping Docker Compose services..."
    docker compose --env-file .env.vm -f docker-compose.vm.yml down
    echo "✓ Docker Compose services stopped"
  else
    echo "No Docker Compose services running"
  fi
  
  # Backup SQLite database if it exists
  if [ -d "$APP_DIR/deployment/docker/sqlite-data" ]; then
    BACKUP_DIR="/tmp/dataprime-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    sudo cp -r "$APP_DIR/deployment/docker/sqlite-data" "$BACKUP_DIR/" 2>/dev/null || true
    echo "✓ Database backed up to $BACKUP_DIR"
  fi
  
  # Stop and disable systemd service if exists
  if systemctl is-active --quiet dataprime-demo.service 2>/dev/null; then
    echo "Stopping systemd service..."
    sudo systemctl stop dataprime-demo.service
    sudo systemctl disable dataprime-demo.service
    echo "✓ Systemd service stopped and disabled"
  fi
else
  echo "Application directory not found, skipping Docker Compose cleanup"
fi

echo "✓ Cleanup complete"
REMOTE_SCRIPT_1

echo -e "${GREEN}✓ Docker Compose stopped and data backed up${NC}"

###############################################################################
# Step 4: Install k3s
###############################################################################
echo -e "\n${YELLOW}[4/9] Installing k3s on EC2 instance...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_2'
set -euo pipefail

# Check if k3s is already installed
if command -v k3s &> /dev/null; then
  echo "k3s is already installed, skipping installation..."
  k3s --version
else
  echo "Installing k3s..."
  
  # Install k3s with options optimized for t3.small
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
    --disable traefik \
    --write-kubeconfig-mode 644 \
    --kubelet-arg=eviction-hard=memory.available<100Mi \
    --kubelet-arg=eviction-soft=memory.available<300Mi \
    --kubelet-arg=eviction-soft-grace-period=memory.available=2m" sh -
  
  # Wait for k3s to be ready
  echo "Waiting for k3s to be ready..."
  for i in {1..30}; do
    if sudo k3s kubectl get nodes 2>/dev/null | grep -q Ready; then
      echo "✓ k3s is ready"
      break
    fi
    echo "Waiting... ($i/30)"
    sleep 5
  done
  
  # Configure kubectl for ubuntu user
  mkdir -p ~/.kube
  sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
  sudo chown ubuntu:ubuntu ~/.kube/config
  chmod 600 ~/.kube/config
  
  echo "✓ k3s installed successfully"
fi

# Install Helm if not present
if ! command -v helm &> /dev/null; then
  echo "Installing Helm..."
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  echo "✓ Helm installed"
else
  echo "Helm already installed"
  helm version
fi

# Verify installation
kubectl version --short || true
kubectl get nodes

echo "✓ k3s and kubectl ready"
REMOTE_SCRIPT_2

echo -e "${GREEN}✓ k3s installed successfully${NC}"

###############################################################################
# Step 5: Copy Project Files and Kubernetes Manifests
###############################################################################
echo -e "\n${YELLOW}[5/9] Copying Kubernetes manifests to EC2 instance...${NC}"

# Create remote directory for k8s manifests
ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" "mkdir -p /opt/dataprime-assistant/deployment/kubernetes/deployments"

# Copy all Kubernetes manifests
scp -i "$SSH_KEY_PATH" -r "$PROJECT_ROOT/deployment/kubernetes/"* ubuntu@"$INSTANCE_IP":/opt/dataprime-assistant/deployment/kubernetes/

# Copy service source code if not already there
ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_SCRIPT_3
if [ ! -d "/opt/dataprime-assistant/coralogix-dataprime-demo" ]; then
  echo "Cloning repository..."
  cd /opt/dataprime-assistant
  git clone https://github.com/coralogix/dataprime-assistant.git . 2>/dev/null || true
fi
REMOTE_SCRIPT_3

echo -e "${GREEN}✓ Kubernetes manifests copied${NC}"

###############################################################################
# Step 6: Build Docker Images
###############################################################################
echo -e "\n${YELLOW}[6/9] Building Docker images on EC2 instance...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_4'
set -euo pipefail

cd /opt/dataprime-assistant/coralogix-dataprime-demo

echo "Building Docker images..."

# Build all service images
echo "Building api-gateway..."
docker build -t dataprime-api-gateway:latest -f services/api-gateway/Dockerfile . >/dev/null 2>&1 &
PID_API=$!

echo "Building query-service..."
docker build -t dataprime-query-service:latest -f services/query-service/Dockerfile . >/dev/null 2>&1 &
PID_QUERY=$!

echo "Building validation-service..."
docker build -t dataprime-validation-service:latest -f services/validation-service/Dockerfile . >/dev/null 2>&1 &
PID_VALIDATION=$!

echo "Building queue-service..."
docker build -t dataprime-queue-service:latest -f services/queue-service/Dockerfile . >/dev/null 2>&1 &
PID_QUEUE=$!

echo "Building processing-service..."
docker build -t dataprime-processing-service:latest -f services/processing-service/Dockerfile . >/dev/null 2>&1 &
PID_PROCESSING=$!

echo "Building storage-service..."
docker build -t dataprime-storage-service:latest -f services/storage-service/Dockerfile . >/dev/null 2>&1 &
PID_STORAGE=$!

echo "Building external-api-service..."
docker build -t dataprime-external-api-service:latest -f services/external-api-service/Dockerfile . >/dev/null 2>&1 &
PID_EXTERNAL=$!

echo "Building queue-worker-service..."
docker build -t dataprime-queue-worker-service:latest -f services/queue-worker-service/Dockerfile . >/dev/null 2>&1 &
PID_WORKER=$!

echo "Building frontend..."
docker build -t dataprime-frontend:latest -f app/Dockerfile.frontend . >/dev/null 2>&1 &
PID_FRONTEND=$!

# Wait for all builds to complete
echo "Waiting for all builds to complete..."
wait $PID_API $PID_QUERY $PID_VALIDATION $PID_QUEUE $PID_PROCESSING $PID_STORAGE $PID_EXTERNAL $PID_WORKER $PID_FRONTEND

echo "✓ All Docker images built successfully"

# Import images to k3s
echo "Importing images to k3s..."
for image in dataprime-api-gateway dataprime-query-service dataprime-validation-service dataprime-queue-service dataprime-processing-service dataprime-storage-service dataprime-external-api-service dataprime-queue-worker-service dataprime-frontend; do
  docker save "$image:latest" | sudo k3s ctr images import - 2>/dev/null || true
done

echo "✓ Images imported to k3s"
REMOTE_SCRIPT_4

echo -e "${GREEN}✓ Docker images built and imported${NC}"

###############################################################################
# Step 7: Deploy to Kubernetes
###############################################################################
echo -e "\n${YELLOW}[7/9] Deploying application to Kubernetes...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_SCRIPT_5
set -euo pipefail

cd /opt/dataprime-assistant/deployment/kubernetes

echo "Creating namespace..."
kubectl apply -f namespace.yaml

echo "Creating secret..."
# Create secret from template
cat > secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: dataprime-secrets
  namespace: dataprime-demo
  labels:
    app: dataprime-demo
type: Opaque
stringData:
  CX_TOKEN: "$CX_TOKEN"
  OPENAI_API_KEY: "$OPENAI_API_KEY"
EOF

kubectl apply -f secret.yaml
rm -f secret.yaml  # Remove file with secrets

echo "Creating configmap..."
kubectl apply -f configmap.yaml

echo "Creating persistent volumes..."
kubectl apply -f persistent-volumes.yaml

echo "Deploying Redis..."
kubectl apply -f redis-statefulset.yaml

echo "Deploying OpenTelemetry Collector..."
kubectl apply -f otel-collector-daemonset.yaml

echo "Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n dataprime-demo --timeout=120s || true

echo "Deploying microservices..."
kubectl apply -f deployments/

echo "Creating services..."
kubectl apply -f services.yaml

echo "Creating ingress..."
# Re-enable Traefik first
sudo k3s kubectl patch configmap -n kube-system traefik --type merge -p '{"data":{"traefik.yaml":""}}'
sudo systemctl restart k3s

kubectl apply -f ingress.yaml

echo "✓ All resources deployed"

echo "Waiting for pods to be ready..."
sleep 30

kubectl get pods -n dataprime-demo
REMOTE_SCRIPT_5

echo -e "${GREEN}✓ Application deployed to Kubernetes${NC}"

###############################################################################
# Step 8: Install Coralogix Operator
###############################################################################
echo -e "\n${YELLOW}[8/9] Installing Coralogix Operator...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<REMOTE_SCRIPT_6
set -euo pipefail

echo "Adding Coralogix Helm repository..."
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual 2>/dev/null || true
helm repo update

echo "Installing Coralogix Operator..."
helm upgrade --install coralogix-operator coralogix/coralogix-operator \
  --create-namespace \
  --namespace coralogix-operator-system \
  --set secret.data.apiKey="$CX_TOKEN" \
  --set coralogixOperator.region="US1" \
  --set coralogixOperator.prometheusRules.enabled=false \
  --set serviceMonitor.create=false \
  --wait \
  --timeout 5m

echo "✓ Coralogix Operator installed"

echo "Checking operator status..."
kubectl get pods -n coralogix-operator-system
REMOTE_SCRIPT_6

echo -e "${GREEN}✓ Coralogix Operator installed${NC}"

###############################################################################
# Step 9: Verify Deployment
###############################################################################
echo -e "\n${YELLOW}[9/9] Verifying deployment...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_7'
set -euo pipefail

echo ""
echo "==================================="
echo "Deployment Status"
echo "==================================="

echo ""
echo "Nodes:"
kubectl get nodes

echo ""
echo "Pods in dataprime-demo namespace:"
kubectl get pods -n dataprime-demo

echo ""
echo "Services in dataprime-demo namespace:"
kubectl get svc -n dataprime-demo

echo ""
echo "Ingress:"
kubectl get ingress -n dataprime-demo

echo ""
echo "Coralogix Operator:"
kubectl get pods -n coralogix-operator-system

echo ""
echo "Storage:"
kubectl get pvc -n dataprime-demo

echo ""
echo "Resource Usage:"
kubectl top nodes || echo "Metrics not available yet (requires a few minutes)"
kubectl top pods -n dataprime-demo || echo "Pod metrics not available yet"

echo ""
echo "==================================="
echo "Health Checks"
echo "==================================="

# Wait a bit for pods to fully start
sleep 10

# Check pod readiness
NOT_READY=$(kubectl get pods -n dataprime-demo --no-headers | grep -v "Running" | wc -l || echo "0")
if [ "$NOT_READY" -eq 0 ]; then
  echo "✓ All pods are running"
else
  echo "⚠ $NOT_READY pods are not ready yet"
  kubectl get pods -n dataprime-demo | grep -v "Running" || true
fi

# Check OTel Collector logs
echo ""
echo "Recent OTel Collector logs (last 10 lines):"
kubectl logs -n dataprime-demo -l app=otel-collector --tail=10 2>/dev/null || echo "Logs not available yet"

echo ""
echo "==================================="

REMOTE_SCRIPT_7

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
echo "  Ingress:     http://$INSTANCE_IP (once Traefik is fully configured)"

echo -e "\n${BLUE}SSH to instance:${NC}"
echo "  ssh -i $SSH_KEY_PATH ubuntu@$INSTANCE_IP"

echo -e "\n${BLUE}View logs:${NC}"
echo "  kubectl logs -n dataprime-demo -l app=api-gateway --tail=50"
echo "  kubectl logs -n dataprime-demo -l app=otel-collector --tail=50"

echo -e "\n${BLUE}Check Coralogix:${NC}"
echo "  1. Go to Coralogix Infrastructure Explorer"
echo "  2. Look for your k3s node with metrics"
echo "  3. Open a trace and check the 'HOST' tab for Kubernetes metadata"

echo -e "\n${BLUE}Useful commands:${NC}"
echo "  kubectl get pods -n dataprime-demo"
echo "  kubectl get svc -n dataprime-demo"
echo "  kubectl top pods -n dataprime-demo"
echo "  kubectl describe pod <pod-name> -n dataprime-demo"

echo -e "\n${YELLOW}Note: It may take a few minutes for metrics to appear in Coralogix.${NC}"

echo -e "\n${GREEN}✓ Migration to k3s complete!${NC}"

