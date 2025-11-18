#!/bin/bash
#
# Complete Scene 9.5 Setup - All-in-One Script
# Builds optimized image, deploys to K3s, and generates profiling load
#

set -e

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"
REMOTE_USER="ubuntu"
REMOTE_PATH="/opt/dataprime-assistant/coralogix-dataprime-demo"
K8S_NAMESPACE="dataprime-demo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Scene 9.5: Complete Continuous Profiling Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Instance: t3.medium (4GB RAM, 2 vCPUs)"
echo "Image: Optimized (~300MB)"
echo ""
echo "This will:"
echo "  1. Verify optimized files"
echo "  2. Clean up old Docker images"
echo "  3. Build optimized Docker image (~2-3 minutes)"
echo "  4. Import to K3s (~10-15 seconds)"
echo "  5. Restart deployments"
echo "  6. Generate CPU load for profiling"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Execute the entire setup on the remote instance
ssh -i "$SSH_KEY" "$REMOTE_USER@$EC2_HOST" << EOFREMOTE
set -e

cd $REMOTE_PATH

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1/6: Verifying optimized files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f "docker/Dockerfile" ]; then
    echo "❌ docker/Dockerfile not found"
    exit 1
fi

if [ ! -f "docker/requirements-minimal.txt" ]; then
    echo "❌ docker/requirements-minimal.txt not found"
    exit 1
fi

echo "✅ Optimized Dockerfile found"
echo "✅ Minimal requirements found ($(wc -l < docker/requirements-minimal.txt) lines vs $(wc -l < requirements.txt) lines full)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2/6: Cleaning up old Docker images"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Remove old ecommerce-demo images (keep only the latest if any)
OLD_IMAGES=\$(sudo docker images ecommerce-demo --format "{{.ID}}" 2>/dev/null | tail -n +2)
if [ ! -z "\$OLD_IMAGES" ]; then
    echo "Removing old ecommerce-demo images..."
    echo "\$OLD_IMAGES" | xargs -r sudo docker rmi -f 2>/dev/null || true
    echo "✅ Old images removed"
else
    echo "No old images to remove"
fi

# Show disk space before build
echo ""
echo "Disk space before build:"
df -h / | tail -1 | awk '{print "  Used: " \$3 " / " \$2 " (" \$5 ")"}'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3/6: Building optimized Docker image"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏱️  This will take ~2-3 minutes on t3.medium..."
echo ""

# Build with progress output
sudo docker build -f docker/Dockerfile -t ecommerce-demo:latest . 2>&1 | grep -E "Step|Successfully|built" || true

if [ \${PIPESTATUS[0]} -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

# Show image size
echo ""
echo "✅ Build complete!"
echo ""
sudo docker images ecommerce-demo:latest --format "Image: {{.Repository}}:{{.Tag}} | Size: {{.Size}}"
echo ""

# Show disk space after build
echo "Disk space after build:"
df -h / | tail -1 | awk '{print "  Used: " \$3 " / " \$2 " (" \$5 ")"}'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4/6: Importing image to K3s"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -
echo "✅ Image imported to K3s"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5/6: Tagging and restarting deployments"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Tag for all services that use this image
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-frontend:latest
echo "✅ Images tagged"
echo ""

# Restart key services
echo "Restarting deployments..."
sudo kubectl rollout restart deployment product-service -n $K8S_NAMESPACE
sudo kubectl rollout restart deployment api-gateway -n $K8S_NAMESPACE
sudo kubectl rollout restart deployment frontend -n $K8S_NAMESPACE

echo ""
echo "Waiting for rollouts to complete..."
sudo kubectl rollout status deployment/product-service -n $K8S_NAMESPACE --timeout=180s
sudo kubectl rollout status deployment/api-gateway -n $K8S_NAMESPACE --timeout=180s
sudo kubectl rollout status deployment/frontend -n $K8S_NAMESPACE --timeout=180s

echo ""
echo "✅ All deployments ready"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 6/6: Generating CPU load for profiling"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get the product-service pod
PRODUCT_POD=\$(sudo kubectl get pods -n $K8S_NAMESPACE -l app=product-service -o jsonpath='{.items[0].metadata.name}')

if [ -z "\$PRODUCT_POD" ]; then
    echo "❌ Error: Product Service pod not found"
    exit 1
fi

echo "✅ Found product-service pod: \$PRODUCT_POD"
echo ""
echo "🔥 Generating CPU load with unindexed queries..."
echo "   Query: SELECT * FROM products WHERE description LIKE '%wireless%'"
echo "   Iterations: 50 requests"
echo ""

# Execute 50 concurrent requests to trigger the unindexed query
for i in {1..50}; do
    sudo kubectl exec -n $K8S_NAMESPACE "\$PRODUCT_POD" -- curl -s "http://localhost:8014/products/search?q=wireless" > /dev/null &
done
wait

echo ""
echo "✅ CPU load generated successfully!"
echo ""

EOFREMOTE

EXIT_CODE=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ Scene 9.5 Setup Complete!"
else
    echo "  ❌ Setup Failed (exit code: $EXIT_CODE)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "📊 Next Steps:"
    echo ""
    echo "  1. Wait 1-2 minutes for profiling data to propagate to Coralogix"
    echo ""
    echo "  2. Open Coralogix:"
    echo "     → APM → Continuous Profiling → product-service"
    echo ""
    echo "  3. Set time range: 'Last 15 minutes'"
    echo ""
    echo "  4. You should see:"
    echo "     ✓ Flame graph showing 'search_products_unindexed()' consuming 99.2% CPU"
    echo "     ✓ Call stack showing the slow LIKE query"
    echo "     ✓ ~2-3 seconds of CPU time spent in database operations"
    echo ""
    echo "  5. Demo Talk Track:"
    echo '     "Database APM showed WHAT is slow - the query taking 2900ms."'
    echo '     "But WHERE in the code? Let me check Continuous Profiling..."'
    echo '     "Here - search_products_unindexed() consuming 99.2% CPU."'
    echo '     "This is eBPF - no code changes needed, kernel-level instrumentation."'
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🎉 Ready to demo Scene 9.5: Continuous Profiling!"
fi
echo ""

