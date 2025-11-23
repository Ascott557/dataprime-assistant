# OpenTelemetry Telemetry Setup - E-commerce Platform

## Overview

This document describes the complete OpenTelemetry telemetry setup for the e-commerce platform, including trace propagation, instrumentation patterns, and Coralogix integration.

## Architecture

```
┌─────────────────┐
│ Load Generator  │
│  (Port 8010)   │
└────────┬────────┘
         │ traceparent header
         ▼
┌─────────────────┐     ┌──────────────┐
│ Product Catalog │────►│ PostgreSQL   │
│  (Port 8014)   │     │ (Port 5432)  │
└─────────────────┘     └──────────────┘
         │
         │ traceparent header
         ▼
┌─────────────────┐     ┌──────────────┐
│   Checkout      │────►│ PostgreSQL   │
│  (Port 8016)   │     │ (Port 5432)  │
└─────────────────┘     └──────────────┘
         │
         │ All traces flow to ▼
┌──────────────────────────────────┐
│ Coralogix OpenTelemetry Collector│
│        (Port 4317 - gRPC)        │
└──────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────┐
│     Coralogix Platform (EU2)     │
│  https://eu2.coralogix.com       │
└──────────────────────────────────┘
```

## Core Components

### 1. Shared Telemetry Module

**File**: `app/shared_telemetry.py`

This is the foundation of all telemetry in the platform.

```python
# Key features:
- TracerProvider initialization with service identity
- OTLP exporter to local OTel Collector
- Resource attributes (service.name, service.version)
- Automatic instrumentation (requests, psycopg2)
- Flask auto-instrumentation DISABLED (for manual control)
```

**Configuration**:
```python
# Environment variables required
SERVICE_NAME=product-catalog
SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://coralogix-opentelemetry-collector:4317
CX_APPLICATION_NAME=ecommerce-platform
CX_SUBSYSTEM_NAME=product-catalog
```

**Initialization Pattern** (Used by all services):
```python
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize BEFORE importing psycopg2 or other instrumented libraries
telemetry_enabled = ensure_telemetry_initialized()

# NOW safe to import database libraries
import psycopg2
```

### 2. Consistent Span Attributes

**File**: `app/shared_span_attributes.py`

Ensures Flow Alerts can trigger with consistent attribute naming.

**Class: DemoSpanAttributes**
```python
# Methods:
1. set_slow_query(span, duration_ms, missing_index, rows_scanned)
   - Sets: db.slow_query, db.full_table_scan, db.missing_index
   
2. set_pool_exhausted(span, max_conn, wait_ms, rejected_count)
   - Sets: db.connection.pool.exhausted, db.connection.pool.size
   
3. set_checkout_failed(span, order_id, user_id, total, failure_reason)
   - Sets: checkout.failed, checkout.failure_reason, checkout.cart_abandoned
```

**Helper Functions**:
```python
calculate_demo_minute() - Unix timestamp-based timing
is_demo_mode() - Check if in demo mode
get_demo_phase(minute) - Get current phase name
```

## Trace Propagation Patterns

### Pattern 1: Extract and Attach (Receiving Service)

**Used in**: All services that receive HTTP requests

```python
def extract_and_attach_trace_context():
    """
    Extract W3C Trace Context from incoming HTTP headers.
    Returns: (token, is_root_span)
    """
    try:
        headers = dict(request.headers)
        
        # Try standard W3C propagation
        propagator = TraceContextTextMapPropagator()
        incoming_context = propagator.extract(headers)
        
        # Check for traceparent header
        traceparent_found = any(key.lower() == 'traceparent' for key in headers.keys())
        
        if traceparent_found:
            # Parse: "00-{trace_id}-{span_id}-01"
            for key, value in headers.items():
                if key.lower() == 'traceparent':
                    parts = value.split('-')
                    if len(parts) == 4:
                        manual_trace_id = parts[1]
                        manual_span_id = parts[2]
                        # Create parent context manually if needed
        
        if incoming_context:
            token = context.attach(incoming_context)
            return token, False  # False = child span
        
        return None, True  # True = root span
    except Exception as e:
        logger.error("trace_extraction_failed", error=str(e))
        return None, True
```

**Usage in request handler**:
```python
@app.route('/products', methods=['GET'])
def get_products():
    # CRITICAL: Call this first
    token, is_root = extract_and_attach_trace_context()
    
    try:
        with tracer.start_as_current_span("get_products_from_db") as span:
            # Your business logic
            span.set_attribute("db.system", "postgresql")
            # ...
            
    finally:
        # CRITICAL: Detach context
        if token:
            context.detach(token)
```

