# re:Invent 2025 Demo - Quick Reference

## 🚀 Quick Deploy

```bash
./scripts/deploy-multi-service-db-demo.sh 54.235.171.176
```

---

## 📊 Architecture

```
3 Services → 1 PostgreSQL Database → 100 Connection Pool (Shared)

┌─────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ product-service │       │inventory-service │       │  order-service   │
│   Port 30010    │       │   Port 30015     │       │   Port 30016     │
└────────┬────────┘       └────────┬─────────┘       └────────┬─────────┘
         └────────────────────┬────┴─────────────────────────┘
                              ▼
                     ┌────────────────────┐
                     │    PostgreSQL      │
                     │ ThreadedConnPool   │
                     │   maxconn=100      │
                     └────────────────────┘
```

---

## 🧪 Demo Scenarios

### Scenario 1: Normal Operations (Baseline)

```bash
# Product lookup (AI → Product Service → PostgreSQL)
curl "http://54.235.171.176:30010/products?category=Wireless%20Headphones&price_min=0&price_max=100"

# Check stock
curl http://54.235.171.176:30015/inventory/check/5

# Popular products
curl http://54.235.171.176:30016/orders/popular-products?limit=5
```

**Expected:**
- Query time: 5-20ms
- Pool utilization: 3-5%
- All 3 services in Coralogix Database Monitoring

---

### Scenario 2: Slow Queries (Performance Degradation)

```bash
# Enable 2900ms delay on ALL services
curl -X POST http://54.235.171.176:30015/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30016/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'
curl -X POST http://54.235.171.176:30010/demo/enable-slow-queries -H "Content-Type: application/json" -d '{"delay_ms":2900}'

# Now make requests
curl http://54.235.171.176:30015/inventory/check/5  # Takes 2900ms
```

**Expected:**
- Query time: 2900ms
- All services show slow query pattern
- Span attribute: `db.simulation.slow_query_enabled: true`

---

### Scenario 3: Connection Pool Exhaustion (Catastrophic)

```bash
# Hold 95 of 100 connections
curl -X POST http://54.235.171.176:30015/demo/simulate-pool-exhaustion

# Check pool status
curl http://54.235.171.176:30015/health | jq '.connection_pool'
# Output: {"active_connections":95,"max_connections":100,"utilization_percent":95,"available_connections":5}

# Try to use the service (competes for 5 remaining connections)
curl http://54.235.171.176:30016/orders/popular-products?limit=5  # May timeout!
```

**Expected:**
- Pool utilization: 95%
- Only 5 connections available
- New requests queue or timeout
- Span metrics show high utilization

---

### Reset Demo

```bash
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
curl -X POST http://54.235.171.176:30010/demo/reset
```

---

## 🔍 Coralogix Verification

### Database Monitoring View

1. **APM** → **Database Catalog** → **productcatalog**

2. **Calling Services** (should show 3):
   - ✅ product-service
   - ✅ inventory-service
   - ✅ order-service

3. **Operations by Service:**
   - product-service: `SELECT products`
   - inventory-service: `SELECT products`, `UPDATE products`
   - order-service: `SELECT orders`, `INSERT orders`

4. **Metrics to show:**
   - Query Time Average
   - Total Queries
   - Connection pool utilization
   - Failure rate

---

## 📋 Service Endpoints

| Service | Port | Endpoints |
|---------|------|-----------|
| Product Service | 30010 | `/products`, `/health`, `/demo/*` |
| Inventory Service | 30015 | `/inventory/check/<id>`, `/inventory/reserve`, `/health`, `/demo/*` |
| Order Service | 30016 | `/orders/popular-products`, `/orders/create`, `/health`, `/demo/*` |

---

## 🎯 Key Talking Points

1. **Shared Connection Pool:**
   - All 3 services compete for the same 100 connections
   - Realistic microservices architecture
   - Shows pool exhaustion impact across services

2. **Complete Observability:**
   - Every database query has all 5 required Coralogix attributes
   - Span kind = CLIENT for proper categorization
   - Connection pool metrics in every span

3. **Manual Instrumentation:**
   - Reliable, proven pattern across all services
   - Explicit trace context propagation
   - Full control over span attributes

4. **Demo Scenarios:**
   - Normal: Everything works perfectly
   - Slow queries: See performance degradation
   - Pool exhaustion: Services compete and fail

---

## ⚡ One-Liners for Demo

```bash
# Check all services are healthy
curl http://54.235.171.176:30015/health && curl http://54.235.171.176:30016/health && curl http://54.235.171.176:30010/health

# Enable slow queries everywhere
for port in 30015 30016 30010; do curl -X POST http://54.235.171.176:$port/demo/enable-slow-queries -d '{"delay_ms":2900}'; done

# Reset everything
for port in 30015 30016 30010; do curl -X POST http://54.235.171.176:$port/demo/reset; done
```

---

## 📊 Database Schema

### products table (9 rows)
- id, name, category, price, description, image_url, stock_quantity

### orders table (10 sample rows)
- id, user_id, product_id, quantity, order_date
- Indexes on product_id and user_id

---

## 🔧 Troubleshooting

### Pods not running
```bash
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176
sudo kubectl get pods -n dataprime-demo | grep -E "inventory|order|product"
sudo kubectl logs -n dataprime-demo -l app=inventory-service --tail=50
```

### Services not in Coralogix
1. Wait 2-3 minutes
2. Make several requests to generate data
3. Verify span attributes in trace view

---

## ✅ Pre-Demo Checklist

- [ ] All 3 services deployed and running
- [ ] PostgreSQL has orders table with sample data
- [ ] All NodePorts accessible (30010, 30015, 30016)
- [ ] Health endpoints return 200 OK
- [ ] Connection pool shows correct max (100)
- [ ] All 3 services visible in Coralogix Database Monitoring
- [ ] Demo endpoints working (enable-slow-queries, simulate-pool-exhaustion)

---

## 🎤 Demo Flow

1. **Show baseline** (all services working)
2. **Enable slow queries** (show performance impact)
3. **Show Coralogix** (query time spikes across all services)
4. **Reset**
5. **Simulate pool exhaustion** (catastrophic scenario)
6. **Show Coralogix** (95% pool utilization, timeouts)
7. **Reset**
8. **Show Database Monitoring** (all 3 services, operations, metrics)

**Total demo time:** 5-7 minutes

---

**Deploy:** `./scripts/deploy-multi-service-db-demo.sh 54.235.171.176`

**Status:** ✅ Ready!

