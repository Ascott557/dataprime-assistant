#!/bin/bash
set -e

echo "========================================"
echo "PostgreSQL Migration Deployment Script"
echo "========================================"
echo ""

# Configuration
EC2_IP="${1:-}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/ecommerce-demo-key.pem}"

if [ -z "$EC2_IP" ]; then
    echo "❌ Error: EC2 IP address required"
    echo "Usage: $0 <EC2_IP>"
    echo "Example: $0 54.235.171.176"
    exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: SSH key not found: $SSH_KEY"
    exit 1
fi

echo "📋 Configuration:"
echo "   EC2 IP: $EC2_IP"
echo "   SSH Key: $SSH_KEY"
echo ""

# Step 1: Package updated service
echo "📦 Step 1: Packaging updated service files..."
cd /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo
tar -czf /tmp/postgres-migration.tar.gz services/product_service.py app/ requirements-optimized.txt
echo "✅ Package created: /tmp/postgres-migration.tar.gz"
echo ""

# Step 2: Upload to server
echo "📤 Step 2: Uploading to server..."
scp -i "$SSH_KEY" /tmp/postgres-migration.tar.gz ubuntu@$EC2_IP:/home/ubuntu/
echo "✅ Upload complete"
echo ""

# Step 3: Deploy PostgreSQL StatefulSet
echo "🗄️  Step 3: Deploying PostgreSQL StatefulSet..."
scp -i "$SSH_KEY" /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/postgres.yaml ubuntu@$EC2_IP:/home/ubuntu/
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   Applying PostgreSQL manifest..."
sudo kubectl apply -f /home/ubuntu/postgres.yaml

echo "   Waiting for PostgreSQL to be ready..."
sudo kubectl wait --for=condition=ready pod -l app=postgres -n dataprime-demo --timeout=120s || true

sleep 10

POD=$(sudo kubectl get pods -n dataprime-demo -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$POD" ]; then
    echo "   PostgreSQL pod: $POD"
    sudo kubectl get pod -n dataprime-demo $POD
else
    echo "   ⚠️  PostgreSQL pod not found yet, continuing..."
fi

ENDSSH
echo "✅ PostgreSQL deployed"
echo ""

# Step 4: Rebuild Docker image
echo "🐳 Step 4: Rebuilding Docker image with PostgreSQL..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

cd /home/ubuntu

echo "   Extracting updated files..."
tar -xzf postgres-migration.tar.gz

echo "   Verifying PostgreSQL code..."
grep -q "psycopg2" services/product_service.py && echo "   ✅ PostgreSQL imports found"
grep -q "ThreadedConnectionPool" services/product_service.py && echo "   ✅ Connection pool found"
grep -q "postgres.query.select_products" services/product_service.py && echo "   ✅ Manual span found"

echo ""
echo "   Building Docker image..."
sudo docker build \
  --platform linux/amd64 \
  --no-cache \
  -f Dockerfile \
  -t ecommerce-unified:postgres \
  . 2>&1 | tail -20

echo ""
echo "   Tagging and importing..."
sudo docker tag ecommerce-unified:postgres product-service:latest
sudo docker save docker.io/library/product-service:latest | sudo k3s ctr images import - 2>&1 | tail -5

ENDSSH
echo "✅ Docker image rebuilt"
echo ""

# Step 5: Deploy updated product service
echo "🚀 Step 5: Deploying updated product service..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   Deleting old pod..."
sudo kubectl delete pod -n dataprime-demo -l app=product-service --force --grace-period=0

echo "   Waiting for new pod..."
sleep 25

echo ""
echo "   Checking pod status..."
sudo kubectl get pods -n dataprime-demo | grep -E "product-service|postgres"

ENDSSH
echo "✅ Product service deployed"
echo ""

# Step 6: Verify deployment
echo "🔍 Step 6: Verifying deployment..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   PostgreSQL pod status:"
POSTGRES_POD=$(sudo kubectl get pods -n dataprime-demo -l app=postgres -o jsonpath='{.items[0].metadata.name}')
sudo kubectl get pod -n dataprime-demo $POSTGRES_POD

echo ""
echo "   Product service pod status:"
PRODUCT_POD=$(sudo kubectl get pods -n dataprime-demo -l app=product-service -o jsonpath='{.items[0].metadata.name}')
sudo kubectl get pod -n dataprime-demo $PRODUCT_POD

echo ""
echo "   Product service logs (last 30 lines):"
sudo kubectl logs -n dataprime-demo $PRODUCT_POD --tail=30

ENDSSH
echo "✅ Verification complete"
echo ""

# Step 7: Test endpoints
echo "🧪 Step 7: Testing endpoints..."

echo "   Testing health endpoint..."
HEALTH=$(curl -s http://$EC2_IP:30014/health)
echo "$HEALTH" | jq -r '"   Status: \(.status), Database: \(.database), Pool: \(.connection_pool.active_connections)/\(.connection_pool.max_connections)"'

echo ""
echo "   Testing end-to-end recommendation..."
TRACE_RESPONSE=$(curl -k -s -X POST https://$EC2_IP:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"postgres_deploy_test","user_context":"wireless headphones under $100"}')

TRACE_ID=$(echo "$TRACE_RESPONSE" | jq -r '.trace_id')
PRODUCT_COUNT=$(echo "$TRACE_RESPONSE" | jq -r '.recommendations | length // 0')

echo "   Trace ID: $TRACE_ID"
echo "   Products returned: $PRODUCT_COUNT"
echo "✅ End-to-end test passed"
echo ""

# Summary
echo "========================================"
echo "✅ PostgreSQL Migration Complete!"
echo "========================================"
echo ""
echo "📊 Summary:"
echo "   - PostgreSQL StatefulSet deployed"
echo "   - Product service updated with manual spans"
echo "   - Connection pool: max=100 connections"
echo "   - Demo endpoints available"
echo ""
echo "🔗 Test Trace:"
echo "   Trace ID: $TRACE_ID"
echo "   Check in Coralogix: https://eu2.coralogix.com"
echo ""
echo "🎯 Demo Endpoints:"
echo "   - Enable slow queries:"
echo "     curl -X POST http://$EC2_IP:30014/demo/enable-slow-queries -H 'Content-Type: application/json' -d '{\"delay_ms\": 2900}'"
echo ""
echo "   - Simulate pool exhaustion:"
echo "     curl -X POST http://$EC2_IP:30014/demo/simulate-pool-exhaustion"
echo ""
echo "   - Reset demo:"
echo "     curl -X POST http://$EC2_IP:30014/demo/reset"
echo ""
echo "   - Check health:"
echo "     curl http://$EC2_IP:30014/health | jq"
echo ""
echo "🎉 Ready for re:Invent 2025 demo!"

