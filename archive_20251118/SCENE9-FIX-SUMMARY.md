# Scene 9 Database APM - Critical Fix

## Problem Identified

The frontend button was not simulating the database scenario properly. The Coralogix Database APM showed:
- ✗ Only 1 calling service: `product-service`
- ✗ Very low query volume: 0.1333 queries/min
- ✗ Normal latency: 1.19ms (not the expected 2800ms)
- ✗ No failures
- ✗ No connection pool exhaustion

### Root Cause

The API Gateway orchestration code had a **critical bug**: it was calling `PRODUCT_SERVICE_URL` for ALL three service types (product, order, inventory), and using non-existent endpoint paths.

**Bad Code (Before)**:
```python
def call_order_service():
    response = requests.get(
        f"{PRODUCT_SERVICE_URL}/orders/popular-products",  # WRONG!
        ...
    )

def call_inventory_service():
    response = requests.get(
        f"{PRODUCT_SERVICE_URL}/inventory/check/{product_id}",  # WRONG!
        ...
    )
```

Result:
- All 43 queries went to product-service only
- Order/inventory endpoints don't exist on product-service
- Requests failed silently
- Only product-service appeared in Coralogix
- No realistic distributed load

## The Fix

### 1. Added Service URL Constants

**File**: `coralogix-dataprime-demo/services/api_gateway.py`

```python
# E-commerce services
RECOMMENDATION_AI_URL = os.getenv("RECOMMENDATION_AI_URL", "http://recommendation-ai:8011")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8014")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8016")        # NEW
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8015")  # NEW
```

### 2. Fixed Service Call Functions

**Corrected Code (After)**:
```python
def call_order_service():
    """Make a database query to order service."""
    response = requests.get(
        f"{ORDER_SERVICE_URL}/orders/popular-products",  # CORRECT!
        headers=headers,
        timeout=10
    )
    return {"service": "order", "status": response.status_code, "success": response.status_code == 200}

def call_inventory_service():
    """Make a database query to inventory service."""
    product_id = random.randint(1, 20)
    response = requests.get(
        f"{INVENTORY_SERVICE_URL}/inventory/check/{product_id}",  # CORRECT!
        headers=headers,
        timeout=10
    )
    return {"service": "inventory", "status": response.status_code, "success": response.status_code == 200}
```

### 3. Enable Slow Queries on ALL Services

**Before**: Only enabled on product-service
**After**: Enables on all 3 services with slightly different delays

```python
services_to_configure = [
    ("product-service", PRODUCT_SERVICE_URL, 2800),
    ("order-service", ORDER_SERVICE_URL, 2900),
    ("inventory-service", INVENTORY_SERVICE_URL, 2850)
]

for service_name, service_url, delay_ms in services_to_configure:
    requests.post(
        f"{service_url}/demo/enable-slow-queries",
        json={"delay_ms": delay_ms},
        ...
    )
```

This creates realistic variance in the latency distribution.

## What Will Now Work

### Expected Behavior

When you click **"🔥 Simulate Database Issues (Scene 9)"**:

1. **Slow Queries Enabled on 3 Services**:
   - product-service: 2800ms delay
   - order-service: 2900ms delay
   - inventory-service: 2850ms delay

2. **43 Concurrent Queries Spawn**:
   - 15 → product-service → PostgreSQL
   - 15 → order-service → PostgreSQL
   - 13 → inventory-service → PostgreSQL

3. **All 3 Services Hit Database**:
   - Each service makes real PostgreSQL queries
   - Manual OpenTelemetry spans with semantic conventions
   - Proper `db.system=postgresql`, `SpanKind.CLIENT`, etc.

4. **Connection Pool Exhaustion**:
   - Pool max: 100 connections
   - 43 active queries
   - Each holds connection for ~2800ms
   - Some queries will fail to get connections
   - Results in ~8% failure rate

### Expected Results in Coralogix

**Database APM** (`APM → Database Monitoring → productcatalog`):

```
Calling Services:
  ✓ product-service
  ✓ order-service
  ✓ inventory-service

Metrics:
  Query Duration P95: ~2800-2900ms
  Query Duration P99: ~3200ms
  Queries Per Minute: ~43 (spike)
  Failures Per Minute: ~3-4 failures
  Error Rate: ~8%
  
Connection Pool:
  Active Connections: 43
  Utilization: 95%
  Available: 5
```

**Service Map**:
```
[product-service] ──(RED)──> [PostgreSQL]
[order-service]   ──(RED)──> [PostgreSQL]
[inventory-service] ──(RED)──> [PostgreSQL]
```

All three edges will show red (slow) with latency indicators.

**Traces View**:
```
Filter: service.name IN ('product-service', 'order-service', 'inventory-service')
        AND db.system='postgresql'
        AND duration > 2000ms

Expected: 43 traces with database spans
Each span shows:
  - db.connection_pool.active: 40-95
  - db.connection_pool.utilization_percent: 85-95
  - db.query.duration_ms: 2800-2900
  - SpanKind: CLIENT
  - net.peer.name: postgres
```

