#!/bin/bash
#
# Complete Profiling Setup - Run this after Docker build completes
#

set -e

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Complete Profiling Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will:"
echo "  1. Import Docker image to K3s (~10-15 seconds)"
echo "  2. Tag images for services"
echo "  3. Restart deployments"
echo "  4. Verify pods are running"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE'
set -e

echo "Step 1/4: Importing image to K3s..."
echo "         (This takes 10-15 seconds, please wait)"
cd /opt/dataprime-assistant/coralogix-dataprime-demo

timeout 30s sudo docker save ecommerce-demo:latest | sudo k3s ctr images import - > /dev/null 2>&1 || true

echo "✅ Image imported"
echo ""

echo "Step 2/4: Tagging images for services..."
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest 2>/dev/null || true
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-frontend:latest 2>/dev/null || true
echo "✅ Images tagged"
echo ""

echo "Step 3/4: Restarting deployments..."
sudo kubectl delete pods --field-selector status.phase=Failed -n dataprime-demo > /dev/null 2>&1 || true
sudo kubectl rollout restart deployment product-service -n dataprime-demo 2>/dev/null || echo "  (product-service deployment not found, skipping)"
sudo kubectl rollout restart deployment order-service -n dataprime-demo 2>/dev/null || echo "  (order-service deployment not found, skipping)"
sudo kubectl rollout restart deployment inventory-service -n dataprime-demo 2>/dev/null || echo "  (inventory-service deployment not found, skipping)"

echo ""
echo "Waiting 30 seconds for pods to start..."
sleep 30

echo ""
echo "Step 4/4: Verifying pod status..."
echo ""
sudo kubectl get pods -n dataprime-demo | grep -E "NAME|product-service|order-service|inventory-service|profiler" | head -10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
EOFREMOTE

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ Setup Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 Next Steps:"
    echo ""
    echo "1. Generate profiling data:"
    echo "   ./run-scene9.5-demo.sh"
    echo ""
    echo "2. Wait 1-2 minutes, then check Coralogix:"
    echo "   APM → Continuous Profiling → product-service"
    echo ""
    echo "3. Look for:"
    echo "   • Flame graph showing search_products_unindexed() at 99.2% CPU"
    echo "   • Query duration ~2900ms"
    echo ""
else
    echo "  ❌ Setup encountered an error"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Check the logs above for details."
    echo ""
fi

