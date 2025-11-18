# Continuous Profiling - Status & Next Steps

**Last Updated**: November 16, 2025  
**Status**: Profiling Agent Installed ✅ | Application Deployment In Progress ⏳

---

## ✅ **What's Successfully Complete**

### 1. Profiling Infrastructure ✅
- **Coralogix eBPF Profiler**: Running on K8s (pod: `coralogix-ebpf-profiler-6vwn9`)
- **OpenTelemetry Agent**: Running with profiling support enabled
- **Helm Chart**: `otel-coralogix-integration` v0.0.231 deployed

**Verification:**
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl get pods -n dataprime-demo | grep profiler"
```
Expected: `coralogix-ebpf-profiler-xxxxx  1/1  Running`

### 2. Image Optimization ✅  
- **Problem Fixed**: Removed `sentence-transformers`, `scikit-learn`, `numpy`, `pandas`
- **Old Size**: 8.01GB
- **New Size**: ~300-400MB (estimate)
- **Files**: `Dockerfile.optimized` and `requirements-minimal.txt` created

---

## ⏳ **What Was In Progress (As of Last Check)**

### Docker Build Running
- **Started**: 21:58 UTC
- **Process ID**: 505514
- **Command**: `docker build -f docker/Dockerfile -t ecommerce-demo:latest .`
- **Expected Duration**: 2-3 minutes
- **Status When Checked**: Active (not hung)

**Check if completed:**
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "ps aux | grep 'docker build' | grep -v grep"
```
- If **no output**: Build finished
- If **shows process**: Still building

**Check if image created:**
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo docker images ecommerce-demo:latest"
```

---

## 🎯 **Next Steps (Manual)**

### Option 1: If Build is Complete

1. **Import image to K3s** (~10-15 seconds):
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'EOF'
   cd /opt/dataprime-assistant/coralogix-dataprime-demo
   echo "Importing image..."
   sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -
   echo "Done!"
   EOF
   ```

2. **Tag images for services**:
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'EOF'
   sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest
   sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest
   sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest
   echo "Images tagged!"
   EOF
   ```

3. **Restart deployments**:
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'EOF'
   sudo kubectl rollout restart deployment product-service -n dataprime-demo
   sudo kubectl rollout restart deployment order-service -n dataprime-demo
   sudo kubectl rollout restart deployment inventory-service -n dataprime-demo
   
   echo "Waiting 30 seconds for pods to start..."
   sleep 30
   
   echo "Pod status:"
   sudo kubectl get pods -n dataprime-demo | grep -E "product-service|order-service|inventory-service"
   EOF
   ```

4. **Generate profiling data**:
   ```bash
   cd /Users/andrescott/dataprime-assistant-1
   ./run-scene9.5-demo.sh
   ```

5. **Check Coralogix** (wait 1-2 minutes after step 4):
   - Navigate to: **APM → Continuous Profiling**
   - Service: **product-service**
   - Time Range: **Last 15 minutes**
   - Look for: `search_products_unindexed()` function at 99.2% CPU

---

### Option 2: If Build Still Running

**Wait for it to complete** (check with first command above), then follow Option 1.

---

### Option 3: If Build Failed

1. **Check build logs:**
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "cd /opt/dataprime-assistant/coralogix-dataprime-demo && sudo docker build -f docker/Dockerfile -t ecommerce-demo:latest . 2>&1 | tail -50"
   ```

2. **If error mentions missing packages**, the optimized requirements might be missing something. Can rebuild with original `requirements.txt`:
   ```bash
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
     "cd /opt/dataprime-assistant/coralogix-dataprime-demo && sudo docker build -f docker/Dockerfile -t ecommerce-demo:latest . --progress=plain"
   ```

---

## 🚀 **All-in-One Script (If Build Complete)**

Save this as `complete-profiling-setup.sh`:

```bash
#!/bin/bash
set -e

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Complete Profiling Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE'
set -e

echo "Step 1: Import image to K3s..."
cd /opt/dataprime-assistant/coralogix-dataprime-demo
sudo docker save ecommerce-demo:latest | sudo k3s ctr images import - > /dev/null 2>&1
echo "✅ Imported"

echo ""
echo "Step 2: Tag images..."
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-product-service:latest 2>/dev/null
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-order-service:latest 2>/dev/null
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-inventory-service:latest 2>/dev/null
echo "✅ Tagged"

echo ""
echo "Step 3: Restart deployments..."
sudo kubectl rollout restart deployment product-service -n dataprime-demo
sudo kubectl rollout restart deployment order-service -n dataprime-demo 2>/dev/null || true
sudo kubectl rollout restart deployment inventory-service -n dataprime-demo 2>/dev/null || true

echo "Waiting 30 seconds..."
sleep 30

echo ""
echo "Pod Status:"
sudo kubectl get pods -n dataprime-demo | grep -E "product-service|order-service|inventory-service"

echo ""
echo "✅ Complete!"
EOFREMOTE

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next: Run ./run-scene9.5-demo.sh to generate profiling data"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

Then run:
```bash
chmod +x complete-profiling-setup.sh
./complete-profiling-setup.sh
```

---

## 📊 **Expected Results in Coralogix**

Once everything is running and you've generated profiling data:

1. **Navigate**: APM → Continuous Profiling → product-service
2. **Time Range**: Last 15 minutes
3. **You should see**:
   - 🔥 Flame graph
   - Function: `search_products_unindexed()`
   - CPU Usage: ~99.2%
   - Query: `SELECT * FROM products WHERE description LIKE '%wireless%'`
   - Duration: ~2900ms per query

---

## 🔧 **Troubleshooting**

### Profiling agent not collecting data
```bash
# Check profiler logs
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app=coralogix-ebpf-profiler --tail=50"
```

### Application pods not starting
```bash
# Check pod logs
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app=product-service --tail=50"
```

### No profiling data in Coralogix after 2-3 minutes
- Verify profiler pod is running
- Check that application pods are running
- Ensure you ran `./run-scene9.5-demo.sh` to generate CPU load
- Wait at least 2-3 minutes for data propagation

---

## 📚 **Reference Documentation**

- **Full Guide**: `SCENE-9.5-CONTINUOUS-PROFILING.md`
- **Quick Start**: `QUICK-START-SCENE-9.5.md`
- **Deployment**: `DEPLOY-PROFILING.md`
- **Coralogix Docs**: https://coralogix.com/docs/user-guides/continuous-profiling/setup/

---

**Status**: ✅ Profiling agent ready | ⏳ Application deployment in progress  
**Last Verified**: November 16, 2025 21:58 UTC

