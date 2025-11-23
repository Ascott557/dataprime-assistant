#!/bin/bash
# =============================================================================
# Black Friday Demo: Database Issues Setup Script
# =============================================================================
#
# This script configures the database to simulate Black Friday failures:
# 1. Drops indexes on products table (causes slow queries)
# 2. Sets connection pool to 20 (causes pool exhaustion)
# 3. Simulates missing read replica configuration
#
# SAFE TO RUN MULTIPLE TIMES: Idempotent design
# =============================================================================

set -e

# ANSI colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DATABASE DEMO CONFIGURATION${NC}"
echo -e "${BLUE}========================================${NC}"

# Get script directory (works even if script is symlinked)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SQL_FILE="$SCRIPT_DIR/missing_index_config.sql"

# Configuration
NAMESPACE="ecommerce-demo"
POSTGRES_POD="postgresql-primary-0"
POSTGRES_USER="ecommerce_user"
POSTGRES_DB="ecommerce"

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

echo -e "${BLUE}Running pre-flight checks...${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} kubectl available"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}✗ Namespace $NAMESPACE not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Namespace $NAMESPACE exists"

# Check if PostgreSQL pod exists and is ready
if ! kubectl get pod "$POSTGRES_POD" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL pod $POSTGRES_POD not found${NC}"
    exit 1
fi

POD_STATUS=$(kubectl get pod "$POSTGRES_POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
if [ "$POD_STATUS" != "Running" ]; then
    echo -e "${RED}✗ PostgreSQL pod not running (status: $POD_STATUS)${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} PostgreSQL pod is running"

# Check PostgreSQL is accepting connections
if ! kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- pg_isready -U "$POSTGRES_USER" &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL not accepting connections${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} PostgreSQL accepting connections"

# =============================================================================
# STEP 1: DROP INDEXES (Causes Slow Queries)
# =============================================================================

echo ""
echo -e "${BLUE}Step 1: Dropping product indexes...${NC}"

# Copy SQL file to pod (proper way to handle multi-line SQL)
echo -e "  📋 Copying SQL script to pod..."
kubectl cp "$SQL_FILE" \
  "$NAMESPACE/$POSTGRES_POD:/tmp/missing_index.sql"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to copy SQL file${NC}"
    exit 1
fi

# Execute SQL script
echo -e "  🗄️  Executing SQL commands..."
kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/missing_index.sql

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to execute SQL${NC}"
    exit 1
fi

# =============================================================================
# STEP 2: VERIFY INDEXES ARE DROPPED
# =============================================================================

echo -e "${BLUE}Step 2: Verifying index removal...${NC}"

# Get list of indexes on products table
INDEXES=$(kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "\di products*" 2>/dev/null || echo "")

# Check that critical indexes are missing
if echo "$INDEXES" | grep -q "idx_products_category"; then
    echo -e "${RED}✗ ERROR: idx_products_category still exists!${NC}"
    echo -e "${YELLOW}  This index should have been dropped${NC}"
    exit 1
else
    echo -e "${GREEN}✓${NC} Removed idx_products_category"
fi

if echo "$INDEXES" | grep -q "idx_products_stock_quantity"; then
    echo -e "${RED}✗ ERROR: idx_products_stock_quantity still exists!${NC}"
    echo -e "${YELLOW}  This index should have been dropped${NC}"
    exit 1
else
    echo -e "${GREEN}✓${NC} Removed idx_products_stock_quantity"
fi

# =============================================================================
# STEP 3: UPDATE CONNECTION POOL CONFIGURATION
# =============================================================================

echo ""
echo -e "${BLUE}Step 3: Configuring connection pool...${NC}"

# Update ConfigMap to set max connections to 20
kubectl patch configmap ecommerce-config -n "$NAMESPACE" \
  --patch '{"data": {"DB_MAX_CONNECTIONS": "20"}}' \
  > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  ConfigMap patch failed (may not exist yet)${NC}"
else
    echo -e "${GREEN}✓${NC} Set connection pool to 20 (normally 100)"
fi

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DATABASE CONFIGURATION COMPLETE${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Configuration applied:"
echo -e "  ${GREEN}✓${NC} Dropped indexes on products table"
echo -e "  ${GREEN}✓${NC} Set connection pool max to 20"
echo -e "  ${GREEN}✓${NC} Database ready for demo"
echo ""
echo -e "${YELLOW}NOTE:${NC} Pods will need to be restarted to pick up new connection pool size"
echo -e "${YELLOW}NOTE:${NC} Run the main orchestration script to complete setup"
echo ""
echo -e "${BLUE}Expected Behavior:${NC}"
echo -e "  - Product queries will be slow (2500ms+)"
echo -e "  - Connection pool will exhaust at ~120 req/min"
echo -e "  - Checkout failures will start at minute 20"
echo ""

