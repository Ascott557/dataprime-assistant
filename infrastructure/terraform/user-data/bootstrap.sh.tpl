#!/bin/bash
###############################################################################
# E-commerce Recommendation System - EC2 Bootstrap Script (K3s)
# 
# This script:
# 1. Updates system and installs dependencies
# 2. Installs K3s and Helm
# 3. Clones application code
# 4. Creates Kubernetes secrets
# 5. Deploys PostgreSQL
# 6. Installs Coralogix OpenTelemetry Collector
# 7. Deploys application services
# 8. Sets up firewall rules
# 9. Configures health check monitoring
#
# All output is logged to /var/log/ecommerce-bootstrap.log
###############################################################################

set -euo pipefail

# Logging setup
LOGFILE="/var/log/ecommerce-bootstrap.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "======================================================================"
echo "E-commerce Recommendation System Bootstrap - Started at $(date)"
echo "======================================================================"

# Environment variables from Terraform
export CX_TOKEN="${coralogix_token}"
export CX_DOMAIN="${coralogix_domain}"
export CX_APPLICATION_NAME="${coralogix_app_name}"
export CX_SUBSYSTEM_NAME="${coralogix_subsystem}"
export OPENAI_API_KEY="${openai_api_key}"
export CX_RUM_PUBLIC_KEY="${cx_rum_public_key}"
export DB_PASSWORD="${db_password}"
export PROJECT_NAME="${project_name}"
export ENVIRONMENT="${environment}"

# Application directory
APP_DIR="/opt/dataprime-assistant"
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

###############################################################################
# 1. System Update and Dependencies
###############################################################################
echo "[1/9] Updating system packages..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

echo "[1/9] Installing essential packages..."
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

echo "[1/9] System dependencies installed!"

###############################################################################
# 2. Install K3s and Helm
###############################################################################
echo "[2/9] Installing K3s..."

# Install K3s
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644 \
  --disable traefik \
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

echo "[2/9] K3s and Helm installed successfully!"

###############################################################################
# 3. Clone Application Code
###############################################################################
echo "[3/9] Setting up application code..."

# Create application directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone repository (or use pre-uploaded code)
if [ ! -d "$APP_DIR/.git" ]; then
  echo "Cloning repository from ${repository_url}..."
  git clone "${repository_url}" .
else
  echo "Application code already exists, updating..."
  git pull
fi

echo "[3/9] Application code ready!"

###############################################################################
# 4. Create Kubernetes Namespace and Secrets
###############################################################################
echo "[4/9] Creating Kubernetes namespace and secrets..."

# Create namespace
kubectl create namespace dataprime-demo --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
kubectl create secret generic dataprime-secrets \
  --from-literal=OPENAI_API_KEY="$${OPENAI_API_KEY}" \
  --from-literal=CX_TOKEN="$${CX_TOKEN}" \
  --from-literal=DB_PASSWORD="$${DB_PASSWORD}" \
  --from-literal=CX_RUM_PUBLIC_KEY="$${CX_RUM_PUBLIC_KEY}" \
  -n dataprime-demo \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[4/9] Secrets created!"

###############################################################################
# 5. Apply ConfigMap
###############################################################################
echo "[5/9] Applying ConfigMap..."

kubectl apply -f "$APP_DIR/deployment/kubernetes/configmap.yaml"

echo "[5/9] ConfigMap applied!"

###############################################################################
# 6. Deploy PostgreSQL
###############################################################################
echo "[6/9] Deploying PostgreSQL..."

kubectl apply -f "$APP_DIR/deployment/kubernetes/postgres-init-configmap.yaml"
kubectl apply -f "$APP_DIR/deployment/kubernetes/postgres-statefulset.yaml"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n dataprime-demo --timeout=300s || true

echo "[6/9] PostgreSQL deployed!"

###############################################################################
# 7. Install Coralogix OpenTelemetry Collector
###############################################################################
echo "[7/9] Installing Coralogix OpenTelemetry Collector..."

# Add Coralogix Helm repo
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

# Create secret for Coralogix keys (used by Helm chart)
kubectl create secret generic coralogix-keys \
  --from-literal=PRIVATE_KEY="$${CX_TOKEN}" \
  -n dataprime-demo \
  --dry-run=client -o yaml | kubectl apply -f -

# Install Coralogix OpenTelemetry Collector
helm upgrade --install coralogix-otel coralogix/otel-integration \
  -f "$APP_DIR/deployment/kubernetes/coralogix-infra-values.yaml" \
  -n dataprime-demo \
  --wait \
  --timeout 5m

echo "[7/9] Coralogix OpenTelemetry Collector installed!"

###############################################################################
# 8. Deploy Application Services
###############################################################################
echo "[8/9] Deploying application services..."

# Apply services first
kubectl apply -f "$APP_DIR/deployment/kubernetes/services.yaml"

# Deploy application deployments
kubectl apply -f "$APP_DIR/deployment/kubernetes/deployments/"

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available deployment -l service -n dataprime-demo --timeout=300s || true

echo "[8/9] Application services deployed!"

# Show deployment status
echo ""
echo "Deployment Status:"
kubectl get pods -n dataprime-demo
echo ""

###############################################################################
# 9. Configure Firewall (UFW)
###############################################################################
echo "[9/9] Configuring firewall..."

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
ufw allow 30010/tcp comment 'API Gateway NodePort'
ufw allow 30020/tcp comment 'Frontend NodePort'

# Enable UFW
ufw --force enable

echo "[9/9] Firewall configured!"

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
kubectl get all -n dataprime-demo
echo ""
echo "Access your application at:"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "  Frontend:    http://$PUBLIC_IP:30020"
echo "  API Gateway: http://$PUBLIC_IP:30010"
echo ""
echo "To check logs:"
echo "  tail -f $LOGFILE"
echo "  kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50"
echo "  kubectl logs -n dataprime-demo -l app=product-service --tail=50"
echo ""
echo "To check OTel Collector:"
echo "  kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=50"
echo "======================================================================"

exit 0
