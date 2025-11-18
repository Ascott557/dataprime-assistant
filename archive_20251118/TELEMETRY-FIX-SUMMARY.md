# Telemetry Fix Summary - Lessons Learned

**Date**: November 18, 2025  
**Issue**: No traces appearing in Coralogix UI  
**Root Cause**: Using Coralogix Helm Chart instead of the proven manual OTel Collector approach

---

## The Problem

Traces were not appearing in Coralogix, despite:
- Applications generating traces
- OTel exporter being configured
- Network connectivity being functional

## What We Tried (That DIDN'T Work)

### ❌ Attempt 1: Fix Helm Chart Authentication
- **Action**: Updated `coralogix-keys` secret with `PRIVATE_KEY`
- **Result**: Collector still failed with `Unauthenticated` errors
- **Error**: `rpc error: code = Unauthenticated desc = c5e597274094beff3ed21416556add2a344b6f11`

### ❌ Attempt 2: Direct Coralogix Export
- **Action**: Configured apps to send traces directly to `ingress.eu2.coralogix.com:4317`
- **Result**: `StatusCode.DEADLINE_EXCEEDED` errors
- **Issue**: Complex authentication headers and TLS configuration for direct gRPC export

### ❌ Attempt 3: Restart and Reconfigure Helm Collector
- **Action**: Multiple collector pod restarts, secret updates
- **Result**: Same authentication failures persisted
- **Issue**: The Coralogix Helm chart has complex OpAMP configuration that wasn't working

---

## The Actual Solution ✅

### What Worked: Use Manual OTel Collector (Like old_app_files)

**Key Insight**: The `old_app_files` project used a **simple manual Kubernetes DaemonSet** with the official OpenTelemetry Collector Contrib image, NOT a Helm chart.

### Implementation Steps:

1. **Removed Helm Chart Components**
   ```bash
   kubectl delete deployment coralogix-opentelemetry-collector -n dataprime-demo
   kubectl delete daemonset coralogix-opentelemetry-agent -n dataprime-demo
   kubectl delete daemonset coralogix-opentelemetry-collector -n dataprime-demo
   kubectl delete service coralogix-opentelemetry-collector -n dataprime-demo
   ```

2. **Deployed Simple Manual Collector**
   - Used: `old_app_files/deployment/kubernetes/otel-collector-daemonset.yaml`
   - Image: `otel/opentelemetry-collector-contrib:0.91.0`
   - Configuration: Simple YAML file with Coralogix exporter

3. **Updated Application Configuration**
   - Set `OTEL_EXPORTER_OTLP_ENDPOINT` to: `otel-collector.dataprime-demo.svc.cluster.local:4317`
   - Removed direct Coralogix connection attempts
   - Simplified `shared_telemetry.py` to use `insecure=True` for local gRPC

4. **Key Configuration (Working)**
   ```yaml
   exporters:
     coralogix:
       domain: "${env:CX_DOMAIN}"  # eu2.coralogix.com
       private_key: "${env:CX_TOKEN}"
       application_name: "${env:CX_APPLICATION_NAME}"
       subsystem_name: "k3s-infrastructure"
       timeout: 30s
       compression: gzip
   ```

---

## Critical Lessons Learned

### 1. **Don't Use Coralogix Helm Chart for Simple Deployments**
- ❌ **Complex**: OpAMP management, multiple components, hard to debug
- ❌ **Authentication Issues**: Frequent `Unauthenticated` errors
- ✅ **Use Manual Collector**: Simple DaemonSet with official OTel image

### 2. **Reference Working Implementations**
- Always check `old_app_files` or previous working deployments
- Don't reinvent the wheel with "newer" approaches if old one works

### 3. **Telemetry Architecture Pattern (That Works)**
```
Application → Local OTel Collector → Coralogix
    (gRPC)         (processes)        (exports)
   insecure       batching, k8s      compressed
                  enrichment
```

### 4. **PostgreSQL Instrumentation Requirements**
For Coralogix Database Monitoring to work correctly:
```python
from opentelemetry.trace import SpanKind

with tracer.start_as_current_span(
    f"SELECT {db_name}.products",  # OTel naming: "OPERATION database.table"
    kind=SpanKind.CLIENT  # REQUIRED!
) as db_span:
    # REQUIRED attributes for Database Monitoring:
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.name", db_name)  # e.g., "productcatalog"
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.sql.table", "products")
    db_span.set_attribute("net.peer.name", "postgres")  # REQUIRED!
    db_span.set_attribute("net.peer.port", 5432)
    db_span.set_attribute("db.statement", "SELECT ...")  # Full SQL
```

