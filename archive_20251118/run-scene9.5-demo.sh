#!/bin/bash
#
# Scene 9.5: Continuous Profiling Demo Runner
#
# This script triggers the unindexed query endpoint to generate CPU load.
# The eBPF profiling agent will capture this and show it in the flame graph.
#
# Expected Results in Coralogix Continuous Profiling:
# - Flame graph showing search_products_unindexed() function
# - 99.2% CPU consumption in that function
# - The exact slow query: SELECT * FROM products WHERE description LIKE '%wireless%'
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"
NAMESPACE="dataprime-demo"
SEARCH_TERM="wireless"
ITERATIONS=50
CONCURRENT_WORKERS=10

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔥 Scene 9.5: Continuous Profiling Demo${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Triggering UNINDEXED query to generate CPU load...${NC}"
echo ""
echo "Query: SELECT * FROM products WHERE description LIKE '%${SEARCH_TERM}%'"
echo "Iterations: ${ITERATIONS} requests across ${CONCURRENT_WORKERS} concurrent workers"
echo ""

# Check SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Error: SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

echo -e "${YELLOW}📡 Connecting to AWS EC2 ($EC2_HOST)...${NC}"
echo ""

# Execute load generation on remote server
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << ENDSSH
set -e

# Get the product-service pod name
PRODUCT_POD=\$(sudo kubectl get pods -n $NAMESPACE -l app=product-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "\$PRODUCT_POD" ]; then
    echo "❌ Error: Could not find product-service pod"
    exit 1
fi

echo "✅ Found product-service pod: \$PRODUCT_POD"
echo ""
echo "🔥 Generating CPU load with unindexed queries..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create a load generation script on the pod
sudo kubectl exec -n $NAMESPACE \$PRODUCT_POD -- bash -c "cat > /tmp/generate_load.py << 'PYTHON_SCRIPT'
import requests
import time
import concurrent.futures
import sys

def make_request(i):
    try:
        url = 'http://localhost:8014/products/search?q=$SEARCH_TERM'
        start = time.time()
        response = requests.get(url, timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            products_count = len(data.get('products', []))
            query_time = data.get('query_duration_ms', 0)
            print(f'[{i:3d}] ✓ {response.status_code} - {products_count} products - {query_time:.1f}ms')
            return True
        else:
            print(f'[{i:3d}] ✗ {response.status_code}')
            return False
    except Exception as e:
        print(f'[{i:3d}] ✗ Error: {str(e)[:50]}')
        return False

print('Starting load generation...')
print(f'Target: {$ITERATIONS} requests with {$CONCURRENT_WORKERS} concurrent workers')
print('')

start_time = time.time()
success_count = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=$CONCURRENT_WORKERS) as executor:
    futures = [executor.submit(make_request, i) for i in range(1, $ITERATIONS + 1)]
    
    for future in concurrent.futures.as_completed(futures):
        if future.result():
            success_count += 1

duration = time.time() - start_time

print('')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print(f'Completed: {success_count}/{$ITERATIONS} successful requests')
print(f'Duration: {duration:.1f}s')
print(f'Rate: {$ITERATIONS/duration:.1f} req/s')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
PYTHON_SCRIPT
"

# Run the load generation script
sudo kubectl exec -n $NAMESPACE \$PRODUCT_POD -- python3 /tmp/generate_load.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ENDSSH

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ CPU load generated successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}📊 Next Steps:${NC}"
    echo ""
    echo "  1. Wait 30-60 seconds for profiling data to propagate"
    echo ""
    echo "  2. Open Coralogix:"
    echo "     → APM → Continuous Profiling → product-service"
    echo ""
    echo "  3. Look for the flame graph showing:"
    echo "     • search_products_unindexed() function"
    echo "     • High CPU consumption (99.2%)"
    echo "     • The unindexed LIKE query on description field"
    echo ""
    echo "  4. Demo Talk Track:"
    echo "     'Database APM showed us WHAT is slow - a query taking 2900ms.'"
    echo "     'But it doesn't show WHERE in the code. Let me check Continuous Profiling...'"
    echo "     '[Open flame graph]'"
    echo "     'Here's our product-service. Look at search_products_unindexed()'"
    echo "     'consuming 99.2% of CPU time. Click into it...'"
    echo "     'And here's the culprit: SELECT * FROM products WHERE description LIKE \"%wireless%\"'"
    echo "     'This is a full table scan. There's no index on the description field.'"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ Error: Failed to generate load${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    exit 1
fi

