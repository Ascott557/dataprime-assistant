#!/bin/bash
# Build Docker images for K8s deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==============================================="
echo "Building Docker images for E-commerce Demo"
echo "==============================================="

cd "$PROJECT_ROOT"

# Build single base image
echo "Building base image from coralogix-dataprime-demo..."
docker build -f deployment/kubernetes/Dockerfile \
    -t dataprime-base:latest \
    coralogix-dataprime-demo/

# Tag for each service
echo "Tagging images for each service..."
for service in api-gateway recommendation-ai product-service validation-service storage-service frontend; do
  echo "  - dataprime-$service:latest"
  docker tag dataprime-base:latest dataprime-$service:latest
done

echo ""
echo "✅ Docker images built successfully!"
echo ""
echo "Images created:"
docker images | grep dataprime | head -7

echo ""
echo "To load these images into K3s, run:"
echo "  sudo docker save dataprime-base:latest | sudo k3s ctr images import -"
echo ""
echo "Or use the deploy-k3s.sh script for automatic deployment."


