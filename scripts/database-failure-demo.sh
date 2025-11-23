#!/usr/bin/env bash
#
# Database Failure Demo - re:Invent 2025
# Demonstrates PostgreSQL connection pool exhaustion and slow queries (>3000ms)
#
# This script orchestrates a realistic infrastructure failure scenario:
# 1. Normal operation (~10ms queries)
# 2. Slow queries enabled (3000ms+ JOINs and SELECTs)
# 3. Connection pool exhaustion (95+ connections held)
# 4. AI receiving incomplete/stale data
# 5. Multiple services competing for database resources
#
# Usage: ./scripts/database-failure-demo.sh <EC2_IP>

set -e

EC2_IP=$1

if [ -z "$EC2_IP" ]; then
    echo "❌ Error: EC2 IP address required"
    echo "Usage: $0 <EC2_IP>"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 re:Invent 2025 - Database Failure Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Scenario: Infrastructure Failure - PostgreSQL Pool Exhaustion"
echo ""
echo -e "${CYAN}What you'll see in Coralogix:${NC}"
echo "  • Database queries >3000ms (JOIN and SELECT spans)"
echo "  • Connection pool utilization: 0% → 95%+"
echo "  • Multiple services (product, inventory, order) competing"
echo "  • Query queuing and timeouts"
echo "  • AI recommendations affected by stale data"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Function to check service availability
check_service() {
    local url=$1
    local name=$2
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name${NC}"
        return 0
    else
        echo -e "${RED}❌ $name${NC}"
        return 1
    fi
}

echo "🔍 Checking services..."
check_service "http://${EC2_IP}:30014/health" "product-service (port 30014)"
check_service "http://${EC2_IP}:30015/health" "inventory-service (port 30015)"
check_service "http://${EC2_IP}:30016/health" "order-service (port 30016)"
check_service "http://${EC2_IP}:30010/health" "api-gateway (port 30010)"
echo ""

# Step 1: Reset to clean state
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 1: Resetting to clean state...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -X POST "http://${EC2_IP}:30014/demo/reset" 2>/dev/null | jq '.'
echo ""
sleep 2

# Step 2: Baseline - Normal operation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 2: Baseline - Normal Operation (30 seconds)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}Expected in Coralogix Database APM:${NC}"
echo "  • Query latency: ~7-15ms"
echo "  • Pool utilization: ~5-10%"
echo "  • No failures"
echo ""
echo "Generating normal traffic..."

# Generate baseline traffic
for i in {1..10}; do
    # Simple SELECT queries
    curl -s "http://${EC2_IP}:30014/products?category=Wireless%20Headphones&price_min=0&price_max=100" > /dev/null &
    curl -s "http://${EC2_IP}:30015/inventory/check/$((RANDOM % 10 + 1))" > /dev/null &
    curl -s "http://${EC2_IP}:30016/orders/popular-products" > /dev/null &
    
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    sleep 2
done

wait
echo ""
echo -e "${GREEN}✅ Baseline traffic complete${NC}"
echo ""
sleep 3

# Step 3: Enable slow queries (>3000ms)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 3: Enabling SLOW QUERIES (3000ms delay)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -X POST "http://${EC2_IP}:30014/demo/enable-slow-queries" \
    -H "Content-Type: application/json" \
    -d '{"delay_ms": 3000}' 2>/dev/null | jq '.'
echo ""
sleep 2

# Step 4: Generate traffic with slow queries
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 4: Generating traffic with SLOW queries (60 seconds)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}Expected in Coralogix Database APM:${NC}"
echo "  • P95 latency: ~2800-3100ms"
echo "  • Query queuing visible"
echo "  • JOIN spans taking >3000ms"
echo "  • SELECT spans taking >3000ms"
echo ""
echo "Generating slow query traffic..."

# Generate slow traffic with JOIN queries
for i in {1..15}; do
    # Complex JOIN queries (will be slow)
    curl -s "http://${EC2_IP}:30014/products/popular-with-history?limit=10" > /dev/null &
    
    # Regular queries (also slow now)
    curl -s "http://${EC2_IP}:30014/products?category=Wireless%20Headphones&price_min=0&price_max=100" > /dev/null &
    curl -s "http://${EC2_IP}:30015/inventory/check/$((RANDOM % 10 + 1))" > /dev/null &
    curl -s "http://${EC2_IP}:30016/orders/popular-products" > /dev/null &
    
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    sleep 3
done

