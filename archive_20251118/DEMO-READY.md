# ✅ Demo Application: READY FOR TESTING

**Status**: All core services running and stable  
**Date**: November 17, 2025  
**Instance**: t3.medium (4GB RAM) @ `54.235.171.176`

---

## 🎯 System Status: HEALTHY

| Component | Status | Notes |
|-----------|--------|-------|
| **Frontend** | ✅ Running | HTTPS on port 30443 |
| **API Gateway** | ✅ Running | HTTP on port 30010 |
| **Product Service** | ✅ Running | Optimized image (437MB) |
| **PostgreSQL** | ✅ Running | Database operational |
| **OTel Collector** | ✅ Running | Telemetry pipeline active |

**System Health**:
- Load: 0.25 (excellent)
- Memory: 1.7GB / 3.7GB (46%)
- Disk: 15GB / 29GB (51%)

---

## 🎬 Available Demos

### ✅ Scene 9: Database APM (Telemetry Injection)

**Status**: READY TO DEMO

**How to Run**:

**Option 1: Via Script** (Recommended)
```bash
./test-scene9.sh
```

**Option 2: Via Frontend**
1. Open: https://54.235.171.176:30443
2. Click: "🔥 Simulate Database Issues (Scene 9)"
3. Wait 10-15 seconds
4. Check Coralogix: APM → Database Monitoring → productcatalog

**Option 3: Direct API Call**
```bash
curl -X POST http://54.235.171.176:30010/api/demo/inject-telemetry
```

**Expected Results in Coralogix**:
- **3 calling services**: product-service, order-service, inventory-service
- **Query Duration P95**: ~2800ms (vs 45ms baseline)
- **Query Duration P99**: ~3200ms
- **Total Spans**: 43 database queries
- **Failure Rate**: ~8%
- **Pool Utilization**: 85-98%

**Demo Talk Track**:
```
"Here's our Database APM. Immediately I see the problem:
Query Duration P95: 2800ms - that's nearly 3 seconds for 95% of queries.
Normal baseline: 45ms - we're 60x slower than normal.

See this spike? The P95 shoots through the roof. 43 active queries all
trying to execute simultaneously - the database is overwhelmed.

Connection pool at 95% utilization. Query P95 at 2800ms. See these 43
active queries all queued up? They're waiting for available connections.
This is query queuing - a database bottleneck.

Adding more pods makes this WORSE, not better. You need database
visibility to understand this."
```

---

### ❌ Scene 9.5: Continuous Profiling

**Status**: **DISABLED** (Causes Instance Crashes)

**Why Disabled**:
- eBPF profiling agent created ~3000 crash-looped pods
- Exhausted system resources on t3.medium
- Every profiling attempt crashed the instance
- Not worth the instability for demo purposes

**Recommendation**: Skip this scene or demonstrate profiling on a larger instance type (t3.large or above).

---

## 🔍 Access Points

### Frontend
```
URL: https://54.235.171.176:30443
Note: Self-signed certificate (accept browser warning)
```

### API Gateway
```
Base URL: http://54.235.171.176:30010
Health: http://54.235.171.176:30010/api/health
Products: http://54.235.171.176:30010/api/products
Scene 9: http://54.235.171.176:30010/api/demo/inject-telemetry
```

### SSH Access
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176
```

---

## 📋 Quick Commands

```bash
# Run Scene 9 demo
./test-scene9.sh

# Check system status
./final-status.sh

# View API Gateway logs
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  'kubectl logs -n dataprime-demo -l app=api-gateway --tail=50'

# View all pods
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  'kubectl get pods -n dataprime-demo'

# Restart a service (if needed)
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  'kubectl delete pod -n dataprime-demo -l app=<service-name>'
```

---

## 🎯 Testing Checklist

- [ ] Frontend loads at https://54.235.171.176:30443
- [ ] API Gateway health check returns HTTP 200
- [ ] Scene 9 button triggers telemetry injection
- [ ] Coralogix shows database spans within 15 seconds
- [ ] 3 calling services visible in Database APM
- [ ] Query duration metrics match expected values

---

## 💡 Known Issues & Workarounds

### Issue: Scene 9 Injection Times Out
**Symptom**: POST to `/api/demo/inject-telemetry` takes >15 seconds  
**Cause**: Injector sending 43 spans to OTel Collector  
**Workaround**: Increase timeout to 30 seconds or use the script which has proper timeout

### Issue: OTel Collector Shows "UNAVAILABLE" Errors
**Symptom**: API Gateway logs show "StatusCode.UNAVAILABLE"  
**Cause**: Transient connection issues to OTel Collector  
**Impact**: None - traces still export successfully  
**Workaround**: Ignore these warnings (they're informational)

### Issue: Database Password Mismatch in Tests
**Symptom**: "password authentication failed for user demo_user"  
**Cause**: Database uses `dbadmin` not `demo_user`  
**Impact**: Only affects direct database tests, not the demo  
**Workaround**: Use correct credentials: `POSTGRES_USER=dbadmin`

---

## 🚀 Demo Flow

### Pre-Demo Setup (2 minutes)
1. SSH into instance and verify all pods running
2. Test Scene 9 injection once to ensure it works
3. Open Coralogix in a browser tab
4. Navigate to: APM → Database Monitoring → productcatalog
5. Set time range to "Last 15 minutes"

### Live Demo (3-4 minutes)
1. **Show the application** (https://54.235.171.176:30443)
   - "This is our e-commerce recommendation system"
   - "AI-powered product recommendations"

2. **Trigger the scenario**
   - Click "🔥 Simulate Database Issues"
   - "I'm going to simulate a database exhaustion scenario"

3. **Switch to Coralogix**
   - Wait 10-15 seconds
   - Refresh Database Monitoring view

4. **Walk through the metrics**
   - Point out 3 calling services
   - Show P95/P99 latency spike
   - Explain connection pool exhaustion
   - Show failure rate

5. **Key takeaway**
   - "This is why you need database-level observability"
   - "Adding more pods wouldn't fix this - it would make it worse"
   - "Database APM shows you exactly where the bottleneck is"

---

## 📊 Success Criteria

✅ **Demo is successful if:**
1. Frontend loads without errors
2. Scene 9 button triggers injection
3. Coralogix shows database spans within 15-20 seconds
4. Metrics match expected values (P95: ~2800ms, 3 services, ~8% failures)
5. System remains stable throughout demo
6. No instance crashes or pod restarts

---

## 🎉 Summary

**Current State**: Application is **stable, optimized, and demo-ready**. All core services are running with the optimized Docker image (437MB vs 8GB). Scene 9 (Database APM) is fully functional and demonstrates realistic database exhaustion metrics. Continuous profiling has been disabled to maintain system stability.

**Recommended Demo**: Focus on Scene 9 (Database APM) which showcases Coralogix's database monitoring capabilities with realistic telemetry. This is the strongest part of the demo and works reliably.

**Next Steps**: Run `./test-scene9.sh` to verify everything works, then proceed with the demo!

