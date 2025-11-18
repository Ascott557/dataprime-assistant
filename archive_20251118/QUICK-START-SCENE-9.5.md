# Quick Start: Scene 9.5 - Continuous Profiling

## 🚀 **3-Step Setup**

### **1. Install Profiling (5 minutes)**

```bash
cd /Users/andrescott/dataprime-assistant-1
./install-continuous-profiling.sh
```

*Enter your Coralogix Private API Key when prompted*

---

### **2. Generate CPU Load (1 minute)**

```bash
./run-scene9.5-demo.sh
```

*Makes 50 requests with unindexed query to generate flame graph data*

---

### **3. View in Coralogix (wait 1-2 minutes)**

**Navigate to:** `APM → Continuous Profiling → product-service`

**Look for:**
- 🔥 Flame graph showing `search_products_unindexed()` at **99.2% CPU**
- The slow query: `SELECT * FROM products WHERE description LIKE '%wireless%'`
- Function consuming **~2900ms** per request

---

## 🎬 **Demo Talk Track (30 seconds)**

> "Database APM showed WHAT is slow - 2900ms queries.  
> But Continuous Profiling shows WHERE in the code.  
> [Open flame graph]  
> Look - `search_products_unindexed()` consuming 99.2% CPU.  
> The culprit: unindexed LIKE query on the description field.  
> eBPF auto-instrumentation - no code changes needed.  
> From alert → database metric → exact line of code.  
> All in one unified platform."

---

## 🔧 **If Profiling Data Doesn't Appear**

1. **Check profiler is running:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "sudo kubectl get pods -n dataprime-demo | grep profiler"
   ```

2. **Wait longer** - eBPF data can take 30-90 seconds to propagate

3. **Run demo again** - More CPU load = clearer flame graph

4. **Check time range** - Set to "Last 15 minutes" in Coralogix

---

## ✅ **Expected Results**

| Metric | Value |
|--------|-------|
| **CPU Consumption** | 99.2% in `search_products_unindexed()` |
| **Query Duration** | ~2900ms per request |
| **Flame Graph** | Shows full call stack to slow query |
| **Issue Identified** | Full table scan on `description` field |
| **Solution** | Add index to `description` column |

---

**🎯 Demo-Ready in 7 minutes!**

Full documentation: `SCENE-9.5-CONTINUOUS-PROFILING.md`

