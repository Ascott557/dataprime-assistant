# Multi-Service Database Load Demo for re:Invent 2025

**Purpose:** Demonstrate realistic database load patterns with multiple microservices sharing a PostgreSQL database, showcasing Coralogix Database Monitoring and connection pool exhaustion scenarios.

**Date:** November 16, 2025  
**Status:** ✅ Ready to Deploy

---

## Architecture Overview

### Before: Single Service
```
┌─────────────────┐
│ product-service │──┐
└─────────────────┘  │
                     ▼
              ┌──────────────┐
              │  PostgreSQL  │
              │  Pool: 100   │
              └──────────────┘
```

### After: Multi-Service Load
```
┌─────────────────┐
│ product-service │──┐
└─────────────────┘  │
                     │
┌──────────────────┐ │
│inventory-service │─┼──▶ ┌──────────────┐
└──────────────────┘ │    │  PostgreSQL  │
                     │    │  Pool: 100   │
┌──────────────────┐ │    │  SHARED!     │
│  order-service   │─┘    └──────────────┘
└──────────────────┘
```

**Key Point:** All 3 services share the SAME ThreadedConnectionPool(maxconn=100)

---

## New Services

### 1. Inventory Service (Port 30015)

**Purpose:** Check and manage product stock levels

**Database Operations:**
- `SELECT stock_quantity FROM products WHERE id = %s` (READ)
- `UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s` (WRITE)

**Endpoints:**
- `GET /inventory/check/<product_id>` - Check stock for a product
- `POST /inventory/reserve` - Reserve stock (decrease quantity)
- `GET /health` - Health check with connection pool stats
- `GET /stats` - Service statistics
- `POST /demo/enable-slow-queries` - Enable 2900ms delays
- `POST /demo/simulate-pool-exhaustion` - Hold 95 connections
- `POST /demo/reset` - Reset all demo modes

**Example Request:**
```bash
curl http://54.235.171.176:30015/inventory/check/5
```

**Example Response:**
```json
{
  "product_id": 5,
  "product_name": "JBL Tune 510BT",
  "stock_quantity": 150,
  "in_stock": true
}
```

---

### 2. Order Service (Port 30016)

**Purpose:** Query order history and product popularity

**Database Operations:**
- `SELECT product_id, COUNT(*) FROM orders GROUP BY product_id` (AGGREGATE)
- `INSERT INTO orders (user_id, product_id, quantity) VALUES (%s, %s, %s)` (WRITE)

**New Database Table: `orders`**
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

**Endpoints:**
- `GET /orders/popular-products?limit=N` - Get most ordered products
- `POST /orders/create` - Create a new order
- `GET /health` - Health check with connection pool stats
- `GET /stats` - Service statistics
- `POST /demo/enable-slow-queries` - Enable 2900ms delays
- `POST /demo/simulate-pool-exhaustion` - Hold 95 connections
- `POST /demo/reset` - Reset all demo modes

**Example Request:**
```bash
curl http://54.235.171.176:30016/orders/popular-products?limit=5
```

**Example Response:**
```json
{
  "popular_products": [
    {
      "product_id": 5,
      "product_name": "JBL Tune 510BT",
      "order_count": 5
    },
    {
      "product_id": 6,
      "product_name": "Anker Soundcore Q30",
      "order_count": 3
    }
  ],
  "count": 2
}
```

---

## OpenTelemetry Instrumentation

All services use the **EXACT SAME manual instrumentation pattern** from `product_service.py`:

### Required Coralogix Database Monitoring Attributes

```python
from opentelemetry.trace import SpanKind

with tracer.start_as_current_span(
    "SELECT productcatalog.products",  # OTel naming: {operation} {db.name}.{table}
    kind=SpanKind.CLIENT  # REQUIRED: Database client span
) as db_span:
    # REQUIRED attributes
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", "productcatalog")
    db_span.set_attribute("db.operation", "SELECT")  # or UPDATE, INSERT
    db_span.set_attribute("db.statement", "SELECT * FROM products...")
    db_span.set_attribute("net.peer.name", "postgres")
    
    # Additional recommended attributes
    db_span.set_attribute("db.sql.table", "products")
    db_span.set_attribute("db.user", "dbadmin")
    
    # Connection pool metrics
    db_span.set_attribute("db.connection_pool.active", active_connections)
    db_span.set_attribute("db.connection_pool.max", 100)
    db_span.set_attribute("db.connection_pool.utilization_percent", utilization)
```

