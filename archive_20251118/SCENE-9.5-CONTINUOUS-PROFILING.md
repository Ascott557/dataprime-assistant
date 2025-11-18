# Scene 9.5: Continuous Profiling - Complete Setup Guide

## 🎯 **Overview**

This guide covers **Scene 9.5: Continuous Profiling**, which demonstrates finding the exact code causing slow database queries using eBPF-based continuous profiling.

### **The Investigation Flow:**
1. **Scene 9 (Database APM)**: "Database is slow - 2800ms queries"
2. **Scene 9.5 (Continuous Profiling)**: "Here's the exact function and line of code"

## 📋 **Prerequisites**

- ✅ Scene 9 (Database APM) completed
- ✅ K8s cluster running (K3s on AWS EC2)
- ✅ Coralogix Private API Key
- ✅ Helm v3.9+ installed on cluster
- ✅ kubectl access to cluster

## 🚀 **Step 1: Install Continuous Profiling**

### **Run the Installation Script:**

```bash
cd /Users/andrescott/dataprime-assistant-1
./install-continuous-profiling.sh
```

**What this does:**
1. Adds Coralogix Helm repository
2. Creates/updates `coralogix-keys` secret with your Private API Key
3. Deploys eBPF profiling agent (DaemonSet on all nodes)
4. Configures OpenTelemetry collector to export profiling data
5. Uses Helm chart version **v0.0.231** (per [Coralogix docs](https://coralogix.com/docs/user-guides/continuous-profiling/setup/))

### **Verify Installation:**

```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl get pods -n dataprime-demo | grep -E 'profiler|otel'"
```

**Expected output:**
```
coralogix-ebpf-profiler-xxxxx     1/1     Running     0          2m
opentelemetry-agent-xxxxx         1/1     Running     0          2m
```

## 🔥 **Step 2: Generate Profiling Data**

The unindexed query function is already implemented in `product_service.py`:

```python
@app.route('/products/search', methods=['GET'])
def search_products_unindexed():
    """
    UNINDEXED search - demonstrates profiling catching slow queries.
    Uses LIKE '%term%' on description field without index.
    Shows in flame graph as search_products_unindexed() consuming 99.2% CPU.
    """
    # ...
    query = """
        SELECT id, name, category, price, description, image_url, stock_quantity
        FROM products
        WHERE description LIKE %s  -- NO INDEX! Full table scan!
    """
    cursor.execute(query, (f'%{search_term}%',))
```

### **Run the Demo Script:**

```bash
./run-scene9.5-demo.sh
```

**What this does:**
- Makes 50 concurrent requests to `/products/search?q=wireless`
- Each request triggers the unindexed query
- Generates sustained CPU load (~30-60 seconds)
- eBPF agent captures stack traces showing CPU time distribution

**Expected output:**
```
🔥 Generating CPU load with unindexed queries...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[  1] ✓ 200 - 15 products - 2847.3ms
[  2] ✓ 200 - 15 products - 2891.2ms
[  3] ✓ 200 - 15 products - 2763.8ms
...
[50] ✓ 200 - 15 products - 2812.5ms

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Completed: 50/50 successful requests
Duration: 35.2s
Rate: 1.4 req/s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 📊 **Step 3: View in Coralogix**

### **Navigate to Profiling:**

1. Open Coralogix
2. Go to: **APM → Continuous Profiling**
3. Select service: **product-service**
4. Time range: **Last 15 minutes**

### **What You Should See:**

**Flame Graph View:**
- 🔥 `search_products_unindexed()` function consuming **99.2% CPU**
- Stack trace showing: `cursor.execute()` → `SELECT ... LIKE` query
- Histogram showing query duration spikes to **~2800-2900ms**

**Profiling Details:**
- **Function**: `search_products_unindexed()`
- **File**: `product_service.py`
- **Line**: ~372 (the `cursor.execute()` call)
- **CPU Time**: 99.2% of service CPU
- **Issue**: Full table scan on `description` field (no index)

## 🎬 **Demo Talk Track**

**Scene 9 → Scene 9.5 Transition:**

> **"Database APM showed us WHAT is slow - a query taking 2900ms.**
> 
> **But it doesn't show WHERE in the code. Let me check Continuous Profiling...**
> 
> **[Open flame graph]**
> 
> **Here's our product-service. This flame graph shows time distribution across all functions. Look at this - `search_products_unindexed()` is consuming 99.2% of our CPU time. Almost 3 full seconds.**
> 
> **Click into it... and here's the culprit: `SELECT * FROM products WHERE description LIKE '%wireless%'`. This is a full table scan. There's no index on the description field.**
> 
> **This is eBPF auto-instrumentation. We didn't add any profiling code. The eBPF agent automatically captures function-level performance data by instrumenting the kernel. From alert, to database metric, to the exact line of code - all in one unified platform.**
> 
> **This is the difference between 'I know something is slow' and 'I know exactly which function to fix.' Competitor tools stop at the database layer. We take you all the way to the code."**

## 🔧 **Troubleshooting**

### **No Profiling Data Appearing?**

1. **Check profiler pods are running:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "sudo kubectl get pods -n dataprime-demo | grep profiler"
   ```

2. **Check profiler logs:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "sudo kubectl logs -n dataprime-demo -l app=coralogix-ebpf-profiler --tail=50"
   ```

3. **Verify eBPF kernel support:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "uname -r && ls /sys/kernel/debug/tracing/"
   ```

4. **Check product-service has CPU load:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "sudo kubectl top pod -n dataprime-demo | grep product-service"
   ```

### **Profiling Data Delayed?**

- eBPF profiling data can take **30-90 seconds** to appear in Coralogix
- Run the demo script, then **wait 1-2 minutes** before checking Coralogix
- Refresh the Coralogix UI to ensure latest data is loaded

### **Function Not Showing in Flame Graph?**

- Ensure you ran `./run-scene9.5-demo.sh` to generate CPU load
- Check the time range in Coralogix matches when you ran the demo
- Python functions need sustained CPU time (~30s+) to appear clearly in flame graphs

## 🎯 **Key Differences: Scene 9 vs Scene 9.5**

| Aspect | Scene 9 (Database APM) | Scene 9.5 (Continuous Profiling) |
|--------|------------------------|----------------------------------|
| **Question** | "WHAT is slow?" | "WHERE in the code?" |
| **Answer** | "Database query: 2900ms" | "Function: `search_products_unindexed()`" |
| **View** | Database metrics, latency charts | Flame graph, function-level CPU time |
| **Data Source** | Database spans (OpenTelemetry) | eBPF kernel instrumentation |
| **Granularity** | Query-level | Line-of-code level |
| **Action** | "The database is bottlenecked" | "Fix this exact function" |

## 📚 **Additional Resources**

- [Coralogix Continuous Profiling Docs](https://coralogix.com/docs/user-guides/continuous-profiling/setup/)
- [eBPF Official Site](https://ebpf.io/)
- [OpenTelemetry Profiling](https://opentelemetry.io/docs/specs/otel/profiles/)

## ✅ **Checklist: Demo Ready**

- [ ] Continuous Profiling installed via Helm
- [ ] Profiler pods running (verify with `kubectl get pods`)
- [ ] Ran `./run-scene9.5-demo.sh` successfully
- [ ] Waited 1-2 minutes for data propagation
- [ ] Opened Coralogix → APM → Continuous Profiling → product-service
- [ ] See flame graph with `search_products_unindexed()` function
- [ ] CPU time showing ~99.2% for that function
- [ ] Ready to record demo! 🎬

---

**Status**: ✅ READY FOR DEMO  
**Last Updated**: November 16, 2025  
**Helm Chart Version**: v0.0.231  
**eBPF Agent**: Coralogix eBPF Profiler

