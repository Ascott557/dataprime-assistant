# 🎯 re:Invent 2025 Demo - Cheat Sheet

**Print this page or keep it on a second screen during your demo!**

---

## ⚡ Quick Start

```bash
./scripts/reinvent-demo-scenario.sh 54.235.171.176
```

**Duration:** 6 minutes  
**Format:** Automated (just press Enter at pauses)

---

## 📋 Pre-Demo Checklist (2 minutes before)

```bash
# 1. Check services
curl http://54.235.171.176:30015/health | jq .
curl http://54.235.171.176:30016/health | jq .

# 2. Open Coralogix tabs
# Tab 1: https://eu2.coralogix.com/apm/databases
# Tab 2: https://eu2.coralogix.com/apm/traces

# 3. Test script
./scripts/reinvent-demo-scenario.sh 54.235.171.176
# (Ctrl+C after dependency checks pass)
```

---

## 🎬 Demo Flow (6 Minutes)

### Phase 1: Baseline (60s)
- **What:** Normal traffic, 10 threads
- **Show:** 10ms queries, 10-20% pool
- **Say:** *"This is what healthy operations look like"*
- **Coralogix:** Point to low latency graph

### Phase 2: Slow Queries (90s)
- **What:** 2900ms delays enabled, 20 threads
- **Show:** 2900ms queries, 60-80% pool
- **Say:** *"Watch what happens when a slow query hits ALL services"*
- **Coralogix:** Show latency spike, all services affected

### Phase 3: Pool Exhaustion (60s)
- **What:** 95 connections held, 30 threads
- **Show:** 95% pool, timeouts
- **Say:** *"This is a production incident - customers seeing errors"*
- **Coralogix:** Point to 95% utilization, queuing

### Phase 4: Recovery (10s)
- **What:** Reset all modes
- **Show:** Back to normal
- **Say:** *"With Coralogix, you can prevent this before it happens"*

---

## 💬 Key Talking Points

### Opening
> "Today I'll show you how Coralogix Database APM helps prevent production incidents by monitoring connection pools across ALL your microservices."

### Baseline Phase
> "Under normal load, all 3 services share a 100-connection pool. Query times are fast - under 20 milliseconds. Pool utilization is low at 10-20%. This is healthy."

### Slow Query Phase
> "Now a slow query hits - maybe a missing index or lock contention. Watch what happens: Query time jumps to 3 seconds. Pool utilization climbs to 60-80% because queries hold connections longer. Notice ALL services are affected - inventory, order, and product."

### Pool Exhaustion Phase
> "At 95% pool utilization, this is a production incident. New requests have to wait for connections. Some timeout. Customers see errors. Without monitoring, you'd only know when customers start calling. With Coralogix, you see the exact moment it happened."

### Closing
> "Coralogix Database APM gives you: real-time pool monitoring, all calling services in one view, complete distributed traces, and the ability to set alerts at 80% to prevent incidents before they become critical."

---

## 📊 What to Show in Coralogix

### During Baseline
1. Navigate: **APM → Database Catalog → productcatalog**
2. Point to: **Query Time** (show ~10ms)
3. Point to: **Calling Services** (show 3 services)
4. Say: *"All healthy, all fast"*

### During Slow Queries
1. Stay on: **Database Catalog**
2. Point to: **Query Time Graph** (show spike to 2900ms)
3. Click: **Operations** tab
4. Show: **ALL services affected** (inventory, order, product)
5. Say: *"This is the blast radius of one slow query"*

### During Pool Exhaustion
1. Click: **Connection Pool** metric
2. Show: **95% utilization**
3. Show: **Active: 95/100 connections**
4. Say: *"This is critical - only 5 connections left"*

### After Demo
1. Click: **Traces** tab
2. Pick: Any trace ID from terminal output
3. Show: Complete distributed trace
4. Show: Database span with pool metrics
5. Show: `db.connection_pool.utilization_percent: 95.0`

---

## 🔧 Emergency Commands

### If Script Hangs
```bash
# Press Ctrl+C (script handles cleanup)
```

### If Services Down
```bash
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176
sudo kubectl get pods -n dataprime-demo
sudo kubectl logs -n dataprime-demo deployment/inventory-service
```

### Manual Reset
```bash
curl -X POST http://54.235.171.176:30015/demo/reset
curl -X POST http://54.235.171.176:30016/demo/reset
```

### Quick Health Check
```bash
curl http://54.235.171.176:30015/health | jq '.connection_pool'
curl http://54.235.171.176:30016/health | jq '.connection_pool'
```

---

## 🎯 Coralogix URLs (Bookmark These)

```
Database Catalog:
https://eu2.coralogix.com/apm/databases

APM Traces:
https://eu2.coralogix.com/apm/traces

Database productcatalog:
https://eu2.coralogix.com/apm/databases/productcatalog
```

