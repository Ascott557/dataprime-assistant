# OpenTelemetry Semantic Conventions Fix - Scene 9

## Problem

Database spans were not appearing correctly in Coralogix Database APM:
- ❌ Only 1 calling service ("storage-service") instead of 3
- ❌ "Series 1" generic labels (no proper span attributes)
- ❌ "0 Services", "N/A" latency = Coralogix couldn't parse spans
- ❌ No query data propagating

**Root Cause**: Not following [OpenTelemetry Semantic Conventions v1.38.0 for Database Spans](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)

## What Was Wrong

| Issue | Old Code | Problem |
|-------|----------|---------|
| Deprecated attributes | `net.peer.name`, `net.peer.port` | Removed in OTel v1.24.0 |
| Wrong attribute name | `db.operation` | Should be `db.operation.name` |
| Wrong attribute name | `db.sql.table` | Should be `db.collection.name` |
| Error handling | `span.set_attribute("error", ...)` | Should use `span.set_status(Status(StatusCode.ERROR))` |
| Missing context | No `db.query.text` | Reduced visibility |

## What Was Fixed

### 1. Server Attributes (v1.38.0)
```python
# ❌ OLD (Deprecated)
span.set_attribute("net.peer.name", "postgres")
span.set_attribute("net.peer.port", 5432)

# ✅ NEW (v1.38.0)
span.set_attribute("server.address", "postgres.dataprime-demo.svc.cluster.local")
span.set_attribute("server.port", 5432)
```

### 2. Database Operation Name
```python
# ❌ OLD
span.set_attribute("db.operation", "SELECT")

# ✅ NEW
span.set_attribute("db.operation.name", "SELECT")
```

### 3. Collection/Table Name
```python
# ❌ OLD
span.set_attribute("db.sql.table", "products")

# ✅ NEW
span.set_attribute("db.collection.name", "products")
```

### 4. Error Status
```python
# ❌ OLD
if failure:
    span.set_attribute("error", "ConnectionError")

# ✅ NEW
if failure:
    span.set_status(Status(StatusCode.ERROR, "connection pool exhausted: timeout acquiring connection"))
    span.set_attribute("error.type", "ConnectionPoolTimeoutError")
    span.set_attribute("db.operation.success", False)
else:
    span.set_status(Status(StatusCode.OK))
    span.set_attribute("db.operation.success", True)
```

### 5. Query Context
```python
# ✅ NEW - Added for visibility
span.set_attribute("db.query.text", "SELECT id, name, category, price FROM products WHERE category = $1")
span.set_attribute("db.response.returned_rows", random.randint(1, 50))
```

### 6. Span Naming
```python
# OTel convention: "{db.operation.name} {db.collection.name}"
with tracer.start_as_current_span(
    "SELECT products",  # Not "SELECT productcatalog.products"
    kind=SpanKind.CLIENT  # REQUIRED for database operations
) as span:
```

## Complete Correct Implementation

```python
from opentelemetry.trace import SpanKind, Status, StatusCode

with tracer.start_as_current_span(
    "SELECT products",  # Span name: "{operation} {collection}"
    kind=SpanKind.CLIENT  # REQUIRED
) as span:
    # REQUIRED attributes
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.name", "productcatalog")
    span.set_attribute("db.operation.name", "SELECT")
    span.set_attribute("db.collection.name", "products")
    span.set_attribute("server.address", "postgres.dataprime-demo.svc.cluster.local")
    span.set_attribute("server.port", 5432)
    
    # RECOMMENDED attributes
    span.set_attribute("db.query.text", "SELECT id, name FROM products WHERE category = $1")
    span.set_attribute("db.response.returned_rows", 25)
    
    # Custom attributes (demo purposes)
    span.set_attribute("db.query.duration_ms", 2800)
    span.set_attribute("db.connection_pool.active", 95)
    span.set_attribute("db.connection_pool.max", 100)
    span.set_attribute("db.connection_pool.utilization_percent", 95)
    
    # Status
    if success:
        span.set_status(Status(StatusCode.OK))
    else:
        span.set_status(Status(StatusCode.ERROR, "timeout acquiring connection"))
        span.set_attribute("error.type", "ConnectionPoolTimeoutError")
```

## Expected Results in Coralogix

After the fix, you should see in **APM → Database Monitoring → productcatalog**:

1. **Calling Services Dropdown**: 
   - ✅ product-service
   - ✅ order-service
   - ✅ inventory-service

2. **Metrics Panel**:
   - ✅ Query Duration P95: ~2800ms
   - ✅ Query Duration P99: ~3200ms
   - ✅ Total Queries: 43
   - ✅ Failure Rate: ~8%

3. **Queries Chart**:
   - ✅ Proper labels (not "Series 1")
   - ✅ Query breakdown by service

4. **Service Map**:
   - ✅ 3 services → PostgreSQL
   - ✅ High latency connections (red/orange)

## Key Takeaways

1. **Always use current semantic conventions** - Check the version!
2. **Deprecated attributes won't work** - `net.peer.*` removed in v1.24.0
3. **Attribute naming matters** - `db.operation` ≠ `db.operation.name`
4. **SpanKind.CLIENT is required** - Database operations MUST use CLIENT kind
5. **Status matters for errors** - Set proper `Status(StatusCode.ERROR)`, not just attributes

## References

- [OpenTelemetry Database Span Conventions v1.38.0](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [OTel Semantic Conventions Migration Guide](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)

---

**Status**: ✅ FIXED AND DEPLOYED  
**Deployment**: November 16, 2025  
**Version**: OTel Semantic Conventions v1.38.0

