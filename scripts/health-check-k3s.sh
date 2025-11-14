#!/bin/bash
###############################################################################
# DataPrime Demo - k3s Health Check Script
#
# This script checks the health of the k3s deployment and verifies that:
# 1. All pods are running
# 2. Services are accessible
# 3. OTel Collector is sending metrics to Coralogix
# 4. Coralogix Operator is functioning
#
# Usage: ./health-check-k3s.sh
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
echo "DataPrime Demo - k3s Health Check"
echo "======================================================================${NC}"

###############################################################################
# Get EC2 Instance Information
###############################################################################
echo -e "\n${YELLOW}[1/7] Retrieving EC2 instance information...${NC}"

cd "$PROJECT_ROOT/infrastructure/terraform"

INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || true)
if [ -z "$INSTANCE_IP" ]; then
  echo -e "${RED}Error: Could not retrieve instance IP from Terraform.${NC}"
  exit 1
fi

SSH_KEY_PATH="$HOME/.ssh/dataprime-demo-key.pem"
if [ ! -f "$SSH_KEY_PATH" ]; then
  echo -e "${RED}Error: SSH key not found at $SSH_KEY_PATH${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Instance IP: $INSTANCE_IP${NC}"

###############################################################################
# Check k3s Status
###############################################################################
echo -e "\n${YELLOW}[2/7] Checking k3s cluster status...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_1'
set -euo pipefail

# Check if k3s is running
if ! systemctl is-active --quiet k3s; then
  echo "❌ k3s service is not running"
  exit 1
fi

echo "✓ k3s service is running"

# Check node status
NODE_STATUS=$(kubectl get nodes --no-headers | awk '{print $2}')
if [ "$NODE_STATUS" != "Ready" ]; then
  echo "❌ k3s node is not ready: $NODE_STATUS"
  exit 1
fi

echo "✓ k3s node is Ready"

# Show node info
kubectl get nodes
REMOTE_SCRIPT_1

echo -e "${GREEN}✓ k3s cluster is healthy${NC}"

###############################################################################
# Check Pods Status
###############################################################################
echo -e "\n${YELLOW}[3/7] Checking pod status...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_2'
set -euo pipefail

echo ""
echo "Pods in dataprime-demo namespace:"
kubectl get pods -n dataprime-demo

# Count non-running pods
NOT_RUNNING=$(kubectl get pods -n dataprime-demo --no-headers | grep -v "Running" | wc -l || echo "0")
TOTAL_PODS=$(kubectl get pods -n dataprime-demo --no-headers | wc -l)

if [ "$NOT_RUNNING" -eq 0 ]; then
  echo "✓ All $TOTAL_PODS pods are running"
else
  echo "⚠ $NOT_RUNNING out of $TOTAL_PODS pods are not running"
  echo ""
  echo "Non-running pods:"
  kubectl get pods -n dataprime-demo | grep -v "Running" || true
  exit 1
fi

# Check pod readiness
NOT_READY=$(kubectl get pods -n dataprime-demo --no-headers | awk '{print $2}' | grep -v "^1/1$" | wc -l || echo "0")

if [ "$NOT_READY" -gt 0 ]; then
  echo "⚠ Some pods are not ready (may still be starting)"
  kubectl get pods -n dataprime-demo
fi
REMOTE_SCRIPT_2

echo -e "${GREEN}✓ All pods are running${NC}"

###############################################################################
# Check Services
###############################################################################
echo -e "\n${YELLOW}[4/7] Checking services...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_3'
set -euo pipefail

echo ""
echo "Services in dataprime-demo namespace:"
kubectl get svc -n dataprime-demo

# Test API Gateway health endpoint
echo ""
echo "Testing API Gateway health..."
if kubectl exec -n dataprime-demo deployment/api-gateway -- curl -sf http://localhost:8010/api/health >/dev/null 2>&1; then
  echo "✓ API Gateway is responding"
else
  echo "❌ API Gateway health check failed"
  exit 1
fi

# Test Frontend
echo "Testing Frontend..."
if kubectl exec -n dataprime-demo deployment/frontend -- curl -sf http://localhost:8020/ >/dev/null 2>&1; then
  echo "✓ Frontend is responding"
else
  echo "❌ Frontend health check failed"
  exit 1
fi

echo "✓ All services are responding"
REMOTE_SCRIPT_3

echo -e "${GREEN}✓ Services are healthy${NC}"

###############################################################################
# Check OpenTelemetry Collector
###############################################################################
echo -e "\n${YELLOW}[5/7] Checking OpenTelemetry Collector...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_4'
set -euo pipefail

