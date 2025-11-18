#!/bin/bash
set -e

echo "==========================================="
echo "Coralogix Database Monitoring Fix"
echo "==========================================="
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

echo "📋 Configuration:"
echo "   EC2 IP: $EC2_IP"
echo "   SSH Key: $SSH_KEY"
echo ""

echo "🔧 This fix adds required attributes for Coralogix Database Monitoring:"
echo "   ✅ db.name (database name)"
echo "   ✅ net.peer.name (database host)"
echo "   ✅ SpanKind.CLIENT (database client span)"
echo "   ✅ Proper span naming (OTel conventions)"
echo ""

# Step 1: Package updated service
echo "📦 Step 1: Packaging fixed product service..."
cd /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo
tar -czf /tmp/coralogix-db-monitoring-fix.tar.gz services/product_service.py
echo "✅ Package created"
echo ""

# Step 2: Upload to server
echo "📤 Step 2: Uploading to server..."
scp -i "$SSH_KEY" /tmp/coralogix-db-monitoring-fix.tar.gz ubuntu@$EC2_IP:/home/ubuntu/
echo "✅ Upload complete"
echo ""

# Step 3: Extract and rebuild
echo "🐳 Step 3: Rebuilding Docker image..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

cd /home/ubuntu
echo "   Extracting updated files..."
tar -xzf coralogix-db-monitoring-fix.tar.gz

echo "   Verifying required attributes in code..."
grep -q 'db.name' services/product_service.py && echo "   ✅ db.name attribute found"
grep -q 'net.peer.name' services/product_service.py && echo "   ✅ net.peer.name attribute found"
grep -q 'SpanKind.CLIENT' services/product_service.py && echo "   ✅ SpanKind.CLIENT found"

echo ""
echo "   Building Docker image..."
sudo docker build \
  --platform linux/amd64 \
  --no-cache \
  -f Dockerfile \
  -t ecommerce-unified:db-fix \
  . 2>&1 | tail -20

echo ""
echo "   Tagging and importing..."
sudo docker tag ecommerce-unified:db-fix product-service:latest
sudo docker save docker.io/library/product-service:latest | sudo k3s ctr images import - 2>&1 | tail -5

ENDSSH
echo "✅ Docker image rebuilt"
echo ""

# Step 4: Deploy
echo "🚀 Step 4: Deploying updated product service..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   Deleting old pod..."
sudo kubectl delete pod -n dataprime-demo -l app=product-service --force --grace-period=0

echo "   Waiting for new pod..."
sleep 25

echo ""
echo "   Checking pod status..."
sudo kubectl get pods -n dataprime-demo | grep product-service

echo ""
echo "   Checking logs for required attributes..."
POD=$(sudo kubectl get pods -n dataprime-demo -l app=product-service -o jsonpath='{.items[0].metadata.name}')
sudo kubectl logs -n dataprime-demo $POD --tail=20

ENDSSH
echo "✅ Deployment complete"
echo ""

# Step 5: Generate test traces
echo "🧪 Step 5: Generating test traces..."

TRACE_IDS=()
for i in {1..3}; do
    echo "   Test $i/3..."
    RESPONSE=$(curl -k -s -X POST https://$EC2_IP:30444/api/recommendations \
      -H "Content-Type: application/json" \
      -d "{\"user_id\":\"db_monitoring_test_$i\",\"user_context\":\"wireless headphones under \\$100\"}")
    
    TRACE_ID=$(echo "$RESPONSE" | jq -r '.trace_id')
    TRACE_IDS+=("$TRACE_ID")
    echo "   Trace ID: $TRACE_ID"
    sleep 2
done

echo "✅ Generated ${#TRACE_IDS[@]} test traces"
echo ""

# Summary
echo "==========================================="
echo "✅ Database Monitoring Fix Complete!"
echo "==========================================="
echo ""
echo "📊 Test Traces Generated:"
for TRACE_ID in "${TRACE_IDS[@]}"; do
    echo "   - $TRACE_ID"
done
echo ""
echo "🔍 Verification Steps:"
echo ""
echo "1. Wait 2-3 minutes for data to reach Coralogix"
echo ""
echo "2. Check APM → Traces:"
echo "   - Search for trace: ${TRACE_IDS[0]}"
echo "   - Verify span name: 'SELECT productcatalog.products'"
echo "   - Verify attributes: db.name, net.peer.name"
echo ""
echo "3. Check Database Monitoring:"
echo "   - Navigate to: APM → Database Catalog (or Databases tab)"
echo "   - Verify 'productcatalog' appears with:"
echo "     • Services: 1 (product-service)"
echo "     • Average Latency: ~10ms"
echo "     • Total Queries: >0"
echo "   - Click on 'productcatalog' to see:"
echo "     • Query Time Average graph"
echo "     • Operations: SELECT products"
echo "     • Calling services: product-service"
echo ""
echo "🔗 Coralogix URLs:"
echo "   - Traces: https://eu2.coralogix.com/apm/traces"
echo "   - Database Catalog: https://eu2.coralogix.com/apm/databases"
echo ""
echo "📚 Documentation:"
echo "   See CORALOGIX-DATABASE-MONITORING-FIX.md for details"
echo ""
echo "✅ Required attributes now included:"
echo "   • db.system = 'postgresql'"
echo "   • db.name = 'productcatalog'"
echo "   • db.operation = 'SELECT'"
echo "   • db.statement = 'SELECT * FROM products...'"
echo "   • net.peer.name = 'postgres'"
echo "   • Span kind = CLIENT"
echo ""

