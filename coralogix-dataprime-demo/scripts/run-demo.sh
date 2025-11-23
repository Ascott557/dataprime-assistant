#!/bin/bash
# =============================================================================
# Black Friday Demo Orchestration Script
# =============================================================================
#
# Complete 30-minute demo with:
# - Pre-flight checks
# - Database configuration
# - Traffic generation
# - Real-time monitoring
# - Automatic cleanup
#
# =============================================================================

set -e

# ANSI colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ecommerce-demo"
DEMO_DURATION_MINUTES=30

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  BLACK FRIDAY DEMO - STARTING${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

echo -e "${CYAN}Running pre-flight checks...${NC}"
echo ""

# Check kubectl
echo -n "  Checking kubectl... "
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo -e "${RED}kubectl cannot connect to cluster${NC}"
    exit 1
fi

# Check namespace
echo -n "  Checking namespace... "
if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Namespace $NAMESPACE not found${NC}"
    exit 1
fi

# Check services
echo -n "  Checking services... "
PODS_COUNT=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
if [ "$PODS_COUNT" -gt 5 ]; then
    echo -e "${GREEN}✓ ($PODS_COUNT pods running)${NC}"
else
    echo -e "${RED}✗ Only $PODS_COUNT pods running${NC}"
    exit 1
fi

# Check PostgreSQL
echo -n "  Checking PostgreSQL... "
PG_CHECK=$(kubectl exec -n "$NAMESPACE" postgresql-primary-0 -- pg_isready -U ecommerce_user 2>&1 | grep "accepting connections" || echo "")
if [ -n "$PG_CHECK" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ PostgreSQL not ready${NC}"
    exit 1
fi

# Check OTel Collector
echo -n "  Checking OTel Collector... "
OTEL_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=opentelemetry-collector -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")
if [ "$OTEL_POD" == "Running" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ OTel Collector not found (telemetry may not work)${NC}"
fi

echo ""
echo -e "${GREEN}✓ All pre-flight checks passed${NC}"
echo ""

# =============================================================================
# DEMO TIMELINE
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}         DEMO TIMELINE${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  ${GREEN}0-10 min${NC}:  Traffic ramp (30→120 req/min)"
echo -e " ${GREEN}10-15 min${NC}:  Peak traffic, normal ops"
echo -e " ${YELLOW}15-20 min${NC}:  Database degradation begins"
echo -e " ${YELLOW}20-25 min${NC}:  Connection pool exhaustion"
echo -e " ${RED}22-23 min${NC}:  🚨 FLOW ALERT TRIGGERS"
echo -e " ${RED}25-30 min${NC}:  Peak failure rate (35%)"
echo -e "${BLUE}========================================${NC}"
echo ""

read -p "Press Enter to start the demo (or Ctrl+C to cancel)..."
echo ""

# =============================================================================
# APPLY DATABASE CONFIGURATION
# =============================================================================

echo -e "${CYAN}Step 1: Applying database configuration...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Run database setup script
if [ -f "$PROJECT_ROOT/infrastructure/database/setup_demo_database_issues.sh" ]; then
    bash "$PROJECT_ROOT/infrastructure/database/setup_demo_database_issues.sh"
else
    echo -e "${RED}✗ Database setup script not found${NC}"
    exit 1
fi

echo ""

# =============================================================================
# UPDATE CONFIGMAP WITH UNIX TIMESTAMP
# =============================================================================

echo -e "${CYAN}Step 2: Configuring demo mode...${NC}"

# Create Unix timestamp for synchronization
DEMO_START_TS=$(date +%s)
echo -e "  Demo start timestamp: ${YELLOW}$DEMO_START_TS${NC}"

# Update ConfigMap with Unix timestamp
kubectl patch configmap ecommerce-config -n "$NAMESPACE" \
  --patch "{\"data\": {\"DEMO_MODE\": \"blackfriday\", \"DEMO_START_TIMESTAMP\": \"$DEMO_START_TS\"}}" \
  > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} ConfigMap updated with DEMO_MODE=blackfriday"
else
    echo -e "  ${YELLOW}⚠${NC} ConfigMap update failed (may not exist)"
fi

echo ""

# =============================================================================
# RESTART SERVICES
# =============================================================================

echo -e "${CYAN}Step 3: Restarting services...${NC}"

# Restart all deployments
kubectl rollout restart deployment -n "$NAMESPACE" > /dev/null 2>&1
echo -e "  ${BLUE}→${NC} Deployments restarted, waiting for rollout..."

# Wait for rollout
kubectl rollout status deployment -n "$NAMESPACE" --timeout=120s > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} All services restarted successfully"
else
    echo -e "  ${YELLOW}⚠${NC} Some services may still be starting"
fi

# CRITICAL: Verify pods picked up new config
echo -e "  ${BLUE}→${NC} Verifying configuration..."

kubectl wait --for=condition=ready pod \
  -l app=product-catalog -n "$NAMESPACE" \
  --timeout=120s > /dev/null 2>&1

# Check DEMO_MODE in a pod
CATALOG_POD=$(kubectl get pods -n "$NAMESPACE" -l app=product-catalog \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$CATALOG_POD" ]; then
    DEMO_MODE_CHECK=$(kubectl exec -n "$NAMESPACE" "$CATALOG_POD" -- \
      env | grep "DEMO_MODE=blackfriday" 2>/dev/null || echo "")
    
    if [ -n "$DEMO_MODE_CHECK" ]; then
        echo -e "  ${GREEN}✓${NC} Pods have correct configuration"
    else
        echo -e "  ${YELLOW}⚠${NC} DEMO_MODE may not be set correctly"
    fi
fi

echo ""

# =============================================================================
# START TRAFFIC GENERATION
# =============================================================================

echo -e "${CYAN}Step 4: Starting traffic generation...${NC}"

# Get load generator pod
LOAD_POD=$(kubectl get pods -n "$NAMESPACE" -l app=load-generator \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$LOAD_POD" ]; then
    echo -e "${RED}✗ Load generator pod not found${NC}"
    exit 1
fi

echo -e "  Load generator pod: ${YELLOW}$LOAD_POD${NC}"

# Start demo
DEMO_START_RESPONSE=$(kubectl exec -n "$NAMESPACE" "$LOAD_POD" -- \
  curl -s -X POST http://localhost:8010/admin/start-demo \
  -H 'Content-Type: application/json' \
  -d "{\"scenario\": \"blackfriday\", \"duration_minutes\": $DEMO_DURATION_MINUTES, \"peak_rpm\": 120}" 2>/dev/null)

if echo "$DEMO_START_RESPONSE" | grep -q "demo_started"; then
    echo -e "  ${GREEN}✓${NC} Traffic generation started"
else
    echo -e "  ${RED}✗${NC} Failed to start traffic:"
    echo "$DEMO_START_RESPONSE"
    exit 1
fi

echo ""

# =============================================================================
# REAL-TIME MONITORING
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    MONITORING DEMO PROGRESS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

for minute in $(seq 1 $DEMO_DURATION_MINUTES); do
    echo -e "${BLUE}--- Minute $minute/$DEMO_DURATION_MINUTES ---${NC}"
    
    # Fetch current status
    STATUS=$(kubectl exec -n "$NAMESPACE" "$LOAD_POD" -- \
      curl -s http://localhost:8010/admin/demo-status 2>/dev/null || echo '{}')
    
    if [ -z "$STATUS" ] || [ "$STATUS" == "{}" ]; then
        echo -e "  ${YELLOW}⚠${NC} Could not fetch status"
    else
        # Parse JSON (requires jq, fallback to grep)
        if command -v jq &> /dev/null; then
            PHASE=$(echo "$STATUS" | jq -r '.phase // "unknown"')
            RPM=$(echo "$STATUS" | jq -r '.current_rpm // 0')
            ERROR_RATE=$(echo "$STATUS" | jq -r '.current_error_rate // 0')
            REQUESTS=$(echo "$STATUS" | jq -r '.requests_sent // 0')
            ERRORS=$(echo "$STATUS" | jq -r '.errors // 0')
            
            ERROR_PCT=$(echo "$ERROR_RATE * 100" | bc -l 2>/dev/null | cut -c1-5)
            
            echo -e "  Phase: ${CYAN}$PHASE${NC} | RPM: $RPM | Requests: $REQUESTS | Errors: $ERRORS ($ERROR_PCT%)"
        else
            echo -e "  ${YELLOW}⚠${NC} Install jq for detailed status"
            echo "$STATUS" | head -n 3
        fi
    fi
    
    # Highlight key moments
    if [ $minute -eq 10 ]; then
        echo -e "  ${YELLOW}⚠️  Peak traffic reached (120 rpm)${NC}"
    elif [ $minute -eq 15 ]; then
        echo -e "  ${YELLOW}⚠️  Database degradation starting${NC}"
    elif [ $minute -eq 20 ]; then
        echo -e "  ${RED}🚨 Connection pool exhaustion beginning${NC}"
    elif [ $minute -eq 22 ]; then
        echo -e "  ${RED}🚨🚨🚨 FLOW ALERT SHOULD TRIGGER NOW 🚨🚨🚨${NC}"
        echo -e "  ${CYAN}📧 Check Coralogix → Incidents${NC}"
        echo -e "  ${CYAN}🔗 https://eu2.coralogix.com/incidents${NC}"
    fi
    
    echo ""
    sleep 60
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DEMO COMPLETED${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# =============================================================================
# CLEANUP FUNCTION
# =============================================================================

cleanup_demo() {
    echo ""
    echo -e "${CYAN}Cleaning up demo configuration...${NC}"
    
    # Restore database indexes
    echo -e "  ${BLUE}→${NC} Restoring indexes..."
    kubectl exec -n "$NAMESPACE" postgresql-primary-0 -- \
      psql -U ecommerce_user -d ecommerce -c "
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
        CREATE INDEX IF NOT EXISTS idx_products_stock_quantity ON products(stock_quantity);
      " > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Indexes restored"
    else
        echo -e "  ${YELLOW}⚠${NC} Failed to restore indexes"
    fi
    
    # Reset ConfigMap
    echo -e "  ${BLUE}→${NC} Resetting configuration..."
    kubectl patch configmap ecommerce-config -n "$NAMESPACE" \
      --patch '{"data": {"DB_MAX_CONNECTIONS": "100", "DEMO_MODE": "off"}}' \
      > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} ConfigMap restored"
    fi
    
    # Stop traffic (if still running)
    kubectl exec -n "$NAMESPACE" "$LOAD_POD" -- \
      curl -s -X POST http://localhost:8010/admin/stop-demo \
      > /dev/null 2>&1 || true
    
    echo -e "  ${GREEN}✓${NC} Demo cleanup complete"
    echo ""
    echo -e "${GREEN}Demo environment restored to normal operations${NC}"
}

# Register cleanup on exit
trap cleanup_demo EXIT INT TERM

echo ""
echo -e "${CYAN}Demo monitoring complete. Cleaning up...${NC}"

