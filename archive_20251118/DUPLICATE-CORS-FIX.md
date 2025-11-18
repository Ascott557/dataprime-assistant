# Duplicate CORS Headers Fix

**Date**: November 18, 2025  
**Status**: ✅ RESOLVED

---

## The Problem

Browser error:
```
Access to fetch at 'https://54.235.171.176:30444/api/recommendations' has been blocked by CORS policy: 
The 'Access-Control-Allow-Origin' header contains multiple values 'https://54.235.171.176:30443, *', 
but only one is allowed.
```

**Root Cause**: Both nginx proxy AND API Gateway were adding CORS headers, resulting in duplicate `Access-Control-Allow-Origin` headers.

---

## The Solution

Updated nginx configuration to **remove** CORS headers from `/api/*` routes and let the API Gateway (which has `flask-cors` enabled) handle CORS.

### Before (broken):
```nginx
location /api/ {
    add_header 'Access-Control-Allow-Origin' '*' always;  # ← nginx adds CORS
    # ...
    proxy_pass http://api-gateway:8010;  # ← API Gateway also adds CORS via flask-cors
}
```
**Result**: TWO `Access-Control-Allow-Origin` headers → Browser rejects

### After (working):
```nginx
location /api/ {
    # NO CORS headers here - API Gateway handles them via flask-cors
    proxy_pass http://api-gateway:8010;
}

location /demo/ {
    # CORS headers ONLY on demo endpoints (product service needs them)
    add_header 'Access-Control-Allow-Origin' '*' always;
    proxy_pass http://product-service:8014;
}
```
**Result**: ONE `Access-Control-Allow-Origin` header → Browser accepts

---

## Test Results

### API Endpoint (CORS from API Gateway):
```bash
$ curl -k -i -X POST https://localhost:30444/api/recommendations

HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://54.235.171.176:30443  ← ONE header from API Gateway
```

### Demo Endpoint (CORS from nginx):
```bash
$ curl -k -i -X POST https://localhost:30444/demo/enable-slow-queries

HTTP/1.1 200 OK
Access-Control-Allow-Origin: *  ← ONE header from nginx
```

---

## Why This Works

| Route | CORS Source | Reason |
|-------|-------------|--------|
| `/api/*` | API Gateway (`flask-cors`) | API Gateway already has CORS configured, nginx just proxies |
| `/demo/*` | Nginx | Product service may not have complete CORS, nginx adds it |
| `/` (default) | API Gateway (`flask-cors`) | Default route goes to API Gateway |

---

## Deployment

```bash
# Update ConfigMap
kubectl create configmap nginx-https-config \
  --from-file=nginx.conf=https-proxy-nginx-no-duplicate-cors.conf \
  -n dataprime-demo \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart proxy
kubectl delete pod -n dataprime-demo -l app=https-proxy
```

---

## File Modified

**File**: `deployment/kubernetes/https-proxy-nginx-no-duplicate-cors.conf`

**Key Change**: Removed `add_header 'Access-Control-Allow-Origin'` from `/api/*` location block.

---

## Status: FIXED ✅

The duplicate CORS header issue is resolved. The `/api/recommendations` endpoint should now work without CORS errors.

**Test**: Refresh `https://54.235.171.176:30443` and click "Get Recommendations" - should work without CORS errors!

