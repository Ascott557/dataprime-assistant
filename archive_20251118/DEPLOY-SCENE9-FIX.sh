#!/bin/bash
# Deploy Scene 9 Fix - Multiple Services Calling Database

set -e

echo "======================================================"
echo "Deploying Scene 9 Database APM Fix"
echo "======================================================"
echo ""
echo "Changes:"
echo "  ✓ API Gateway now calls ORDER and INVENTORY services"
echo "  ✓ Slow queries enabled on all 3 services"
echo "  ✓ 43 concurrent queries: 15 product + 15 order + 13 inventory"
echo "  ✓ All 3 services will show in Coralogix 'Calling Services'"
echo ""
echo "======================================================"
echo ""

# Check if we're on the remote server or local
if [ -f "/etc/rancher/k3s/k3s.yaml" ]; then
    echo "✓ Running on AWS instance"
    IS_REMOTE=true
else
    echo "✓ Running locally - will SSH to AWS"
    IS_REMOTE=false
fi

if [ "$IS_REMOTE" = false ]; then
    echo ""
    echo "Step 1: Copy files to AWS instance..."
    scp -i ~/.ssh/dataprime-demo-key.pem \
        coralogix-dataprime-demo/services/api_gateway.py \
        ubuntu@54.235.171.176:/opt/dataprime-assistant/coralogix-dataprime-demo/services/api_gateway.py
    
    echo "✓ Files copied"
    echo ""
    echo "Step 2: SSH to AWS and rebuild..."
    ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'ENDSSH'
    set -e
    cd /opt/dataprime-assistant/coralogix-dataprime-demo
    
    echo ""
    echo "Building Docker image..."
    sudo docker build -t ecommerce-demo:latest . | tail -n 20
    
    echo ""
    echo "Importing to K3s..."
    sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -
    
    echo ""
    echo "Tagging images..."
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest
    
    echo ""
    echo "Restarting deployments..."
    sudo kubectl rollout restart deployment api-gateway -n dataprime-demo
    sudo kubectl rollout restart deployment product-service -n dataprime-demo
    sudo kubectl rollout restart deployment order-service -n dataprime-demo
    sudo kubectl rollout restart deployment inventory-service -n dataprime-demo
    
    echo ""
    echo "Waiting for rollout to complete..."
    sudo kubectl rollout status deployment api-gateway -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment product-service -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment order-service -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment inventory-service -n dataprime-demo --timeout=120s
    
    echo ""
    echo "======================================================"
    echo "Deployment Complete!"
    echo "======================================================"
    echo ""
    echo "Pod Status:"
    sudo kubectl get pods -n dataprime-demo | grep -E 'NAME|product-service|order-service|inventory-service|api-gateway'
    
    echo ""
    echo "======================================================"
    echo "Testing the Demo"
    echo "======================================================"
    echo ""
    echo "Option 1: Via Frontend"
    echo "  1. Navigate to: https://54.235.171.176:30443/"
    echo "  2. Click: '🔥 Simulate Database Issues (Scene 9)'"
    echo ""
    echo "Option 2: Via API"
    echo "  curl -X POST http://api-gateway:8010/api/demo/trigger-database-scenario"
    echo ""
    echo "Option 3: Via kubectl port-forward"
    echo "  kubectl port-forward -n dataprime-demo svc/api-gateway 8010:8010"
    echo "  curl -X POST http://localhost:8010/api/demo/trigger-database-scenario"
    echo ""
    echo "Expected Results in Coralogix Database APM:"
    echo "  - 3 calling services: product-service, order-service, inventory-service"
    echo "  - Query Duration P95: ~2800-2900ms"
    echo "  - Active Queries: 43 concurrent"
    echo "  - Pool Utilization: 95%"
    echo "  - Failure Rate: ~8%"
    echo ""
    echo "======================================================"
ENDSSH
else
    # Running on remote server
    cd /opt/dataprime-assistant/coralogix-dataprime-demo
    
    echo ""
    echo "Building Docker image..."
    sudo docker build -t ecommerce-demo:latest . | tail -n 20
    
    echo ""
    echo "Importing to K3s..."
    sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -
    
    echo ""
    echo "Tagging images..."
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest
    sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest
    
    echo ""
    echo "Restarting deployments..."
    sudo kubectl rollout restart deployment api-gateway -n dataprime-demo
    sudo kubectl rollout restart deployment product-service -n dataprime-demo
    sudo kubectl rollout restart deployment order-service -n dataprime-demo
    sudo kubectl rollout restart deployment inventory-service -n dataprime-demo
    
    echo ""
    echo "Waiting for rollout to complete..."
    sudo kubectl rollout status deployment api-gateway -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment product-service -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment order-service -n dataprime-demo --timeout=120s
    sudo kubectl rollout status deployment inventory-service -n dataprime-demo --timeout=120s
    
    echo ""
    echo "======================================================"
    echo "Deployment Complete!"
    echo "======================================================"
fi

echo ""
echo "✓ Deployment successful!"
echo ""

