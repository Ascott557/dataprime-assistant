# Demo Orchestration Script - Complete Guide

**Script:** `scripts/reinvent-demo-scenario.sh`  
**Purpose:** Automated re:Invent 2025 database monitoring demonstration  
**Duration:** ~6 minutes

---

## Overview

This script orchestrates a complete database monitoring demonstration, automatically progressing through:
1. ✅ Normal operations (baseline)
2. 🐌 Slow query degradation
3. 💥 Connection pool exhaustion
4. ♻️ Recovery

**No manual intervention required** - the script handles everything!

---

## Quick Start

```bash
# Run the full demo
./scripts/reinvent-demo-scenario.sh 54.235.171.176
```

That's it! The script will guide you through the entire demo with:
- **Talking points** at each step
- **Coralogix actions** to show the audience
- **Automatic pauses** for you to narrate
- **Color-coded output** for easy reading

---

## What It Does

### Phase 1: Baseline (60 seconds)

**What happens:**
- Resets all services to normal state
- Generates 30 seconds of normal traffic
- 10 threads, 10 RPS
- Shows healthy system metrics

**Show in Coralogix:**
- Query time: ~10ms
- Pool utilization: 10-20%
- All services responding

**Talking points (provided by script):**
- "This is what healthy database operations look like"
- "Under normal load, pool utilization is low and queries are fast"

---

### Phase 2: Slow Queries (90 seconds)

**What happens:**
- Enables 2900ms query delay on all services
- Generates 60 seconds of traffic with slow queries
- 20 threads, 15 RPS
- Shows performance degradation

**Show in Coralogix:**
- Query time: ~2900ms
- Pool utilization: 60-80%
- P95 latency spike

**Talking points (provided by script):**
- "Now let's see what happens when a slow query hits"
- "This could be a missing index, unoptimized query, or lock contention"
- "Watch what happens to the entire system when queries slow down"

---

### Phase 3: Pool Exhaustion (60 seconds)

**What happens:**
- Holds 95 of 100 database connections
- Generates 45 seconds of traffic
- 30 threads, 20 RPS
- Shows connection queuing and timeouts

**Show in Coralogix:**
- Pool utilization: 95%+
- Active connections: 95/100
- Connection queuing visible
- Some requests timing out

**Talking points (provided by script):**
- "Now let's push it further - what if the pool runs out of connections?"
- "With 95% of connections held, new requests must wait or timeout"
- "This is what a production incident looks like"

---

### Phase 4: Recovery (10 seconds)

**What happens:**
- Resets all demo modes
- Releases all held connections
- Shows recovery to normal

**Show in Coralogix:**
- Pool utilization drops back to normal
- Query times return to baseline
- System healthy again

---

## Script Features

### 🎨 Color-Coded Output

- **🟢 Green:** Success messages, healthy states
- **🟡 Yellow:** Warnings, degraded performance
- **🔴 Red:** Errors, critical states
- **🔵 Blue:** Coralogix actions
- **🟣 Magenta:** Step headers

### 🔍 Dependency Checking

The script automatically verifies:
- ✅ Python 3 installed
- ✅ curl installed
- ✅ jq installed (optional, for prettier output)
- ✅ Load generator script exists
- ✅ Services are reachable

If anything is missing, it tells you exactly what to install!

### 🛡️ Error Handling

- Validates EC2 IP parameter
- Tests connectivity before starting
- Cleans up background processes
- Provides helpful error messages

### 📊 Real-Time Pool Statistics

At each phase, shows current pool state:
```
Current Pool Status:
   inventory-service:
      Active: 18/100 (18%)
   order-service:
      Active: 16/100 (16%)
```

### ⏸️ Interactive Pauses

The script pauses at key moments:
- Before starting the demo
- Between major phases
- Before showing critical metrics

This gives you time to:
- Narrate what's happening
- Show Coralogix UI
- Answer questions

---

## Usage

### Basic Usage

```bash
./scripts/reinvent-demo-scenario.sh <EC2_IP>
```

**Example:**
```bash
./scripts/reinvent-demo-scenario.sh 54.235.171.176
```

### What You'll See

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          🎯 re:Invent 2025 Demo Scenario                          ║
║          Database Connection Pool Monitoring with Coralogix       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

Configuration:
   Target: http://54.235.171.176
   Services: inventory-service, order-service
   Demo Duration: ~6 minutes

💬 TALKING POINT: Today I'll show you how Coralogix Database APM helps prevent production incidents

