# PostgreSQL Instrumentation Fix for Coralogix Database Monitoring

## Problem
PostgreSQL database calls were not appearing correctly in the Coralogix Database Monitoring UI. The spans were either:
- Showing as SQLite instead of PostgreSQL
- Not appearing in the "Calling Services" dropdown
- Missing critical OpenTelemetry semantic conventions

## Root Cause
The database spans were missing three critical requirements for Coralogix Database Monitoring:

1. **Missing `SpanKind.CLIENT`**: Required for Coralogix to recognize spans as database operations
2. **Incorrect span naming**: Using `"database.select_products"` instead of the OTel convention `"SELECT productcatalog.products"`
3. **Missing required attributes**:
   - `net.peer.name` (database host)
   - `net.peer.port` (database port)
   - `db.name` was incorrect ("ecommerce" instead of "productcatalog")
   - Using `db.table` instead of `db.sql.table`

## Solution Applied

### Files Updated
1. `coralogix-dataprime-demo/services/product_service.py`
2. `coralogix-dataprime-demo/services/inventory_service.py`
3. `coralogix-dataprime-demo/services/order_service.py`

### Changes Made

#### 1. Import SpanKind
```python
from opentelemetry.trace import SpanKind
```

#### 2. Update Database Span Creation
**Before:**
```python
with tracer.start_as_current_span("database.select_products") as db_span:
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", os.getenv("DB_NAME", "ecommerce"))
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.table", "products")
```

**After:**
```python
db_name = os.getenv("DB_NAME", "productcatalog")
with tracer.start_as_current_span(
    f"SELECT {db_name}.products",  # OTel convention: "OPERATION database.table"
    kind=SpanKind.CLIENT  # REQUIRED for Coralogix Database Monitoring
) as db_span:
    # Set REQUIRED OpenTelemetry database semantic conventions
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", db_name)
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.sql.table", "products")  # Use db.sql.table (not db.table)
    db_span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE category = %s AND price BETWEEN %s AND %s ORDER BY price ASC LIMIT 10")
    db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))  # REQUIRED
    db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
    db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
```

### OpenTelemetry Database Semantic Conventions

According to [OpenTelemetry Database Span Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/):

**Required Attributes:**
- `db.system`: Database system identifier (e.g., "postgresql")
- `db.name`: Database name being accessed
- `db.operation`: Database operation (e.g., "SELECT", "INSERT", "UPDATE")
- `db.sql.table`: Table name (for SQL databases)
- `db.statement`: Full SQL statement
- `net.peer.name`: Host name of the database server
- `net.peer.port`: Port number of the database server

**Span Naming Convention:**
- Format: `{operation} {db.name}.{db.sql.table}`
- Examples:
  - `SELECT productcatalog.products`
  - `UPDATE productcatalog.products`
  - `INSERT productcatalog.orders`

**SpanKind:**
- Must be `SpanKind.CLIENT` for database operations
- This tells Coralogix that this span represents an outgoing call to an external system (the database)

## Deployment

1. Updated service files on EC2 instance
2. Rebuilt Docker images for all three services
3. Imported images into K3s containerd
4. Restarted pods to apply changes

## Verification

Tested all three services successfully:
- ✅ **Product Service**: Returns products filtered by category and price
- ✅ **Inventory Service**: Returns stock levels for products
- ✅ **Order Service**: Returns popular products based on order history

## Expected Results in Coralogix

After these fixes, the Coralogix Database Monitoring UI should now show:

1. **Database APM View**:
   - PostgreSQL database appears as "productcatalog"
   - All three services appear in "Calling Services" dropdown:
     - product-service
     - inventory-service
     - order-service

2. **Database Spans**:
   - Span names follow OTel convention (e.g., "SELECT productcatalog.products")
   - SpanKind is CLIENT
   - All required attributes are present

3. **Span View in Traces**:
   - Database operations appear as child spans with proper hierarchy
   - Connection pool metrics visible
   - Query duration and statement visible

## References

- [OpenTelemetry Database Span Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [Coralogix Database Monitoring](https://coralogix.com/docs/user-guides/apm/features/database-monitoring/)

---
**Date Fixed**: November 16, 2025
**Status**: ✅ Complete - Services deployed and tested

