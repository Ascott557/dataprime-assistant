#!/bin/bash
set -e

# E-commerce Platform - Docker Image Build Script
# Builds all microservices with optimized Dockerfile (<1GB per image)

echo "🚀 Building E-commerce Platform Docker Images"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Service definitions
SERVICES=(
  "load-generator:8010"
  "product-catalog:8014"
  "checkout:8016"
  "cart:8013"
  "recommendation:8011"
  "currency:8018"
  "shipping:8019"
  "ad:8017"
)

# Build statistics
TOTAL_SERVICES=${#SERVICES[@]}
SUCCESSFUL_BUILDS=0
FAILED_BUILDS=0
TOTAL_SIZE=0

echo "🔨 Building $TOTAL_SERVICES services..."
echo ""

# Build each service
for service_def in "${SERVICES[@]}"; do
  IFS=':' read -r service port <<< "$service_def"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📦 Building: ecommerce-$service"
  echo "   Port: $port"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Build the image
  if docker build \
    -f coralogix-dataprime-demo/docker/Dockerfile.optimized \
    -t ecommerce-$service:latest \
    --build-arg SERVICE_NAME=$service \
    coralogix-dataprime-demo/ \
    --quiet; then
    
    # Get image size
    IMAGE_SIZE=$(docker images ecommerce-$service:latest --format "{{.Size}}")
    IMAGE_SIZE_BYTES=$(docker images ecommerce-$service:latest --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "0")
    
    echo -e "${GREEN}✅ Built successfully${NC}"
    echo "   Image: ecommerce-$service:latest"
    echo "   Size: $IMAGE_SIZE"
    
    # Check if under 1GB
    if [[ "$IMAGE_SIZE" == *"MB"* ]]; then
      echo -e "   ${GREEN}✓ Under 1GB threshold${NC}"
    elif [[ "$IMAGE_SIZE" == *"GB"* ]]; then
      SIZE_NUM=$(echo $IMAGE_SIZE | sed 's/GB//')
      if (( $(echo "$SIZE_NUM < 1" | bc -l) )); then
        echo -e "   ${GREEN}✓ Under 1GB threshold${NC}"
      else
        echo -e "   ${YELLOW}⚠ WARNING: Image exceeds 1GB!${NC}"
      fi
    fi
    
    SUCCESSFUL_BUILDS=$((SUCCESSFUL_BUILDS + 1))
  else
    echo -e "${RED}❌ Build failed${NC}"
    FAILED_BUILDS=$((FAILED_BUILDS + 1))
  fi
  
  echo ""
done

# Build summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Build Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Total services: $TOTAL_SERVICES"
echo -e "   ${GREEN}Successful: $SUCCESSFUL_BUILDS${NC}"
if [ $FAILED_BUILDS -gt 0 ]; then
  echo -e "   ${RED}Failed: $FAILED_BUILDS${NC}"
fi
echo ""

# List all images
echo "📋 Built Images:"
docker images | grep "ecommerce-" | awk '{printf "   %-30s %-15s %-10s\n", $1":"$2, $4, $7}'
echo ""

if [ $FAILED_BUILDS -eq 0 ]; then
  echo -e "${GREEN}✅ All images built successfully!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Test locally: docker-compose up"
  echo "  2. Deploy to K8s: ./scripts/deploy-ecommerce-k8s.sh"
  exit 0
else
  echo -e "${RED}❌ Some builds failed. Please check the errors above.${NC}"
  exit 1
fi

