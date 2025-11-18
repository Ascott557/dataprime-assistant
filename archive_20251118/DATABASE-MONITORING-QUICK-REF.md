# Coralogix Database Monitoring - Quick Reference

## Required Attributes (ALL 5 MUST BE PRESENT)

```python
from opentelemetry.trace import SpanKind

with tracer.start_as_current_span(
    "SELECT productcatalog.products",  # {operation} {db.name}.{table}
    kind=SpanKind.CLIENT  # REQUIRED: Marks as database client span
) as db_span:
    # ✅ REQUIRED ATTRIBUTES (all 5)
    db_span.set_attribute("db.system", "postgresql")         # DBMS type
    db_span.set_attribute("db.name", "productcatalog")       # Database name
    db_span.set_attribute("db.operation", "SELECT")          # SQL operation
    db_span.set_attribute("db.statement", "SELECT * FROM...") # SQL query
    db_span.set_attribute("net.peer.name", "postgres")       # DB host
    
    # ✅ RECOMMENDED ATTRIBUTES
    db_span.set_attribute("db.sql.table", "products")
    db_span.set_attribute("db.user", "dbadmin")
    
    # Execute your database query here
    cursor.execute("SELECT * FROM products WHERE category = %s", (category,))
    results = cursor.fetchall()
    
    # ✅ PERFORMANCE ATTRIBUTES
    db_span.set_attribute("db.query.duration_ms", duration)
    db_span.set_attribute("db.rows_returned", len(results))
```

---

## Checklist

- [ ] Span kind = `SpanKind.CLIENT`
- [ ] Span name = `{db.operation} {db.name}.{db.sql.table}`
- [ ] `db.system` attribute (e.g., "postgresql", "mysql", "mongodb")
- [ ] `db.name` attribute (database name)
- [ ] `db.operation` attribute (e.g., "SELECT", "INSERT", "UPDATE")
- [ ] `db.statement` attribute (full SQL query)
- [ ] `net.peer.name` attribute (database hostname or IP)

---

## Common Mistakes

### ❌ Missing Required Attributes
```python
# This WON'T appear in Database Monitoring
with tracer.start_as_current_span("postgres.query") as db_span:
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.operation", "SELECT")
    # ❌ Missing: db.name, net.peer.name
```

### ❌ Wrong Span Kind
```python
# This WON'T appear in Database Monitoring
with tracer.start_as_current_span("SELECT products") as db_span:
    # ❌ Missing: kind=SpanKind.CLIENT
    db_span.set_attribute("db.system", "postgresql")
```

### ✅ Correct Implementation
```python
# This WILL appear in Database Monitoring
with tracer.start_as_current_span(
    "SELECT productcatalog.products",
    kind=SpanKind.CLIENT  # ✅
) as db_span:
    db_span.set_attribute("db.system", "postgresql")      # ✅
    db_span.set_attribute("db.name", "productcatalog")    # ✅
    db_span.set_attribute("db.operation", "SELECT")       # ✅
    db_span.set_attribute("db.statement", "SELECT * ...") # ✅
    db_span.set_attribute("net.peer.name", "postgres")    # ✅
```

---

## Database Systems

| `db.system` Value | Database |
|-------------------|----------|
| `postgresql` | PostgreSQL |
| `mysql` | MySQL |
| `mongodb` | MongoDB |
| `redis` | Redis |
| `elasticsearch` | Elasticsearch |
| `dynamodb` | DynamoDB |
| `cassandra` | Cassandra |
| `sqlite` | SQLite |

---

## Span Naming Conventions

### OTel Recommended Format
`{db.operation} {db.name}.{db.sql.table}`

### Examples
- `SELECT productcatalog.products`
- `INSERT productcatalog.orders`
- `UPDATE users.profiles`
- `DELETE logs.old_entries`

---

## TCO Pipeline Requirement

Database spans **MUST** be sent to:
- **Medium: Monitoring** TCO pipeline

Span kind **'Client'** automatically includes database queries.

---

## Verification

### In Coralogix APM → Traces
Look for:
- ✅ Span name: `SELECT productcatalog.products`
- ✅ Span kind badge: "CLIENT"
- ✅ All 5 required attributes present

### In Coralogix Database Monitoring
Look for:
- ✅ Database appears in catalog
- ✅ Services count > 0
- ✅ Average Latency shows actual time
- ✅ Total Queries > 0
- ✅ Can drill down to see individual queries

---

## Quick Test

```bash
# 1. Generate a test trace
curl -X POST http://localhost:8014/products?category=Headphones&price_min=0&price_max=100

# 2. Check logs for span attributes
kubectl logs -n dataprime-demo -l app=product-service | grep "db.name"

# 3. Wait 2-3 minutes, then check Coralogix:
# - APM → Traces (verify span attributes)
# - APM → Database Catalog (verify database appears)
```

---

## References

- [Coralogix Database Monitoring](https://coralogix.com/docs/user-guides/apm/features/database-monitoring/)
- [OpenTelemetry Database Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [OpenTelemetry Python SpanKind](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html#opentelemetry.trace.SpanKind)

