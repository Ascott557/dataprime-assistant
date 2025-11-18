#!/bin/bash
#
# Install Coralogix Continuous Profiling (Scene 9.5)
#
# This script installs the Coralogix eBPF profiling agent on your K8s cluster
# following the official documentation:
# https://coralogix.com/docs/user-guides/continuous-profiling/setup/
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"
NAMESPACE="dataprime-demo"
CLUSTER_NAME="dataprime-demo-cluster"
CORALOGIX_DOMAIN="cx498.coralogix.com"  # Update if needed
HELM_VERSION="0.0.231"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔥 Installing Coralogix Continuous Profiling${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}This will install eBPF-based continuous profiling on your K8s cluster${NC}"
echo ""

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Error: SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Get API key from environment variable or prompt
if [ -z "$CORALOGIX_PRIVATE_KEY" ]; then
    read -p "$(echo -e ${YELLOW}Enter your Coralogix Private API Key: ${NC})" PRIVATE_KEY
    echo ""
else
    PRIVATE_KEY="$CORALOGIX_PRIVATE_KEY"
    echo -e "${GREEN}✅ Using API key from environment variable${NC}"
    echo ""
fi

# Validate API key
if [ -z "$PRIVATE_KEY" ]; then
    echo -e "${RED}❌ Error: No API key provided${NC}"
    exit 1
fi

echo -e "${YELLOW}📡 Connecting to AWS EC2 ($EC2_HOST)...${NC}"
echo ""

# Execute installation on remote server
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << ENDSSH
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Add Coralogix Helm Repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual || true
sudo helm repo update

echo ""
echo "✅ Helm repository added"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Create/Update Coralogix Keys Secret"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Delete existing secret if it exists
sudo kubectl delete secret coralogix-keys -n $NAMESPACE --ignore-not-found=true

# Create new secret
sudo kubectl create secret generic coralogix-keys \
  --from-literal=PRIVATE_KEY="$PRIVATE_KEY" \
  -n $NAMESPACE

echo ""
echo "✅ Secret created"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Create Profiling Values File"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat > /tmp/profiling-values.yaml << 'EOF'
opentelemetry-agent:
  enabled: true
  presets:
    profilesCollection:
      enabled: true
  command:
    extraArgs: [ "--feature-gates=service.profilesSupport" ]

coralogix-ebpf-profiler:
  enabled: true
  tolerations:
    - effect: NoSchedule
      operator: Exists
  nodeSelector: {}
EOF

echo "✅ Values file created"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Deploy Continuous Profiling"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# K3s requires KUBECONFIG to be set for Helm
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

sudo --preserve-env=KUBECONFIG helm upgrade --install otel-coralogix-integration coralogix/otel-integration \
  --version=$HELM_VERSION \
  --namespace=$NAMESPACE \
  --create-namespace \
  --set global.domain="$CORALOGIX_DOMAIN" \
  --set global.clusterName="$CLUSTER_NAME" \
  -f /tmp/profiling-values.yaml

echo ""
echo "✅ Profiling deployed"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Verify Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Waiting for profiling pods to start (30 seconds)..."
sleep 30

echo ""
echo "Profiling Pods:"
sudo kubectl get pods -n $NAMESPACE | grep -E "profiler|otel" || echo "No profiling pods found yet"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ENDSSH

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ Continuous Profiling Installed Successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}📊 Next Steps:${NC}"
    echo ""
    echo "  1. Wait 2-3 minutes for profiling data to start flowing"
    echo ""
    echo "  2. Open Coralogix:"
    echo "     → APM → Continuous Profiling"
    echo ""
    echo "  3. You should see profiling data for your services"
    echo ""
    echo "  4. Run the slow query demo to generate flamegraph data:"
    echo "     ./run-scene9.5-demo.sh"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ Installation Failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi

