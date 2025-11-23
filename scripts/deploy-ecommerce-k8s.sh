#!/bin/bash
set -e

# E-commerce Platform - Kubernetes Deployment Script

echo "🚀 Deploying E-commerce Platform to Kubernetes"
echo "=============================================="

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check cluster connection
echo "🔍 Checking Kubernetes cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo "Please configure kubectl to connect to your cluster."
    exit 1
fi

echo -e "${GREEN}✅ Connected to Kubernetes cluster${NC}"
echo ""

# Create secret with Coralogix token and DB password
echo "🔐 Creating secrets..."
kubectl create namespace ecommerce-demo --dry-run=client -o yaml | kubectl apply -f -

# Create secret
kubectl create secret generic ecommerce-secrets \
  --from-literal=CX_TOKEN="${CX_TOKEN:-cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6}" \
  --from-literal=DB_PASSWORD="${DB_PASSWORD:-ecommerce_password}" \
  --namespace=ecommerce-demo \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Secrets created${NC}"
echo ""

# Apply namespace
echo "📦 Creating namespace..."
kubectl apply -f deployment/kubernetes/namespace.yaml
echo ""

# Apply ConfigMap
echo "⚙️  Applying ConfigMap..."
kubectl apply -f deployment/kubernetes/configmap.yaml
echo ""

# Deploy PostgreSQL
echo "🗄️  Deploying PostgreSQL..."
if [ -f deployment/kubernetes/postgres-statefulset.yaml ]; then
    kubectl apply -f deployment/kubernetes/postgres-statefulset.yaml
    echo "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgresql -n ecommerce-demo --timeout=120s || true
fi
echo ""

# Deploy Redis
echo "💾 Deploying Redis..."
if [ -f deployment/kubernetes/redis-statefulset.yaml ]; then
    kubectl apply -f deployment/kubernetes/redis-statefulset.yaml
    echo "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n ecommerce-demo --timeout=120s || true
fi
echo ""

# Deploy all services
echo "🚢 Deploying microservices..."
kubectl apply -f deployment/kubernetes/deployments/
echo ""

# Apply services
echo "🌐 Creating Kubernetes services..."
kubectl apply -f deployment/kubernetes/services.yaml
echo ""

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl rollout status deployment/load-generator -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/product-catalog -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/checkout -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/cart -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/recommendation -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/currency -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/shipping -n ecommerce-demo --timeout=180s || true
kubectl rollout status deployment/ad-service -n ecommerce-demo --timeout=180s || true
echo ""

# Check deployment status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Deployment Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
kubectl get pods -n ecommerce-demo
echo ""
kubectl get services -n ecommerce-demo
echo ""

# Show deployment summary
READY_PODS=$(kubectl get pods -n ecommerce-demo --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
TOTAL_PODS=$(kubectl get pods -n ecommerce-demo --no-headers 2>/dev/null | wc -l | tr -d ' ')

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Namespace: ecommerce-demo"
echo "   Ready Pods: $READY_PODS/$TOTAL_PODS"
echo "   Application: ecommerce-platform"
echo "   Coralogix Region: EU2"
echo ""

if [ "$READY_PODS" -eq "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Check pods: kubectl get pods -n ecommerce-demo"
    echo "  2. Check logs: kubectl logs -f deployment/load-generator -n ecommerce-demo"
    echo "  3. Port-forward to test: kubectl port-forward svc/load-generator 8010:8010 -n ecommerce-demo"
    echo "  4. Generate traffic: curl -X POST http://localhost:8010/admin/generate-traffic -H 'Content-Type: application/json' -d '{\"duration_seconds\": 60, \"requests_per_minute\": 30}'"
    echo "  5. Check Coralogix: Application = ecommerce-platform"
else
    echo -e "${YELLOW}⚠️  Some pods are not ready yet. Check status with: kubectl get pods -n ecommerce-demo${NC}"
fi