### Pattern 2: Propagate Trace Context (Calling Service)

**Used in**: Load generator and any service making HTTP calls

```python
def propagate_trace_context(headers=None):
    """
    Propagate current trace context to downstream services.
    Returns: headers dict with traceparent
    """
    if headers is None:
        headers = {}
    
    # Try standard propagation
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    
    # Manual fallback for reliability
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        trace_id = format(span_context.trace_id, '032x')
        span_id = format(span_context.span_id, '016x')
        
        # Create W3C traceparent header
        headers['traceparent'] = f"00-{trace_id}-{span_id}-01"
    
    return headers
```

**Usage when calling downstream services**:
```python
with tracer.start_as_current_span("call_product_catalog") as span:
    headers = propagate_trace_context()
    
    response = requests.get(
        "http://product-catalog:8014/products",
        params={"category": "electronics"},
        headers=headers,  # ← Propagates trace
        timeout=10
    )
```

### Pattern 3: Database Span Creation

**CRITICAL for Coralogix Database Monitoring**

```python
with tracer.start_as_current_span(
    f"SELECT {db_name}.products",  # Name: "OPERATION database.table"
    kind=SpanKind.CLIENT  # REQUIRED for DB monitoring
) as db_span:
    # REQUIRED OpenTelemetry database semantic conventions
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", db_name)
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.sql.table", "products")
    db_span.set_attribute("db.statement", "SELECT id, name FROM products WHERE category = %s")
    db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
    db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
    db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
    
    # Execute query
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Set results
    db_span.set_attribute("db.rows_returned", len(results))
```

**Why these attributes matter**:
- `SpanKind.CLIENT` - Tells Coralogix this is a database call
- `db.system`, `db.name` - Required for Database APM
- `net.peer.name`, `net.peer.port` - Required for topology mapping
- `db.statement` - Shows up in Database APM query analysis

## Service-Specific Configuration

### Product Catalog Service

**Port**: 8014  
**Subsystem**: `product-catalog`

**Key Features**:
- Progressive slow query simulation (500ms → 2500ms)
- Database span creation with semantic conventions
- Connection pool monitoring

**Demo Attributes**:
```python
if is_demo_mode():
    delay_ms = get_progressive_delay()
    demo_minute = calculate_demo_minute()
    
    if delay_ms > 1000:
        DemoSpanAttributes.set_slow_query(
            span,
            duration_ms=delay_ms,
            missing_index="idx_products_category",
            rows_scanned=10000
        )
```

### Checkout Service

**Port**: 8016  
**Subsystem**: `checkout`

**Key Features**:
- Connection pool exhaustion simulation
- Checkout failure tracking
- Revenue impact attributes

**Demo Attributes**:
```python
if pool_simulator.should_fail_connection(main_span, order_data):
    # Sets:
    # - db.connection.pool.exhausted=true
    # - checkout.failed=true
    # - checkout.failure_reason="ConnectionPoolExhausted"
    # - checkout.total=<revenue lost>
    return jsonify({"error": "Connection timeout"}), 503
```

### Load Generator

**Port**: 8010  
**Subsystem**: `load-generator`

**Key Features**:
- Traffic orchestration with trace propagation
- User journey tracking
- Real-time statistics

**Trace Creation**:
```python
with tracer.start_as_current_span(f"user_journey.{journey_type}") as span:
    span.set_attribute("user.journey", journey_type)
    span.set_attribute("user.session_id", session_id)
    
    # Execute steps with propagation
    for step in journey_steps:
        headers = propagate_trace_context()
        response = requests.post(url, headers=headers)
```

## Coralogix Integration

### Configuration

**Environment Variables** (Set in ConfigMap):
```bash
# Coralogix endpoint (EU2 region)
CX_ENDPOINT=https://ingress.eu2.coralogix.com:443

# API token (from Coralogix settings)
CX_TOKEN=cxtp_<your-token-here>

# Application name (groups all services)
CX_APPLICATION_NAME=ecommerce-platform

# Subsystem name (per-service)
CX_SUBSYSTEM_NAME=product-catalog  # Changes per service
```

### OpenTelemetry Collector

**Deployed via Helm**:
```bash
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

helm upgrade --install coralogix-opentelemetry-collector \
  coralogix/opentelemetry-collector \
  --namespace ecommerce-demo \
  --set global.domain="EU2" \
  --set global.clusterName="ecommerce-k3s" \
  --set global.defaultApplicationName="ecommerce-platform" \
  --set global.defaultSubsystemName="ecommerce-services"
```

