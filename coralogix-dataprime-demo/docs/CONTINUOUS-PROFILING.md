# Continuous Profiling with Coralogix eBPF Agent

## Overview

Continuous profiling helps you identify slow functions and CPU hotspots in your application without modifying code. The Coralogix eBPF profiler runs at the kernel level and captures stack traces to show you exactly where your application is spending time.

## Scene 9.5: Profiling Demo - Unindexed Query

This demo shows how continuous profiling catches a performance issue that's hard to spot in traditional APM traces.

### The Problem

The `/products/search` endpoint uses an unindexed LIKE query on the `description` field:

```sql
SELECT * FROM products WHERE description LIKE '%search_term%'
```

This causes a **full table scan** - PostgreSQL must examine every row in the products table. While APM traces show the query takes a long time, profiling reveals the **exact function** consuming CPU.

### Expected Observations in Coralogix

#### 1. Database APM (Scene 9)
- Query Duration P95: 2800ms
- Active Queries: 43 concurrent queries
- Operation: `SELECT products` (slow)

#### 2. Continuous Profiling (Scene 9.5)
- Flame graph shows `search_products_unindexed()` consuming **99.2% CPU**
- Call stack traces back to the database full table scan
- Clear visual identification of the bottleneck

### How to Trigger

1. Navigate to the demo frontend
2. Click **"Simulate Database Issues (Scene 9)"** to generate load
3. The unindexed search endpoint is called as part of the concurrent query generation

Or manually:

```bash
curl "http://product-service:8014/products/search?q=wireless"
```

### Deployment

The eBPF profiler is deployed as a DaemonSet in Kubernetes, running on every node.

## Installation

### Option 1: Kubernetes (Production)

Deploy the Coralogix eBPF profiler DaemonSet:

```bash
kubectl apply -f deployment/kubernetes/profiling-daemonset.yaml
```

The DaemonSet will:
- Run on all nodes (including new ones automatically)
- Mount host paths for kernel access
- Require privileged mode for eBPF operations
- Auto-discover pods and capture profiles

### Option 2: Docker Compose (Local Development)

For local testing with Docker Compose:

```bash
cd coralogix-dataprime-demo/docker
docker-compose -f docker-compose-profiling.yml up -d
```

## Verification

Check profiler status:

```bash
# Kubernetes
kubectl get pods -n dataprime-demo -l app=coralogix-profiler

# Docker Compose
docker ps | grep coralogix-profiler
```

Check logs:

```bash
# Kubernetes
kubectl logs -n dataprime-demo -l app=coralogix-profiler --tail=50

# Docker Compose
docker-compose -f docker-compose-profiling.yml logs coralogix-profiler
```

## Viewing Flame Graphs in Coralogix

1. Open Coralogix UI → **APM** → **Continuous Profiling**
2. Select your service: `product-service`
3. Time range: Last 15 minutes
4. Look for function: `search_products_unindexed`

### What You'll See

**Flame Graph Structure:**
```
┌─────────────────────────────────────────────┐
│ search_products_unindexed() ────────────────│ 99.2% CPU
│  ├─ psycopg2.execute() ────────────────────│ 98.8%
│  │  └─ PostgreSQL full table scan ────────│ 98.5%
│  └─ JSON serialization ────────────────────│ 0.4%
└─────────────────────────────────────────────┘
```

The wider the block, the more CPU time that function consumes.

## Fixing the Performance Issue

### Solution: Add Database Index

```sql
-- Add index on description field for LIKE searches
CREATE INDEX idx_products_description_trgm 
ON products 
USING gin(description gin_trgm_ops);

-- Enable trigram extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### After Fix - Expected Results

- Query Duration P95: **45ms** (60x improvement!)
- Flame graph shows `search_products_unindexed()` at **<1% CPU**
- Database index scan replaces full table scan

## Technical Details

### eBPF Profiler Configuration

The profiler uses these key configurations:

```yaml
env:
  - name: CORALOGIX_DOMAIN
    value: "EU2"
  - name: PROFILING_SAMPLE_RATE
    value: "100"  # 100 samples/second
  - name: PROFILING_UPLOAD_INTERVAL
    value: "60"   # Upload every 60 seconds
```

### Resource Requirements

```yaml
resources:
  requests:
    cpu: 100m      # Minimal CPU overhead
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Security Context

The profiler requires privileged access for eBPF:

```yaml
securityContext:
  privileged: true  # Required for eBPF operations
  capabilities:
    add:
      - SYS_ADMIN  # Kernel tracing
      - SYS_PTRACE # Process inspection
```

## Troubleshooting

### Profiler Not Capturing Data

1. Check kernel version:
   ```bash
   uname -r  # Requires kernel 4.9+
   ```

2. Verify eBPF support:
   ```bash
   ls /sys/kernel/debug/tracing/
   ```

3. Check profiler permissions:
   ```bash
   kubectl get pod <profiler-pod> -o yaml | grep -A5 securityContext
   ```

### Profiles Not Appearing in Coralogix

1. Verify API key:
   ```bash
   kubectl get secret dataprime-secrets -o yaml | grep CX_API_KEY
   ```

2. Check profiler logs for upload errors:
   ```bash
   kubectl logs <profiler-pod> | grep -i "upload\|error"
   ```

3. Verify network connectivity to Coralogix:
   ```bash
   kubectl exec <profiler-pod> -- curl -v https://ingress.eu2.coralogix.com
   ```

## Demo Talk Track

### Scene 9.5: Continuous Profiling

> **Narrator**: "We know the database is slow from APM, but WHERE exactly is the bottleneck? Let's look at continuous profiling."
>
> *Switches to Coralogix Continuous Profiling view*
>
> **Narrator**: "This flame graph shows CPU time. See this wide block? That's `search_products_unindexed()` consuming 99.2% of CPU time."
>
> *Clicks into the function to show stack trace*
>
> **Narrator**: "The call stack reveals it's spending all its time in `psycopg2.execute()` doing a PostgreSQL full table scan. The query is using LIKE on an unindexed description field."
>
> **Key Point**: "This is the power of eBPF profiling - it pinpoints the exact function, even in third-party libraries, without any code changes."
>
> **Narrator**: "The fix? Add a GIN index on the description field. After deploying that, the query drops from 2800ms to 45ms - a 60x improvement."

## Key Differentiators

### Why eBPF Profiling?

1. **No Code Changes**: Kernel-level instrumentation
2. **Production Safe**: Minimal overhead (<1% CPU)
3. **Language Agnostic**: Works with Python, Go, Java, C++, Rust
4. **Real Production Data**: Not sampling from synthetic tests

### Coralogix Integration

- Flame graphs automatically linked to traces
- Navigate from slow trace → flame graph → function
- Correlate profiling data with logs, metrics, and traces
- AI-powered insights for optimization recommendations

## References

- [Coralogix Continuous Profiling Docs](https://coralogix.com/docs/continuous-profiling/)
- [eBPF Introduction](https://ebpf.io/)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [pg_trgm Extension](https://www.postgresql.org/docs/current/pgtrgm.html)

## Next Steps

After Scene 9.5, proceed to **Scene 10: Logs with Cora AI** to see how structured logging and AI help investigate the database errors.


