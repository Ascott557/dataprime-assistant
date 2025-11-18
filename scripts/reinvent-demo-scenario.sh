#!/bin/bash
set -e

#==============================================================================
# re:Invent 2025 Demo Scenario - Database APM
# 
# Demonstrates:
# - Normal database operations
# - Slow query performance degradation
# - Connection pool exhaustion
# - Real-time monitoring in Coralogix Database APM
#
# Usage: ./scripts/reinvent-demo-scenario.sh <EC2_IP>
# Example: ./scripts/reinvent-demo-scenario.sh 54.235.171.176
#==============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
EC2_IP="${1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOAD_GENERATOR="${SCRIPT_DIR}/generate-demo-load.py"

# Validate parameters
if [ -z "$EC2_IP" ]; then
    echo -e "${RED}❌ Error: EC2 IP address required${NC}"
    echo "Usage: $0 <EC2_IP>"
    echo "Example: $0 54.235.171.176"
    exit 1
fi

# Check dependencies
echo -e "${CYAN}🔍 Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found${NC}"
    echo "Please install Python 3"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ Error: curl not found${NC}"
    echo "Please install curl"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: jq not found (optional)${NC}"
    echo "Install jq for better output formatting: brew install jq"
    HAS_JQ=false
else
    HAS_JQ=true
fi

if [ ! -f "$LOAD_GENERATOR" ]; then
    echo -e "${RED}❌ Error: Load generator not found at $LOAD_GENERATOR${NC}"
    exit 1
fi

# Test connectivity
echo -e "${CYAN}🔗 Testing connectivity to services...${NC}"
if ! curl -s -f -m 5 "http://${EC2_IP}:30015/health" > /dev/null; then
    echo -e "${RED}❌ Error: Cannot reach inventory-service at http://${EC2_IP}:30015${NC}"
    echo "Please verify the services are running"
    exit 1
fi

if ! curl -s -f -m 5 "http://${EC2_IP}:30016/health" > /dev/null; then
    echo -e "${RED}❌ Error: Cannot reach order-service at http://${EC2_IP}:30016${NC}"
    echo "Please verify the services are running"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies verified${NC}"
echo ""

#==============================================================================
# Helper Functions
#==============================================================================