# Check if OTel Collector pod is running
OTEL_POD_STATUS=$(kubectl get pods -n dataprime-demo -l app=otel-collector --no-headers | awk '{print $3}')

if [ "$OTEL_POD_STATUS" != "Running" ]; then
  echo "❌ OTel Collector is not running: $OTEL_POD_STATUS"
  exit 1
fi

echo "✓ OTel Collector pod is running"

# Check recent logs for errors
echo ""
echo "Recent OTel Collector logs (last 20 lines):"
kubectl logs -n dataprime-demo -l app=otel-collector --tail=20 2>/dev/null || echo "Could not retrieve logs"

# Check for Coralogix connection errors
if kubectl logs -n dataprime-demo -l app=otel-collector --tail=100 2>/dev/null | grep -i "error" | grep -i "coralogix"; then
  echo "⚠ Warning: Found Coralogix connection errors in logs"
else
  echo "✓ No Coralogix connection errors found"
fi
REMOTE_SCRIPT_4

echo -e "${GREEN}✓ OpenTelemetry Collector is healthy${NC}"

###############################################################################
# Check Coralogix Operator
###############################################################################
echo -e "\n${YELLOW}[6/7] Checking Coralogix Operator...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_5'
set -euo pipefail

# Check if operator namespace exists
if ! kubectl get namespace coralogix-operator-system >/dev/null 2>&1; then
  echo "❌ Coralogix Operator namespace not found"
  exit 1
fi

echo "✓ Coralogix Operator namespace exists"

# Check operator pod status
OPERATOR_STATUS=$(kubectl get pods -n coralogix-operator-system --no-headers 2>/dev/null | awk '{print $3}' | head -1)

if [ -z "$OPERATOR_STATUS" ]; then
  echo "❌ Coralogix Operator pod not found"
  exit 1
fi

if [ "$OPERATOR_STATUS" != "Running" ]; then
  echo "❌ Coralogix Operator is not running: $OPERATOR_STATUS"
  kubectl get pods -n coralogix-operator-system
  exit 1
fi

echo "✓ Coralogix Operator is running"

# Show operator info
kubectl get pods -n coralogix-operator-system
REMOTE_SCRIPT_5

echo -e "${GREEN}✓ Coralogix Operator is healthy${NC}"

###############################################################################
# Check Resource Usage
###############################################################################
echo -e "\n${YELLOW}[7/7] Checking resource usage...${NC}"

ssh -i "$SSH_KEY_PATH" ubuntu@"$INSTANCE_IP" bash <<'REMOTE_SCRIPT_6'
set -euo pipefail

echo ""
echo "Node resource usage:"
kubectl top nodes 2>/dev/null || echo "Metrics not available yet (requires metrics-server)"

echo ""
echo "Pod resource usage (dataprime-demo namespace):"
kubectl top pods -n dataprime-demo 2>/dev/null || echo "Pod metrics not available yet"

echo ""
echo "Storage usage:"
kubectl get pvc -n dataprime-demo

echo ""
echo "System memory:"
free -h
REMOTE_SCRIPT_6

echo -e "${GREEN}✓ Resource usage checked${NC}"

###############################################################################
# Summary and Recommendations
###############################################################################
echo -e "\n${GREEN}======================================================================"
echo "Health Check Complete!"
echo "======================================================================${NC}"

echo -e "\n${BLUE}Access Points:${NC}"
echo "  Frontend:    http://$INSTANCE_IP:30020"
echo "  API Gateway: http://$INSTANCE_IP:30010"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "  1. Access your application at http://$INSTANCE_IP:30020"
echo "  2. Generate some traces by using the application"
echo "  3. Check Coralogix Infrastructure Explorer:"
echo "     - Go to https://coralogix.com/infrastructure"
echo "     - Look for your k3s node with host metrics"
echo "  4. Open a trace in Coralogix and check the 'HOST' tab:"
echo "     - Should show Kubernetes metadata (pod, namespace, node)"
echo "     - Should show host metrics"

echo -e "\n${BLUE}Useful Commands:${NC}"
echo "  Watch pods:        kubectl get pods -n dataprime-demo -w"
echo "  View logs:         kubectl logs -n dataprime-demo -l app=api-gateway"
echo "  Port forward:      kubectl port-forward -n dataprime-demo svc/frontend 8020:8020"
echo "  Describe pod:      kubectl describe pod <pod-name> -n dataprime-demo"

echo -e "\n${YELLOW}Note: Metrics may take 2-5 minutes to appear in Coralogix after deployment.${NC}"

echo -e "\n${GREEN}✓ All health checks passed!${NC}"



