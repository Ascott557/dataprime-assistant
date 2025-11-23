#!/bin/bash
#
# Dual-Mode Traffic Validation Script
# Tests both baseline and demo endpoints and checks traffic statistics
#

set -e

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}  Dual-Mode Traffic Validation${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Get load generator pod
LOAD_POD=$(kubectl get pods -n ecommerce-demo -l app=load-generator -o jsonpath='{.items[0].metadata.name}')

if [ -z "$LOAD_POD" ]; then
    echo -e "${RED}✗ Load generator pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Load generator pod: $LOAD_POD"
echo ""

# Test 1: Baseline endpoint
echo -e "${BLUE}1. Testing baseline endpoint (/products)...${NC}"
BASELINE_RESULT=$(kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/products?category=electronics 2>&1 || echo "error")

if echo "$BASELINE_RESULT" | grep -q "products"; then
    PRODUCT_COUNT=$(echo "$BASELINE_RESULT" | jq -r '.products | length' 2>/dev/null || echo "N/A")
    echo -e "${GREEN}✓${NC} Baseline endpoint responding"
    echo -e "   Products returned: $PRODUCT_COUNT"
else
    echo -e "${RED}✗${NC} Baseline endpoint failed"
    echo "   Response: $BASELINE_RESULT"
fi
echo ""

# Test 2: Demo endpoint
echo -e "${BLUE}2. Testing demo endpoint (/products/recommendations)...${NC}"
DEMO_RESULT=$(kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/products/recommendations?category=electronics 2>&1 || echo "error")

if echo "$DEMO_RESULT" | grep -q "products"; then
    PRODUCT_COUNT=$(echo "$DEMO_RESULT" | jq -r '.products | length' 2>/dev/null || echo "N/A")
    echo -e "${GREEN}✓${NC} Demo endpoint responding"
    echo -e "   Products returned: $PRODUCT_COUNT"
else
    echo -e "${YELLOW}⚠${NC}  Demo endpoint returned error (expected during high failure rate)"
    echo "   Response: ${DEMO_RESULT:0:100}..."
fi
echo ""

# Test 3: Health check with dual-mode info
echo -e "${BLUE}3. Checking product catalog health...${NC}"
HEALTH_RESULT=$(kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/health 2>&1 || echo "error")

if echo "$HEALTH_RESULT" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Health check passed"
    
    # Extract demo info if available
    DEMO_MODE=$(echo "$HEALTH_RESULT" | jq -r '.demo_mode' 2>/dev/null || echo "N/A")
    DEMO_MINUTE=$(echo "$HEALTH_RESULT" | jq -r '.demo_minute' 2>/dev/null || echo "N/A")
    
    echo -e "   Demo mode: $DEMO_MODE"
    if [ "$DEMO_MINUTE" != "null" ] && [ "$DEMO_MINUTE" != "N/A" ]; then
        echo -e "   Demo minute: $DEMO_MINUTE"
    fi
else
    echo -e "${RED}✗${NC} Health check failed"
fi
echo ""

# Test 4: Traffic statistics
echo -e "${BLUE}4. Checking traffic stats...${NC}"
STATS_RESULT=$(kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://localhost:8010/admin/traffic-stats 2>&1 || echo "error")

if echo "$STATS_RESULT" | grep -q "baseline"; then
    echo -e "${GREEN}✓${NC} Traffic stats available"
    echo ""
    echo "$STATS_RESULT" | jq '.' 2>/dev/null || echo "$STATS_RESULT"
else
    echo -e "${YELLOW}⚠${NC}  Traffic stats not available (generator may not be running)"
    echo "   Response: $STATS_RESULT"
fi
echo ""

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}    Validation Complete${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Check Coralogix APM for traffic.type = 'baseline'"
echo "  2. Check Coralogix APM for traffic.type = 'demo'"
echo "  3. Compare error rates and latencies"
echo ""

