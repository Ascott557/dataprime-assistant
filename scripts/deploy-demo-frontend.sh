#!/bin/bash
set -e

echo "======================================================================"
echo "🎯 Deploying Demo Frontend for Database Monitoring"
echo "======================================================================"
echo ""

EC2_IP="54.235.171.176"
SSH_KEY="$HOME/.ssh/ecommerce-demo-key.pem"

echo "Step 1: Updating AWS Security Group (Terraform)..."
cd infrastructure/terraform
terraform apply -auto-approve -target=module.security.aws_security_group.main
echo "✅ Security group updated"
echo ""

echo "Step 2: Uploading frontend code to EC2..."
cd ../..
scp -i "$SSH_KEY" coralogix-dataprime-demo/services/demo_frontend.py ubuntu@${EC2_IP}:~/services/
echo "✅ Frontend code uploaded"
echo ""

echo "Step 3: Deploying frontend to K3s..."
ssh -i "$SSH_KEY" ubuntu@${EC2_IP} << 'EOF'
# Apply service first
sudo kubectl apply -f deployment/kubernetes/services.yaml -n dataprime-demo

# Apply frontend deployment
sudo kubectl apply -f deployment/kubernetes/deployments/demo-frontend.yaml -n dataprime-demo

# Wait for pod to be ready
echo "Waiting for frontend pod to be ready..."
sudo kubectl wait --for=condition=ready pod -l app=demo-frontend -n dataprime-demo --timeout=60s

# Check status
sudo kubectl get pods -l app=demo-frontend -n dataprime-demo
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "======================================================================"
echo "🎯 Demo Frontend Ready!"
echo "======================================================================"
echo ""
echo "Access the demo at:"
echo "  http://${EC2_IP}:30017"
echo ""
echo "This frontend provides buttons to trigger:"
echo "  • Inventory operations (check stock, reserve)"
echo "  • Order operations (popular products, create order)"
echo "  • Demo scenarios (load generation, slow queries)"
echo ""
echo "Each button click will:"
echo "  1. Create proper trace context"
echo "  2. Call services with trace propagation"
echo "  3. Generate database spans with connection pool metrics"
echo "  4. Show trace ID for verification in Coralogix"
echo ""
echo "======================================================================"