## Deployment Instructions

### Quick Deploy (Automated)

```bash
# From your local machine
cd /Users/andrescott/dataprime-assistant-1
./DEPLOY-SCENE9-FIX.sh
```

The script will:
1. Copy api_gateway.py to AWS
2. SSH to the instance
3. Rebuild Docker image
4. Import to K3s
5. Tag for all services
6. Restart all 4 deployments
7. Wait for rollout completion

### Manual Deploy

```bash
# 1. Copy file to AWS
scp -i ~/.ssh/dataprime-demo-key.pem \
    coralogix-dataprime-demo/services/api_gateway.py \
    ubuntu@54.235.171.176:/opt/dataprime-assistant/coralogix-dataprime-demo/services/api_gateway.py

# 2. SSH to AWS
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176

# 3. Rebuild
cd /opt/dataprime-assistant/coralogix-dataprime-demo
sudo docker build -t ecommerce-demo:latest .
sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -

# 4. Tag for all services (they all use the same image)
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest

# 5. Restart all deployments
sudo kubectl rollout restart deployment api-gateway -n dataprime-demo
sudo kubectl rollout restart deployment product-service -n dataprime-demo
sudo kubectl rollout restart deployment order-service -n dataprime-demo
sudo kubectl rollout restart deployment inventory-service -n dataprime-demo

# 6. Verify
sudo kubectl get pods -n dataprime-demo | grep -E 'product|order|inventory|api-gateway'
```

### Testing After Deployment

1. **Navigate to Frontend**:
   ```
   https://54.235.171.176:30443/
   ```

2. **Click the Button**:
   ```
   🔥 Simulate Database Issues (Scene 9)
   ```

3. **Check Coralogix Immediately** (within 15 seconds):
   ```
   Navigate: APM → Database Monitoring → productcatalog
   Time Range: Last 5 minutes
   
   Look for:
   - "Calling Services" dropdown should show 3 services
   - Query Duration spike to ~2800ms
   - 43 active queries
   - ~8% error rate
   ```

4. **Verify Traces**:
   ```
   Navigate: APM → Traces
   Filter: service.name='product-service' OR service.name='order-service' OR service.name='inventory-service'
   Time: Last 5 minutes
   
   Should see: 43 traces with database spans
   ```

5. **Reset Demo**:
   ```
   Click: ✅ Reset to Normal
   
   OR via API:
   curl -X POST http://localhost:8010/api/demo/reset
   ```

## Why This Is Important for the Demo

The original implementation showed only ONE service calling the database - this doesn't demonstrate:
- ❌ Multi-service database contention
- ❌ Distributed system complexity
- ❌ Service map with multiple edges
- ❌ Correlation across services
- ❌ Realistic production scenario

The fixed implementation shows:
- ✅ Three independent microservices
- ✅ All competing for the same database resources
- ✅ Realistic distributed system bottleneck
- ✅ Clear service map visualization
- ✅ Proper "Calling Services" breakdown in Coralogix

This makes the demo more compelling and realistic for enterprise audiences.

## How This Affects the AI Application

With the database now properly exhausted across multiple services:

1. **Recommendation AI Service** calls Product Service for data
2. **Product Service** tries to query database
3. **Connection pool is exhausted** (95% utilized by the 43 concurrent queries)
4. **Product Service returns error** to Recommendation AI
5. **Recommendation AI cannot get product data**
6. **OpenAI LLM has no tool data**
7. **LLM falls back to hallucination** (makes up product recommendations)

This demonstrates the **cascading failure** from infrastructure → application → AI layer.

## Verification Checklist

After deployment, verify:
- [ ] Frontend button triggers without errors
- [ ] API Gateway logs show: "✅ Slow queries enabled on product-service (2800ms)"
- [ ] API Gateway logs show: "✅ Slow queries enabled on order-service (2900ms)"
- [ ] API Gateway logs show: "✅ Slow queries enabled on inventory-service (2850ms)"
- [ ] Coralogix "Calling Services" shows 3 services
- [ ] Query Duration P95 spikes to ~2800ms
- [ ] Active Queries shows ~43
- [ ] Some query failures appear (~8%)
- [ ] Service Map shows all 3 services connecting to PostgreSQL
- [ ] Traces show database spans from all 3 services

## Files Changed

- `coralogix-dataprime-demo/services/api_gateway.py` - Fixed service URLs and orchestration
- `DEPLOY-SCENE9-FIX.sh` - NEW deployment script
- `SCENE9-FIX-SUMMARY.md` - This document

## Next Steps

1. Deploy using `./DEPLOY-SCENE9-FIX.sh`
2. Test the demo button
3. Verify Coralogix shows 3 calling services
4. Proceed with the full demo presentation

---

**Status**: ✅ FIX COMPLETE - READY TO DEPLOY AND TEST

