#!/bin/bash
# Deploy Telemetry Injector Approach for Scene 9

set -e

echo "======================================================"
echo "Deploying Scene 9: Telemetry Injector Approach"
echo "======================================================"
echo ""
echo "This approach directly injects database spans into"
echo "Coralogix without needing real service orchestration."
echo ""
echo "Benefits:"
echo "  ✓ Guaranteed to work (no service dependencies)"
echo "  ✓ Fast execution (no real queries)"
echo "  ✓ Consistent results every time"
echo "  ✓ Perfect for demos"
echo ""
echo "======================================================"
echo ""

# Copy files to AWS
echo "Step 1: Copying files to AWS..."
scp -i ~/.ssh/dataprime-demo-key.pem \
    coralogix-dataprime-demo/services/api_gateway.py \
    coralogix-dataprime-demo/services/simple_demo_injector.py \
    coralogix-dataprime-demo/app/ecommerce_frontend.py \
    ubuntu@54.235.171.176:/tmp/

echo "✓ Files copied to /tmp/ on AWS"
echo ""

# SSH and deploy
echo "Step 2: SSH to AWS and deploy..."
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'ENDSSH'
set -e

echo "Moving files to project directory..."
sudo mv /tmp/api_gateway.py /opt/dataprime-assistant/coralogix-dataprime-demo/services/
sudo mv /tmp/simple_demo_injector.py /opt/dataprime-assistant/coralogix-dataprime-demo/services/
sudo mv /tmp/ecommerce_frontend.py /opt/dataprime-assistant/coralogix-dataprime-demo/app/
sudo chown ubuntu:ubuntu /opt/dataprime-assistant/coralogix-dataprime-demo/services/*.py
sudo chown ubuntu:ubuntu /opt/dataprime-assistant/coralogix-dataprime-demo/app/*.py

cd /opt/dataprime-assistant/coralogix-dataprime-demo

echo ""
echo "Building Docker image..."
sudo docker build -t ecommerce-demo:latest . 2>&1 | tail -n 20

echo ""
echo "Importing to K3s..."
sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -

echo ""
echo "Tagging images..."
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-frontend:latest

echo ""
echo "Restarting deployments..."
sudo kubectl rollout restart deployment api-gateway -n dataprime-demo
sudo kubectl rollout restart deployment frontend -n dataprime-demo

echo ""
echo "Waiting for rollout..."
sudo kubectl rollout status deployment api-gateway -n dataprime-demo --timeout=120s
sudo kubectl rollout status deployment frontend -n dataprime-demo --timeout=120s

echo ""
echo "======================================================"
echo "✅ Deployment Complete!"
echo "======================================================"
echo ""
echo "Pod Status:"
sudo kubectl get pods -n dataprime-demo | grep -E 'NAME|api-gateway|frontend'

echo ""
echo "======================================================"
echo "How to Test"
echo "======================================================"
echo ""
echo "1. Navigate to: https://54.235.171.176:30443/"
echo ""
echo "2. Click: '🔥 Simulate Database Issues (Scene 9)'"
echo ""
echo "3. Wait 10-15 seconds for telemetry to propagate"
echo ""
echo "4. Check Coralogix:"
echo "   • Navigate: APM → Database Monitoring → productcatalog"
echo "   • Time Range: Last 5 minutes"
echo ""
echo "5. You should see:"
echo "   • Calling Services: 3 (product, order, inventory)"
echo "   • Query Duration P95: ~2800ms"
echo "   • 43 database query spans"
echo "   • ~8% failure rate"
echo ""
echo "======================================================"
ENDSSH

echo ""
echo "✓ Deployment successful!"
echo ""
echo "Next: Test the frontend button and check Coralogix"
echo ""