Press Enter to begin the demo scenario...
```

---

## Step-by-Step Walkthrough

### Step 1: Reset to Clean State

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: Resetting to Clean State 🔄
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 TALKING POINT: Let's start with a clean slate - resetting all demo simulations

Resetting inventory-service...
✅ Inventory service reset
Resetting order-service...
✅ Order service reset

✅ All services reset to normal operation
📊 CORALOGIX: Database APM should show normal metrics
```

**What to say:**
- "We're starting with a fresh environment"
- "All demo simulations are disabled"
- "This represents our production system under normal load"

---

### Step 2: Establishing Baseline

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: Establishing Baseline - Normal Operations ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 TALKING POINT: This is what healthy database operations look like

Generating normal traffic:
   • Threads: 10
   • Requests/sec: 10
   • Duration: 30 seconds
   • Expected Response Time: 5-20ms
   • Expected Pool Utilization: 10-20%

📊 CORALOGIX: Open: APM → Database Catalog → productcatalog
📊 CORALOGIX: Watch: Query time should be ~10ms, pool utilization ~10-20%

⏳ Generating baseline traffic: 30s remaining...
```

**What to show in Coralogix:**
1. Navigate to: **APM → Database Catalog → productcatalog**
2. Point out:
   - Low query latency (~10ms average)
   - Low pool utilization (10-20%)
   - All services healthy
   - No queuing

**What to say:**
- "Here's our system under normal load"
- "Three microservices sharing one database"
- "Query times are fast, under 20 milliseconds"
- "Connection pool has plenty of capacity"

---

### Step 3: Simulating Slow Queries

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: Simulating Slow Database Queries 🐌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 TALKING POINT: Now let's see what happens when a slow query hits
💬 TALKING POINT: This could be a missing index, unoptimized query, or lock contention

Enabling 2900ms query delay on all services...
✅ Inventory service: 2900ms delay enabled
✅ Order service: 2900ms delay enabled

✅ Slow query simulation enabled
📊 CORALOGIX: Database APM will now show query time spike
```

**What to say:**
- "In production, this could be an unoptimized query"
- "Maybe someone forgot to add an index"
- "Or there's lock contention from a long-running transaction"
- "Watch what happens to ALL services when one query slows down"

---

### Step 4: Observing Impact

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: Observing Slow Query Impact 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generating traffic with slow queries:
   • Threads: 20
   • Requests/sec: 15
   • Duration: 60 seconds
   • Expected Response Time: 2900-3100ms
   • Expected Pool Utilization: 60-80%

📊 CORALOGIX: Watch: P95 latency should spike to ~2800-3000ms
📊 CORALOGIX: Watch: Pool utilization climbing to 60-80%
📊 CORALOGIX: Watch: ALL services affected (inventory, order)

⏳ Generating slow query traffic: 60s remaining...
```

**What to show in Coralogix:**
1. **Query Time Graph:** Spike from 10ms → 2900ms
2. **Pool Utilization:** Climbing to 60-80%
3. **Operations Grid:** ALL services showing slow queries
4. **Trace View:** Pick a trace, show 2900ms database span

**What to say:**
- "Look at this - query time just jumped to nearly 3 seconds"
- "Pool utilization is climbing because queries hold connections longer"
- "Notice ALL services are affected - inventory, order, product"
- "This is the blast radius of one slow query"

---

### Step 5 & 6: Pool Exhaustion

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5: Simulating Connection Pool Exhaustion 💥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 TALKING POINT: Now let's push it further - what if the pool runs out of connections?

Exhausting connection pool (holding 95 of 100 connections)...
✅ Pool exhaustion activated

⚠️  Connection pool exhausted!
Current Pool Status:
   inventory-service:
      Active: 95/100 (95%)
   order-service:
      Active: 95/100 (95%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6: Demonstrating Pool Exhaustion Impact 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 TALKING POINT: With 95% of connections held, new requests must wait or timeout

Generating traffic with exhausted pool:
   • Threads: 30
   • Requests/sec: 20
   • Duration: 45 seconds
   • Expected: Timeouts and errors
   • Pool: 95/100 connections (95%)

⏳ Generating traffic with exhausted pool: 45s remaining...
```

**What to show in Coralogix:**
1. **Pool Utilization:** 95%+
2. **Active Connections:** 95/100
3. **Connection Queuing:** Visible in traces
4. **Error Rate:** Some requests failing

