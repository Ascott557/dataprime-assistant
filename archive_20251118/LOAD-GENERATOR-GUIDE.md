# Load Generator Guide for re:Invent 2025 Demo

**Purpose:** Generate realistic database load to demonstrate connection pool exhaustion and database monitoring in Coralogix.

**File:** `scripts/generate-demo-load.py`

---

## Overview

The load generator simulates realistic traffic across all three database-backed services:
- **product-service** - Product catalog queries
- **inventory-service** - Stock checking
- **order-service** - Popular products analytics

It creates concurrent load that pushes the shared PostgreSQL connection pool (maxconn=100) to demonstrate:
- Normal operations (10-20% pool utilization)
- Heavy load (80-90% pool utilization)
- Pool exhaustion (95%+ utilization with queuing)

---

## Features

✅ **Concurrent requests** across multiple services  
✅ **Configurable parameters** (threads, RPS, duration)  
✅ **Real-time statistics** (every 5 seconds)  
✅ **Trace ID collection** for Coralogix verification  
✅ **Demo mode support** (auto-enable slow queries)  
✅ **Automatic cleanup** (reset demo modes)  

---

## Installation

```bash
# No installation needed - uses standard Python libraries
python3 --version  # Requires Python 3.7+

# Optional: Install in virtual environment
cd /Users/andrescott/dataprime-assistant-1
python3 -m venv venv
source venv/bin/activate
pip install requests urllib3
```

---

## Usage

### Basic Syntax

```bash
python scripts/generate-demo-load.py \
  --host <EC2_IP> \
  --threads <NUM_THREADS> \
  --rps <REQUESTS_PER_SECOND> \
  --duration <SECONDS> \
  [--enable-slow-queries]
```

### Demo Scenarios

#### 1. Normal Traffic (Baseline)

**Goal:** 10-20% pool utilization, fast response times

```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 10 \
  --rps 10 \
  --duration 60
```

**Expected Results:**
- Pool utilization: 10-20%
- Response time: 5-20ms
- Success rate: 99%+
- All services healthy

---

#### 2. Heavy Load

**Goal:** 80-90% pool utilization, some queuing

```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 50 \
  --rps 30 \
  --duration 120
```

**Expected Results:**
- Pool utilization: 80-90%
- Response time: 10-50ms
- Success rate: 95%+
- Some connection queuing

---

#### 3. Pool Exhaustion (Demo Scenario)

**Goal:** 95%+ pool utilization, significant queuing

```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 50 \
  --rps 30 \
  --duration 120 \
  --enable-slow-queries
```

**What this does:**
1. Enables 2900ms slow query delays on all services
2. Generates 50 concurrent threads
3. Attempts 30 requests/second
4. Each query holds a connection for ~3 seconds
5. Pool quickly exhausts (95/100 connections)
6. New requests queue or timeout

**Expected Results:**
- Pool utilization: 95%+
- Response time: 2900-3500ms (slow queries + queuing)
- Success rate: 70-90% (some timeouts)
- Visible queuing in Coralogix

---

#### 4. Quick Test

**Goal:** Verify services are responding

```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 5 \
  --rps 5 \
  --duration 30
```

**Expected Results:**
- Quick verification that all services work
- Generates trace IDs for Coralogix verification

---

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `--host` | *required* | - | EC2 IP address or hostname |
| `--threads` | 20 | 1-200 | Number of concurrent worker threads |
| `--rps` | 20 | 1-1000 | Target requests per second |
| `--duration` | 120 | 10-3600 | Duration in seconds |
| `--enable-slow-queries` | false | - | Enable 2900ms query delays |

---

## Output

### Real-Time Stats (Every 5 seconds)

```
📊 Stats (t=15s):
   Requests: 230 total, 228 success, 2 failed
   Success Rate: 99.1%
   Actual RPS: 15.3
   Response Time: avg=18ms, p95=45ms
   By Service:
      product-service: 46 requests
      inventory-service: 138 requests
      order-service: 46 requests
   Errors:
      Timeout: 2
```

### Final Results

```
📈 FINAL RESULTS
====================================================================
📊 Stats (t=120s):
   Requests: 2400 total, 2280 success, 120 failed
   Success Rate: 95.0%
   Actual RPS: 20.0
   Response Time: avg=2950ms, p95=3100ms
   By Service:
      product-service: 480 requests
      inventory-service: 1440 requests
      order-service: 480 requests
   Errors:
      Timeout: 85
      ConnectionError: 35

🔍 Generated Trace IDs (2280 total):
   First 10:
   cd5541cb6583355c02ec7a4104843cd3
   0be2e7b0288ad8a1d95d32990054751e
   ...
```

---

## Connection Pool Math

Understanding how the load translates to pool utilization:

### Formula
```
Pool Utilization = (Threads × Avg Query Time) / Pool Size
```

### Examples

**Scenario 1: Normal Load**
- Threads: 10
- Avg Query Time: 15ms
- Pool Size: 100
- **Utilization:** (10 × 0.015) / 100 = **0.15% per thread** → ~10-20% total