### Trace Context Propagation

All services use `extract_and_attach_trace_context()` to:
1. Extract trace context from incoming requests
2. Attach to the current context
3. Ensure spans are children of the calling service

This creates a complete distributed trace across all services.

---

## Deployment

### Quick Deploy

```bash
./scripts/deploy-multi-service-db-demo.sh 54.235.171.176
```

This script will:
1. Package the new services
2. Upload to EC2
3. Build Docker images
4. Update PostgreSQL schema
5. Deploy services to K3s
6. Run test requests

### Manual Steps

If you need to deploy manually:

```bash
# 1. Build images on EC2
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

cd /home/ubuntu
sudo docker build --platform linux/amd64 -f Dockerfile -t inventory-service:latest .
sudo docker build --platform linux/amd64 -f Dockerfile -t order-service:latest .

# 2. Import to K3s
sudo docker save docker.io/library/inventory-service:latest | sudo k3s ctr images import -
sudo docker save docker.io/library/order-service:latest | sudo k3s ctr images import -

# 3. Apply manifests
sudo kubectl apply -f deployment/kubernetes/postgres.yaml
sudo kubectl apply -f deployment/kubernetes/services.yaml
sudo kubectl apply -f deployment/kubernetes/deployments/inventory-service.yaml
sudo kubectl apply -f deployment/kubernetes/deployments/order-service.yaml

# 4. Verify
sudo kubectl get pods -n dataprime-demo | grep -E "inventory|order|product"
```

---

## Demo Scenarios

### Scenario 1: Normal Load - All Services Working

```bash
# Check product stock
curl http://54.235.171.176:30015/inventory/check/5

# Get popular products
curl http://54.235.171.176:30016/orders/popular-products?limit=5

# Get products by category
curl "http://54.235.171.176:30010/products?category=Wireless%20Headphones&price_min=0&price_max=100"
```

**Expected in Coralogix:**
- All 3 services appear in Database Monitoring "Calling Services"
- Query times: 5-20ms
- Connection pool utilization: 3-5%

---

### Scenario 2: Slow Queries - Database Performance Issues

```bash
# Enable slow queries on ALL services (2900ms delay)
curl -X POST http://54.235.171.176:30015/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30016/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30010/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'

# Now make requests
curl http://54.235.171.176:30015/inventory/check/5  # Takes 2900ms
curl http://54.235.171.176:30016/orders/popular-products?limit=5  # Takes 2900ms
```

**Expected in Coralogix:**
- Query duration spikes to 2900ms for ALL services
- Database Monitoring shows slow query patterns
- Span attributes include `db.simulation.slow_query_enabled: true`

---

### Scenario 3: Connection Pool Exhaustion

```bash
# Exhaust the connection pool (hold 95 of 100 connections)
curl -X POST http://54.235.171.176:30015/demo/simulate-pool-exhaustion

# Check pool status
curl http://54.235.171.176:30015/health | jq '.connection_pool'
curl http://54.235.171.176:30016/health | jq '.connection_pool'
curl http://54.235.171.176:30010/health | jq '.connection_pool'

# Try to make requests (they'll queue or timeout)
curl http://54.235.171.176:30016/orders/popular-products?limit=5
```

**Expected Behavior:**
- Connection pool shows 95/100 active connections
- New requests must wait for available connections
- Timeout errors may occur (ConnectionError: Could not acquire connection within 3000ms)
- All services compete for the remaining 5 connections

**Expected in Coralogix:**
- Connection pool metrics in spans show 95% utilization
- Increased query queuing time
- Potential timeout errors in traces

**Reset:**
```bash
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
curl -X POST http://54.235.171.176:30010/demo/reset
```

---

## Verification in Coralogix

### 1. Database Monitoring View

**Wait 2-3 minutes after deployment**

1. Navigate to: **APM** → **Database Catalog** (or **Databases** tab)

2. Click on `productcatalog` database

3. **Verify "Calling Services" dropdown shows ALL 3 services:**
   - ✅ product-service
   - ✅ inventory-service
   - ✅ order-service

