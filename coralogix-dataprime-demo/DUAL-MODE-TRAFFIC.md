# Dual-Mode Traffic Architecture - Black Friday Demo V4

## Overview

The Black Friday Demo V4 implements a **dual-mode traffic architecture** that runs two types of traffic simultaneously:

1. **Baseline Traffic**: 100 rpm to `/products` endpoint (fast, indexed) - always healthy
2. **Demo Traffic**: 800→4200 rpm to `/products/recommendations` endpoint (slow, unindexed) - progressive failures

This architecture creates a compelling narrative by proving the system works (baseline stays green) while demonstrating how a specific new feature fails under load (demo turns red).

## Why Dual-Mode Matters

### Without Baseline Traffic
- System fails during demo
- Audience thinks: "Maybe it's just broken?"
- No proof the infrastructure is healthy
- Hard to isolate the root cause

### With Baseline Traffic
- Baseline traffic (green) stays healthy throughout demo
- Demo traffic (red) fails progressively
- Audience sees: "The system works - the NEW FEATURE is the problem"
- Clear isolation: Not infrastructure, not DB capacity - it's the unindexed query

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Load Generator                     │
│                     (Port 8010)                      │
└────────────┬───────────────────────────┬────────────┘
             │                           │
             │ Baseline: 100 rpm         │ Demo: 800→4200 rpm
             │ Always healthy            │ Progressive failures
             │                           │
             ▼                           ▼
┌────────────────────────┐    ┌────────────────────────┐
│   GET /products        │    │ GET /products/         │
│   (Fast, indexed)      │    │ recommendations        │
│   ✅ 0% errors         │    │ (Slow, no index)       │
│   ✅ ~50ms latency     │    │ 🔴 Up to 78% errors    │
└────────────┬───────────┘    └───────────┬────────────┘
             │                             │
             └──────────┬──────────────────┘
                        ▼
             ┌────────────────────┐
             │ Product Catalog    │
             │    (Port 8014)     │
             │                    │
             │ Routes to:         │
             │ • Fast queries     │ ← Baseline
             │ • Slow queries     │ ← Demo
             └─────────┬──────────┘
                       │
                       ▼
             ┌────────────────────┐
             │    PostgreSQL      │
             │                    │
             │ Baseline queries:  │
             │ • Use index        │
             │ • Fast (50ms)      │
             │                    │
             │ Demo queries:      │
             │ • No index         │
             │ • Slow (3,200ms)   │
             └────────────────────┘
```

## Traffic Comparison

| Time (min) | Baseline RPM | Demo RPM | Total RPM | Baseline Errors | Demo Errors |
|------------|--------------|----------|-----------|-----------------|-------------|
| 0          | 100          | 0        | 100       | 0%              | 0%          |
| 1          | 100          | 800      | 900       | 0%              | 2%          |
| 5          | 100          | 2100     | 2200      | 0%              | 15%         |
| 10         | 100          | 3400     | 3500      | 0%              | 45%         |
| 15         | 100          | 4200     | 4300      | 0%              | 65%         |
| 20         | 100          | 4200     | 4300      | 0%              | **78%** 🔴  |
| 25         | 100          | 4200     | 4300      | 0%              | **78%** 🚨  |

## Endpoint Comparison

### Baseline Endpoint: `/products`

**Purpose**: Fast, indexed queries for normal product browsing

**Characteristics**:
- Uses proper index: `idx_products_category_active`
- Query time: 50-120ms
- Error rate: 0-2% (minimal)
- Traffic type: `baseline`
- Always healthy

**SQL**:
```sql
SELECT * FROM products WHERE category = %s LIMIT 50;
-- Uses: idx_products_category_active
-- Execution time: ~50ms
```

### Demo Endpoint: `/products/recommendations`

**Purpose**: Slow, unindexed queries simulating a new recommendation feature

**Characteristics**:
- Missing index on `category` + `active` + `price` + `popularity`
- Query time: 100ms → 2800ms (progressive)
- Error rate: 2% → 78% (progressive)
- Traffic type: `demo`
- Progressive degradation

**SQL**:
```sql
SELECT * FROM products 
WHERE category = %s 
  AND active = true 
  AND price BETWEEN %s AND %s 