**Service Endpoint**:
```
http://coralogix-opentelemetry-collector:4317
```

**What it does**:
1. Receives traces from all services via gRPC (port 4317)
2. Batches traces for efficiency
3. Adds cluster/node metadata
4. Forwards to Coralogix ingress endpoint
5. Handles retries and backpressure

### Trace Flow

```
Service → OTel SDK → BatchSpanProcessor → OTLP Exporter (gRPC)
                                              ↓
                                   OTel Collector (K8s Service)
                                              ↓
                                   Coralogix Ingress (EU2)
                                              ↓
                                   Coralogix Platform
                                              ↓
                              APM / Traces / Incidents / Flow Alerts
```

## Structured Logging

### Configuration

All services use `structlog` with JSON output:

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
```

### Usage

```python
logger.info(
    "demo_slow_query_triggered",
    duration_ms=2500,
    demo_minute=18,
    service="product-catalog",
    missing_index="idx_products_category"
)

logger.error(
    "demo_pool_exhaustion",
    max_connections=20,
    active_connections=20,
    wait_time_ms=5000,
    rejected_count=156
)
```

### Correlation with Traces

Logs automatically include:
- Timestamp (ISO format)
- Log level
- Structured fields (queryable in Coralogix)
- Service name (from environment)

## Verification Commands

### Check Telemetry Initialization

```bash
# Product catalog logs
kubectl logs -n ecommerce-demo -l app=product-catalog --tail=50 | grep -i telemetry

# Should see:
# ✅ OpenTelemetry SDK imports successful
# ✅ OTLP exporter configured for local OTel Collector
# ✅ Telemetry initialized successfully
```

### Check OTel Collector

```bash
# Check collector is running
kubectl get pods -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector

# Check collector logs
kubectl logs -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=100

# Should see:
# Exporter traces sending to Coralogix
# No errors about authentication or connection
```

### Check Trace Propagation

```bash
# Generate traffic
kubectl exec -n ecommerce-demo -l app=load-generator -- \
  python3 -c "
import requests
response = requests.post(
    'http://localhost:8010/api/products/browse',
    json={'category': 'electronics'}
)
print(response.status_code)
"

# Check product catalog received trace
kubectl logs -n ecommerce-demo -l app=product-catalog --tail=20 | grep -i trace

# Should see:
# ✅ Product Service - Attached to incoming trace context
# Parent trace ID: <32-character hex>
```

### Check in Coralogix

1. **Go to APM** → https://eu2.coralogix.com/apm
2. **Filter by**: Application = `ecommerce-platform`
3. **Look for**:
   - Services: product-catalog, checkout, load-generator
   - Operations: GET /products, POST /orders/create
   - Traces with multiple spans (parent → child)

4. **Click on a trace** to see:
   - Waterfall view (timeline of spans)
   - Span attributes (db.*, checkout.*, etc.)
   - Parent-child relationships

## Demo-Specific Telemetry

### Demo Mode Detection

```python
# Check if in demo mode
is_demo = is_demo_mode()  # Checks DEMO_MODE=blackfriday

# Get current demo minute (Unix timestamp-based)
minute = calculate_demo_minute()  # Uses DEMO_START_TIMESTAMP

# Get phase name
phase = get_demo_phase(minute)  # "ramp", "peak", "degradation", "critical"
```

### Flow Alert Attributes

**Required for Flow Alert triggering**:

```python
# Slow query attributes
span.set_attribute("db.slow_query", True)
span.set_attribute("db.full_table_scan", True)
span.set_attribute("db.missing_index", "idx_products_category")
span.set_attribute("db.rows_scanned", 10000)

# Pool exhaustion attributes
span.set_attribute("db.connection.pool.exhausted", True)
span.set_attribute("db.connection.pool.size", 20)
span.set_attribute("db.connection.pool.wait_time_ms", 5000)

# Checkout failure attributes
span.set_attribute("checkout.failed", True)
span.set_attribute("checkout.failure_reason", "ConnectionPoolExhausted")
span.set_attribute("checkout.cart_abandoned", True)
```

### Structured Logging Events

```python
# Slow query event
logger.warning("demo_slow_query_triggered", ...)

# Pool exhaustion event
logger.error("demo_pool_exhaustion", ...)

