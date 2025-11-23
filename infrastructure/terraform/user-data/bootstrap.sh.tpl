#!/bin/bash
###############################################################################
# E-commerce Platform - EC2 Bootstrap Script (K3s)
# 
# This script:
# 1. Updates system and installs dependencies
# 2. Installs Docker for building images
# 3. Installs K3s and Helm
# 4. Clones application code
# 5. Builds Docker images locally
# 6. Creates Kubernetes secrets
# 7. Deploys PostgreSQL and Redis
# 8. Installs Coralogix OpenTelemetry Collector
# 9. Deploys e-commerce microservices
# 10. Sets up firewall rules
#
# All output is logged to /var/log/ecommerce-bootstrap.log
###############################################################################

set -euo pipefail

# Logging setup
LOGFILE="/var/log/ecommerce-bootstrap.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "======================================================================"
echo "E-commerce Platform Bootstrap - Started at $(date)"
echo "======================================================================"

# Environment variables from Terraform
export CX_TOKEN="${coralogix_token}"
export CX_ENDPOINT="https://ingress.${coralogix_domain}"
export CX_APPLICATION_NAME="${coralogix_app_name}"
export CX_SUBSYSTEM_NAME="${coralogix_subsystem}"
export CX_RUM_PUBLIC_KEY="${cx_rum_public_key}"
export DB_PASSWORD="${db_password}"
export PROJECT_NAME="${project_name}"
export ENVIRONMENT="${environment}"
export DEMO_MODE="normal"

# Application directory
APP_DIR="/opt/ecommerce-platform"
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

###############################################################################
# 1. System Update and Dependencies
###############################################################################
echo "[1/10] Updating system packages..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

echo "[1/10] Installing essential packages..."
apt-get install -y \
  curl \
  wget \
  git \
  unzip \
  jq \
  ca-certificates \
  gnupg \
  postgresql-client \
  apt-transport-https \
  software-properties-common

echo "[1/10] System dependencies installed!"

###############################################################################
# 2. Install Docker
###############################################################################
echo "[2/10] Installing Docker..."

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
systemctl enable docker
systemctl start docker

echo "[2/10] Docker installed successfully!"
docker --version

###############################################################################
# 3. Install K3s and Helm
###############################################################################
echo "[3/10] Installing K3s..."

# Install K3s with Docker as container runtime
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --docker \
  --node-name $(hostname)

# Wait for K3s to be ready
echo "Waiting for K3s to be ready..."
until kubectl get nodes 2>/dev/null | grep -q Ready; do
  echo "  Waiting for K3s..."
  sleep 5
done

echo "K3s is ready!"
kubectl get nodes

# Install Helm
echo "Installing Helm..."
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version

echo "[3/10] K3s and Helm installed successfully!"

###############################################################################
# 4. Clone Application Code
###############################################################################
echo "[4/10] Setting up application code..."

# Create application directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone repository
if [ ! -d "$APP_DIR/.git" ]; then
  echo "Cloning repository from ${repository_url}..."
  git clone "${repository_url}" .
else
  echo "Application code already exists, updating..."
  git pull
fi

echo "[4/10] Application code ready!"

###############################################################################
# 5. Build Docker Images Locally
###############################################################################
echo "[5/10] Building Docker images..."

cd "$APP_DIR"

SERVICES=(
  "load-generator:8010"
  "product-catalog:8014"
  "checkout:8016"
  "cart:8013"
  "recommendation:8011"
  "currency:8018"
  "shipping:8019"
  "ad:8017"
)

for service_def in "$${SERVICES[@]}"; do
  IFS=':' read -r service port <<< "$service_def"
  
  echo "Building ecommerce-$service..."
  docker build \
    -f coralogix-dataprime-demo/docker/Dockerfile.optimized \
    -t ecommerce-$service:latest \
    --build-arg SERVICE_NAME=$service \
    coralogix-dataprime-demo/
  
  echo "✓ Built ecommerce-$service:latest"
done

echo "[5/10] All Docker images built!"
docker images | grep ecommerce-

###############################################################################
# 6. Create Kubernetes Namespace and Secrets
###############################################################################
echo "[6/10] Creating Kubernetes namespace and secrets..."

# Create namespace
kubectl create namespace ecommerce-demo --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
kubectl create secret generic ecommerce-secrets \
  --from-literal=CX_TOKEN="$${CX_TOKEN}" \
  --from-literal=DB_PASSWORD="$${DB_PASSWORD}" \
  --from-literal=POSTGRES_PASSWORD="$${DB_PASSWORD}" \
  -n ecommerce-demo \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[6/10] Secrets created!"

###############################################################################
# 7. Apply ConfigMap
###############################################################################
echo "[7/10] Applying ConfigMap..."

kubectl apply -f "$APP_DIR/deployment/kubernetes/configmap.yaml"

echo "[7/10] ConfigMap applied!"

