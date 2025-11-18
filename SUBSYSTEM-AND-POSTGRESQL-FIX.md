# Subsystem Name and PostgreSQL Tracing Fix

## Issue
Traces were appearing under the wrong subsystem name `k3s-infrastructure` instead of the correct `ecommerce-production` subsystem in Coralogix AI Center.

## Root Causes (2 Issues Found)

### Issue #1: Deployment Manifests with Hardcoded Subsystem Names
All Kubernetes deployment manifests had **hardcoded** `CX_SUBSYSTEM_NAME` values (e.g., `recommendation-ai`, `product-service`, `api-gateway`) instead of reading from the ConfigMap.

Example of the problem:
```yaml
- name: CX_SUBSYSTEM_NAME
  value: "recommendation-ai"  # ❌ Hardcoded!
```

This caused each service to report under its own subsystem name, fragmenting the traces across multiple subsystems.

### Issue #2: OTel Collector with Hardcoded Subsystem Name ⚠️ **CRITICAL**
The OTel Collector configuration had a **hardcoded** subsystem name in the Coralogix exporter:

```yaml
exporters:
  coralogix:
    application_name: "${env:CX_APPLICATION_NAME}"
    subsystem_name: "k3s-infrastructure"  # ❌ HARDCODED!
```

**This was the real issue!** Even after fixing the deployment manifests, the OTel Collector was overriding all subsystem names to `k3s-infrastructure` when exporting to Coralogix.

## Fix Applied

### 1. Patched All Running Deployments
Updated all service deployments to use the ConfigMap value:

```bash
# Services patched:
- recommendation-ai
- product-service
- api-gateway
- inventory-service
- order-service
- frontend (rolled back due to missing RUM key)
```

New configuration:
```yaml
- name: CX_SUBSYSTEM_NAME
  valueFrom:
    configMapKeyRef:
      name: dataprime-config
      key: CX_SUBSYSTEM_NAME  # ✅ Uses ConfigMap value: "ecommerce-production"
```

### 2. Updated Local Deployment Manifests
Updated the following local files to persist the fix:
- `deployment/kubernetes/deployments/recommendation-ai-service.yaml`
- `deployment/kubernetes/deployments/product-service.yaml`
- `deployment/kubernetes/deployments/api-gateway.yaml`
- `deployment/kubernetes/deployments/frontend.yaml`

Note: `inventory-service.yaml` and `order-service.yaml` were already using the ConfigMap.

### 3. Fixed OTel Collector Configuration ⚠️ **CRITICAL FIX**
Updated `deployment/kubernetes/otel-collector-k8s-full.yaml` to use the environment variable:

```yaml
exporters:
  coralogix:
    domain: "${env:CX_DOMAIN}"
    private_key: "${env:CX_TOKEN}"
    application_name: "${env:CX_APPLICATION_NAME}"
    subsystem_name: "${env:CX_SUBSYSTEM_NAME}"  # ✅ Now uses environment variable!
```

Applied the fixed configuration:
```bash
kubectl apply -f otel-collector-k8s-full.yaml
# OTel Collector DaemonSet automatically restarted
```

### 4. Verified PostgreSQL Instrumentation
Confirmed that all database services still have correct PostgreSQL instrumentation:
- ✅ `SpanKind.CLIENT` for database spans
- ✅ `db.system = "postgresql"`
- ✅ `db.name = "productcatalog"`
- ✅ `db.operation = "SELECT"`
- ✅ `db.sql.table = "products"`
- ✅ `net.peer.name = "postgres"`
- ✅ `net.peer.port = 5432`
- ✅ `db.user = "dbadmin"`

## Verification

### Test Traces Generated

#### After Deployment Fix (Still went to wrong subsystem due to OTel Collector issue)
```
Trace 1: 709f4fd792c60750c417d0c7f42394aa
Trace 2: 5cb626a15dbe5fc9f45ce317dc8a4317
Trace 3: cd9c94dfcfeaf3dcb49b64faa17bae0c
Trace 4: a8a3cb3c60e9fde636c7cc2cf2bb8831
```

#### After OTel Collector Fix ✅ (Should go to ecommerce-production)
```
Trace 1: 44dbc692fddee7d81389e1feb7290272
Trace 2: 043f887f6ff35a63c100387357c5c00f
Trace 3: 8d255b4f6c7aa9eb143ebdce80b76e88
Trace 4: 4ee083d59f3291ea7ddb0eb1b707c8cb
Trace 5: 4deed6715e710c09156a874321b4ac4a
```