ORDER BY popularity DESC 
LIMIT 10;
-- Missing: idx_products_category (composite index)
-- Execution time: ~2,500ms (full table scan on 500K rows)
```

## Implementation Details

### Load Generator (Auto-Start)

The load generator automatically starts both traffic streams when the service starts:

```python
# Starts automatically in main block
if __name__ == '__main__':
    start_dual_mode_on_startup()
    app.run(host='0.0.0.0', port=8010)
```

**Baseline Traffic**:
- 100 requests per minute (constant)
- Targets: `http://product-catalog:8014/products`
- Parameters: `category=electronics`
- Timeout: 2 seconds
- Expected: 0% errors, ~50ms latency

**Demo Traffic**:
- 800 → 4200 requests per minute (progressive)
- Targets: `http://product-catalog:8014/products/recommendations`
- Parameters: `category=electronics`, `user_id=user-XXXX`
- Timeout: 6 seconds
- Expected: 0% → 78% errors, 50ms → 3,200ms latency

### Product Catalog Service

**Baseline Handler**:
```python
@app.route('/products', methods=['GET'])
def get_products():
    with tracer.start_as_current_span("get_products_from_db") as span:
        span.set_attribute("traffic.type", "baseline")
        span.set_attribute("endpoint.type", "fast_indexed")
        span.set_attribute("db.index_used", "idx_products_category_active")
        # Fast query execution (50-120ms)
```

**Demo Handler**:
```python
@app.route('/products/recommendations', methods=['GET'])
def get_product_recommendations():
    demo_minute = calculate_demo_minute()
    
    # Progressive delays
    if demo_minute < 10:
        delay_ms = random.uniform(100, 300)
        failure_rate = 0.02
    elif demo_minute < 15:
        delay_ms = random.uniform(500, 1200)
        failure_rate = 0.15
    # ... continues to 78% at minute 20+
```

### Checkout Service Integration

The checkout service calls the recommendation endpoint during checkout, **blocking the order** if it times out:

```python
if is_demo_mode() and demo_minute >= 1:
    try:
        rec_response = requests.get(
            f"{PRODUCT_CATALOG_URL}/products/recommendations",
            timeout=5
        )
    except requests.exceptions.Timeout:
        # Checkout FAILS
        DemoSpanAttributes.set_checkout_failed(
            span=main_span,
            failure_reason="product-recommendations-timeout"
        )
        return jsonify({"error": "Checkout failed"}), 503
```

## OpenTelemetry Span Attributes

### Critical for Filtering

Every span MUST include `traffic.type` attribute:

```python
span.set_attribute("traffic.type", "baseline")  # or "demo"
```

This enables filtering in Coralogix:
- `traffic.type = "baseline"` → Shows healthy system behavior
- `traffic.type = "demo"` → Shows failure behavior
- Both visible → Shows the contrast

### Complete Attribute Set

**Baseline Traffic**:
```python
span.set_attribute("traffic.type", "baseline")
span.set_attribute("endpoint.type", "fast_indexed")
span.set_attribute("db.index_used", "idx_products_category_active")
```

**Demo Traffic**:
```python
span.set_attribute("traffic.type", "demo")
span.set_attribute("endpoint.type", "slow_unindexed")
span.set_attribute("db.index_used", "NONE")
span.set_attribute("demo.minute", demo_minute)
span.set_attribute("demo.phase", phase)
```

## Demo Presentation Flow

### Act 1: The Calm (0:00 - 1:30)

**Show**: Coralogix APM > Service Catalog > product-catalog

**Filter**: `traffic.type = "baseline"`

```
✅ Product Catalog: 0% errors, 54ms P95
✅ Throughput: 100 rpm (steady)
✅ All green - system is healthy
```

**Narrative**: 
*"Here's our product catalog service during normal operations. You can see baseline traffic is completely healthy - zero errors, fast response times. The system works perfectly fine."*

### Act 2: Black Friday Begins (1:30 - 3:00)

**Show**: Coralogix APM > Service Catalog > product-catalog

**Filter**: `traffic.type = "demo"`

```
🟡 Product Catalog: 15% errors, 1,200ms P95
📈 Throughput: 3,400 rpm (ramping)
```

**Switch Filter**: `traffic.type = "baseline"`

