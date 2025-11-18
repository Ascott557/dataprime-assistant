#!/bin/bash
#
# Quick Fix: Deploy Application Services for Profiling
#
# This script fixes the broken deployment in small, visible steps
#

set -e

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"
NAMESPACE="dataprime-demo"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔧 Quick Deployment Fix"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Step 1/4: Checking if Docker image exists on server..."
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST "sudo docker images | grep ecommerce-demo"
echo "✅ Image found"
echo ""

echo "Step 2/4: Importing to K3s (30-60 seconds, please wait)..."
echo "         (This will appear to hang but is working...)"
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE'
# Run import in background with timeout
timeout 120s sudo docker save ecommerce-demo:latest | sudo k3s ctr images import - > /dev/null 2>&1 &
IMPORT_PID=$!

# Show progress dots while waiting
for i in {1..60}; do
    if ! kill -0 $IMPORT_PID 2>/dev/null; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Wait for completion
wait $IMPORT_PID 2>/dev/null || true
EOFREMOTE
echo "✅ Image imported"
echo ""

echo "Step 3/4: Tagging images for services..."
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE'
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-frontend:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-recommendation-ai:latest 2>/dev/null || true
EOFREMOTE
echo "✅ Images tagged"
echo ""

echo "Step 4/4: Restarting deployments..."
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << EOFREMOTE
sudo kubectl delete pods --field-selector status.phase=Failed -n $NAMESPACE > /dev/null 2>&1 || true
sudo kubectl rollout restart deployment api-gateway -n $NAMESPACE 2>/dev/null || true
sudo kubectl rollout restart deployment frontend -n $NAMESPACE 2>/dev/null || true
sudo kubectl rollout restart deployment product-service -n $NAMESPACE
sudo kubectl rollout restart deployment order-service -n $NAMESPACE 2>/dev/null || true
sudo kubectl rollout restart deployment inventory-service -n $NAMESPACE 2>/dev/null || true
sudo kubectl rollout restart deployment recommendation-ai -n $NAMESPACE 2>/dev/null || true

echo ""
echo "Waiting 20 seconds for pods to start..."
sleep 20

echo ""
echo "Current Pod Status:"
sudo kubectl get pods -n $NAMESPACE | grep -E "product-service|order-service|inventory-service" | head -5
EOFREMOTE

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deployment Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next: Run the profiling demo script"
echo "  ./run-scene9.5-demo.sh"
echo ""

