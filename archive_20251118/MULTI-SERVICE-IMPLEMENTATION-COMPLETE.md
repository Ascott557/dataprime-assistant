# Multi-Service Database Load Demo - Implementation Complete

**Date:** November 16, 2025  
**Status:** ✅ COMPLETE - Ready to Deploy

---

## Summary

I've successfully implemented **2 additional microservices** to demonstrate realistic database load patterns for your re:Invent 2025 demo. All services share the same PostgreSQL database and connection pool, enabling powerful demonstrations of:

1. **Multiple services accessing one database**
2. **Connection pool exhaustion** (95/100 connections)
3. **Complete visibility in Coralogix Database Monitoring**

---

## What Was Created

### 🆕 New Services

#### 1. Inventory Service (Port 30015)
- **File:** `coralogix-dataprime-demo/services/inventory_service.py`
- **Purpose:** Stock management and inventory control
- **Database Operations:**
  - `SELECT` - Check product stock levels
  - `UPDATE` - Reserve stock (decrease quantity)
- **Endpoints:**
  - `GET /inventory/check/<product_id>` - Check stock
  - `POST /inventory/reserve` - Reserve inventory
  - `GET /health` - Health + pool stats
  - `POST /demo/enable-slow-queries`
  - `POST /demo/simulate-pool-exhaustion`
  - `POST /demo/reset`

#### 2. Order Service (Port 30016)
- **File:** `coralogix-dataprime-demo/services/order_service.py`
- **Purpose:** Order management and product popularity analytics
- **Database Operations:**
  - `SELECT` with `JOIN` and `GROUP BY` - Aggregate order data
  - `INSERT` - Create new orders
- **Endpoints:**
  - `GET /orders/popular-products?limit=N` - Most ordered products
  - `POST /orders/create` - Create order
  - `GET /health` - Health + pool stats
  - `POST /demo/enable-slow-queries`
  - `POST /demo/simulate-pool-exhaustion`
  - `POST /demo/reset`
- **New Database Table:** `orders` (with 10 sample records)

---

## 🎯 Key Features

### 1. Exact Same Manual Instrumentation Pattern

All services use the **PROVEN pattern from product_service.py:**

```python
# Extract trace context (for distributed tracing)
token, is_root = extract_and_attach_trace_context()

# Main span
with tracer.start_as_current_span("service_name.operation") as main_span:
    # Add connection pool metrics
    pool_stats = get_pool_stats()
    main_span.set_attribute("db.connection_pool.active", pool_stats["active_connections"])
    main_span.set_attribute("db.connection_pool.utilization_percent", pool_stats["utilization_percent"])
    
    # Database span with ALL required attributes
    with tracer.start_as_current_span(
        "SELECT productcatalog.products",  # OTel naming convention
        kind=SpanKind.CLIENT  # REQUIRED
    ) as db_span:
        # ALL 5 REQUIRED attributes for Coralogix Database Monitoring
        db_span.set_attribute("db.system", "postgresql")
        db_span.set_attribute("db.name", "productcatalog")
        db_span.set_attribute("db.operation", "SELECT")
        db_span.set_attribute("db.statement", "SELECT * FROM products...")
        db_span.set_attribute("net.peer.name", "postgres")
        
        # Execute query
        cursor.execute(query, params)
```

### 2. Shared Connection Pool

All 3 services use:
- `ThreadedConnectionPool(minconn=5, maxconn=100)`
- Same PostgreSQL connection details
- Compete for the same 100 connections
- Report pool metrics in every span

### 3. Demo Simulation Support

Each service supports:
- **Slow queries:** Add 2900ms delay to any query
- **Pool exhaustion:** Hold 95 connections
- **Reset:** Return to normal operation
- **Health checks:** Report pool utilization

---

## 📦 Files Created

### Service Code
1. ✅ `coralogix-dataprime-demo/services/inventory_service.py` (580 lines)
2. ✅ `coralogix-dataprime-demo/services/order_service.py` (620 lines)

### Kubernetes Manifests
3. ✅ `deployment/kubernetes/deployments/inventory-service.yaml`
4. ✅ `deployment/kubernetes/deployments/order-service.yaml`
5. ✅ `deployment/kubernetes/services.yaml` (updated with NodePorts 30015, 30016)
6. ✅ `deployment/kubernetes/postgres.yaml` (updated with orders table init)