```
✅ Still healthy! Error rate: 0.1%
✅ Still fast! P95 latency: 52ms
```

**Narrative**:
*"Black Friday traffic is starting to hit. Notice demo traffic is experiencing delays and some errors. But here's the key - baseline traffic is STILL healthy. This immediately tells us it's not an infrastructure problem."*

### Act 3: The Catastrophe (3:00 - 5:00)

**Show**: Split screen - baseline vs demo

```
LEFT: traffic.type = "baseline"       RIGHT: traffic.type = "demo"
✅ Error rate: 0.2%                     🔴 Error rate: 78%
✅ P95: 55ms                            🔴 P95: 3,247ms
✅ Throughput: 100 rpm                  🔴 Throughput: 4,200 rpm
```

**Show**: Flow Alert triggered

**Narrative**:
*"Now we're in full Black Friday mode. The demo traffic has completely collapsed - 78% error rate, 3+ second latencies. But look at baseline - still perfect. This proves our database can handle the queries when they use the proper index. The problem is the new recommendation feature isn't using the index."*

### Act 4: The Investigation (5:00 - 8:00)

**Show**: Distributed Tracing - Compare two traces side by side

**Baseline Trace**:
```
✅ GET /products (52ms, OK)
   └─ ✅ SELECT ecommerce.products (35ms, OK)
       └─ 🏷️ db.index_used: idx_products_category_active
```

**Demo Trace**:
```
🔴 GET /products/recommendations (5,530ms, ERROR)
   └─ 🔴 SELECT ecommerce.products (3,730ms, ERROR)
       ├─ ⏱️ Connection pool wait: 2,100ms
       ├─ ⏱️ Query execution: 1,100ms
       └─ 🏷️ db.full_table_scan: true
           🏷️ db.missing_index: idx_products_category
           🏷️ db.rows_scanned: 487,342
```

**Narrative**:
*"Here's the smoking gun. The recommendation endpoint does a full table scan on 487,000 rows without using an index. The baseline endpoint uses a proper index and completes in 35ms. Same database, same data, completely different performance."*

## Manual Validation Steps

### Step 1: Verify Baseline Health (Before Demo)

```bash
# In Coralogix: APM > Service Catalog > product-catalog
# Filter: traffic.type = "baseline"

Expected:
- Error rate: 0-2%
- P95 latency: 50-120ms
- Throughput: ~100 rpm
- Status: Green
```

### Step 2: Start Demo Mode

```bash
# Generate Unix timestamp
TIMESTAMP=$(date +%s)

# Update all deployments
kubectl set env deployment/product-catalog -n ecommerce-demo \
  DEMO_START_TIMESTAMP=$TIMESTAMP \
  DEMO_MODE=blackfriday

kubectl set env deployment/load-generator -n ecommerce-demo \
  DEMO_START_TIMESTAMP=$TIMESTAMP \
  DEMO_MODE=blackfriday

kubectl set env deployment/checkout -n ecommerce-demo \
  DEMO_START_TIMESTAMP=$TIMESTAMP \
  DEMO_MODE=blackfriday
```

### Step 3: Verify Dual-Mode (Minute 10)

```bash
# In Coralogix: Split screen or two tabs

Left: traffic.type = "baseline"
✅ Error rate: 0-2%
✅ P95 latency: ~50ms
✅ Status: Green

Right: traffic.type = "demo"
🟡 Error rate: ~15%
🟡 P95 latency: ~1,200ms
🟡 Status: Yellow
```

### Step 4: Verify Critical Phase (Minute 22)

```bash
# In Coralogix APM

Baseline (traffic.type = "baseline"):
✅ Error rate: 0-2%
✅ P95: ~50ms
✅ Status: Green

Demo (traffic.type = "demo"):
🔴 Error rate: ~78%
🔴 P95: ~3,200ms
🔴 Status: Red

# Check for Flow Alert trigger
# Examine distributed traces showing the difference
```

## Validation Commands

### Check Traffic Stats

```bash
# Get load generator pod
LOAD_POD=$(kubectl get pods -n ecommerce-demo -l app=load-generator \
  -o jsonpath='{.items[0].metadata.name}')

# Check traffic statistics
kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://localhost:8010/admin/traffic-stats | jq
```

