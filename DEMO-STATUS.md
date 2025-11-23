# 🚀 Black Friday Demo - RUNNING

## Status: ✅ ACTIVE

**Start Time**: November 23, 2025 at 06:29 UTC  
**Demo Duration**: 30 minutes  
**Traffic Rate**: 100 requests/minute  
**End Time**: ~06:59 UTC

## Configuration Applied ✅

### Database Issues
- ✅ **Indexes Dropped**: `idx_products_category` and `idx_products_stock_quantity` removed
- ✅ **Connection Pool**: Set to 20 (normally 100) - **THIS WILL CAUSE FAILURES**
- ✅ **ConfigMap**: `DEMO_MODE=blackfriday`, `DEMO_START_TIMESTAMP=1763879162`

### Services Restarted
- ✅ All 8 e-commerce services restarted with new configuration
- ✅ PostgreSQL ready with missing indexes
- ✅ Load generator running traffic simulation

## Expected Timeline

| Time | Phase | What Happens |
|------|-------|--------------|
| **0-10 min** | 🟢 Ramp | Traffic increasing, queries start slowing |
| **10-15 min** | 🟡 Peak | 100+ rpm, database strain increasing |
| **15-20 min** | 🟠 Degradation | 2500ms queries, P95 latency spike |
| **20-25 min** | 🔴 Critical | Connection pool exhaustion begins |
| **22-23 min** | 🚨 **ALERT** | **FLOW ALERT SHOULD TRIGGER** |
| **25-30 min** | 💥 Peak Failure | 35% error rate, revenue impact |

## Current Demo Minute: Calculate from timestamp

```bash
# Current demo minute
echo $(( ($(date +%s) - 1763879162) / 60 ))
```

## Monitoring Commands

### Check Load Generator Status
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl logs -n ecommerce-demo -l app=load-generator --tail=20'
```

### Check Product Catalog (Slow Queries)
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl logs -n ecommerce-demo -l app=product-catalog --tail=30 | grep -i "slow\|duration\|delay"'
```

### Check Checkout (Pool Exhaustion)
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl logs -n ecommerce-demo -l app=checkout --tail=30 | grep -i "pool\|connection\|exhausted"'
```

### Check All Pods
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl get pods -n ecommerce-demo'
```

### Check PostgreSQL Indexes (Should be missing)
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl exec -n ecommerce-demo postgresql-primary-0 -- psql -U ecommerce_user -d ecommerce -c "\di products*"'
```

## What to Watch in Coralogix

### 1. Traces (Application: ecommerce-platform)
Look for spans with these attributes:
- `db.slow_query=true` (after minute 10)
- `db.full_table_scan=true` (after minute 15)
- `db.connection.pool.exhausted=true` (after minute 20)
- `checkout.failed=true` (after minute 20)

### 2. Logs (Subsystem: ecommerce-services)
Look for structured logs:
- `demo_slow_query_triggered`
- `demo_pool_exhaustion`  
- `demo_checkout_failed`

### 3. Incidents (Expected at minute ~22)
- **Flow Alert** should trigger
- **Root Cause**: Database misconfiguration
- **Impact**: High error rate + slow queries + failed checkouts

## Key Metrics to Monitor

1. **P95 Latency**: Should spike from ~50ms to 2500ms+
2. **Error Rate**: Should increase from 0% to ~35%
3. **Checkout Success Rate**: Should drop from 100% to ~65%
4. **Database Connection Pool**: Should hit 100% utilization

## Demo Commands

### Get Real-Time Status
```bash
DEMO_START=1763879162
CURRENT=$(date +%s)
ELAPSED_MINUTES=$(( (CURRENT - DEMO_START) / 60 ))
echo "Demo Minute: $ELAPSED_MINUTES / 30"

if [ $ELAPSED_MINUTES -lt 10 ]; then
    echo "Phase: RAMP - Traffic increasing"
elif [ $ELAPSED_MINUTES -lt 15 ]; then
    echo "Phase: PEAK - Normal operations at peak load"
elif [ $ELAPSED_MINUTES -lt 20 ]; then
    echo "Phase: DEGRADATION - Database issues emerging"
else
    echo "Phase: CRITICAL - Connection pool exhaustion"
fi
```

### Check Traffic Generation
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'cat /Users/andrescott/.cursor/projects/Users-andrescott-Movies-Coralogix-Reinventdemo-code-workspace/terminals/4.txt'
```

## Cleanup (After Demo)

After 30 minutes or when ready to stop:

```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 'bash -s' << 'EOF'
# Restore indexes
sudo kubectl exec -n ecommerce-demo postgresql-primary-0 -- \
  psql -U ecommerce_user -d ecommerce -c "
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
    CREATE INDEX IF NOT EXISTS idx_products_stock_quantity ON products(stock_quantity);
  "

# Reset ConfigMap
sudo kubectl patch configmap ecommerce-config -n ecommerce-demo \
  --patch '{"data": {"DB_MAX_CONNECTIONS": "100", "DEMO_MODE": "off"}}'

# Restart services
sudo kubectl rollout restart deployment -n ecommerce-demo

echo "✅ Demo cleanup complete"
EOF
```

## Success Indicators

- ✅ Traffic is generating (100 rpm)
- ✅ Database indexes are missing
- ✅ Connection pool is limited to 20
- ✅ Services are in DEMO_MODE=blackfriday
- ⏳ Waiting for minute 22 for Flow Alert...

## Coralogix Links

- **Incidents**: https://eu2.coralogix.com/incidents
- **APM**: https://eu2.coralogix.com/apm
- **Logs**: https://eu2.coralogix.com/logs
- **Application**: `ecommerce-platform`

---

**🎯 Goal**: Demonstrate how Coralogix observability catches complex production issues  
**⏱️  Timeline**: 30 minutes from 06:29 UTC  
**🚨 Alert Expected**: Minute 22-23