**What to say:**
- "Now we're at 95% pool utilization - this is critical"
- "New requests have to wait for a connection to free up"
- "Some requests are timing out - this means customers see errors"
- "In production, this is when you get paged at 3 AM"

---

### Step 7: System State

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7: Current System State 📈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Final Pool Statistics:
   inventory-service:
      Active: 95/100 (95%)
   order-service:
      Active: 95/100 (95%)

💬 TALKING POINT: This is what a production incident looks like
💬 TALKING POINT: 95% pool utilization means customers are experiencing timeouts

📊 CORALOGIX: In Coralogix Database APM, you can see:
   ✓ Exact moment pool exhausted
   ✓ Which services are affected
   ✓ Query patterns causing the issue
   ✓ Connection pool utilization over time
```

**What to say:**
- "This is what a production incident looks like"
- "Without monitoring, you'd only know when customers start calling"
- "With Coralogix, you can see the exact moment it happened"
- "You can identify which service caused it"
- "You can set alerts to prevent this before it becomes critical"

---

### Step 8: Recovery

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8: Restoring Normal Operation ♻️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Resetting all services to normal operation...
✅ Inventory service: Demo modes disabled, connections released
✅ Order service: Demo modes disabled

Restored Pool Status:
   inventory-service:
      Active: 2/100 (2%)
   order-service:
      Active: 1/100 (1%)

✅ System restored to normal operation
```

**What to say:**
- "And just like that, we can restore normal operations"
- "In production, you'd fix the slow query or scale the pool"
- "Coralogix helps you make that decision with data"

---

## Final Summary

The script concludes with a comprehensive summary:

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                 ✅ Demo Scenario Complete!                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: What We Demonstrated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Normal Operations
   • Baseline: ~10ms queries, 10-20% pool utilization
   • All services healthy and responsive

⚠️  Performance Degradation
   • Slow queries: ~2900ms response time
   • Pool utilization climbed to 60-80%
   • System still operational but degraded

🔥 Production Incident
   • Pool exhaustion: 95% utilization
   • Connection queuing visible
   • Timeouts and errors occurring
   • Customer impact: Slow/failed requests

📊 Coralogix Database APM Visibility
   • All 3 services visible: inventory, order, product
   • Real-time connection pool metrics
   • Query latency tracking
   • Complete distributed traces
```

---

## Coralogix Navigation Guide

After the demo completes, show the audience:

### Database Catalog View

**URL:** `https://eu2.coralogix.com/apm/databases`

**What to show:**
1. **Database:** productcatalog
2. **Calling Services:** 3 services
   - inventory-service (SELECT, UPDATE)
   - order-service (SELECT, INSERT)
   - product-service (SELECT)
3. **Query Time Graph:** The spike from 10ms → 2900ms
4. **Connection Pool:** Utilization from 10% → 95%

### Trace View

**Pick any trace ID from the logs**

**What to show:**
1. Complete distributed trace
2. Database span with connection pool metrics:
   - `db.connection_pool.active`
   - `db.connection_pool.max`
   - `db.connection_pool.utilization_percent`
3. Query duration showing 2900ms
4. All services in the trace chain

### Operations Grid

**What to show:**
- Click on "Operations" tab
- Show operations by service:
  - **inventory-service:** SELECT, UPDATE
  - **order-service:** SELECT, INSERT
  - **product-service:** SELECT
- Click on any operation to see individual queries

---

## Key Talking Points

### Problem Statement

**Without Database Monitoring:**
- ❌ You only know about issues when customers complain
- ❌ No visibility into which service caused the problem
- ❌ Can't see connection pool utilization
- ❌ Difficult to correlate slow queries across services

### Solution

**With Coralogix Database Monitoring:**
- ✅ See issues before customers are impacted
- ✅ Identify which services are affected
- ✅ Monitor connection pool in real-time
- ✅ Set alerts at 80% utilization to prevent incidents
- ✅ Drill down to specific slow queries
- ✅ Make data-driven decisions about scaling

---

## Troubleshooting

### Issue: Script can't reach services

**Error:**
```
❌ Error: Cannot reach inventory-service at http://54.235.171.176:30015
```

**Solution:**
```bash
# Check service health
curl http://54.235.171.176:30015/health
curl http://54.235.171.176:30016/health

# Check K3s pods
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  sudo kubectl get pods -n dataprime-demo
```

---

### Issue: jq not found warning

**Warning:**
```
⚠️  Warning: jq not found (optional)
```

**Solution:**
```bash
# macOS
brew install jq

# Ubuntu
sudo apt-get install jq
```