---

## Files Modified

### 1. Removed/Replaced
- ❌ Any Helm chart based collectors
- ❌ Complex direct Coralogix exporter configuration

### 2. Key Files Deployed
- ✅ `old_app_files/deployment/kubernetes/otel-collector-daemonset.yaml`
- ✅ Updated `deployment/kubernetes/configmap.yaml`:
  - `OTEL_EXPORTER_OTLP_ENDPOINT: "otel-collector.dataprime-demo.svc.cluster.local:4317"`
- ✅ Simplified `coralogix-dataprime-demo/app/shared_telemetry.py`:
  - Removed direct Coralogix TLS logic
  - Simple `OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)`

### 3. Services Fixed (PostgreSQL Instrumentation)
- ✅ `coralogix-dataprime-demo/services/product_service.py`
- ✅ `coralogix-dataprime-demo/services/inventory_service.py`
- ✅ `coralogix-dataprime-demo/services/order_service.py`

---

## Verification Checklist

To verify telemetry is working:

```bash
# 1. Check OTel Collector is running
kubectl get pods -n dataprime-demo | grep otel-collector
# Should show: Running

# 2. Verify app endpoint configuration
kubectl get configmap dataprime-config -n dataprime-demo -o yaml | grep OTEL_EXPORTER
# Should show: otel-collector.dataprime-demo.svc.cluster.local:4317

# 3. Test connectivity from app to collector
kubectl exec -n dataprime-demo -l app=product-service -- \
  curl -v telnet://otel-collector.dataprime-demo.svc.cluster.local:4317
# Should show: Connected

# 4. Check Coralogix secret exists
kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.CX_TOKEN}' | base64 -d
# Should show: cxtp_... token

# 5. Generate test traffic
kubectl exec -n dataprime-demo -l app=api-gateway -- \
  curl -s 'http://product-service:8014/products?category=Wireless%20Headphones'

# 6. Check Coralogix UI after 2-3 minutes
# https://eu2.coralogix.com → APM → Traces
# Look for: application="ecommerce-recommendation"
```

---

## For Future Reference

### ✅ DO THIS:
1. Use the **manual OTel Collector DaemonSet** from `old_app_files`
2. Keep telemetry architecture **simple**: App → Collector → Coralogix
3. Use `SpanKind.CLIENT` for all **database operations**
4. Add required database semantic conventions (`db.name`, `net.peer.name`)
5. Reference working implementations before trying new approaches

### ❌ DON'T DO THIS:
1. Don't use Coralogix Helm chart for simple K3s deployments
2. Don't try to send traces directly from apps to Coralogix
3. Don't skip `SpanKind.CLIENT` for database spans
4. Don't assume "newer" = "better" - check if old approach worked

---

## Quick Recovery Command

If telemetry breaks again, run this to restore working configuration:

```bash
# From the project root
cd /Users/andrescott/dataprime-assistant-1

# 1. Deploy working collector
scp -i ~/.ssh/ecommerce-demo-key.pem \
  old_app_files/deployment/kubernetes/otel-collector-daemonset.yaml \
  ubuntu@54.235.171.176:~/

ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl apply -f otel-collector-daemonset.yaml"

# 2. Verify ConfigMap endpoint
# Should be: otel-collector.dataprime-demo.svc.cluster.local:4317

# 3. Restart app pods to pick up correct config
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl delete pod -n dataprime-demo -l 'app in (product-service,inventory-service,order-service,recommendation-ai,api-gateway)'"
```

---

## Key Takeaway

**"Keep It Simple, Stupid" (KISS)**

The working solution from `old_app_files` was simpler and more reliable than the newer Helm chart approach. When troubleshooting telemetry:

1. **First**: Check if `old_app_files` has a working solution
2. **Second**: Use that exact approach
3. **Third**: Only innovate if the old approach truly doesn't work

The manual OTel Collector DaemonSet approach has been proven to work reliably across multiple deployments.

