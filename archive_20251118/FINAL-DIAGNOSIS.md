# 🔴 FINAL DIAGNOSIS: Telemetry Not Flowing to Coralogix

**Date**: November 17, 2025  
**Status**: ❌ **BLOCKED** - Telemetry infrastructure broken

---

## 💥 **The Core Problem**

**OpenTelemetry spans are being created but NEVER reach the OTel Collector.**

### Evidence:
```
✅ simple_demo_injector.py ran successfully
✅ Created 43 database spans  
✅ Reported "Done! Check Coralogix"
❌ Collector logs: ZERO activity
❌ No spans received
❌ No batch logs
❌ No export logs
```

---

## 🔍 **What This Means**

Despite all fixes:
- ✅ Collector is running and listening on port 4317
- ✅ Services are configured with correct collector IP
- ✅ Coralogix credentials are loaded
- ✅ Config has Coralogix exporter in all pipelines
- ✅ Network connectivity test passed (port 4317 reachable)

**BUT**: The OTLP gRPC connection is **not actually working**.

---

## 🚨 **Root Cause: Collector Not Receiving OTLP**

### Hypothesis:
The OTel Collector's OTLP gRPC receiver is either:
1. Not starting correctly
2. Not bound to the right interface
3. Has a configuration error preventing it from accepting connections
4. There's a network policy blocking gRPC traffic
5. The collector image doesn't have the OTLP receiver compiled in

### Why We Know This:
- Direct span injection failed (bypassed application entirely)
- No collector logs showing ANY received telemetry
- Even health checks don't generate telemetry logs in collector

---

## 📊 **Timeline of Fixes (What Was Done)**

### 1. Fixed JavaScript Syntax Error ✅
- **Time**: 22:00 UTC
- **Issue**: Frontend buttons not working due to JS syntax error
- **Fix**: Changed single quotes to backticks in template strings
- **Result**: ✅ Buttons now work

### 2. Fixed OTel Collector OOMKill ✅
- **Time**: 22:12 UTC  
- **Issue**: Collector had 256MB RAM, crashed 9 times
- **Fix**: Increased DaemonSet memory limit to 1Gi
- **Result**: ✅ Collector stable, no more crashes

### 3. Fixed Missing Coralogix Credentials ✅
- **Time**: 22:28 UTC
- **Issue**: Collector pod didn't have CX_TOKEN/CX_DOMAIN loaded
- **Fix**: Restarted collector to load secrets from dataprime-secrets
- **Result**: ✅ Credentials now configured in DaemonSet spec

### 4. Updated Service Endpoints ✅
- **Time**: 22:17 - 22:29 UTC
- **Issue**: Services using old collector IP
- **Fix**: Updated all deployments to use current collector pod IP
- **Result**: ✅ All services have `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`

### 5. Tested Direct Span Injection ❌
- **Time**: 22:33 UTC
- **Test**: Ran simple_demo_injector.py to send spans directly
- **Expected**: Collector logs show received spans
- **Actual**: ❌ NO collector activity whatsoever
- **Conclusion**: **Collector OTLP receiver is not functional**

---

## 🎯 **The Real Issue**

**The OTel Collector is NOT receiving telemetry on port 4317.**

This is NOT an application issue. This is a **collector infrastructure issue**.

---

## 🛠️ **What Needs to Happen Next**

### Option 1: Restart Collector with Debug Logging
```bash
# Enable debug logging
kubectl edit configmap otel-collector-config -n dataprime-demo
# Change: level: info → level: debug

# Restart collector
kubectl delete pod -n dataprime-demo \
  $(kubectl get pods -n dataprime-demo -l app=coralogix-opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')

# Check logs
kubectl logs -n dataprime-demo \
  $(kubectl get pods -n dataprime-demo -l app=coralogix-opentelemetry-collector -o jsonpath='{.items[0].metadata.name}') \
  -f
```

### Option 2: Verify OTLP Receiver is Actually Running
```bash
# Check if collector is listening on all interfaces
kubectl exec -n dataprime-demo \
  $(kubectl get pods -n dataprime-demo -l app=coralogix-opentelemetry-collector -o jsonpath='{.items[0].metadata.name}') \
  -- netstat -tuln | grep 4317

# Should show: 0.0.0.0:4317
```