**Scenario 2: Heavy Load**
- Threads: 50
- Avg Query Time: 20ms
- Pool Size: 100
- **Utilization:** (50 × 0.020) / 100 = **1.0** → ~80-90% total

**Scenario 3: Pool Exhaustion (Slow Queries)**
- Threads: 50
- Avg Query Time: 2900ms (slow queries enabled)
- Pool Size: 100
- **Utilization:** (50 × 2.9) / 100 = **145%** → **POOL EXHAUSTED** ⚠️

When utilization exceeds 100%, new requests must wait for connections to be released!

---

## Demo Flow

### Step 1: Establish Baseline

```bash
# Show normal operations
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 10 \
  --rps 10 \
  --duration 60
```

**Show in Coralogix:**
- Low pool utilization (10-20%)
- Fast query times (5-20ms)
- All services reporting healthy

---

### Step 2: Increase Load

```bash
# Ramp up to heavy load
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 40 \
  --rps 25 \
  --duration 90
```

**Show in Coralogix:**
- Pool utilization climbing (60-80%)
- Query times increasing slightly (10-30ms)
- Services still healthy but working harder

---

### Step 3: Pool Exhaustion

```bash
# Enable slow queries and exhaust pool
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 50 \
  --rps 30 \
  --duration 120 \
  --enable-slow-queries
```

**Show in Coralogix:**
- Pool utilization at 95%+
- Query times spiking (2900ms+)
- Connection queuing visible
- Some timeouts/errors
- Database Monitoring showing slow queries across all 3 services

---

### Step 4: Verify Traces

Use the collected trace IDs to show:
1. Complete distributed traces
2. Database spans with pool metrics
3. Slow query indicators
4. Connection queuing time

---

## Monitoring in Coralogix

### What to Check

1. **Database Monitoring UI**
   - Go to: APM → Database Catalog → productcatalog
   - Check: Connection pool utilization graph
   - Verify: All 3 services visible as "Calling Services"

2. **APM Traces**
   - Search for any trace ID from the output
   - Verify: Complete trace with database spans
   - Check: `db.connection_pool.utilization_percent` attribute

3. **Metrics**
   - Query time average (should spike during slow queries)
   - Total queries (should match request count)
   - Connection pool metrics

---

## Troubleshooting

### High Error Rate (>20%)

**Possible causes:**
- Services not fully started
- Network issues
- Pool already exhausted by other traffic

**Solutions:**
```bash
# Check service health
curl http://54.235.171.176:30015/health | jq .
curl http://54.235.171.176:30016/health | jq .

# Reset demo modes
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
```

---

### Not Reaching Target RPS

**Possible causes:**
- Not enough threads
- Services too slow
- Network latency

**Solutions:**
```bash
# Increase threads
--threads 60

# Or reduce RPS target
--rps 15
```

---

### No Trace IDs Generated

**Possible causes:**
- Services not returning trace IDs in response
- All requests failing

**Solutions:**
- Check that services are responding successfully
- Verify at least some requests have 200 status

---

## Advanced Usage

### Custom Load Patterns

Modify the script to add custom endpoints:

```python
# In LoadGenerator.__init__()
self.endpoints = [
    ('product-service', f'http://{host}:30010/products?category=Headphones&price_min=0&price_max=300'),
    ('inventory-service', f'http://{host}:30015/inventory/check/5'),
    # Add more endpoints...
]
```

### Gradual Ramp-Up

```bash
# Start light, increase every 30 seconds
for threads in 10 20 30 40 50; do
  echo "Running with $threads threads..."
  python scripts/generate-demo-load.py \
    --host 54.235.171.176 \
    --threads $threads \
    --rps $threads \
    --duration 30
  sleep 5
done
```

### Stress Test

```bash
# Maximum load
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 100 \
  --rps 50 \
  --duration 300 \
  --enable-slow-queries
```

---

## Integration with Demo

### Before Demo

1. **Verify services are healthy:**
   ```bash
   python scripts/generate-demo-load.py \
     --host 54.235.171.176 \
     --threads 5 \
     --rps 5 \
     --duration 20
   ```

2. **Collect some baseline trace IDs for reference**

### During Demo

1. **Show normal operations** (Step 1)
2. **Increase load gradually** (Step 2)
3. **Demonstrate pool exhaustion** (Step 3)
4. **Show Coralogix traces** (Step 4)

### After Demo

The script automatically resets demo modes, but you can manually verify:

```bash
# Check all services are reset
curl http://54.235.171.176:30015/health | jq '.demo_mode'
curl http://54.235.171.176:30016/health | jq '.demo_mode'
```

---

## Summary

The load generator provides a controlled way to demonstrate database performance under various load conditions. By adjusting threads, RPS, and enabling slow queries, you can show:

✅ **Normal operations** - Everything works smoothly  
✅ **Performance degradation** - Load increases but system copes  
✅ **Pool exhaustion** - Critical issue requiring attention  

All visible in real-time through Coralogix Database Monitoring!

---

**Questions?** Check the inline help:

```bash
python scripts/generate-demo-load.py --help
```

