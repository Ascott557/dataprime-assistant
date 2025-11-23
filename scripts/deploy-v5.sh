#!/bin/bash
set -e

echo "=========================================="
echo "   V5 E-COMMERCE DEPLOYMENT"
echo "=========================================="
echo ""

# Configuration (can be overridden via environment variables)
CLUSTER_HOST=${CLUSTER_HOST:-"54.235.171.176"}
SSH_KEY=${SSH_KEY:-"~/.ssh/ecommerce-platform-key.pem"}
NAMESPACE=${NAMESPACE:-"ecommerce-demo"}
REGISTRY=${REGISTRY:-"local"}

echo "Configuration:"
echo "  Cluster: $CLUSTER_HOST"
echo "  Namespace: $NAMESPACE"
echo "  Registry: $REGISTRY"
echo ""

cd /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo

echo "=========================================="
echo "PHASE 1: Building Docker Images"
echo "=========================================="
echo ""

echo "Building payment-service:v5..."
docker build -t payment-service:v5 -f docker/Dockerfile.payment . || { echo "❌ Payment build failed"; exit 1; }
echo "✓ Payment service built"
echo ""

echo "Building frontend:v5..."
docker build -t frontend:v5 -f docker/Dockerfile.frontend . || { echo "❌ Frontend build failed"; exit 1; }
echo "✓ Frontend built"
echo ""

echo "Rebuilding product-catalog:v5 (with traffic.type attributes)..."
docker build -t product-catalog:v5 -f docker/Dockerfile.optimized --build-arg SERVICE_FILE=product_catalog_service.py . || { echo "❌ Product-catalog build failed"; exit 1; }
echo "✓ Product-catalog rebuilt"
echo ""

echo "Rebuilding load-generator:v5 (with Frontend targets)..."
docker build -t load-generator:v5 -f docker/Dockerfile.optimized --build-arg SERVICE_FILE=load_generator.py . || { echo "❌ Load-generator build failed"; exit 1; }
echo "✓ Load-generator rebuilt"
echo ""

echo "✅ All Docker images built successfully"
echo ""

# Tag and push to registry (if not local)
if [ "$REGISTRY" != "local" ]; then
    echo "=========================================="
    echo "PHASE 2: Pushing to Registry"
    echo "=========================================="
    echo ""
    
    echo "Tagging and pushing images to $REGISTRY..."
    docker tag frontend:v5 $REGISTRY/frontend:v5
    docker push $REGISTRY/frontend:v5
    
    docker tag payment-service:v5 $REGISTRY/payment-service:v5
    docker push $REGISTRY/payment-service:v5
    
    docker tag product-catalog:v5 $REGISTRY/product-catalog:v5
    docker push $REGISTRY/product-catalog:v5
    
    docker tag load-generator:v5 $REGISTRY/load-generator:v5
    docker push $REGISTRY/load-generator:v5
    
    echo "✓ Images pushed to registry"
    echo ""
fi

echo "=========================================="
echo "PHASE 3: Deploying to Kubernetes"
echo "=========================================="
echo ""

# Copy manifests to server
echo "Copying Kubernetes manifests to server..."
scp -i $SSH_KEY /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/redis.yaml ubuntu@$CLUSTER_HOST:/tmp/ || { echo "❌ SCP failed"; exit 1; }
scp -i $SSH_KEY /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/payment.yaml ubuntu@$CLUSTER_HOST:/tmp/ || { echo "❌ SCP failed"; exit 1; }
scp -i $SSH_KEY /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/frontend.yaml ubuntu@$CLUSTER_HOST:/tmp/ || { echo "❌ SCP failed"; exit 1; }
scp -i $SSH_KEY /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/configmap.yaml ubuntu@$CLUSTER_HOST:/tmp/ || { echo "❌ SCP failed"; exit 1; }
echo "✓ Manifests copied"
echo ""

# If not using a registry, need to load images to k3s
if [ "$REGISTRY" == "local" ]; then
    echo "Loading images to k3s (this may take a while)..."
    docker save frontend:v5 | ssh -i $SSH_KEY ubuntu@$CLUSTER_HOST 'sudo k3s ctr images import -'
    docker save payment-service:v5 | ssh -i $SSH_KEY ubuntu@$CLUSTER_HOST 'sudo k3s ctr images import -'
    docker save product-catalog:v5 | ssh -i $SSH_KEY ubuntu@$CLUSTER_HOST 'sudo k3s ctr images import -'
    docker save load-generator:v5 | ssh -i $SSH_KEY ubuntu@$CLUSTER_HOST 'sudo k3s ctr images import -'
    echo "✓ Images loaded to k3s"
    echo ""
fi

# Apply Kubernetes resources
echo "Applying Kubernetes resources..."
ssh -i $SSH_KEY ubuntu@$CLUSTER_HOST << EOF
  echo "Deploying Redis..."
  sudo kubectl apply -f /tmp/redis.yaml
  
  echo "Deploying Payment Service..."
  sudo kubectl apply -f /tmp/payment.yaml
  
  echo "Deploying Frontend..."
  sudo kubectl apply -f /tmp/frontend.yaml
  
  echo "Updating ConfigMap..."
  sudo kubectl apply -f /tmp/configmap.yaml
  
  echo "Restarting updated services..."
  sudo kubectl rollout restart deployment/product-catalog -n $NAMESPACE
  sudo kubectl rollout restart deployment/load-generator -n $NAMESPACE
  
  echo ""
  echo "Waiting for new services to be ready..."
  sudo kubectl rollout status deployment/redis -n $NAMESPACE --timeout=120s
  sudo kubectl rollout status deployment/payment-service -n $NAMESPACE --timeout=120s
  sudo kubectl rollout status deployment/frontend -n $NAMESPACE --timeout=120s
  
  echo "Waiting for restarted services..."
  sudo kubectl rollout status deployment/product-catalog -n $NAMESPACE --timeout=120s
  sudo kubectl rollout status deployment/load-generator -n $NAMESPACE --timeout=120s
  
  echo ""
  echo "=========================================="
  echo "   POD STATUS"
  echo "=========================================="
  sudo kubectl get pods -n $NAMESPACE -o wide
EOF

echo ""
echo "=========================================="
echo "   V5 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""

echo "Services deployed:"
echo "  ✅ Redis (port 6379)"
echo "  ✅ Payment Service (port 8017)"
echo "  ✅ Frontend (port 8018) - NEW ORCHESTRATOR"
echo "  ✅ Product-Catalog (updated with traffic.type)"
echo "  ✅ Load Generator (updated to call Frontend)"
echo ""

echo "Next steps:"
echo "1. Wait 2-3 minutes for services to stabilize"
echo "2. Run validation: ./scripts/validate-v5.sh"
echo "3. Check Coralogix for 6+ services"
echo ""

echo "If issues arise, rollback with:"
echo "  ./scripts/rollback-v5.sh"
echo ""

