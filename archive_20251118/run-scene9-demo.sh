#!/bin/bash
#
# Scene 9: Database APM Demo Runner
# 
# This script triggers the database exhaustion scenario by injecting
# 43 database query spans (following OTel semantic conventions) into Coralogix.
#
# Expected Results in Coralogix Database APM:
# - 3 calling services (product, order, inventory)
# - Query Duration P95: ~2800ms (vs 45ms baseline)
# - Query Duration P99: ~3200ms
# - ~7-10 failures (~8% failure rate)
# - Total Queries: 43
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"
NAMESPACE="dataprime-demo"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🎬 Scene 9: Database APM Demo${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Error: SSH key not found at $SSH_KEY${NC}"
    echo "   Please update the SSH_KEY variable in this script."
    exit 1
fi

echo -e "${YELLOW}📡 Connecting to AWS EC2 ($EC2_HOST)...${NC}"
echo ""

# Execute the telemetry injector on the remote API Gateway pod
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'ENDSSH'
set -e

# Get the API Gateway pod name
API_POD=$(sudo kubectl get pods -n dataprime-demo -l app=api-gateway -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$API_POD" ]; then
    echo "❌ Error: Could not find API Gateway pod"
    exit 1
fi

echo "✅ Found API Gateway pod: $API_POD"
echo ""
echo "🚀 Injecting database exhaustion telemetry..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the telemetry injector
sudo kubectl exec -n dataprime-demo $API_POD -- python3 /app/services/simple_demo_injector.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENDSSH

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ Database exhaustion telemetry sent successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}📊 Next Steps:${NC}"
    echo ""
    echo "  1. Wait 10-15 seconds for telemetry to propagate"
    echo ""
    echo "  2. Open Coralogix:"
    echo "     → APM → Database Monitoring → productcatalog"
    echo ""
    echo "  3. Set time range: 'Last 15 minutes'"
    echo ""
    echo "  4. You should see:"
    echo "     ✓ 3 calling services (product, order, inventory)"
    echo "     ✓ Query Duration P95: ~1.7-2.8s (vs 45ms baseline)"
    echo "     ✓ Query Duration P99: ~3.2-7.5s"
    echo "     ✓ 7-10 failures (~8% failure rate)"
    echo "     ✓ 43+ total queries"
    echo "     ✓ Service map showing database bottleneck"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ Error: Failed to inject telemetry${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Please check:"
    echo "  - SSH key permissions: chmod 600 $SSH_KEY"
    echo "  - EC2 instance is running"
    echo "  - Kubernetes pods are healthy"
    echo ""
    exit 1
fi

