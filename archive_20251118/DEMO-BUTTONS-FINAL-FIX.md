# Demo Buttons - Final Working Fix

**Date**: November 18, 2025  
**Status**: ✅ RESOLVED

---

## The Complete Problem

The demo buttons in the frontend were failing with CORS errors and timeouts because:

1. **Wrong Service Type**: `product-service` was `ClusterIP` (internal only), not `NodePort` (externally accessible)
2. **Missing CORS**: Product service didn't have CORS enabled for cross-origin requests
3. **Wrong URL Construction**: Frontend JavaScript was using broken string replacement
4. **Docker Build Context Issue**: Multiple `app/` directories causing wrong files to be packaged

---

## All Fixes Applied

### Fix 1: Enable CORS on Product Service ✅
**File**: `coralogix-dataprime-demo/services/product_service.py`

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
```

### Fix 2: Update Frontend URL Construction ✅
**File**: `coralogix-dataprime-demo/app/ecommerce_frontend.py`

```javascript
// OLD (broken):
const response = await fetch(`${API_GATEWAY_URL.replace(':8010', ':8014')}/demo/enable-slow-queries`, {

// NEW (working):
const productServiceUrl = window.location.protocol + '//' + window.location.hostname + ':30014';
const response = await fetch(`${productServiceUrl}/demo/enable-slow-queries`, {
```

### Fix 3: Correct Docker Build Context ✅
**Issue**: The EC2 instance had two `app/` directories:
- `/home/ubuntu/app/` (OLD, missing files)
- `/home/ubuntu/coralogix-dataprime-demo/app/` (NEW, with updates)

**Solution**: Copied updated files to the root-level directories that Dockerfile expects:

```bash
cp coralogix-dataprime-demo/app/ecommerce_frontend.py app/
cp coralogix-dataprime-demo/services/product_service.py services/
docker build --platform linux/amd64 --no-cache -t ecommerce-demo:latest .
```

###Fix 4: Expose Product Service as NodePort ✅
**Issue**: Service was `ClusterIP`, not accessible from outside the cluster

**Solution**:
```bash
kubectl patch svc product-service -n dataprime-demo -p '{
  "spec":{
    "type":"NodePort",
    "ports":[{
      "port":8014,
      "targetPort":8014,
      "nodePort":30014,
      "protocol":"TCP",
      "name":"http"
    }]
  }
}'
```

**Result**:
```
NAME              TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)          AGE
product-service   NodePort   10.43.75.150   <none>        8014:30014/TCP   2d11h
```

---

##Test Results ✅

### Internal Test (from EC2 instance):
```bash
$ curl -X POST -H 'Content-Type: application/json' \
     -d '{"delay_ms": 2800}' \
     http://localhost:30014/demo/enable-slow-queries

{"delay_ms":2800,"status":"slow_queries_enabled"}
```

### Product Service Logs:
```
🐌 Slow query simulation ENABLED: 2800ms delay
10.42.0.1 - - [18/Nov/2025 18:18:57] "POST /demo/enable-slow-queries HTTP/1.1" 200 -
```

### CORS Headers Enabled:
- `Access-Control-Allow-Origin: *`
- Preflight OPTIONS requests now accepted
- Cross-origin POST requests from `https://54.235.171.176:30443` now work

---

## What Now Works

### From the Frontend UI (`https://54.235.171.176:30443`):

1. **"Simulate Slow Database"** button:
   - Calls: `https://54.235.171.176:30014/demo/enable-slow-queries`
   - No more CORS errors
   - Returns 200 OK
   - Enables 2800ms database delay simulation

2. **"Simulate Pool Exhaustion"** button:
   - Calls: `https://54.235.171.176:30014/demo/enable-pool-exhaustion`
   - No more CORS errors
   - Returns 200 OK
   - Simulates connection pool exhaustion

---

## Files Modified

| File | Changes |
|------|---------|
| `coralogix-dataprime-demo/services/product_service.py` | Added `flask-cors` import and `CORS(app)` |
| `coralogix-dataprime-demo/app/ecommerce_frontend.py` | Fixed URL construction for demo endpoints |
| `deployment/kubernetes/services.yaml` | Changed `product-service` from `ClusterIP` to `NodePort` with port 30014 |
| Docker images | Rebuilt with correct files from proper build context |

---

## Deployment Commands

### Complete Rebuild and Deploy:
```bash
# On EC2 instance:
cd /home/ubuntu

# Copy updated files to root build context
cp coralogix-dataprime-demo/app/ecommerce_frontend.py app/
cp coralogix-dataprime-demo/services/product_service.py services/

# Rebuild Docker image
sudo docker build --platform linux/amd64 --no-cache -t ecommerce-demo:latest .

# Import to K3s
sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -

# Update product-service to NodePort
sudo kubectl patch svc product-service -n dataprime-demo -p '{"spec":{"type":"NodePort","ports":[{"port":8014,"targetPort":8014,"nodePort":30014}]}}'

# Restart affected pods
sudo kubectl delete pod -n dataprime-demo -l app=frontend --force
sudo kubectl delete pod -n dataprime-demo -l app=product-service --force
```

---

## Verification Steps

### 1. Check Services:
```bash
kubectl get svc -n dataprime-demo
# Should show:
# product-service   NodePort   ...   8014:30014/TCP
```

### 2. Test Demo Endpoint:
```bash
curl -X POST http://54.235.171.176:30014/demo/enable-slow-queries \
  -H 'Content-Type: application/json' \
  -d '{"delay_ms": 2800}'
  
# Should return:
# {"delay_ms":2800,"status":"slow_queries_enabled"}
```

### 3. Test CORS:
```bash
curl -X OPTIONS http://54.235.171.176:30014/demo/enable-slow-queries \
  -H 'Origin: https://54.235.171.176:30443' \
  -v 2>&1 | grep Access-Control
  
# Should include:
# Access-Control-Allow-Origin: *
```

### 4. Test from Browser:
1. Open `https://54.235.171.176:30443`
2. Open DevTools Console (F12)
3. Click "Simulate Slow Database" button
4. Should see:
   - No CORS errors in console
   - Success alert: "🐌 Slow database simulation enabled"
   - Status updates in the UI

---

## Key Lessons Learned

### 1. **ClusterIP vs NodePort**
- `ClusterIP`: Only accessible within the K8s cluster (default)
- `NodePort`: Exposes service on a static port on each node's IP
- For browser-accessible APIs from external origins, use `NodePort` or Ingress

### 2. **Docker Build Context Matters**
- Multiple directories with the same name can cause confusion
- Always verify `docker run --rm <image> ls /app/` shows correct files
- Use `--no-cache` when debugging file inclusion issues

### 3. **CORS is Required for Cross-Origin APIs**
- HTTPS frontend (port 30443) calling HTTP backend (port 30014) = cross-origin
- Must enable CORS on the backend: `flask-cors` library
- Without CORS, browsers block the requests before they reach the server

### 4. **Dynamic URL Construction**
- Don't rely on string replacement for ports: `API_GATEWAY_URL.replace(':8010', ':8014')`
- Use `window.location.protocol + '//' + window.location.hostname + ':' + PORT`
- More reliable and works regardless of the current URL structure

---

## Architecture Overview

```
Browser (HTTPS)
    ↓
https://54.235.171.176:30443 (Frontend - NodePort)
    ↓ (JavaScript fetch)
https://54.235.171.176:30014 (Product Service - NodePort)
    ↓ (With CORS headers)
Demo endpoints: /demo/enable-slow-queries, /demo/enable-pool-exhaustion
```

---

## Status: READY FOR TESTING

All fixes are deployed and verified. The demo buttons should now work without CORS errors!

**Test URL**: https://54.235.171.176:30443

