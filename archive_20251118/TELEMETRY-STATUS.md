# Telemetry Status - Complete Analysis

**Date**: November 17, 2025, 22:32 UTC  
**Instance**: 54.235.171.176

---

## 🔴 **CRITICAL ISSUE: Telemetry Not Flowing to Coralogix**

Despite extensive fixes, **NO telemetry is reaching Coralogix AI Center**.

---

## ✅ What's WORKING:

| Component | Status | Details |
|-----------|--------|---------|
| Frontend Buttons | ✅ | JavaScript fixed, all buttons functional |
| API Gateway | ✅ | Running, responding to requests |
| OTel Collector | ✅ | Running, listening on `10.42.0.242:4317` |
| Collector Memory | ✅ | Increased to 1Gi (no more OOMKill) |
| Collector Config | ✅ | Coralogix exporter configured in all pipelines |
| Coralogix Credentials | ✅ | `CX_TOKEN` and `CX_DOMAIN` (eu2.coralogix.com) loaded |
| Services Config | ✅ | All services configured with `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317` |

---

## ❌ What's BROKEN:

### Primary Issue: **Zero Telemetry Flow**

**Symptom**: OTel Collector logs show **NO incoming telemetry** despite:
- Services are running
- Requests are being processed
- Collector is listening on port 4317
- Services have correct collector endpoint configured

**Evidence**:
```bash
# API Gateway has correct config
OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317

# Collector is listening
Starting GRPC server on 0.0.0.0:4317

# But NO telemetry logs:
- No "Batch" logs
- No "Export" logs  
- No "Received" logs
- ZERO activity
```

---

## 🔍 **Root Cause Analysis**

### Possible Causes:

1. **Services Not Actually Sending** 
   - OpenTelemetry SDK might not be initialized correctly
   - Exporters might be failing silently
   - Batch export might be queued but not flushing

2. **Network Issue**
   - Collector pod IP changes when pod restarts
   - Services cache old IP
   - K8s network policy blocking traffic

3. **Collector Not Receiving**
   - Port 4317 listening but not processing
   - OTLP receiver misconfigured
   - Collector crashing/restarting before processing

4. **Application Code Issue**
   - Telemetry initialization failing
   - Spans created but not exported
   - Exporter configured but not used

---

## 🛠️ **What Was Fixed** (But Didn't Solve the Problem)

### 1. JavaScript Syntax Error ✅
- **Problem**: Single quotes with newlines in confirm dialogs
- **Fix**: Changed to template literals (backticks)
- **Result**: Frontend buttons now work

### 2. OTel Collector OOMKill ✅
- **Problem**: Collector had only 256MB RAM, crashed 9 times
- **Fix**: Increased memory limit to 1Gi
- **Result**: Collector now stable, no crashes

### 3. Collector Missing Credentials ✅
- **Problem**: `CX_TOKEN` and `CX_DOMAIN` not loaded in pod
- **Fix**: Restarted collector to load secrets
- **Result**: Credentials now available (verified in DaemonSet spec)

### 4. Service DNS Resolution ✅
- **Problem**: K8s Service had no endpoints (label mismatch)
- **Fix**: Services now use collector pod IP directly
- **Result**: Network connectivity confirmed (port 4317 is reachable)

---

## 📊 **Current State**

```
┌─────────────┐         ┌──────────────┐         ┌────────────┐
│  Frontend   │────────▶│  API Gateway │────────▶│    ???     │
│  (Working)  │  HTTPS  │   (Working)  │   ???   │  No Data   │
└─────────────┘         └──────────────┘         └────────────┘
                                │
                                │ OTEL Export?
                                ▼
                        ┌──────────────┐
                        │   Collector  │
                        │  (Listening) │
                        │ But NO DATA  │
                        └──────────────┘
                                │
                                │ Should Export
                                ▼
                        ┌──────────────┐
                        │  Coralogix   │
                        │  AI Center   │
                        │   (Empty)    │
                        └──────────────┘
```

---