### Option 3: Test with Logging Exporter First
```bash
# Temporarily change config to use logging exporter instead of Coralogix
# This will show if spans are reaching the collector at all

kubectl edit configmap otel-collector-config -n dataprime-demo

# Change:
#   exporters:
#     - coralogix
# To:
#   exporters:
#     - logging

# Restart and test
```

### Option 4: Deploy Fresh Collector
The current collector might be in a bad state. Deploy a fresh one:
```bash
# Delete the DaemonSet
kubectl delete daemonset coralogix-opentelemetry-collector -n dataprime-demo

# Redeploy using your deployment YAML
kubectl apply -f deployment/kubernetes/otel-collector.yaml
```

---

## 💡 **Recommended Immediate Action**

### Test with Logging Exporter (5 minutes)

This will tell us if spans are reaching the collector **at all**:

```yaml
# Edit otel-collector-config ConfigMap
exporters:
  logging:
    verbosity: detailed
    
service:
  pipelines:
    traces:
      receivers:
        - otlp
      processors:
        - memory_limiter
        - batch
      exporters:
        - logging  # Change from coralogix to logging
```

**If you see spans in logs**: Collector is working, issue is Coralogix export  
**If you see nothing**: Collector OTLP receiver is fundamentally broken

---

## 📝 **Current Configuration**

### Collector ConfigMap
- **Location**: `dataprime-demo/otel-collector-config`
- **Receivers**: ✅ OTLP on 0.0.0.0:4317, 0.0.0.0:4318
- **Processors**: ✅ memory_limiter, k8sattributes, resourcedetection, resource, batch
- **Exporters**: ✅ coralogix (domain, private_key, application_name configured)
- **Pipelines**: ✅ traces/metrics/logs → coralogix

### Collector Pod
- **Name**: `coralogix-opentelemetry-collector-xwwfp`
- **IP**: `10.42.0.242`
- **Memory**: 1Gi limit, 512Mi request
- **Status**: Running, 0 restarts
- **Credentials**: Loaded from dataprime-secrets ConfigMap

### Services
- **api-gateway**: `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`
- **frontend**: `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`
- **product-service**: `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`
- **order-service**: `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`
- **inventory-service**: `OTEL_EXPORTER_OTLP_ENDPOINT=10.42.0.242:4317`

---

## 🎬 **What You Should Do**

### 1. First, Try Option 3 (Logging Exporter)
This is the fastest way to determine if the collector is receiving **anything**.

### 2. If Logging Shows Spans
→ Issue is Coralogix export (credentials, network, etc.)  
→ Check Coralogix domain, verify network connectivity to eu2.coralogix.com

### 3. If Logging Shows Nothing
→ Collector OTLP receiver is broken  
→ Redeploy collector or check for conflicting resources

### 4. Check Coralogix Anyway
Maybe data IS flowing but taking longer than expected. Check:
- **APM → Traces** (filter by last 30 minutes)
- **AI Center → Applications** → ecommerce-recommendation
- **Database Monitoring** → productcatalog

Wait 5-10 minutes after generating traffic before concluding there's no data.

---

## ✅ **What IS Working (Summary)**

| Component | Status |
|-----------|--------|
| Frontend | ✅ JavaScript fixed, buttons work |
| API Gateway | ✅ Running, processing requests |
| Backend Services | ✅ All running (product, order, inventory) |
| PostgreSQL | ✅ Database connections working |
| Scene 9 Injector | ✅ Creates spans (but they don't reach collector) |
| OTel Collector | ⚠️ Running but not receiving telemetry |
| Coralogix Config | ✅ Credentials and exporter configured |

---

## ❌ **What is NOT Working**

| Component | Issue |
|-----------|-------|
| **Telemetry Flow** | ❌ **CRITICAL**: Spans never reach collector |
| OTLP gRPC Connection | ❌ Not functional |
| Coralogix Data | ❌ No data in AI Center or APM |
| recommendation-ai | ❌ Pod in ErrImageNeverPull state |

---

## 📞 **Need Help?**

This is a **deep infrastructure issue** that requires:
1. Direct access to collector logs with debug mode
2. Network packet capture to see if gRPC traffic is flowing
3. Possibly redeploying the entire OTel Collector stack
4. Verifying the collector image has the OTLP receiver

**Time spent**: 2+ hours  
**Progress**: Infrastructure fixed, but fundamental telemetry flow broken  
**Status**: **BLOCKED** on OTel Collector OTLP receiver issue

---

**Last Updated**: 2025-11-17 22:35 UTC