4. **Check operations by service:**
   - product-service: `SELECT products`
   - inventory-service: `SELECT products`, `UPDATE products`
   - order-service: `SELECT orders`, `INSERT orders`

### 2. Trace View

Search for a recent trace ID and verify:

```
Trace Structure:
├─ ai_recommendations (recommendation-ai)
│  ├─ chat gpt-4-turbo
│  ├─ product_service.get_products (product-service)
│  │  └─ SELECT productcatalog.products ⭐ CLIENT span
│  └─ chat gpt-4-turbo
```

If you call inventory or order services directly:

```
Trace Structure:
├─ inventory_service.check_stock (inventory-service)
│  └─ SELECT productcatalog.products ⭐ CLIENT span
```

```
Trace Structure:
├─ order_service.get_popular_products (order-service)
│  └─ SELECT productcatalog.orders ⭐ CLIENT span
```

### 3. Connection Pool Metrics

Each database span includes:
- `db.connection_pool.active`: Current active connections
- `db.connection_pool.max`: 100
- `db.connection_pool.utilization_percent`: % utilization
- `db.connection_pool.available_connections`: Free connections

---

## Files Created

### New Service Files
1. `coralogix-dataprime-demo/services/inventory_service.py` - Inventory management service
2. `coralogix-dataprime-demo/services/order_service.py` - Order management service

### Updated Files
3. `deployment/kubernetes/postgres.yaml` - Added orders table init script
4. `deployment/kubernetes/services.yaml` - Added NodePort services for 30015, 30016
5. `deployment/kubernetes/deployments/inventory-service.yaml` - K8s deployment
6. `deployment/kubernetes/deployments/order-service.yaml` - K8s deployment

### Scripts & Documentation
7. `scripts/deploy-multi-service-db-demo.sh` - Automated deployment script
8. `MULTI-SERVICE-DATABASE-DEMO.md` - This documentation

---

## Testing Checklist

- [ ] Deploy all 3 services successfully
- [ ] All pods show Running status
- [ ] All services accessible via NodePorts
- [ ] PostgreSQL has orders table
- [ ] Sample orders data exists
- [ ] Inventory service can check stock
- [ ] Order service can query popular products
- [ ] Order service can create new orders
- [ ] All services share the same connection pool
- [ ] Enable slow queries works on all services
- [ ] Pool exhaustion simulation works
- [ ] All 3 services appear in Coralogix Database Monitoring
- [ ] Database spans have all required attributes
- [ ] Connection pool metrics visible in spans
- [ ] Trace context propagation working

---

## Troubleshooting

### Services not starting

```bash
# Check pod logs
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176
sudo kubectl logs -n dataprime-demo -l app=inventory-service --tail=50
sudo kubectl logs -n dataprime-demo -l app=order-service --tail=50
```

### Orders table not created

```bash
# Manually create orders table
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

### Services not appearing in Coralogix Database Monitoring

1. **Wait 2-3 minutes** for data to arrive
2. **Check spans have required attributes:**
   - db.system
   - db.name
   - db.operation
   - db.statement
   - net.peer.name
3. **Verify span kind = CLIENT**
4. **Make several requests** to generate data

---

## Summary

✅ **3 services** sharing 1 PostgreSQL database  
✅ **100-connection pool** with realistic exhaustion scenarios  
✅ **Manual OTel instrumentation** with all required attributes  
✅ **Full Coralogix visibility** in Database Monitoring  
✅ **Demo-ready** for re:Invent 2025  

**Deploy Command:**
```bash
./scripts/deploy-multi-service-db-demo.sh 54.235.171.176
```

**Test Commands:**
```bash
# Normal operations
curl http://54.235.171.176:30015/inventory/check/5
curl http://54.235.171.176:30016/orders/popular-products?limit=5

# Demo scenarios
curl -X POST http://54.235.171.176:30015/demo/enable-slow-queries
curl -X POST http://54.235.171.176:30015/demo/simulate-pool-exhaustion
```

**Verify in Coralogix:**
- APM → Database Catalog → productcatalog
- All 3 services visible as calling services
- Query metrics and operations for each service

---

**Status:** ✅ Ready to deploy and demo!