print_step() {
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_talking_point() {
    echo -e "${YELLOW}💬 TALKING POINT: $1${NC}"
}

print_coralogix_action() {
    echo -e "${BLUE}📊 CORALOGIX: $1${NC}"
}

wait_with_countdown() {
    local seconds=$1
    local message=$2
    echo -ne "${CYAN}⏳ ${message}${NC}"
    for ((i=$seconds; i>0; i--)); do
        echo -ne "\r${CYAN}⏳ ${message} ${i}s remaining...${NC}"
        sleep 1
    done
    echo -e "\r${GREEN}✅ ${message} Complete!                    ${NC}"
}

get_pool_stats() {
    local service_port=$1
    local service_name=$2
    
    if [ "$HAS_JQ" = true ]; then
        echo -e "${CYAN}   ${service_name}:${NC}"
        curl -s "http://${EC2_IP}:${service_port}/health" | jq -r '.connection_pool | "      Active: \(.active_connections)/\(.max_connections) (\(.utilization_percent)%)"'
    else
        echo -e "${CYAN}   ${service_name}: $(curl -s http://${EC2_IP}:${service_port}/health)${NC}"
    fi
}

#==============================================================================
# Demo Scenario Start
#==============================================================================

clear
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          🎯 re:Invent 2025 Demo Scenario                          ║
║          Database Connection Pool Monitoring with Coralogix       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${CYAN}Configuration:${NC}"
echo -e "   Target: ${GREEN}http://${EC2_IP}${NC}"
echo -e "   Services: ${GREEN}inventory-service, order-service${NC}"
echo -e "   Demo Duration: ${GREEN}~6 minutes${NC}"
echo ""

print_talking_point "Today I'll show you how Coralogix Database APM helps prevent production incidents"
echo ""
read -p "Press Enter to begin the demo scenario..."

#==============================================================================
# STEP 1: Reset to Clean State
#==============================================================================

print_step "STEP 1: Resetting to Clean State 🔄"

print_talking_point "Let's start with a clean slate - resetting all demo simulations"

echo -e "${CYAN}Resetting inventory-service...${NC}"
curl -s -X POST "http://${EC2_IP}:30015/demo/reset" > /dev/null && echo -e "${GREEN}✅ Inventory service reset${NC}"

echo -e "${CYAN}Resetting order-service...${NC}"
curl -s -X POST "http://${EC2_IP}:30016/demo/reset" > /dev/null && echo -e "${GREEN}✅ Order service reset${NC}"

sleep 2

echo -e "\n${GREEN}✅ All services reset to normal operation${NC}"
print_coralogix_action "Database APM should show normal metrics"

#==============================================================================
# STEP 2: Generate Normal Traffic Baseline
#==============================================================================

print_step "STEP 2: Establishing Baseline - Normal Operations ⚡"

print_talking_point "This is what healthy database operations look like"
echo ""

echo -e "${CYAN}Generating normal traffic:${NC}"
echo -e "   • Threads: ${GREEN}10${NC}"
echo -e "   • Requests/sec: ${GREEN}10${NC}"
echo -e "   • Duration: ${GREEN}30 seconds${NC}"
echo -e "   • Expected Response Time: ${GREEN}5-20ms${NC}"
echo -e "   • Expected Pool Utilization: ${GREEN}10-20%${NC}"
echo ""

print_coralogix_action "Open: APM → Database Catalog → productcatalog"
print_coralogix_action "Watch: Query time should be ~10ms, pool utilization ~10-20%"
echo ""

# Run load generator in background
python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 10 --rps 10 --duration 30 > /tmp/demo_baseline.log 2>&1 &
LOAD_PID=$!

wait_with_countdown 30 "Generating baseline traffic"

# Kill load generator if still running
kill $LOAD_PID 2>/dev/null || true
wait $LOAD_PID 2>/dev/null || true

echo ""
echo -e "${CYAN}Current Pool Status:${NC}"
get_pool_stats 30015 "inventory-service"
get_pool_stats 30016 "order-service"

echo ""
print_talking_point "Under normal load, pool utilization is low and queries are fast"
read -p "Press Enter to continue to slow query scenario..."

#==============================================================================
# STEP 3: Enable Slow Query Simulation
#==============================================================================

print_step "STEP 3: Simulating Slow Database Queries 🐌"

print_talking_point "Now let's see what happens when a slow query hits"
print_talking_point "This could be a missing index, unoptimized query, or lock contention"
echo ""

echo -e "${CYAN}Enabling 2900ms query delay on all services...${NC}"

curl -s -X POST "http://${EC2_IP}:30015/demo/enable-slow-queries" \
  -H "Content-Type: application/json" \
  -d '{"delay_ms": 2900}' > /dev/null && echo -e "${GREEN}✅ Inventory service: 2900ms delay enabled${NC}"

curl -s -X POST "http://${EC2_IP}:30016/demo/enable-slow-queries" \
  -H "Content-Type: application/json" \
  -d '{"delay_ms": 2900}' > /dev/null && echo -e "${GREEN}✅ Order service: 2900ms delay enabled${NC}"

sleep 2
echo ""
echo -e "${GREEN}✅ Slow query simulation enabled${NC}"
print_coralogix_action "Database APM will now show query time spike"

#==============================================================================
# STEP 4: Generate Traffic with Slow Queries
#==============================================================================

print_step "STEP 4: Observing Slow Query Impact 📊"

print_talking_point "Watch what happens to the entire system when queries slow down"
echo ""

echo -e "${CYAN}Generating traffic with slow queries:${NC}"
echo -e "   • Threads: ${YELLOW}20${NC}"
echo -e "   • Requests/sec: ${YELLOW}15${NC}"
echo -e "   • Duration: ${YELLOW}60 seconds${NC}"
echo -e "   • Expected Response Time: ${RED}2900-3100ms${NC}"
echo -e "   • Expected Pool Utilization: ${YELLOW}60-80%${NC}"
echo ""

print_coralogix_action "Watch: P95 latency should spike to ~2800-3000ms"
print_coralogix_action "Watch: Pool utilization climbing to 60-80%"
print_coralogix_action "Watch: ALL services affected (inventory, order)"
echo ""

python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 20 --rps 15 --duration 60 > /tmp/demo_slow.log 2>&1 &
LOAD_PID=$!

wait_with_countdown 60 "Generating slow query traffic"

kill $LOAD_PID 2>/dev/null || true
wait $LOAD_PID 2>/dev/null || true

echo ""
echo -e "${CYAN}Current Pool Status:${NC}"
get_pool_stats 30015 "inventory-service"
get_pool_stats 30016 "order-service"

echo ""
print_talking_point "You can see pool utilization climbing - queries are holding connections longer"
read -p "Press Enter to continue to pool exhaustion..."

#==============================================================================
# STEP 5: Simulate Pool Exhaustion
#==============================================================================

print_step "STEP 5: Simulating Connection Pool Exhaustion 💥"

print_talking_point "Now let's push it further - what if the pool runs out of connections?"
echo ""

echo -e "${CYAN}Exhausting connection pool (holding 95 of 100 connections)...${NC}"
curl -s -X POST "http://${EC2_IP}:30015/demo/simulate-pool-exhaustion" > /dev/null && \
  echo -e "${GREEN}✅ Pool exhaustion activated${NC}"

sleep 2

echo ""
echo -e "${RED}⚠️  Connection pool exhausted!${NC}"
echo -e "${CYAN}Current Pool Status:${NC}"
get_pool_stats 30015 "inventory-service"
get_pool_stats 30016 "order-service"

echo ""
print_coralogix_action "Pool utilization should now show ~95%"

#==============================================================================
# STEP 6: Show Pool Exhaustion Impact
#==============================================================================

print_step "STEP 6: Demonstrating Pool Exhaustion Impact 🔥"

print_talking_point "With 95% of connections held, new requests must wait or timeout"
echo ""

echo -e "${CYAN}Generating traffic with exhausted pool:${NC}"
echo -e "   • Threads: ${RED}30${NC}"
echo -e "   • Requests/sec: ${RED}20${NC}"
echo -e "   • Duration: ${RED}45 seconds${NC}"
echo -e "   • Expected: ${RED}Timeouts and errors${NC}"
echo -e "   • Pool: ${RED}95/100 connections (95%)${NC}"
echo ""

print_coralogix_action "Watch: Connection queuing visible"
print_coralogix_action "Watch: Some requests timing out"
print_coralogix_action "Watch: Active connections at maximum (95+)"
echo ""

python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 30 --rps 20 --duration 45 > /tmp/demo_exhaustion.log 2>&1 &
LOAD_PID=$!

wait_with_countdown 45 "Generating traffic with exhausted pool"

kill $LOAD_PID 2>/dev/null || true
wait $LOAD_PID 2>/dev/null || true

#==============================================================================
# STEP 7: Check Pool Statistics
#==============================================================================

print_step "STEP 7: Current System State 📈"

echo -e "${CYAN}Final Pool Statistics:${NC}"
get_pool_stats 30015 "inventory-service"
get_pool_stats 30016 "order-service"

echo ""
print_talking_point "This is what a production incident looks like"
print_talking_point "95% pool utilization means customers are experiencing timeouts"
echo ""

print_coralogix_action "In Coralogix Database APM, you can see:"
echo -e "   ${BLUE}✓${NC} Exact moment pool exhausted"
echo -e "   ${BLUE}✓${NC} Which services are affected"
echo -e "   ${BLUE}✓${NC} Query patterns causing the issue"
echo -e "   ${BLUE}✓${NC} Connection pool utilization over time"

read -p "Press Enter to reset and conclude the demo..."

#==============================================================================
# STEP 8: Reset to Normal
#==============================================================================

print_step "STEP 8: Restoring Normal Operation ♻️"

echo -e "${CYAN}Resetting all services to normal operation...${NC}"

curl -s -X POST "http://${EC2_IP}:30015/demo/reset" > /dev/null && \
  echo -e "${GREEN}✅ Inventory service: Demo modes disabled, connections released${NC}"

curl -s -X POST "http://${EC2_IP}:30016/demo/reset" > /dev/null && \
  echo -e "${GREEN}✅ Order service: Demo modes disabled${NC}"

sleep 2

echo ""
echo -e "${CYAN}Restored Pool Status:${NC}"
get_pool_stats 30015 "inventory-service"
get_pool_stats 30016 "order-service"

echo ""
echo -e "${GREEN}✅ System restored to normal operation${NC}"

#==============================================================================
# Demo Complete
#==============================================================================

echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                 ✅ Demo Scenario Complete!                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

print_step "Summary: What We Demonstrated"

echo -e "${GREEN}✅ Normal Operations${NC}"
echo -e "   • Baseline: ~10ms queries, 10-20% pool utilization"
echo -e "   • All services healthy and responsive"
echo ""

echo -e "${YELLOW}⚠️  Performance Degradation${NC}"
echo -e "   • Slow queries: ~2900ms response time"
echo -e "   • Pool utilization climbed to 60-80%"
echo -e "   • System still operational but degraded"
echo ""

echo -e "${RED}🔥 Production Incident${NC}"
echo -e "   • Pool exhaustion: 95% utilization"
echo -e "   • Connection queuing visible"
echo -e "   • Timeouts and errors occurring"
echo -e "   • Customer impact: Slow/failed requests"
echo ""

echo -e "${BLUE}📊 Coralogix Database APM Visibility${NC}"
echo -e "   • All 3 services visible: inventory, order, product"
echo -e "   • Real-time connection pool metrics"
echo -e "   • Query latency tracking"
echo -e "   • Complete distributed traces"
echo ""

print_step "Next Steps: Viewing in Coralogix"

echo -e "${CYAN}Navigate to:${NC}"
echo -e "   ${BLUE}https://eu2.coralogix.com/apm/databases${NC}"
echo ""

echo -e "${CYAN}You should see:${NC}"
echo -e "   1. Database: ${GREEN}productcatalog${NC}"
echo -e "   2. Calling Services: ${GREEN}3 services${NC}"
echo -e "      • inventory-service (SELECT, UPDATE)"
echo -e "      • order-service (SELECT, INSERT)"
echo -e "      • product-service (SELECT)"
echo -e "   3. Query Time Graph: ${GREEN}Showing the spike from 10ms → 2900ms${NC}"
echo -e "   4. Connection Pool: ${GREEN}Showing utilization from 10% → 95%${NC}"
echo ""

echo -e "${CYAN}Click on any operation to:${NC}"
echo -e "   • See individual database queries"
echo -e "   • View complete distributed traces"
echo -e "   • Check connection pool metrics in span attributes"
echo -e "   • Identify slow query patterns"
echo ""

print_step "Key Takeaways"

echo -e "${YELLOW}💡 Without Database Monitoring:${NC}"
echo -e "   • You'd only know about issues when customers complain"
echo -e "   • No visibility into which service caused the problem"
echo -e "   • Can't see connection pool utilization"
echo -e "   • Difficult to correlate slow queries across services"
echo ""

echo -e "${GREEN}💡 With Coralogix Database Monitoring:${NC}"
echo -e "   • See issues before customers are impacted"
echo -e "   • Identify which services are affected"
echo -e "   • Monitor connection pool in real-time"
echo -e "   • Set alerts at 80% utilization to prevent incidents"
echo -e "   • Drill down to specific slow queries"
echo -e "   • Make data-driven decisions about scaling"
echo ""

echo -e "${CYAN}Demo logs saved to:${NC}"
echo -e "   /tmp/demo_baseline.log"
echo -e "   /tmp/demo_slow.log"
echo -e "   /tmp/demo_exhaustion.log"
echo ""

echo -e "${GREEN}✅ Demo complete! Thank you for watching!${NC}"
echo ""

