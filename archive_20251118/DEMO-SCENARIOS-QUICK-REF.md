# Demo Scenarios - Quick Reference Card

**For:** re:Invent 2025 Database Monitoring Demo  
**Services:** inventory-service, order-service, (product-service)

---

## 🎯 Scenario 1: Normal Operations (Baseline)

**Command:**
```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 10 \
  --rps 10 \
  --duration 60
```

**Expected:**
- ✅ 10-20% pool utilization
- ✅ 5-20ms response times
- ✅ 99%+ success rate

**Talking Points:**
- "Under normal load, all 3 services share the same 100-connection pool"
- "You can see ~10-20% utilization - plenty of headroom"
- "Query times are fast, under 20ms"

---

## 🎯 Scenario 2: Heavy Load

**Command:**
```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 40 \
  --rps 25 \
  --duration 90
```

**Expected:**
- ⚠️ 60-80% pool utilization
- ⚠️ 10-40ms response times
- ✅ 95%+ success rate

**Talking Points:**
- "As load increases, pool utilization climbs to 60-80%"
- "Response times increase slightly but system is coping"
- "All 3 services are competing for connections"

---

## 🎯 Scenario 3: Pool Exhaustion (CRITICAL)

**Command:**
```bash
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 50 \
  --rps 30 \
  --duration 120 \
  --enable-slow-queries
```

**Expected:**
- 🔥 95%+ pool utilization
- 🔥 2900-3500ms response times
- ❌ 70-90% success rate (timeouts)

**Talking Points:**
- "I've enabled a 2900ms delay to simulate a slow database query"
- "Watch what happens - pool quickly exhausts (95 of 100 connections)"
- "New requests have to wait or timeout"
- "In Coralogix, you can see the exact moment the pool exhausts"
- "Database Monitoring shows ALL 3 services affected"
- "This is why connection pool monitoring is critical"

---

## 📊 What to Show in Coralogix

### Database Catalog View
1. Navigate: **APM** → **Database Catalog** → **productcatalog**
2. Show:
   - ✅ All 3 services in "Calling Services" dropdown
   - ✅ Query time graph (spikes during slow queries)
   - ✅ Total queries increasing during load test
   - ✅ Connection pool utilization climbing to 95%

### Trace View
1. Pick a trace ID from load generator output
2. Navigate: **APM** → **Traces** → Search for trace ID
3. Show:
   - ✅ Complete distributed trace
   - ✅ Database span with `SpanKind.CLIENT`
   - ✅ All required attributes (`db.system`, `db.name`, `net.peer.name`)
   - ✅ Connection pool metrics in span attributes:
     - `db.connection_pool.active`
     - `db.connection_pool.max`
     - `db.connection_pool.utilization_percent`

### Operations Grid
1. Show operations by service:
   - **inventory-service:** `SELECT products`, `UPDATE products`
   - **order-service:** `SELECT orders`, `INSERT orders`
   - **product-service:** `SELECT products`

---

## 🚀 Demo Flow (7 minutes)

### Minute 0-2: Introduction
- "I have 3 microservices sharing one PostgreSQL database"
- "Each service has its own workload pattern"
- "They all share a 100-connection pool"

### Minute 2-3: Normal Operations
- Run Scenario 1
- Show 10-20% utilization in Coralogix
- "Everything looks healthy"

### Minute 3-4: Increase Load
- Run Scenario 2
- Show 60-80% utilization
- "Load is increasing but system is coping"

### Minute 4-6: Pool Exhaustion
- Run Scenario 3 (with slow queries)
- Show 95% utilization
- "Now watch what happens when a slow query hits"
- Point out:
  - Query time spike
  - Pool exhaustion
  - All services affected
  - Timeouts starting

### Minute 6-7: Wrap Up
- Show trace with pool metrics
- "With Coralogix Database Monitoring, you can:"
  - Identify connection pool issues before they become critical
  - See which services are impacted
  - Drill down to specific slow queries
  - Make data-driven decisions about scaling

---

## 🔧 Troubleshooting

### Services Not Responding
```bash
# Check health
curl http://54.235.171.176:30015/health | jq .
curl http://54.235.171.176:30016/health | jq .

# Check pool status
curl http://54.235.171.176:30015/health | jq '.connection_pool'
```

### Reset Demo Mode
```bash
# If slow queries are stuck on
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
```

### Quick Test Before Demo
```bash
# 20-second sanity check
python scripts/generate-demo-load.py \
  --host 54.235.171.176 \
  --threads 5 \
  --rps 5 \
  --duration 20
```

---

## 💡 Key Talking Points

1. **Shared Connection Pool**
   - "All services compete for the same 100 connections"
   - "This is realistic - most companies don't run separate DB instances per service"

2. **Manual Instrumentation**
   - "We use manual OpenTelemetry instrumentation"
   - "Every database query includes connection pool metrics"
   - "You can see utilization in real-time"

3. **Coralogix Database Monitoring**
   - "Gives you complete visibility into database performance"
   - "Shows all calling services, not just one"
   - "Includes connection pool metrics in every span"
   - "Helps you prevent incidents before they happen"

4. **Real-World Impact**
   - "95% pool utilization = customers seeing timeouts"
   - "Without monitoring, you'd only know when customers complain"
   - "With Coralogix, you can set alerts at 80% to prevent issues"

---

## 📋 Pre-Demo Checklist

- [ ] Services are healthy (`/health` returns 200)
- [ ] Database has sample data
- [ ] Load generator tested (quick 20s run)
- [ ] Coralogix showing recent data (check APM)
- [ ] Know your trace IDs for examples
- [ ] Demo modes are reset

---

## 🎬 One-Liners for Copy-Paste

```bash
# Baseline
python scripts/generate-demo-load.py --host 54.235.171.176 --threads 10 --rps 10 --duration 60

# Heavy
python scripts/generate-demo-load.py --host 54.235.171.176 --threads 40 --rps 25 --duration 90

# Exhaustion
python scripts/generate-demo-load.py --host 54.235.171.176 --threads 50 --rps 30 --duration 120 --enable-slow-queries

# Quick test
python scripts/generate-demo-load.py --host 54.235.171.176 --threads 5 --rps 5 --duration 20

# Reset
curl -X POST http://54.235.171.176:30015/demo/reset && curl -X POST http://54.235.171.176:30016/demo/reset
```

---

**Status:** ✅ Ready for re:Invent 2025!