**Expected Output**:
```json
{
  "baseline": {
    "rpm": 100,
    "requests": 15234,
    "errors": 12,
    "error_rate": "0.1%"
  },
  "demo": {
    "current_rpm": 4200,
    "demo_minute": 22,
    "requests": 87432,
    "errors": 68197,
    "error_rate": "78.0%"
  }
}
```

### Test Endpoints Manually

```bash
# Test baseline endpoint
kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/products?category=electronics

# Test demo endpoint
kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/products/recommendations?category=electronics

# Check health with dual-mode info
kubectl exec -n ecommerce-demo $LOAD_POD -- \
  curl -s http://product-catalog:8014/health | jq
```

### Run Full Validation Script

```bash
./scripts/validate-dual-mode.sh
```

## Success Criteria

### Baseline Traffic (Always)
- ✅ 100 rpm constant throughput
- ✅ 0-2% error rate maintained
- ✅ 50-120ms P95 latency
- ✅ Green health status throughout entire demo

### Demo Traffic (Progressive)
- ✅ 800 rpm starting, ramping to 4200 rpm by minute 10
- ✅ 2% → 78% error rate increase
- ✅ 50ms → 3,200ms latency increase
- ✅ Yellow → Red health status transition

### Coralogix Validation
- ✅ Can filter by `traffic.type` attribute
- ✅ Database spans show clear performance difference
- ✅ Checkout failures correlate with recommendation timeouts
- ✅ Flow Alert triggers at minute 22-23
- ✅ Traces clearly show baseline vs demo behavior

## Troubleshooting

### Baseline Traffic Failing

**Issue**: Baseline traffic shows errors

**Cause**: Usually configuration issue or database problem

**Fix**:
1. Check product-catalog logs for errors
2. Verify database is accessible
3. Confirm baseline endpoint is correct: `/products`

### Demo Traffic Not Failing

**Issue**: Demo traffic stays healthy (should fail)

**Cause**: Demo mode not enabled or timing issues

**Fix**:
```bash
# Verify demo mode is enabled
kubectl get configmap -n ecommerce-demo ecommerce-config -o yaml | grep DEMO

# Check demo minute calculation
kubectl logs -n ecommerce-demo -l app=product-catalog | grep demo_minute
```

### No Traffic Stats

**Issue**: `/admin/traffic-stats` returns empty or error

**Cause**: Load generator not started or dual-mode not initialized

**Fix**:
```bash
# Restart load generator
kubectl rollout restart deployment/load-generator -n ecommerce-demo

# Check logs
kubectl logs -n ecommerce-demo -l app=load-generator | grep "dual_mode"
```

### Traces Not Correlating

**Issue**: Baseline and demo traces don't show parent-child relationships

**Cause**: Trace context not propagating

**Fix**:
1. Verify `extract_and_attach_trace_context()` is called FIRST in all handlers
2. Check `propagate_trace_context()` is used when making HTTP calls
3. Look for `traceparent` header in logs

## Configuration Reference

### Environment Variables

```yaml
# Baseline Traffic
BASELINE_ENABLED: "true"
BASELINE_RPM: "100"
BASELINE_ENDPOINT: "/products"

# Demo Traffic
DEMO_ENDPOINT: "/products/recommendations"
DEMO_BASE_RPM: "800"
DEMO_PEAK_RPM: "4200"
DEMO_START_TIMESTAMP: ""  # Unix timestamp
DEMO_DURATION_MINUTES: "30"
DEMO_MODE: "blackfriday"
```

### Service URLs

```yaml
PRODUCT_CATALOG_URL: "http://product-catalog:8014"
CHECKOUT_URL: "http://checkout:8016"
```

## References

- **Load Generator**: `services/load_generator.py` (DualModeLoadGenerator class)
- **Product Catalog**: `services/product_catalog_service.py` (/products and /products/recommendations)
- **Checkout**: `services/checkout_service.py` (recommendation blocking call)
- **Validation Script**: `scripts/validate-dual-mode.sh`
- **ConfigMap**: `deployment/kubernetes/configmap.yaml`

---

**Last Updated**: November 23, 2025  
**Version**: 4.0 (Dual-Mode)  
**Maintainer**: Coralogix Demo Team