The script will still work without jq, but output formatting will be less pretty.

---

### Issue: Load generator failing

**Error:**
```
❌ Error: Load generator not found at scripts/generate-demo-load.py
```

**Solution:**
Ensure you're running from the project root:
```bash
cd /Users/andrescott/dataprime-assistant-1
./scripts/reinvent-demo-scenario.sh 54.235.171.176
```

---

## Advanced Usage

### Dry Run (Check Dependencies)

The script automatically checks dependencies before starting. To manually test:

```bash
# Test connectivity
curl http://54.235.171.176:30015/health
curl http://54.235.171.176:30016/health

# Test load generator
python3 scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 5 \
  --rps 5 \
  --duration 10
```

---

### Customize Timing

Edit the script to adjust phase durations:

```bash
# Line 178: Baseline duration (default: 30 seconds)
python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 10 --rps 10 --duration 30

# Line 237: Slow query duration (default: 60 seconds)
python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 20 --rps 15 --duration 60

# Line 289: Pool exhaustion duration (default: 45 seconds)
python3 "$LOAD_GENERATOR" --host "$EC2_IP" --threads 30 --rps 20 --duration 45
```

---

### Run Individual Phases

You can run phases manually if needed:

```bash
# Phase 1: Baseline
curl -X POST http://54.235.171.176:30015/demo/reset
python3 scripts/generate-demo-load.py --host 54.235.171.176 --threads 10 --rps 10 --duration 30

# Phase 2: Slow queries
curl -X POST http://54.235.171.176:30015/demo/enable-slow-queries \
  -H "Content-Type: application/json" -d '{"delay_ms": 2900}'
python3 scripts/generate-demo-load.py --host 54.235.171.176 --threads 20 --rps 15 --duration 60

# Phase 3: Pool exhaustion
curl -X POST http://54.235.171.176:30015/demo/simulate-pool-exhaustion
python3 scripts/generate-demo-load.py --host 54.235.171.176 --threads 30 --rps 20 --duration 45

# Reset
curl -X POST http://54.235.171.176:30015/demo/reset
```

---

## Pre-Demo Checklist

Before running the demo in front of an audience:

- [ ] Services are healthy
  ```bash
  curl http://54.235.171.176:30015/health | jq .
  curl http://54.235.171.176:30016/health | jq .
  ```

- [ ] Coralogix is receiving data
  - Check Database Catalog shows recent queries
  - Verify all 3 services are listed

- [ ] Load generator works
  ```bash
  python3 scripts/generate-demo-load.py \
    --host 54.235.171.176 --threads 5 --rps 5 --duration 10
  ```

- [ ] Script runs successfully
  ```bash
  ./scripts/reinvent-demo-scenario.sh 54.235.171.176
  ```

- [ ] Coralogix login ready (have the URL open in a tab)
  - `https://eu2.coralogix.com/apm/databases`

- [ ] Know your talking points (see above)

---

## Files Summary

| File | Purpose | Size |
|------|---------|------|
| `scripts/reinvent-demo-scenario.sh` | Main orchestration script | 17KB |
| `scripts/generate-demo-load.py` | Load generator (used by orchestration) | 13KB |
| `DEMO-ORCHESTRATION-GUIDE.md` | This guide | 15KB |

---

## Success Criteria

After running the script, you should be able to show:

✅ **Baseline period** with ~10ms queries and 10-20% pool utilization  
✅ **Slow query period** with ~2900ms queries and 60-80% pool utilization  
✅ **Pool exhaustion** with 95% utilization and connection queuing  
✅ **All 3 services** visible in Coralogix Database APM  
✅ **Complete distributed traces** with connection pool metrics  
✅ **Recovery** back to normal operation  

---

## Next Steps

1. **Run the script now:**
   ```bash
   ./scripts/reinvent-demo-scenario.sh 54.235.171.176
   ```

2. **Practice your narrative** using the talking points above

3. **Prepare your Coralogix demo** by bookmarking:
   - Database Catalog view
   - A few example trace IDs
   - Operations grid

4. **Time yourself** - the full demo should take ~6 minutes

5. **Have fun!** This is a powerful demonstration of proactive monitoring

---

**Status:** ✅ **READY FOR RE:INVENT 2025!**

---

**Questions?** Check:
- Load generator guide: `LOAD-GENERATOR-GUIDE.md`
- Quick reference: `DEMO-SCENARIOS-QUICK-REF.md`
- Script help: `./scripts/reinvent-demo-scenario.sh` (without parameters)