## 🎯 **Next Steps to Debug**

### Option 1: Check Application Telemetry Initialization
```bash
# SSH to server
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176

# Check API Gateway logs for telemetry initialization
sudo kubectl logs -n dataprime-demo \
  $(sudo kubectl get pods -n dataprime-demo -l app=api-gateway -o jsonpath='{.items[0].metadata.name}') \
  | grep -i "telemetry\|otlp\|export\|trace"
```

### Option 2: Test Direct OTLP Export
```bash
# Install grpcurl in collector pod and test
sudo kubectl exec -n dataprime-demo \
  $(sudo kubectl get pods -n dataprime-demo -l app=coralogix-opentelemetry-collector -o jsonpath='{.items[0].metadata.name}') \
  -- netstat -tuln | grep 4317
```

### Option 3: Enable Debug Logging
```bash
# Update collector config to debug level
sudo kubectl edit configmap otel-collector-config -n dataprime-demo
# Change: level: info → level: debug
# Restart collector
```

### Option 4: Simplify & Test
- Deploy a simple test app that definitely sends telemetry
- Use Scene 9 button (inject-telemetry) which directly sends spans
- Verify those spans reach Coralogix

---

## 🚨 **Critical Questions**

1. **Is the API Gateway actually creating spans?**
   - Check: `shared_telemetry.py` - is `ensure_telemetry_initialized()` working?
   - Check: Do request logs show trace IDs?

2. **Is the exporter actually sending?**
   - Check: Are spans being batched?
   - Check: Is `force_flush()` being called?

3. **Is there a Python OpenTelemetry bug?**
   - Version mismatch?
   - Missing dependency?
   - Silent failure?

---

## 📝 **Files to Check**

1. `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/app/shared_telemetry.py`
   - Line 20-50: Telemetry initialization
   - Check if `TracerProvider` is configured correctly
   - Check if `OTLPSpanExporter` is created

2. `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/api_gateway.py`
   - Check if spans are being created
   - Check if context is being propagated
   - Check for any export errors

3. `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/simple_demo_injector.py`
   - This DIRECTLY sends spans to collector
   - Test this first to verify collector → Coralogix path

---

## 🎬 **Recommended Action**

### Test Scene 9 (Direct Span Injection)

This bypasses the application and sends spans directly to the collector:

```bash
# Run Scene 9 script
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176 << 'EOF'
API_POD=$(sudo kubectl get pods -n dataprime-demo -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')

# Run injector inside API Gateway pod
sudo kubectl exec -n dataprime-demo $API_POD -- python3 /app/services/simple_demo_injector.py

# Check collector logs
sleep 10
COLLECTOR_POD=$(sudo kubectl get pods -n dataprime-demo -l app=coralogix-opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
sudo kubectl logs -n dataprime-demo $COLLECTOR_POD --tail=100 --since=20s | grep -E "batch|export|trace"
EOF
```

**If this works**: The collector → Coralogix path is fine, issue is with application telemetry  
**If this fails**: The collector is not exporting to Coralogix at all

---

## 💡 **Likely Root Cause**

Based on all evidence, the most likely issue is:

**The Python OpenTelemetry SDK in the application services is NOT actually exporting telemetry.**

Possible reasons:
1. `shared_telemetry.py` initialization is failing silently
2. Exporter is not being added to the `TracerProvider`
3. Spans are being created but not flushed
4. There's an exception being swallowed somewhere

---

## ✅ **To Verify Setup is Working**

Wait 2-3 minutes after generating traffic, then check Coralogix:

**Coralogix UI → APM → Traces**
- Filter: `service.name = api-gateway`
- Time: Last 15 minutes

**Coralogix UI → AI Center → Applications**
- Look for: `ecommerce-recommendation`
- Should see: LLM calls, evaluations, traces

If you see **nothing** in either place:
→ Telemetry is NOT reaching Coralogix (confirmed issue)

---

**Status**: ⚠️ **BLOCKED** - Telemetry infrastructure configured but not functional

