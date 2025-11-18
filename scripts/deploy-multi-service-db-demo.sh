#!/bin/bash
set -e

echo "==========================================="
echo "Multi-Service Database Load Demo Deployment"
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

echo "🎯 This deployment adds 2 new services to demonstrate:"
echo "   ✅ Multiple services sharing the same PostgreSQL database"
echo "   ✅ Connection pool exhaustion across services"
echo "   ✅ ALL services visible in Coralogix Database Monitoring"
echo ""

# Step 1: Package the new services
echo "📦 Step 1: Packaging new services..."
cd /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo

tar -czf /tmp/multi-service-db-demo.tar.gz \
    services/inventory_service.py \
    services/order_service.py

echo "✅ Package created"
echo ""

# Step 2: Package K8s manifests
echo "📦 Step 2: Packaging Kubernetes manifests..."
cd /Users/andrescott/dataprime-assistant-1

tar -czf /tmp/k8s-multi-service.tar.gz \
    deployment/kubernetes/deployments/inventory-service.yaml \
    deployment/kubernetes/deployments/order-service.yaml \
    deployment/kubernetes/services.yaml \
    deployment/kubernetes/postgres.yaml

echo "✅ K8s manifests packaged"
echo ""

# Step 3: Upload to server
echo "📤 Step 3: Uploading to server..."
scp -i "$SSH_KEY" /tmp/multi-service-db-demo.tar.gz ubuntu@$EC2_IP:/home/ubuntu/
scp -i "$SSH_KEY" /tmp/k8s-multi-service.tar.gz ubuntu@$EC2_IP:/home/ubuntu/
echo "✅ Upload complete"
echo ""

# Step 4: Extract and rebuild on server
echo "🐳 Step 4: Building Docker images on server..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

cd /home/ubuntu

echo "   Extracting service files..."
tar -xzf multi-service-db-demo.tar.gz

echo "   Extracting K8s manifests..."
tar -xzf k8s-multi-service.tar.gz

echo ""
echo "   Building inventory-service image..."
sudo docker build \
  --platform linux/amd64 \
  --no-cache \
  -f Dockerfile \
  -t ecommerce-unified:inventory-service \
  . 2>&1 | tail -10

sudo docker tag ecommerce-unified:inventory-service inventory-service:latest
sudo docker save docker.io/library/inventory-service:latest | sudo k3s ctr images import - 2>&1 | tail -3

echo ""
echo "   Building order-service image..."
sudo docker build \
  --platform linux/amd64 \
  --no-cache \
  -f Dockerfile \
  -t ecommerce-unified:order-service \
  . 2>&1 | tail -10

sudo docker tag ecommerce-unified:order-service order-service:latest
sudo docker save docker.io/library/order-service:latest | sudo k3s ctr images import - 2>&1 | tail -3

echo ""
echo "✅ Docker images built and imported"

ENDSSH
echo "✅ Docker images ready"
echo ""

# Step 5: Update PostgreSQL with orders table
echo "🗄️ Step 5: Updating PostgreSQL with orders table..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   Applying updated PostgreSQL manifest..."
sudo kubectl apply -f deployment/kubernetes/postgres.yaml

echo "   Waiting for PostgreSQL to be ready..."
sudo kubectl wait --for=condition=ready pod -l app=postgres -n dataprime-demo --timeout=60s || echo "   Still initializing..."

echo "   Checking if orders table needs to be created..."
POD=$(sudo kubectl get pods -n dataprime-demo -l app=postgres -o jsonpath='{.items[0].metadata.name}')

sudo kubectl exec -n dataprime-demo $POD -- psql -U dbadmin -d productcatalog -c "
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_product_id ON orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);

INSERT INTO orders (user_id, product_id, quantity) VALUES 
    ('demo_user_1', 5, 1),
    ('demo_user_2', 6, 2),
    ('demo_user_3', 5, 1),
    ('demo_user_1', 4, 1),
    ('demo_user_4', 6, 1),
    ('demo_user_2', 5, 3),
    ('demo_user_5', 7, 1),
    ('demo_user_3', 8, 2),
    ('demo_user_6', 9, 1),
    ('demo_user_1', 5, 1)
ON CONFLICT DO NOTHING;
" 2>&1 | grep -E "CREATE|INSERT|ERROR" || echo "   Tables initialized"

echo "✅ PostgreSQL updated with orders table"

ENDSSH
echo "✅ Database schema updated"
echo ""

# Step 6: Deploy new services
echo "🚀 Step 6: Deploying new services..."
ssh -i "$SSH_KEY" ubuntu@$EC2_IP << 'ENDSSH'
set -e

echo "   Applying updated services.yaml..."
sudo kubectl apply -f deployment/kubernetes/services.yaml