wait
echo ""
echo -e "${GREEN}✅ Slow query traffic complete${NC}"
echo ""
sleep 3

# Step 5: Simulate connection pool exhaustion
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 5: Simulating CONNECTION POOL EXHAUSTION${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
curl -X POST "http://${EC2_IP}:30014/demo/simulate-pool-exhaustion" 2>/dev/null | jq '.'
echo ""
sleep 2

# Step 6: Generate traffic with exhausted pool
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 6: Generating traffic with EXHAUSTED pool (60 seconds)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}Expected in Coralogix Database APM:${NC}"
echo "  • Pool utilization: 95%+"
echo "  • Active connections: 95-100"
echo "  • Connection timeouts and errors"
echo "  • 503 Service Unavailable responses"
echo ""
echo "Generating high-load traffic with exhausted pool..."

# Generate aggressive traffic
for i in {1..20}; do
    # Try to hit all services simultaneously
    curl -s "http://${EC2_IP}:30014/products/popular-with-history?limit=10" > /dev/null 2>&1 &
    curl -s "http://${EC2_IP}:30014/products?category=Wireless%20Headphones&price_min=0&price_max=100" > /dev/null 2>&1 &
    curl -s "http://${EC2_IP}:30015/inventory/check/$((RANDOM % 10 + 1))" > /dev/null 2>&1 &
    curl -s "http://${EC2_IP}:30016/orders/popular-products" > /dev/null 2>&1 &
    
    # Also test AI recommendations (will be affected by database issues)
    if [ $((i % 5)) -eq 0 ]; then
        TRACE_ID=$(curl -s -X POST "http://${EC2_IP}:30010/api/recommendations" \
            -H "Content-Type: application/json" \
            -d '{"user_context": "wireless headphones under 100 dollars - pool exhaustion test"}' \
            2>/dev/null | jq -r '.trace_id // "N/A"')
        echo "  Generated AI trace: $TRACE_ID"
    fi
    
    if [ $((i % 3)) -eq 0 ]; then
        echo -n "."
    fi
    sleep 2
done

wait
echo ""
echo -e "${GREEN}✅ Pool exhaustion traffic complete${NC}"
echo ""
sleep 3

# Step 7: Check current pool stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 7: Current Pool Statistics${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
curl -s "http://${EC2_IP}:30014/health" | jq '{
    pool_stats: {
        active: .connection_pool.active_connections,
        available: .connection_pool.available_connections,
        max: .connection_pool.max_connections,
        utilization: .connection_pool.utilization_percent
    },
    simulation: {
        slow_queries: .slow_queries_enabled,
        pool_exhaustion: .pool_exhaustion_simulated
    }
}'
echo ""

# Step 8: Reset to normal operation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Step 8: Resetting to normal operation...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -X POST "http://${EC2_IP}:30014/demo/reset" 2>/dev/null | jq '.'
echo ""
sleep 2

# Final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Demo Scenario Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}📊 Check Coralogix Database APM:${NC}"
echo ""
echo "1️⃣  Navigate to: https://eu2.coralogix.com/apm/databases/productcatalog"
echo ""
echo "2️⃣  What to look for:"
echo "  ✅ Baseline period: ~10ms avg latency, 5-10% pool utilization"
echo "  ⚠️  Slow query period: ~2800-3100ms P95 latency"
echo "     • JOIN productcatalog.products+orders >3000ms"
echo "     • SELECT productcatalog.products >3000ms"
echo "  🔴 Pool exhaustion: 95%+ utilization, connection errors"
echo ""
echo "3️⃣  Calling Services dropdown should show:"
echo "  • product-service (JOIN and SELECT queries)"
echo "  • inventory-service (SELECT queries)"
echo "  • order-service (SELECT queries)"
echo ""
echo "4️⃣  Query Types should show:"
echo "  • SELECT operations"
echo "  • JOIN operations (from /products/popular-with-history)"
echo ""
echo "5️⃣  AI Impact - Check AI Center:"
echo "  • https://eu2.coralogix.com/apm/ai"
echo "  • AI recommendations affected by slow/failed database queries"
echo "  • Look for incomplete or stale product data in responses"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""