### Scripts & Documentation
7. ✅ `scripts/deploy-multi-service-db-demo.sh` (automated deployment)
8. ✅ `MULTI-SERVICE-DATABASE-DEMO.md` (comprehensive guide)
9. ✅ `REINVENT-DEMO-QUICK-REFERENCE.md` (quick reference)
10. ✅ `MULTI-SERVICE-IMPLEMENTATION-COMPLETE.md` (this file)

---

## 🚀 How to Deploy

### One-Command Deploy

```bash
./scripts/deploy-multi-service-db-demo.sh 54.235.171.176
```

**This script will:**
1. Package both new services
2. Upload to EC2
3. Build Docker images for AMD64
4. Import images to K3s
5. Update PostgreSQL with orders table
6. Deploy services to K3s
7. Run test requests
8. Display demo commands

**Estimated time:** 5-7 minutes

---

## 🧪 How to Test

### Basic Functionality

```bash
# 1. Check inventory for product 5
curl http://54.235.171.176:30015/inventory/check/5

# 2. Get popular products
curl http://54.235.171.176:30016/orders/popular-products?limit=5

# 3. Create an order
curl -X POST http://54.235.171.176:30016/orders/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo_user","product_id":5,"quantity":2}'

# 4. Reserve inventory
curl -X POST http://54.235.171.176:30015/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"product_id":5,"quantity":1}'
```

### Demo Scenarios

#### Scenario 1: Slow Queries (Performance Degradation)

```bash
# Enable 2900ms delays on all services
curl -X POST http://54.235.171.176:30015/demo/enable-slow-queries -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30016/demo/enable-slow-queries -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30010/demo/enable-slow-queries -d '{"delay_ms":2900}'

# Now make requests (each takes ~3 seconds)
curl http://54.235.171.176:30015/inventory/check/5
```

#### Scenario 2: Connection Pool Exhaustion (Catastrophic)

```bash
# Exhaust the pool (95 of 100 connections)
curl -X POST http://54.235.171.176:30015/demo/simulate-pool-exhaustion

# Check pool status
curl http://54.235.171.176:30015/health | jq '.connection_pool'
# Output: {"active_connections":95,"max_connections":100,"utilization_percent":95.0}

# Try to use services (they compete for 5 remaining connections!)
curl http://54.235.171.176:30016/orders/popular-products?limit=5
```

#### Reset

```bash
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
curl -X POST http://54.235.171.176:30010/demo/reset
```

---

## 🔍 Verification in Coralogix

### Wait 2-3 minutes after deployment, then:

1. **Navigate to:** APM → Database Catalog → `productcatalog`

2. **Verify "Calling Services" shows ALL 3:**
   - ✅ product-service
   - ✅ inventory-service ⭐ NEW
   - ✅ order-service ⭐ NEW

3. **Check operations:**
   - product-service: `SELECT products`
   - inventory-service: `SELECT products`, `UPDATE products` ⭐
   - order-service: `SELECT orders`, `INSERT orders` ⭐

4. **View metrics:**
   - Query Time Average (should spike to 2900ms in slow query demo)
   - Total Queries (increases as you make requests)
   - Connection pool utilization (95% in exhaustion demo)

5. **Click on any operation to see:**
   - Individual query details
   - Query duration
   - Row counts
   - Full trace links

---

## 📊 What You'll See in Coralogix

### Database Catalog View

```
productcatalog (PostgreSQL)
├─ Calling Services: 3
│  ├─ product-service
│  ├─ inventory-service ⭐
│  └─ order-service ⭐
├─ Average Latency: 10-20ms (baseline) or 2900ms (slow query demo)
├─ Total Queries: 50+
├─ Operations:
│  ├─ SELECT products (product-service, inventory-service)
│  ├─ UPDATE products (inventory-service) ⭐
│  ├─ SELECT orders (order-service) ⭐
│  └─ INSERT orders (order-service) ⭐
└─ Connection Pool:
   ├─ Active: 3-5 (baseline) or 95 (exhaustion demo)
   └─ Utilization: 3-5% or 95%
```

### Trace View

When you click on a database span, you'll see:

```json
{
  "span_name": "SELECT productcatalog.products",
  "span_kind": "CLIENT",
  "attributes": {
    "db.system": "postgresql",
    "db.name": "productcatalog",
    "db.operation": "SELECT",
    "db.statement": "SELECT id, name, stock_quantity FROM products WHERE id = %s",
    "db.sql.table": "products",
    "net.peer.name": "postgres",
    "db.user": "dbadmin",
    "db.query.duration_ms": 8.5,
    "db.rows_returned": 1,
    "db.connection_pool.active": 3,
    "db.connection_pool.max": 100,
    "db.connection_pool.utilization_percent": 3.0
  }
}
```

---

## 🎯 Demo Talking Points

### 1. Architecture
"We have 3 microservices - product, inventory, and orders - all sharing a single PostgreSQL database with a 100-connection pool."

### 2. Observability
"Every database query from every service is instrumented with complete Coralogix Database Monitoring attributes, including connection pool metrics."

### 3. Normal Operations
"Under normal load, all services perform well with 5-20ms query times and 3-5% pool utilization."

### 4. Performance Degradation
"When we enable slow queries, all services are affected. Coralogix shows the query time spike to 2900ms across all services."

### 5. Catastrophic Failure
"When we exhaust the connection pool - holding 95 of 100 connections - new requests must queue or timeout. All services compete for the remaining 5 connections."

### 6. Complete Visibility
"In Coralogix Database Monitoring, we can see all 3 services, their operations, query patterns, and connection pool utilization in real-time."

---

## ✅ Success Criteria

All of these should be true after deployment:

- [ ] inventory-service pod running
- [ ] order-service pod running  
- [ ] product-service pod running (existing)
- [ ] PostgreSQL has orders table with sample data
- [ ] All services accessible via NodePorts (30010, 30015, 30016)
- [ ] All health endpoints return 200 OK
- [ ] Connection pool shows max=100 in all services
- [ ] Can check inventory for products
- [ ] Can reserve inventory
- [ ] Can get popular products
- [ ] Can create new orders
- [ ] Slow query simulation works on all services
- [ ] Pool exhaustion simulation works
- [ ] All 3 services visible in Coralogix Database Monitoring
- [ ] All database spans have required attributes
- [ ] Connection pool metrics visible in spans

---

## 🔧 Troubleshooting

### If deployment fails:

```bash
# Check pod status
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176
sudo kubectl get pods -n dataprime-demo | grep -E "inventory|order|product"

# Check logs
sudo kubectl logs -n dataprime-demo -l app=inventory-service --tail=50
sudo kubectl logs -n dataprime-demo -l app=order-service --tail=50
```

### If services don't appear in Coralogix:

1. Wait 2-3 minutes for data to arrive
2. Make several requests to generate data
3. Check trace view to verify span attributes
4. Verify spans have `kind=CLIENT`
5. Verify all 5 required attributes are present

### If orders table is missing:

```bash
# Manually create it
POD=$(sudo kubectl get pods -n dataprime-demo -l app=postgres -o jsonpath='{.items[0].metadata.name}')
sudo kubectl exec -n dataprime-demo $POD -- psql -U dbadmin -d productcatalog -c "
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"
```

---

## 📚 Documentation

- **Comprehensive Guide:** `MULTI-SERVICE-DATABASE-DEMO.md`
- **Quick Reference:** `REINVENT-DEMO-QUICK-REFERENCE.md`
- **This Summary:** `MULTI-SERVICE-IMPLEMENTATION-COMPLETE.md`

---

## 🎉 Summary

✅ **2 new services created** with identical manual instrumentation  
✅ **All services share the same connection pool** (maxconn=100)  
✅ **Complete Coralogix Database Monitoring** with all required attributes  
✅ **Demo scenarios ready:** normal, slow queries, pool exhaustion  
✅ **One-command deployment** script included  
✅ **Comprehensive documentation** for demo and troubleshooting  

---

## 🚀 Ready to Deploy!

```bash
./scripts/deploy-multi-service-db-demo.sh 54.235.171.176
```

After deployment:
1. Wait 2-3 minutes
2. Test endpoints
3. Verify in Coralogix Database Monitoring
4. Run demo scenarios

**You're ready for re:Invent 2025!** 🎯

