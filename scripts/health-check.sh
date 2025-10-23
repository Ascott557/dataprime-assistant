#!/bin/bash
# DataPrime Assistant - Health Check Script
# Verifies all services are running and healthy

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
HOST="${1:-localhost}"
FAILED_CHECKS=0

echo "========================================="
echo "🔍 DataPrime Assistant Health Check"
echo "========================================="
echo "Target: $HOST"
echo ""

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    printf "%-30s " "$name:"
    
    if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_status" ]; then
            echo -e "${GREEN}✅ OK${NC} (HTTP $response)"
        else
            echo -e "${RED}❌ FAIL${NC} (HTTP $response, expected $expected_status)"
            ((FAILED_CHECKS++))
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (Connection failed)"
        ((FAILED_CHECKS++))
    fi
}

# Check core services
echo "🔹 Core Services:"
check_endpoint "API Gateway" "http://$HOST:8010/api/health"
check_endpoint "Query Service" "http://$HOST:8011/health"
check_endpoint "Validation Service" "http://$HOST:8012/health"
check_endpoint "Queue Service" "http://$HOST:8013/health"
check_endpoint "Processing Service" "http://$HOST:8014/health"
check_endpoint "Storage Service" "http://$HOST:8015/health"
check_endpoint "External API Service" "http://$HOST:8016/health"
check_endpoint "Queue Worker Service" "http://$HOST:8017/health"
check_endpoint "Frontend" "http://$HOST:8020/health"

echo ""
echo "🔹 Infrastructure Services:"
check_endpoint "OTel Collector Health" "http://$HOST:13133"
check_endpoint "OTel Collector Metrics" "http://$HOST:8889/metrics"

# NGINX check (only on production/VM)
if [ "$HOST" != "localhost" ]; then
    echo ""
    echo "🔹 Web Server:"
    check_endpoint "NGINX HTTP" "http://$HOST/"
    check_endpoint "NGINX HTTPS" "https://$HOST/" 200
fi

# Database checks (if on localhost with docker)
if [ "$HOST" = "localhost" ] && command -v docker >/dev/null 2>&1; then
    echo ""
    echo "🔹 Data Stores:"
    
    # PostgreSQL check
    printf "%-30s " "PostgreSQL:"
    if docker exec postgres pg_isready -U dataprime > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAILED_CHECKS++))
    fi
    
    # Redis check
    printf "%-30s " "Redis:"
    if docker exec redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAILED_CHECKS++))
    fi
fi

# Docker container check
if command -v docker >/dev/null 2>&1; then
    echo ""
    echo "🔹 Container Status:"
    
    COMPOSE_FILE="/opt/dataprime-assistant/deployment/docker/docker-compose.vm.yml"
    if [ -f "$COMPOSE_FILE" ]; then
        cd /opt/dataprime-assistant/deployment/docker
        
        TOTAL_CONTAINERS=$(docker compose -f docker-compose.vm.yml ps -q | wc -l)
        RUNNING_CONTAINERS=$(docker compose -f docker-compose.vm.yml ps --filter "status=running" -q | wc -l)
        
        printf "%-30s " "Containers Running:"
        if [ "$RUNNING_CONTAINERS" -eq "$TOTAL_CONTAINERS" ]; then
            echo -e "${GREEN}✅ $RUNNING_CONTAINERS/$TOTAL_CONTAINERS${NC}"
        else
            echo -e "${YELLOW}⚠️  $RUNNING_CONTAINERS/$TOTAL_CONTAINERS${NC}"
        fi
    fi
fi

# Summary
echo ""
echo "========================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    echo "========================================="
    exit 0
else
    echo -e "${RED}❌ $FAILED_CHECKS health check(s) failed!${NC}"
    echo "========================================="
    echo ""
    echo "🔍 Troubleshooting:"
    echo "1. Check service logs:"
    echo "   docker compose -f /opt/dataprime-assistant/deployment/docker/docker-compose.vm.yml logs"
    echo ""
    echo "2. Restart failed services:"
    echo "   docker compose -f /opt/dataprime-assistant/deployment/docker/docker-compose.vm.yml restart"
    echo ""
    echo "3. Check system resources:"
    echo "   docker stats --no-stream"
    echo ""
    exit 1
fi

