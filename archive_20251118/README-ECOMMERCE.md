# E-commerce Recommendation System - Coralogix Observability Demo

## Overview

This is a production-grade e-commerce application demonstrating Coralogix's unified observability platform. The demo showcases the entire investigation journey from alert to resolution using:

- **AI Observability**: AI Center with evaluation tracking, AI-SPM, LLM call analysis
- **Traditional Observability**: Infrastructure, K8s, APM, traces, logs, metrics
- **Database APM**: Query performance monitoring with P95/P99 latency tracking
- **Continuous Profiling**: eBPF-based CPU profiling for identifying slow functions
- **AI-Powered Workflows**: Cora AI for natural language querying and log explanation
- **RUM (Real User Monitoring)**: Frontend performance and user behavior tracking

## Architecture

### Services

```
┌─────────────┐
│   Frontend  │ (Port 8020) - Web UI with RUM integration
│  (Flask)    │
└──────┬──────┘
       │
       v
┌─────────────┐
│ API Gateway │ (Port 8010) - Request orchestration
│  (Flask)    │
└──────┬──────┘
       │
       ├──────────────────┬──────────────────┬────────────────────┐
       v                  v                  v                    v
┌──────────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────────┐
│  Product     │   │ Recommendation│   │   Order     │   │  Inventory    │
│  Service     │   │  AI Service   │   │  Service    │   │  Service      │
│  (Port 8014) │   │  (Port 8011)  │   │ (Port 8012) │   │ (Port 8013)   │
└──────┬───────┘   └───────┬───────┘   └──────┬──────┘   └───────┬───────┘
       │                   │                  │                   │
       └───────────────────┴──────────────────┴───────────────────┘
                                     │
                                     v
                            ┌──────────────────┐
                            │   PostgreSQL     │
                            │  (productcatalog)│
                            └──────────────────┘
```

### Data Flow

1. **User Request** → Frontend (RUM tracking)
2. **Frontend** → API Gateway (trace propagation)
3. **API Gateway** → Recommendation AI Service (LLM call with OpenAI)
4. **Recommendation AI** → Product Service (tool call for product data)
5. **Product Service** → PostgreSQL (database query with manual instrumentation)
6. **Response** → User (with trace context)

## Demo Scenes

### Scene 9: Database APM - Connection Pool Exhaustion

**Objective**: Show database performance degradation and connection pool exhaustion.

**Metrics to Observe**:
- Query Duration P95: 2800ms (baseline: 45ms)
- Query Duration P99: 3200ms
- Active Queries: 43 concurrent queries
- Connection Pool Utilization: 95%
- Query Failure Rate: 8.3%

**How to Trigger**:

1. **Via Frontend UI** (Recommended):
   ```
   1. Navigate to: http://localhost:8020 (or https://your-aws-ip:30443/)
   2. Click: "🔥 Simulate Database Issues (Scene 9)"
   3. Confirm the dialog
   ```

2. **Via API Call**:
   ```bash
   curl -X POST http://localhost:8010/api/demo/trigger-database-scenario
   ```

3. **Via Automated Script**:
   ```bash
   python3 scripts/demo_investigation_flow.py
   ```

**What Happens**:
- Enables slow query simulation (2800ms delay)
- Spawns 43 concurrent database queries across 3 services:
  - Product Service: 15 queries
  - Order Service: 15 queries
  - Inventory Service: 13 queries
- Connection pool reaches 95% utilization
- ~8% of queries fail due to pool exhaustion

**Expected Observations in Coralogix**:

1. **Database APM Dashboard**:
   ```
   Navigate: APM → Database Monitoring → productcatalog
   
   Observe:
   - Query Duration P95: ~2800ms (spike from 45ms baseline)
   - Active Queries: 43 queries simultaneously executing
   - Connection Pool: 95% utilization (95/100 connections)
   - Failure Rate: ~8.3% (connection timeouts)
   - Service Breakdown: 3 services calling the database
   ```

2. **APM Service Map**:
   ```
   Navigate: APM → Service Map
   
   Observe:
   - product-service → postgresql:productcatalog (red: slow)
   - order-service → postgresql:productcatalog (red: slow)
   - inventory-service → postgresql:productcatalog (red: slow)
   - Latency increase visible on connection edges
   ```

