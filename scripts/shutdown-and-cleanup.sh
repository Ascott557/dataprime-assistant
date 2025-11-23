#!/usr/bin/env bash
#
# Complete Project Shutdown and Cleanup
# Removes all Kubernetes resources, Docker images, and temporary files
#

set -e

EC2_IP=$1

if [ -z "$EC2_IP" ]; then
    echo "❌ Error: EC2 IP address required"
    echo "Usage: $0 <EC2_IP>"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 Shutting Down and Cleaning Up Project"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Delete Kubernetes namespace and all resources
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 1: Deleting Kubernetes namespace 'dataprime-demo'${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@${EC2_IP} "
    echo 'Deleting namespace dataprime-demo (this will remove all pods, services, deployments)...'
    sudo kubectl delete namespace dataprime-demo --timeout=60s 2>/dev/null || echo 'Namespace already deleted or not found'
    
    echo ''
    echo 'Verifying namespace deletion...'
    sudo kubectl get namespaces | grep dataprime || echo '✅ Namespace deleted successfully'
"

echo ""
echo -e "${GREEN}✅ Kubernetes namespace deleted${NC}"
echo ""
sleep 2

# Step 2: Remove Docker images
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 2: Removing Docker images${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@${EC2_IP} "
    echo 'Listing Docker images to remove...'
    sudo docker images | grep dataprime || echo 'No dataprime images found'
    
    echo ''
    echo 'Removing dataprime Docker images...'
    sudo docker rmi -f \$(sudo docker images | grep dataprime | awk '{print \$3}') 2>/dev/null || echo 'No images to remove'
    
    echo ''
    echo 'Removing K3s containerd images...'
    sudo k3s ctr images ls | grep dataprime || echo 'No K3s images found'
    sudo k3s ctr images rm \$(sudo k3s ctr images ls | grep dataprime | awk '{print \$1}') 2>/dev/null || echo 'No K3s images to remove'
    
    echo ''
    echo 'Running Docker system prune...'
    sudo docker system prune -af --volumes 2>/dev/null || true
"

echo ""
echo -e "${GREEN}✅ Docker images cleaned up${NC}"
echo ""
sleep 2

# Step 3: Clean up temporary files and build artifacts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 3: Cleaning up temporary files${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@${EC2_IP} "
    echo 'Removing temporary build files...'
    rm -f /home/ubuntu/product_service.py
    rm -f /home/ubuntu/database-failure-demo.sh
    rm -rf /home/ubuntu/services 2>/dev/null || true
    rm -rf /home/ubuntu/app 2>/dev/null || true
    
    echo ''
    echo '✅ Temporary files removed'
"

echo ""
echo -e "${GREEN}✅ Temporary files cleaned${NC}"
echo ""

# Step 4: Verify cleanup
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 4: Verifying cleanup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@${EC2_IP} "
    echo '=== Kubernetes Pods ==='
    sudo kubectl get pods --all-namespaces | grep dataprime || echo '✅ No dataprime pods running'
    
    echo ''
    echo '=== Docker Images ==='
    sudo docker images | grep dataprime || echo '✅ No dataprime images found'
    
    echo ''
    echo '=== Docker Containers ==='
    sudo docker ps -a | grep dataprime || echo '✅ No dataprime containers found'
    
    echo ''
    echo '=== K3s Images ==='
    sudo k3s ctr images ls | grep dataprime || echo '✅ No dataprime K3s images found'
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Project Shutdown Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo "  ✅ Kubernetes namespace 'dataprime-demo' deleted"
echo "  ✅ All pods, services, and deployments removed"
echo "  ✅ Docker images cleaned up"
echo "  ✅ K3s container images removed"
echo "  ✅ Temporary files deleted"
echo ""
echo -e "${CYAN}Resources Preserved:${NC}"
echo "  • K3s cluster (still running)"
echo "  • EC2 instance (still running)"
echo "  • Base system images (postgres, nginx, etc.)"
echo ""
echo -e "${CYAN}To completely tear down:${NC}"
echo "  • Terminate the EC2 instance from AWS Console"
echo "  • Or run: aws ec2 terminate-instances --instance-ids <instance-id>"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