echo "   Deploying inventory-service..."
sudo kubectl apply -f deployment/kubernetes/deployments/inventory-service.yaml

echo "   Deploying order-service..."
sudo kubectl apply -f deployment/kubernetes/deployments/order-service.yaml

echo "   Waiting for pods to start..."
sleep 20

echo ""
echo "   Checking deployment status..."
sudo kubectl get pods -n dataprime-demo | grep -E "inventory-service|order-service|product-service"

echo ""
echo "   Checking services..."
sudo kubectl get svc -n dataprime-demo | grep -E "inventory-service|order-service|product-service"

ENDSSH
echo "✅ Services deployed"
echo ""

# Step 7: Test endpoints
echo "🧪 Step 7: Testing new endpoints..."

echo "   Test 1: Inventory Service - Check stock for product 5..."
RESPONSE=$(curl -s -k http://$EC2_IP:30015/inventory/check/5 || echo '{"error":"connection failed"}')
echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"

echo ""
echo "   Test 2: Order Service - Get popular products..."
RESPONSE=$(curl -s -k http://$EC2_IP:30016/orders/popular-products?limit=5 || echo '{"error":"connection failed"}')
echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"

echo ""
echo "   Test 3: Product Service - Get products..."
RESPONSE=$(curl -s -k "http://$EC2_IP:30010/products?category=Wireless%20Headphones&price_min=0&price_max=100" || echo '{"error":"connection failed"}')
echo "$RESPONSE" | jq '.products[0].name' 2>/dev/null || echo "$RESPONSE"

echo ""
echo "✅ All endpoints tested"
echo ""

# Summary
echo "==========================================="
echo "✅ Multi-Service Database Demo Deployed!"
echo "==========================================="
echo ""
echo "📊 Services Deployed:"
echo "   1. product-service   → http://$EC2_IP:30010/products"
echo "   2. inventory-service → http://$EC2_IP:30015/inventory/check/<id>"
echo "   3. order-service     → http://$EC2_IP:30016/orders/popular-products"
echo ""
echo "🗄️ All 3 services share the SAME PostgreSQL database pool"
echo "   • Max connections: 100"
echo "   • Current utilization: Check /health endpoints"
echo ""
echo "🧪 Demo Commands:"
echo ""
echo "1. Check stock for product 5:"
echo "   curl http://$EC2_IP:30015/inventory/check/5"
echo ""
echo "2. Reserve stock:"
echo "   curl -X POST http://$EC2_IP:30015/inventory/reserve \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"product_id\":5,\"quantity\":1}'"
echo ""
echo "3. Get popular products:"
echo "   curl http://$EC2_IP:30016/orders/popular-products?limit=5"
echo ""
echo "4. Create an order:"
echo "   curl -X POST http://$EC2_IP:30016/orders/create \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_id\":\"demo_user\",\"product_id\":5,\"quantity\":2}'"
echo ""
echo "5. Get products (existing):"
echo "   curl 'http://$EC2_IP:30010/products?category=Wireless%20Headphones&price_min=0&price_max=100'"
echo ""
echo "🔥 Enable Slow Queries on ALL services:"
echo "   curl -X POST http://$EC2_IP:30015/demo/enable-slow-queries -d '{\"delay_ms\":2900}'"
echo "   curl -X POST http://$EC2_IP:30016/demo/enable-slow-queries -d '{\"delay_ms\":2900}'"
echo "   curl -X POST http://$EC2_IP:30010/demo/enable-slow-queries -d '{\"delay_ms\":2900}'"
echo ""
echo "💥 Simulate Pool Exhaustion (95/100 connections):"
echo "   curl -X POST http://$EC2_IP:30015/demo/simulate-pool-exhaustion"
echo ""
echo "♻️ Reset Demo:"
echo "   curl -X POST http://$EC2_IP:30015/demo/reset"
echo "   curl -X POST http://$EC2_IP:30016/demo/reset"
echo "   curl -X POST http://$EC2_IP:30010/demo/reset"
echo ""
echo "🔍 Verify in Coralogix (wait 2-3 minutes):"
echo "   • APM → Database Catalog → productcatalog"
echo "   • Calling Services dropdown should show:"
echo "     1. product-service ✅"
echo "     2. inventory-service ✅"
echo "     3. order-service ✅"
echo ""
echo "📊 All services use Coralogix Database Monitoring attributes:"
echo "   • db.system = 'postgresql'"
echo "   • db.name = 'productcatalog'"
echo "   • db.operation = 'SELECT' | 'UPDATE' | 'INSERT'"
echo "   • db.statement = full SQL query"
echo "   • net.peer.name = 'postgres'"
echo "   • Span kind = CLIENT"
echo ""
echo "✅ Ready for re:Invent 2025 demo!"
echo ""

