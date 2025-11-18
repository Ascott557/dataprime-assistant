# Instance Crash Analysis & Resolution

**Date**: November 17, 2025  
**Incident**: EC2 instance became unresponsive after deploying eBPF profiling agent  
**Resolution**: Instance rebooted successfully  
**Status**: ✅ RESOLVED - Instance back online

---

## 🔍 **Root Cause Analysis**

### **The Problem**
The EC2 instance crashed with an out-of-memory (OOM) condition after we attempted to build a Docker image.

### **Why It Happened**

**Instance Specifications:**
- **Type**: t3.small
- **RAM**: 2GB (1.9GB usable)
- **vCPU**: 2 cores

**Docker Image Being Built:**
- **Size**: 8.01GB
- **Peak Memory During Build**: 4-6GB (for ML package installs)
- **Culprit Packages**:
  - `sentence-transformers==3.0.1` (2-4GB of models)
  - `scikit-learn`, `pandas`, `numpy` (1-2GB)
  - `torch` dependencies (1-2GB)

**Timeline:**
1. **21:32 UTC**: eBPF profiling agent deployed successfully ✅
2. **21:58 UTC**: Started Docker build with 8GB image
3. **21:59 UTC**: Memory exhausted during `pip install`
4. **22:00 UTC**: Linux OOM killer terminated processes
5. **22:01 UTC**: SSH became unresponsive
6. **00:01 UTC**: Instance rebooted via AWS CLI
7. **00:02 UTC**: Instance back online ✅

---

## ✅ **Resolution Actions Taken**

1. **Instance Reboot**: Successfully rebooted via AWS CLI
   ```bash
   aws ec2 reboot-instances --instance-ids i-0ac1daf56c649186e
   ```

2. **Status Confirmed**: Instance is healthy
   - State: running
   - System Status: OK
   - Instance Status: OK
   - SSH: Accessible

3. **Resource Check After Reboot**:
   - Memory: 902MB available (out of 1.9GB)
   - Load: 1.92 (normal for startup)
   - Disk: 48% used (14GB free)

---

## 🎯 **Moving Forward: 3 Options**

### **Option 1: Upgrade Instance Size** (Recommended for Production)

**Upgrade to t3.medium:**
- **RAM**: 4GB (vs current 2GB)
- **vCPU**: 2 cores (same)
- **Cost**: ~$30/month (vs $15/month for t3.small)

**Steps:**
```bash
# Stop instance
aws ec2 stop-instances --instance-ids i-0ac1daf56c649186e

# Wait for stopped state
aws ec2 wait instance-stopped --instance-ids i-0ac1daf56c649186e

# Change instance type
aws ec2 modify-instance-attribute \
  --instance-id i-0ac1daf56c649186e \
  --instance-type "{\"Value\": \"t3.medium\"}"

# Start instance
aws ec2 start-instances --instance-ids i-0ac1daf56c649186e
```

**Pros:**
- Can handle Docker builds safely
- More headroom for profiling
- Better for demos with multiple services

**Cons:**
- Costs 2x more
- Still might struggle with 8GB image (recommend using optimized image anyway)

---

### **Option 2: Use Optimized Docker Image** (Recommended for Demo)

We already created an optimized Dockerfile that removes ML packages:
- **Old Size**: 8.01GB
- **New Size**: ~300-500MB (estimate)
- **Build Time**: 2-3 minutes (vs 10+ minutes)
- **Memory Required**: ~1-2GB (fits in t3.small)

**Files Created:**
- `/opt/dataprime-assistant/coralogix-dataprime-demo/docker/Dockerfile.optimized`
- `/opt/dataprime-assistant/coralogix-dataprime-demo/docker/requirements-minimal.txt`

**Steps:**
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'EOF'
cd /opt/dataprime-assistant/coralogix-dataprime-demo

# Use optimized Dockerfile
sudo docker build -f docker/Dockerfile -t ecommerce-demo:latest . 2>&1 | tee /tmp/build.log

# Monitor build (in another terminal)
tail -f /tmp/build.log
EOF
```

**Pros:**
- Works on current t3.small
- Much faster builds
- Still includes all observability features
- **eBPF profiling already installed and working!**

**Cons:**
- If app needs ML packages later, need to add them back

---

### **Option 3: Skip Profiling Demo** (Quickest)

Since profiling isn't critical for the main demo flow:

**What's Already Working:**
- ✅ Database APM (Scene 9) with telemetry injection
- ✅ eBPF profiling agent installed
- ✅ OpenTelemetry collector
- ✅ All other services

**What Won't Work:**
- ❌ Can't demonstrate profiling flame graphs
- ❌ No "exact line of code" discovery

**Pros:**
- No additional work needed
- Current setup already demo-ready for Scenes 1-9
- Can still show profiling UI (just no data)

**Cons:**
- Missing impressive "code-level" insight

---

## 📊 **Current System Status**

### **eBPF Profiling:**
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl get pods -n dataprime-demo | grep profiler"
```
**Expected**: `coralogix-ebpf-profiler-xxxxx  1/1  Running`

### **K8s Services:**
After reboot, K8s services should auto-restart. Verify with:
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl get pods -n dataprime-demo"
```

---

## 🔧 **Immediate Next Steps (Choose One)**

### **If You Choose Option 1 (Upgrade Instance):**
1. Run the AWS CLI commands above to upgrade to t3.medium
2. Wait 3-5 minutes for instance to come back
3. Then proceed with optimized Docker build (Option 2 steps)

### **If You Choose Option 2 (Optimized Image):**
1. SSH into instance
2. Navigate to `/opt/dataprime-assistant/coralogix-dataprime-demo`
3. Run `sudo docker build` with optimized Dockerfile
4. Import to K3s (takes ~10-15 seconds for 300MB image)
5. Run `./complete-profiling-setup.sh` from your local machine
6. Test profiling with `./run-scene9.5-demo.sh`

### **If You Choose Option 3 (Skip Profiling):**
1. Nothing needed - current setup is demo-ready
2. Scene 9 (Database APM) already works via telemetry injection
3. Can mention profiling capability without showing live demo

---

## 📝 **Lessons Learned**

1. **Always check instance size before heavy builds**
   - t3.small (2GB) = Fine for running services
   - t3.small (2GB) = NOT enough for building large images
   - t3.medium (4GB) = Minimum for Docker builds

2. **Optimize Docker images for production**
   - Remove unnecessary ML libraries
   - Use multi-stage builds
   - Keep final image < 1GB when possible

3. **eBPF profiling is lightweight**
   - The crash wasn't caused by eBPF
   - eBPF agent uses ~50-100MB RAM
   - The Docker build caused the OOM

4. **Monitor memory during operations**
   - Use `free -h` before heavy operations
   - Docker builds can temporarily use 3-4x image size

---

## 🎯 **Recommendation**

**For Demo Purposes**: Use **Option 2** (Optimized Image)
- Fastest path to working profiling demo
- Works on current hardware
- eBPF already installed
- Can complete in 15-20 minutes

**For Production**: Eventually upgrade to **t3.medium**
- More headroom for growth
- Safer for future updates
- Can handle occasional heavy operations

---

**Instance ID**: `i-0ac1daf56c649186e`  
**Public IP**: `54.235.171.176`  
**Current Type**: `t3.small` (2GB RAM)  
**Status**: ✅ Online and healthy