---

## 📱 Audience Q&A Prep

### Q: "How do you set alerts?"
**A:** "In Coralogix, you can create alerts on the `db.connection_pool.utilization_percent` metric. Set a threshold at 80% to get notified before it becomes critical at 95%."

### Q: "Does this work with other databases?"
**A:** "Yes! Coralogix Database APM supports PostgreSQL, MySQL, MongoDB, and more. The key is having the OpenTelemetry instrumentation in place."

### Q: "What about read replicas?"
**A:** "Each database instance gets its own pool monitoring. You can see utilization across primary and replicas, helping you decide when to scale."

### Q: "How much overhead does this add?"
**A:** "Minimal - OpenTelemetry instrumentation adds less than 1ms per query. The connection pool metrics are collected at the application level, not the database level, so there's no database impact."

### Q: "Can I see historical trends?"
**A:** "Absolutely! Coralogix stores all metrics, so you can look back at pool utilization trends over days, weeks, or months. Perfect for capacity planning."

### Q: "What if I have 50 microservices?"
**A:** "That's exactly why this matters! The Database Catalog shows ALL calling services in one view. You can quickly identify which service is causing the issue."

---

## 🎨 Terminal Color Key

- **🟢 Green** = Success, healthy
- **🟡 Yellow** = Warning, degraded
- **🔴 Red** = Error, critical
- **🔵 Blue** = Coralogix action
- **🟣 Magenta** = Step header

---

## ⏱️ Timing Guide

| Phase | Duration | What to Show |
|-------|----------|--------------|
| Intro | 30s | Open Coralogix, explain setup |
| Phase 1 | 60s | Baseline metrics, healthy state |
| Phase 2 | 90s | Slow queries, degradation, ALL services affected |
| Phase 3 | 60s | Pool exhaustion, incident state |
| Phase 4 | 10s | Recovery |
| Wrap-up | 60s | Navigate Coralogix, show traces |
| Q&A | 90s | Answer questions |
| **TOTAL** | **6 min** | *Perfect for conference format* |

---

## 🎤 Opening Line

> "Raise your hand if you've been paged at 3 AM because your database is slow..."  
> *(pause for hands)*  
> "Today I'm going to show you how to prevent that with Coralogix Database APM."

---

## 🎤 Closing Line

> "In 6 minutes, we went from healthy operations to a production incident and back. With Coralogix, you can see this happening in real-time, set alerts to prevent it, and when it does happen, identify the exact cause in seconds instead of hours. That's the difference between a 3 AM page and a good night's sleep."

---

## 📊 Success Metrics to Mention

During the demo, these numbers should appear:
- **Baseline:** 10ms avg query time, 10-20% pool
- **Slow queries:** 2900ms avg query time, 60-80% pool
- **Pool exhaustion:** 95% pool utilization, 95/100 connections
- **Services affected:** 3 (inventory, order, product)
- **Trace IDs collected:** 100+ for verification

If these numbers appear in your terminal, the demo is working correctly!

---

## 🚨 If Something Goes Wrong

### Script Fails to Start
1. Check you're in project root: `pwd` should show `dataprime-assistant-1`
2. Check services are running: `curl http://54.235.171.176:30015/health`
3. Fall back to manual commands from `DEMO-SCENARIOS-QUICK-REF.md`

### Coralogix Shows No Data
1. Wait 2-3 minutes (telemetry has latency)
2. Check OTel Collector: `kubectl logs -n dataprime-demo deployment/coralogix-opentelemetry-collector`
3. If still broken, show the CLI output as backup

### Services Return Errors
1. Press Ctrl+C to stop script
2. Run reset: `curl -X POST http://54.235.171.176:30015/demo/reset`
3. Wait 30 seconds
4. Restart script

---

## 🎬 Body Language Tips

- **Point to the screen** when highlighting metrics
- **Pause after key numbers** (let them sink in)
- **Slow down during Phase 3** (build tension)
- **Speed up during Phase 4** (relief)
- **Make eye contact** during talking points
- **Use your hands** to show "spike" and "drop"

---

## 💡 Remember

- ✅ The script does all the work
- ✅ You just narrate what's happening
- ✅ Pause at the prompts
- ✅ Show Coralogix during traffic generation
- ✅ Have fun - this is impressive!

---

## 📞 Support Contact (if needed)

**Coralogix Support:** [support@coralogix.com](mailto:support@coralogix.com)  
**Demo Issues:** Check `DEMO-ORCHESTRATION-GUIDE.md` for troubleshooting

---

**GOOD LUCK! 🚀**

**You've got this! The demo is automated, professional, and compelling. Just follow along and narrate what you see happening. The audience will be impressed!**

---

*Last updated: November 16, 2025*

