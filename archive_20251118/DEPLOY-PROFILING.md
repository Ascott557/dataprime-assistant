# Deploy Continuous Profiling - Instructions

## 🚀 **Quick Deploy (2 options)**

### **Option 1: Interactive (Recommended for first-time)**

```bash
cd /Users/andrescott/dataprime-assistant-1
./install-continuous-profiling.sh
```

*Enter your Coralogix Private API Key when prompted*

---

### **Option 2: Non-Interactive (with environment variable)**

```bash
cd /Users/andrescott/dataprime-assistant-1
export CORALOGIX_PRIVATE_KEY="your-private-api-key-here"
./install-continuous-profiling.sh
```

---

## ⏱️ **Installation Timeline**

| Step | Duration | What Happens |
|------|----------|--------------|
| 1. Add Helm repo | 10s | Adds Coralogix charts to Helm |
| 2. Create secret | 5s | Stores your API key in K8s |
| 3. Deploy profiling | 30-60s | Installs eBPF agent DaemonSet |
| 4. Verify pods | 30s | Waits for profiler pods to start |
| **Total** | **~2 minutes** | |

---

## ✅ **What Gets Installed**

- **Coralogix eBPF Profiler** (DaemonSet on all nodes)
- **OpenTelemetry Agent** (with profiling support enabled)
- **Helm Chart**: `coralogix/otel-integration` v0.0.231
- **Feature Gates**: `service.profilesSupport` enabled

---

## 🔍 **Verify Installation**

After installation completes, check pod status:

```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl get pods -n dataprime-demo | grep -E 'profiler|otel'"
```

**Expected:**
```
coralogix-ebpf-profiler-xxxxx     1/1     Running     0          2m
opentelemetry-agent-xxxxx         1/1     Running     0          2m
```

---

## 🔥 **Generate Test Data**

Once installed, generate CPU load to test profiling:

```bash
./run-scene9.5-demo.sh
```

This triggers 50 unindexed database queries to create flame graph data.

---

## 📊 **View in Coralogix**

1. Wait **1-2 minutes** after running the demo script
2. Open Coralogix: **APM → Continuous Profiling**
3. Select service: **product-service**
4. Time range: **Last 15 minutes**
5. Look for flame graph showing `search_products_unindexed()` at **99.2% CPU**

---

## 🆘 **Troubleshooting**

### **Installation fails with "Helm not found"**
Helm is installed on the EC2 instance, not locally. The script SSHs into EC2 to run Helm commands.

### **"Permission denied" error**
Check SSH key permissions:
```bash
chmod 600 ~/.ssh/dataprime-demo-key.pem
```

### **Profiler pods not starting**
Check pod logs:
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app=coralogix-ebpf-profiler --tail=50"
```

### **No profiling data in Coralogix**
1. Verify profiler pods are running (see "Verify Installation" above)
2. Wait 2-3 minutes for initial data propagation
3. Run the demo script to generate CPU load
4. Check Coralogix time range matches when you ran the demo

---

## 📚 **Next Steps**

After successful installation:

1. ✅ Install profiling (you just did this!)
2. 🔥 Generate load: `./run-scene9.5-demo.sh`
3. ⏱️ Wait 1-2 minutes
4. 📊 Check Coralogix: APM → Continuous Profiling → product-service
5. 🎬 Ready to demo!

---

**Quick Start Guide**: `QUICK-START-SCENE-9.5.md`  
**Full Documentation**: `SCENE-9.5-CONTINUOUS-PROFILING.md`