###############################################################################
# 8. Deploy PostgreSQL and Redis
###############################################################################
echo "[8/10] Deploying PostgreSQL and Redis..."

# Apply PostgreSQL init script ConfigMap
if [ -f "$APP_DIR/deployment/kubernetes/postgres-init-configmap.yaml" ]; then
  kubectl apply -f "$APP_DIR/deployment/kubernetes/postgres-init-configmap.yaml"
fi

# Deploy PostgreSQL
if [ -f "$APP_DIR/deployment/kubernetes/postgres-statefulset.yaml" ]; then
  kubectl apply -f "$APP_DIR/deployment/kubernetes/postgres-statefulset.yaml"
  echo "Waiting for PostgreSQL to be ready..."
  kubectl wait --for=condition=ready pod -l app=postgresql -n ecommerce-demo --timeout=300s || true
fi

# Deploy Redis
if [ -f "$APP_DIR/deployment/kubernetes/redis-statefulset.yaml" ]; then
  kubectl apply -f "$APP_DIR/deployment/kubernetes/redis-statefulset.yaml"
  echo "Waiting for Redis to be ready..."
  kubectl wait --for=condition=ready pod -l app=redis -n ecommerce-demo --timeout=300s || true
fi

echo "[8/10] Databases deployed!"

###############################################################################
# 9. Install Coralogix OpenTelemetry Collector
###############################################################################
echo "[9/10] Installing Coralogix OpenTelemetry Collector..."

# Add Coralogix Helm repo
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

# Create secret for Coralogix keys
kubectl create secret generic coralogix-keys \
  --from-literal=PRIVATE_KEY="$${CX_TOKEN}" \
  -n ecommerce-demo \
  --dry-run=client -o yaml | kubectl apply -f -

# Install Coralogix OpenTelemetry Collector if values file exists
if [ -f "$APP_DIR/deployment/kubernetes/coralogix-infra-values.yaml" ]; then
  helm upgrade --install coralogix-otel coralogix/otel-integration \
    -f "$APP_DIR/deployment/kubernetes/coralogix-infra-values.yaml" \
    -n ecommerce-demo \
    --wait \
    --timeout 5m
else
  # Use basic configuration
  helm upgrade --install coralogix-otel coralogix/otel-integration \
    --set global.domain="$${CX_ENDPOINT}" \
    --set global.clusterName="ecommerce-k3s" \
    -n ecommerce-demo \
    --wait \
    --timeout 5m
fi

echo "[9/10] Coralogix OpenTelemetry Collector installed!"

###############################################################################
# 10. Deploy E-commerce Microservices
###############################################################################
echo "[10/10] Deploying e-commerce microservices..."

# Apply services first
kubectl apply -f "$APP_DIR/deployment/kubernetes/services.yaml"

# Deploy application deployments
kubectl apply -f "$APP_DIR/deployment/kubernetes/deployments/"

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
sleep 30
kubectl wait --for=condition=available deployment --all -n ecommerce-demo --timeout=300s || true

echo "[10/10] E-commerce microservices deployed!"

# Show deployment status
echo ""
echo "Deployment Status:"
kubectl get pods -n ecommerce-demo
echo ""

###############################################################################
# 11. Configure Firewall (UFW)
###############################################################################
echo "[11/11] Configuring firewall..."

# Install UFW if not already installed
apt-get install -y ufw

# Configure UFW rules
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH, HTTP, HTTPS, NodePorts
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 8010/tcp comment 'Load Generator'
ufw allow 30010:30100/tcp comment 'K3s NodePorts'

# Enable UFW
ufw --force enable

echo "[11/11] Firewall configured!"

###############################################################################
# Finalization
###############################################################################
echo "======================================================================"
echo "Bootstrap Complete!"
echo "======================================================================"
echo "Timestamp: $(date)"
echo "Application Directory: $APP_DIR"
echo "Log File: $LOGFILE"
echo ""
echo "Kubernetes Status:"
kubectl get all -n ecommerce-demo
echo ""
echo "Access your application:"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "  Load Generator: http://$PUBLIC_IP:8010"
echo ""
echo "Generate traffic:"
echo "  curl -X POST http://$PUBLIC_IP:8010/admin/generate-traffic -H 'Content-Type: application/json' -d '{\"duration_seconds\": 60, \"requests_per_minute\": 30}'"
echo ""
echo "To check logs:"
echo "  tail -f $LOGFILE"
echo "  kubectl logs -n ecommerce-demo -l app=load-generator --tail=50"
echo "  kubectl logs -n ecommerce-demo -l app=product-catalog --tail=50"
echo ""
echo "To check OTel Collector:"
echo "  kubectl logs -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=50"
echo ""
echo "View traces in Coralogix:"
echo "  Application: $CX_APPLICATION_NAME"
echo "  https://${coralogix_domain}"
echo "======================================================================"

exit 0