3. **Traces View**:
   ```
   Navigate: APM → Traces
   
   Filter: service.name='product-service' AND duration > 2000ms
   
   Observe:
   - Multiple slow database spans (SELECT operations)
   - Span attributes show:
     • db.connection_pool.active: 95
     • db.connection_pool.utilization_percent: 95
     • db.query.duration_ms: ~2800
   ```

**Talk Track**:

> "Here's our Database APM. Immediately I see the problem:
> 
> Query Duration P95: 2800ms - that's nearly 3 seconds for 95% of queries. Normal baseline: 45ms - we're 60x slower than normal.
> 
> See this spike at 10:47 AM? The P95 shoots through the roof. 43 active queries all trying to execute simultaneously - the database is overwhelmed.
> 
> Here's why. Connection pool at 95% utilization. Query P95 at 2800ms. See these 43 active queries all queued up? They're waiting for available connections. This is query queuing - a database bottleneck.
> 
> Adding more pods makes this WORSE, not better. You need database visibility to understand this."

### Scene 9.5: Continuous Profiling - Identify Slow Functions

**Objective**: Use eBPF profiling to pinpoint the exact function causing slowness.

**Prerequisites**:
- eBPF profiler deployed (see installation section below)
- Database scenario triggered (Scene 9)

**What to Show**:

1. **Flame Graph Analysis**:
   ```
   Navigate: APM → Continuous Profiling → product-service
   
   Time Range: Last 15 minutes
   
   Observe:
   - Function: search_products_unindexed() consuming 99.2% CPU
   - Stack trace shows: psycopg2.execute() → PostgreSQL full table scan
   - Wide flame graph block indicates CPU hotspot
   ```

2. **Stack Trace Drill-down**:
   ```
   Click on: search_products_unindexed()
   
   Observe:
   - Call stack: product_service.py → psycopg2 → libpq → PostgreSQL
   - SQL query: SELECT * FROM products WHERE description LIKE '%...%'
   - Issue: LIKE query on unindexed description field
   ```

**The Problem**:

The `/products/search` endpoint uses an unindexed LIKE query:

```sql
SELECT id, name, category, price, description, image_url, stock_quantity
FROM products
WHERE description LIKE '%search_term%'
```

This causes a **full table scan** - PostgreSQL must read every row in the products table.

**The Fix**:

```sql
-- Add GIN index for LIKE queries
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_products_description_trgm 
ON products 
USING gin(description gin_trgm_ops);
```

**After Fix**:
- Query Duration: **45ms** (60x improvement!)
- CPU Usage: **<1%** for search_products_unindexed()
- Index scan replaces full table scan

**Talk Track**:

> "We know the database is slow from APM, but WHERE exactly is the bottleneck? Let's look at continuous profiling.
> 
> This flame graph shows CPU time. See this wide block? That's `search_products_unindexed()` consuming 99.2% of CPU time.
> 
> The call stack reveals it's spending all its time in `psycopg2.execute()` doing a PostgreSQL full table scan. The query is using LIKE on an unindexed description field.
> 
> This is the power of eBPF profiling - it pinpoints the exact function, even in third-party libraries, without any code changes.
> 
> The fix? Add a GIN index on the description field. After deploying that, the query drops from 2800ms to 45ms - a 60x improvement."

### Scene 10: Logs with Cora AI - Investigate Errors

**Objective**: Use structured logs and Cora AI to investigate connection pool errors.

**What to Show**:

1. **Structured Logs**:
   ```
   Navigate: Logs → Explore
   
   Filter: service.name='product-service' AND level='ERROR'
   
   Observe:
   - Error: "Could not acquire connection for pool exhaustion"
   - Structured fields:
     • connections_held: 95
     • pool_max: 100
     • utilization_percent: 95
     • simulation_type: "pool_exhaustion"
   ```

2. **Cora AI Analysis**:
   ```
   Steps:
   1. Click on a connection error log
   2. Click "Explain with Cora AI"
   3. Cora analyzes the log with full context
   
   Expected Insights:
   - "Connection pool at max capacity (95% utilization)"
   - "43 concurrent queries detected at 10:47 AM"
   - "Correlation: Slow queries (2800ms) causing connection buildup"
   - "Recommendation: Increase pool size OR add read replicas OR optimize queries"
   ```

3. **Log Correlation**:
   ```
   Cora AI correlates:
   - Error logs from product-service
   - Slow query traces from Database APM
   - High CPU usage from Continuous Profiling
   - Connection pool metrics
   
   Result: Complete root cause analysis
   ```

**Talk Track**:

> "Now let's look at the logs to understand what the services experienced.
> 
> These are structured logs exported via OTLP. Each log has rich context: connection pool stats, utilization percentage, error details.
> 
> Let me use Cora AI to analyze this. I'll click 'Explain with Cora AI'...
> 
> Cora immediately identifies: 'Connection pool at max capacity. 43 concurrent queries detected. Slow queries (2800ms) causing connection buildup.'
> 
> Notice how Cora correlates across signals:
> - Logs showing connection errors
> - Traces showing slow queries
> - Profiling showing CPU hotspot
> - Metrics showing pool exhaustion
> 
> This is unified observability with AI - not just collecting data, but understanding the story."

## Installation

### Prerequisites

- Docker and Docker Compose (local development)
- Kubernetes cluster (production deployment)
- Python 3.10+
- Coralogix account with API key

### Environment Variables

Create a `.env` file:

```bash
# Coralogix Configuration
CX_API_KEY=your_coralogix_api_key
CX_APPLICATION_NAME=ecomm_reccomendation
CX_SUBSYSTEM_NAME=demo-app
CX_DOMAIN=EU2

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=coralogix-opentelemetry-collector.dataprime-demo.svc.cluster.local:4317
OTEL_SERVICE_NAME=dataprime_assistant

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=productcatalog
DB_USER=dbadmin
DB_PASSWORD=postgres_secure_pass_2024
DB_MAX_CONNECTIONS=100

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview

# RUM Configuration (Frontend)
CX_RUM_PUBLIC_KEY=your_rum_public_key
```

### Local Development (Docker Compose)

```bash
# Start core services
cd coralogix-dataprime-demo/docker
docker-compose -f docker-compose-ecommerce.yml up -d

# Verify services
docker-compose -f docker-compose-ecommerce.yml ps

# View logs
docker-compose -f docker-compose-ecommerce.yml logs -f product-service
```

### Production Deployment (Kubernetes)

```bash
# Apply all manifests
kubectl apply -f deployment/kubernetes/

# Verify deployment
kubectl get pods -n dataprime-demo

# Check service health
kubectl get svc -n dataprime-demo

# View logs
kubectl logs -n dataprime-demo -l app=product-service --tail=50
```

## Continuous Profiling Setup

The eBPF profiler is required for Scene 9.5.

### Kubernetes Deployment

```bash
# Deploy profiler DaemonSet
kubectl apply -f deployment/kubernetes/profiling-daemonset.yaml

# Verify profiler is running
kubectl get pods -n dataprime-demo -l app=coralogix-profiler

# Check profiler logs
kubectl logs -n dataprime-demo -l app=coralogix-profiler --tail=50
```

### Docker Compose (Local)

```bash
cd coralogix-dataprime-demo/docker
docker-compose -f docker-compose-profiling.yml up -d
```

### Configuration

The profiler requires:
- **Privileged mode**: For eBPF operations
- **Host PID namespace**: To profile all processes
- **Host paths**: `/sys/kernel/debug`, `/sys/fs/cgroup`

See `deployment/kubernetes/profiling-daemonset.yaml` for full configuration.

For detailed profiling documentation, see: [CONTINUOUS-PROFILING.md](coralogix-dataprime-demo/docs/CONTINUOUS-PROFILING.md)

## Running the Demo

### Option 1: Automated Demo Script

The easiest way to run the complete demo:

```bash
# Run automated investigation flow
python3 scripts/demo_investigation_flow.py
```

This script will:
1. Check service health
2. Establish baseline operation
3. Trigger database exhaustion scenario
4. Guide you through Coralogix UI observations
5. Reset demo state

### Option 2: Manual Demo via Frontend

1. **Open the Frontend**:
   ```
   Local: http://localhost:8020
   AWS:   https://your-aws-ip:30443/
   ```

2. **Establish Baseline** (optional):
   ```
   - Enter: "Looking for wireless headphones, budget $50-150"
   - Click: "Get AI Recommendations"
   - Observe: Normal operation with <100ms response time
   ```

3. **Trigger Database Scenario**:
   ```
   - Click: "🔥 Simulate Database Issues (Scene 9)"
   - Confirm the dialog
   - Wait: 10-15 seconds for traces to propagate
   ```

4. **View in Coralogix**:
   - Scene 9: Database APM → productcatalog
   - Scene 9.5: Continuous Profiling → product-service
   - Scene 10: Logs → Explore (filter by ERROR level)

