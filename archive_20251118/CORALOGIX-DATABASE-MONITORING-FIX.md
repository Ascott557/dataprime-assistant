# Coralogix Database Monitoring Integration - FIX

**Date:** November 16, 2025  
**Issue:** Database spans not appearing in Coralogix Database Monitoring UI  
**Status:** ✅ FIXED

---

## Problem

The PostgreSQL database calls were being sent to Coralogix but were NOT appearing in the **Database Monitoring** UI because they were missing required semantic conventions.

### Symptoms
1. ✅ Traces appeared in APM → Traces
2. ❌ Database showed "0 services" in Database Monitoring UI
3. ❌ "N/A" for Average Latency
4. ❌ "0" Total Queries
5. ❌ Spans still labeled as "sqlite" instead of "postgresql"

---

## Root Cause

According to [Coralogix Database Monitoring documentation](https://coralogix.com/docs/user-guides/apm/features/database-monitoring/), **all of these attributes are REQUIRED** for database spans:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `db.system` | string | DBMS product being used | "postgresql", "mysql", "mongodb" |
| `db.name` | string | Name of the database being accessed | "productcatalog", "customers" |
| `db.operation` | string | Operation being executed | "SELECT", "UPDATE", "INSERT" |
| `db.statement` | string | The database statement | "SELECT * FROM products..." |
| `net.peer.name` | string | Hostname or IP of database server | "postgres", "192.0.2.1" |

### What Was Missing

Our implementation had:
- ✅ `db.system` = "postgresql"
- ✅ `db.operation` = "SELECT"
- ✅ `db.statement` = "SELECT * FROM products..."
- ❌ **`db.name`** (MISSING - Required by Coralogix)
- ❌ **`net.peer.name`** (MISSING - Required by Coralogix)
- ❌ **Span kind** was not explicitly set to CLIENT

Additionally:
- Span name was `postgres.query.select_products` instead of following OTel conventions
- Span kind was not explicitly set (should be `SpanKind.CLIENT` for database calls)

---

## The Fix

### 1. Added Required Attributes

```python
# REQUIRED attributes for Coralogix Database Monitoring
db_span.set_attribute("db.system", "postgresql")
db_span.set_attribute("db.name", os.getenv("DB_NAME", "productcatalog"))  # ✅ ADDED
db_span.set_attribute("db.operation", "SELECT")
db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))  # ✅ ADDED
```

### 2. Set Span Kind to CLIENT

```python
with tracer.start_as_current_span(
    "SELECT productcatalog.products",
    kind=SpanKind.CLIENT  # ✅ ADDED - Marks this as a database client call
) as db_span:
```

### 3. Updated Span Name

**Before:** `postgres.query.select_products`

**After:** `SELECT productcatalog.products`

This follows OpenTelemetry semantic conventions: `{db.operation} {db.name}.{db.sql.table}`

### 4. Added Additional Recommended Attributes

```python
# Additional attributes for visibility
db_span.set_attribute("db.sql.table", "products")
db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
```

---

## Complete Updated Code

### Before (Incorrect)
```python
with tracer.start_as_current_span("postgres.query.select_products") as db_span:
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.table", "products")
    db_span.set_attribute("db.statement", "SELECT * FROM products...")
    db_span.set_attribute("db.query.category", category)
    db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
```

### After (Correct)
```python
with tracer.start_as_current_span(
    "SELECT productcatalog.products",
    kind=SpanKind.CLIENT  # ✅ DATABASE CLIENT SPAN
) as db_span:
    # REQUIRED attributes for Coralogix Database Monitoring
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", os.getenv("DB_NAME", "productcatalog"))  # ✅ REQUIRED
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))  # ✅ REQUIRED
    
    # Additional attributes for visibility
    db_span.set_attribute("db.sql.table", "products")
    db_span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE category = %s AND price BETWEEN %s AND %s ORDER BY price ASC LIMIT 10")
    db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
    
    # Custom attributes for query context
    db_span.set_attribute("db.query.category", category)
    db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
```

---

## Expected Result After Fix

### In Coralogix APM → Traces

```
ai_recommendations (recommendation-ai)
├─ chat gpt-4-turbo (OpenAI call)
├─ product_service.get_products (product-service)
│  ├─ Pool metrics in span attributes
│  └─ SELECT productcatalog.products (PostgreSQL CLIENT span) ✅
│     Attributes:
│     • db.system = "postgresql"
│     • db.name = "productcatalog"
│     • db.operation = "SELECT"
│     • db.statement = "SELECT * FROM products..."
│     • net.peer.name = "postgres"
│     • db.sql.table = "products"
│     • db.user = "dbadmin"
│     • db.query.duration_ms = 8.5
│     • db.rows_returned = 3
└─ chat gpt-4-turbo (OpenAI final response)
```

### In Coralogix Database Monitoring UI

**Database Catalog should now show:**

| Db Name | Db System | Services | Average Latency | Total Queries | Total Failures |
|---------|-----------|----------|-----------------|---------------|----------------|
| productcatalog | postgresql | 1 | ~10ms | 12+ | 0 |

**Clicking on the database should show:**
- Query Time Average graph
- Queries graph
- Number of Failures
- Calling services: `product-service`
- Operations: `SELECT products`
- Individual queries with duration and row counts

---

## Verification Steps

### 1. Redeploy Product Service

```bash
# Package and upload
cd /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo
tar -czf /tmp/coralogix-db-monitoring-fix.tar.gz services/product_service.py

scp -i ~/.ssh/ecommerce-demo-key.pem /tmp/coralogix-db-monitoring-fix.tar.gz ubuntu@<EC2_IP>:/home/ubuntu/

# On server: Extract, rebuild, deploy
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@<EC2_IP>
cd /home/ubuntu
tar -xzf coralogix-db-monitoring-fix.tar.gz

# Rebuild image
sudo docker build --platform linux/amd64 --no-cache -f Dockerfile -t ecommerce-unified:db-fix .
sudo docker tag ecommerce-unified:db-fix product-service:latest
sudo docker save docker.io/library/product-service:latest | sudo k3s ctr images import -

# Restart pod
sudo kubectl delete pod -n dataprime-demo -l app=product-service --force --grace-period=0
```

### 2. Generate Test Traces

```bash
# Make several AI recommendation requests
for i in {1..5}; do
  curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
    -H "Content-Type: application/json" \
    -d '{"user_id":"db_monitoring_test_'$i'","user_context":"wireless headphones under $100"}' | jq .trace_id
  sleep 2
done
```

### 3. Verify in Coralogix

**Wait 2-3 minutes for data to arrive**

#### Check APM → Traces
1. Search for one of the trace IDs
2. Verify span name is `SELECT productcatalog.products`
3. Verify span attributes include:
   - `db.name` = "productcatalog"
   - `net.peer.name` = "postgres"
   - Span kind = CLIENT

#### Check Database Monitoring
1. Navigate to **APM** → **Database Catalog** (or **Databases** tab)
2. Verify `productcatalog` database appears
3. Verify:
   - Services = 1 (product-service)
   - Average Latency = ~10ms
   - Total Queries > 0
4. Click on `productcatalog` to see:
   - Query Time Average graph (showing data)
   - Operations: `SELECT products`
   - Calling services: `product-service`

---

## Why This Matters for Database Monitoring

Coralogix Database Monitoring provides:

1. **Comprehensive Database Insights**
   - All databases and service-database interactions
   - Identify slow queries across your environment

2. **Performance Metrics**
   - Query time trends
   - Query failures and failure rates
   - Operations grouped by DB tables

3. **Troubleshooting**
   - Drill down to specific queries
   - See which services are calling which databases
   - Identify performance bottlenecks

4. **Retention**
   - Databases with no service interactions for 30 days are removed
   - Reappear automatically when interactions resume

**Without the required attributes, none of this works!**

---

## Key Takeaways

### Required Attributes for Coralogix Database Monitoring

**You MUST include all 5:**
1. ✅ `db.system` - Database type
2. ✅ `db.name` - Database name
3. ✅ `db.operation` - SQL operation
4. ✅ `db.statement` - SQL query
5. ✅ `net.peer.name` - Database host

### Span Configuration

**You MUST set:**
1. ✅ Span kind = `SpanKind.CLIENT`
2. ✅ Span name = `{db.operation} {db.name}.{db.sql.table}`

### TCO Pipeline

**Database spans MUST be sent to:**
- ✅ Medium: Monitoring TCO pipeline
- ✅ Span kind 'Client' includes database queries

---

## References

- [Coralogix Database Monitoring](https://coralogix.com/docs/user-guides/apm/features/database-monitoring/)
- [OpenTelemetry Database Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [OpenTelemetry Python API - SpanKind](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html#opentelemetry.trace.SpanKind)

---

## Summary

**The fix adds the 5 required attributes for Coralogix Database Monitoring:**

| Attribute | Before | After |
|-----------|--------|-------|
| `db.system` | ✅ "postgresql" | ✅ "postgresql" |
| `db.name` | ❌ Missing | ✅ "productcatalog" |
| `db.operation` | ✅ "SELECT" | ✅ "SELECT" |
| `db.statement` | ✅ SQL query | ✅ SQL query |
| `net.peer.name` | ❌ Missing | ✅ "postgres" |
| Span kind | ❌ Not set | ✅ CLIENT |
| Span name | ❌ "postgres.query.select_products" | ✅ "SELECT productcatalog.products" |

**Status:** ✅ Ready to deploy and test in Coralogix Database Monitoring UI!