# Checkout failure event
logger.error("demo_checkout_failed", ...)
```

## Troubleshooting

### Traces Not Appearing in Coralogix

**Check 1**: OTel Collector running?
```bash
kubectl get pods -n ecommerce-demo | grep otel
```

**Check 2**: Services can reach collector?
```bash
kubectl exec -n ecommerce-demo -l app=product-catalog -- \
  nc -zv coralogix-opentelemetry-collector 4317
```

**Check 3**: Collector can reach Coralogix?
```bash
kubectl logs -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector | grep -i error
```

**Check 4**: Valid Coralogix token?
```bash
kubectl get configmap -n ecommerce-demo ecommerce-config -o yaml | grep CX_TOKEN
```

### Traces Not Connecting (Broken Waterfall)

**Issue**: Each service creates its own root span instead of child spans

**Fix**: Ensure `extract_and_attach_trace_context()` is called FIRST in every request handler

```python
# ❌ WRONG - Creates root span
@app.route('/products')
def get_products():
    with tracer.start_as_current_span("get_products") as span:
        # trace context never extracted
        
# ✅ CORRECT - Creates child span
@app.route('/products')
def get_products():
    token, is_root = extract_and_attach_trace_context()  # ← FIRST!
    try:
        with tracer.start_as_current_span("get_products") as span:
            # This becomes a child span
    finally:
        if token:
            context.detach(token)  # ← LAST!
```

### Database Spans Not in APM

**Issue**: Database queries don't show up in Coralogix Database APM

**Fix**: Use `SpanKind.CLIENT` and required attributes:

```python
# ❌ WRONG - Missing SpanKind
with tracer.start_as_current_span("db_query") as span:
    cursor.execute(query)

# ✅ CORRECT - Has SpanKind.CLIENT
with tracer.start_as_current_span(
    "SELECT ecommerce.products",
    kind=SpanKind.CLIENT  # ← REQUIRED!
) as span:
    span.set_attribute("db.system", "postgresql")  # ← REQUIRED!
    span.set_attribute("net.peer.name", "postgres")  # ← REQUIRED!
    cursor.execute(query)
```

## Best Practices

### 1. Always Extract Context First
```python
token, is_root = extract_and_attach_trace_context()
try:
    # ... your code ...
finally:
    if token:
        context.detach(token)
```

### 2. Use Semantic Conventions
Follow OpenTelemetry semantic conventions:
- Database: `db.*` attributes
- HTTP: `http.*` attributes
- Network: `net.*` attributes

### 3. Set Business Context
```python
span.set_attribute("order.id", order_id)
span.set_attribute("order.total", total_amount)
span.set_attribute("user.id", user_id)
```

### 4. Log Structured Data
```python
logger.info(
    "order_created",
    order_id=123,
    user_id="user-456",
    total=99.99,
    items=3
)
```

### 5. Use Consistent Attribute Names
Use `DemoSpanAttributes` class to ensure consistency across services.

## Performance Considerations

### Sampling

Currently using **always-on sampling** (100% of traces):
```python
# In TracerProvider configuration
# No sampler specified = AlwaysOnSampler
```

For production with high traffic:
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

provider = TracerProvider(
    sampler=ParentBasedTraceIdRatioBased(0.1),  # 10% sampling
    resource=resource
)
```

### Batching

Traces are batched automatically by `BatchSpanProcessor`:
- Max batch size: 512 spans
- Max export delay: 5 seconds
- Reduces network overhead

### Resource Usage

Typical resource usage per service:
- Memory: +20-30 MB for OTel SDK
- CPU: +2-5% for span processing
- Network: ~1-2 KB per trace

## References

### OpenTelemetry Documentation
- Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/
- Python SDK: https://opentelemetry.io/docs/languages/python/
- Trace Context: https://www.w3.org/TR/trace-context/

### Coralogix Documentation
- APM Setup: https://coralogix.com/docs/apm/
- OTel Collector: https://coralogix.com/docs/opentelemetry-using-kubernetes/
- Flow Alerts: https://coralogix.com/docs/flow-alert/

### Code References
- **Shared Telemetry**: `app/shared_telemetry.py`
- **Span Attributes**: `app/shared_span_attributes.py`
- **Product Catalog**: `services/product_catalog_service.py` (lines 48-124, 247-268)
- **Checkout**: `services/checkout_service.py` (lines 119-188, 396-405)
- **Load Generator**: `services/load_generator.py` (lines 53-78, 113-240)

---

**Last Updated**: November 23, 2025  
**Version**: 1.0  
**Maintainer**: Coralogix Demo Team