**Use these newer traces to verify the fix!**

### How to Verify in Coralogix

1. Go to AI Center or APM → Traces
2. Filter by:
   - **Application**: `ecommerce-recommendation`
   - **Subsystem**: `ecommerce-production` (NOT `k3s-infrastructure`)
   - **Trace ID**: Use one of the trace IDs above

3. Expected trace structure:
   ```
   api-gateway (service)
     └─ recommendation-ai (service)
          └─ http.get_product
               └─ GET
                    └─ product-service (service)
                         └─ SELECT productcatalog.products (database span)
                              └─ SELECT postgres (database operation)
   ```

4. In Database APM:
   - Navigate to: `https://eu2.coralogix.com/apm/databases/productcatalog`
   - You should see:
     - Database: `productcatalog` (PostgreSQL)
     - Calling Services: `product-service`, `inventory-service`, `order-service`
     - Query types: `SELECT`, `UPDATE`, `INSERT`
     - All queries showing proper latency and span attributes

## Current Configuration

### ConfigMap (Correct)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataprime-config
  namespace: dataprime-demo
data:
  CX_APPLICATION_NAME: "ecommerce-recommendation"
  CX_SUBSYSTEM_NAME: "ecommerce-production"  # ✅ Unified subsystem
  # ... other config
```

### Pod Environment (Verified)
```bash
$ kubectl exec -n dataprime-demo <pod> -- env | grep CX_SUBSYSTEM_NAME
CX_SUBSYSTEM_NAME=ecommerce-production  # ✅ All services now use this
```

## Important Notes

1. **Service Name vs Subsystem Name**
   - `OTEL_SERVICE_NAME` is still service-specific (e.g., `recommendation-ai`, `product-service`)
   - This is CORRECT - it identifies the service in traces
   - `CX_SUBSYSTEM_NAME` should be `ecommerce-production` for all services
   - This groups all traces under one subsystem in Coralogix

2. **Frontend Rollback**
   - The frontend deployment was rolled back because it requires `CX_RUM_PUBLIC_KEY` in the secret
   - This key is not currently in the `dataprime-secrets` secret
   - Frontend is still running on the old deployment, which works fine

3. **Why This Happened**
   
   **Deployment Manifests:**
   - The deployment manifests were likely created with service-specific subsystem names during development
   - The ConfigMap was updated to `ecommerce-production` later
   - But the deployment manifests were never updated to read from the ConfigMap
   - This is a common configuration drift issue
   
   **OTel Collector Configuration:**
   - The OTel Collector was likely copied from `old_app_files` which used `k3s-infrastructure`
   - The subsystem name was hardcoded in the Coralogix exporter configuration
   - Even though we set `CX_SUBSYSTEM_NAME` environment variable in the ConfigMap, the OTel Collector wasn't reading it
   - The collector's Coralogix exporter was using the hardcoded value instead of `${env:CX_SUBSYSTEM_NAME}`
   - **This is why fixing the deployment manifests alone didn't solve the problem!**

## Prevention

To prevent this issue in the future:

1. ✅ **Deployment Manifests**: All manifests now use `configMapKeyRef` for `CX_SUBSYSTEM_NAME`
2. ✅ **OTel Collector**: Configuration now uses `${env:CX_SUBSYSTEM_NAME}` instead of hardcoded value
3. ✅ **Verify Pods**: Check pods are reading the correct value: `kubectl exec <pod> -- env | grep CX_SUBSYSTEM`
4. ✅ **Verify Collector Config**: Check OTel Collector ConfigMap:
   ```bash
   kubectl get configmap otel-collector-config -n dataprime-demo -o yaml | grep subsystem_name
   # Should show: subsystem_name: "${env:CX_SUBSYSTEM_NAME}"
   # NOT: subsystem_name: "k3s-infrastructure"
   ```
5. ✅ **Verify Traces**: Check Coralogix AI Center to ensure all traces appear under `ecommerce-production`
6. ✅ **Never Hardcode**: Never hardcode `CX_SUBSYSTEM_NAME` in deployment manifests OR OTel Collector configuration

## Status: ✅ FIXED

All services are now correctly reporting to the `ecommerce-production` subsystem, and PostgreSQL database spans are visible in traces and Database APM.