5. **Reset Demo**:
   ```
   - Click: "✅ Reset to Normal"
   - Verify: System status shows "All systems operational"
   ```

### Option 3: API-Based Demo

```bash
# Trigger database scenario
curl -X POST http://localhost:8010/api/demo/trigger-database-scenario

# Wait 10-15 seconds

# Check in Coralogix UI

# Reset
curl -X POST http://localhost:8014/demo/reset
```

## Troubleshooting

### Services Not Starting

```bash
# Check service health
curl http://localhost:8014/health

# View service logs
kubectl logs -n dataprime-demo -l app=product-service --tail=100
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
kubectl get pods -n dataprime-demo -l app=postgres

# Check database connectivity
kubectl exec -it <product-service-pod> -- psql -h postgres -U dbadmin -d productcatalog -c "SELECT 1"
```

### No Traces in Coralogix

1. **Verify OTel Collector**:
   ```bash
   kubectl get pods -n dataprime-demo -l app=otel-collector
   kubectl logs -n dataprime-demo -l app=otel-collector --tail=50
   ```

2. **Check API Key**:
   ```bash
   kubectl get secret dataprime-secrets -o yaml | grep CX_API_KEY
   ```

3. **Verify Endpoint**:
   ```bash
   kubectl get configmap dataprime-config -o yaml | grep OTEL_EXPORTER_OTLP_ENDPOINT
   # Should be: coralogix-opentelemetry-collector.dataprime-demo.svc.cluster.local:4317
   ```

### Profiling Data Not Appearing

1. **Check profiler deployment**:
   ```bash
   kubectl get daemonset -n dataprime-demo coralogix-profiler
   ```

2. **Verify kernel support**:
   ```bash
   uname -r  # Should be 4.9+
   ```

3. **Check profiler logs**:
   ```bash
   kubectl logs -n dataprime-demo -l app=coralogix-profiler | grep -i "upload\|error"
   ```

## Key Differentiators

### Why This Demo Matters

1. **Unified Platform**: One place for infrastructure, application, database, and AI observability
2. **AI-Powered**: Cora AI for log explanation, Olly for accelerated RCA
3. **Production-Grade**: Real distributed system with actual database operations
4. **No Code Changes**: eBPF profiling without instrumentation
5. **Semantic Conventions**: Proper OpenTelemetry spans with required attributes

### What Makes Coralogix Different

- **Data Ownership**: Your data stays yours - critical in the AI era
- **TCO Optimization**: Intelligent tiering reduces costs by 70%
- **AI-Native**: Built-in AI for investigation, not bolted on
- **Database APM**: Deep database visibility with P95/P99 tracking
- **Continuous Profiling**: eBPF-based CPU profiling without overhead

## Technical Details

### OpenTelemetry Semantic Conventions

All database spans follow OTel semantic conventions:

```python
with tracer.start_as_current_span(
    "SELECT productcatalog.products",  # Format: OPERATION db.table
    kind=SpanKind.CLIENT,               # REQUIRED for database spans
    context=ctx
) as span:
    # Required attributes
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.name", "productcatalog")
    span.set_attribute("db.operation", "SELECT")
    span.set_attribute("db.sql.table", "products")
    span.set_attribute("db.statement", "SELECT id, name FROM products...")
    span.set_attribute("net.peer.name", "postgres")  # REQUIRED
    span.set_attribute("net.peer.port", 5432)        # REQUIRED
    
    # Connection pool metrics
    span.set_attribute("db.connection_pool.active", active_count)
    span.set_attribute("db.connection_pool.utilization_percent", 95)
```

### Manual vs Auto-Instrumentation

We use **manual instrumentation** for database operations because:

1. More control over span attributes
2. Custom metrics (pool utilization, active queries)
3. Demo-specific attributes for clarity
4. Consistent with legacy SQLite pattern

Auto-instrumentation (`opentelemetry-instrumentation-psycopg2`) is enabled but primarily for compatibility.

## References

- [Coralogix Documentation](https://coralogix.com/docs/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Database Monitoring Best Practices](https://coralogix.com/docs/database-monitoring/)
- [Continuous Profiling Guide](coralogix-dataprime-demo/docs/CONTINUOUS-PROFILING.md)

## Support

For issues or questions:
- GitHub Issues: [Create an issue](https://github.com/coralogix/dataprime-assistant/issues)
- Coralogix Support: support@coralogix.com
- Documentation: https://coralogix.com/docs/

## License

MIT License - see LICENSE file for details.

