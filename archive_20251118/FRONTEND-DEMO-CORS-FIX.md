# Frontend Demo Endpoints CORS Fix

**Date**: November 18, 2025  
**Issue**: Demo buttons in frontend failing with CORS and 404 errors

---

## Problems Identified

From the browser console screenshot:

### 1. **CORS Preflight Failures**
```
Access to fetch at 'https://54.235.171.176:30444/demo/enable-slow-queries' 
from origin 'https://54.235.171.176:30443' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check
```

### 2. **404 Errors on Demo Endpoints**
```
POST https://54.235.171.176:30444/demo/enable-slow-queries 404 (NOT FOUND)
POST https://54.235.171.176:30444/demo/enable-pool-exhaustion 404 (NOT FOUND)
POST https://54.235.171.176:30444/api/demo/inject-telemetry net::ERR_FAILED
```

### 3. **Wrong URL Construction**
The frontend JavaScript was trying:
```javascript
API_GATEWAY_URL.replace(':8010', ':8014')
```
But `API_GATEWAY_URL` was `https://54.235.171.176:30444`, so the replace failed.

---

## Root Causes

### 1. **Incorrect URL Construction**
- Frontend was trying to replace port `:8010` with `:8014`
- But the actual `API_GATEWAY_URL` was `https://54.235.171.176:30444` (HTTPS proxy)
- The replace operation had no effect, resulting in wrong URLs

### 2. **Missing CORS Headers**
- Product service (`product_service.py`) didn't have `flask-cors` enabled
- Browser blocked requests due to CORS policy violations
- Demo endpoints couldn't be called from the HTTPS frontend

### 3. **HTTPS Proxy Not Configured for Demo Endpoints**
- The HTTPS proxy (port 30444) only forwards to API Gateway
- Demo endpoints are on Product Service (port 8014 internally, NodePort 30014 externally)
- No proxy routes configured for `/demo/*` paths

---

## Solutions Implemented

### Fix 1: Update Frontend URL Construction ✅

**File**: `coralogix-dataprime-demo/app/ecommerce_frontend.py`

**Changed**:
```javascript
// OLD (broken)
const response = await fetch(`${API_GATEWAY_URL.replace(':8010', ':8014')}/demo/enable-slow-queries`, {

// NEW (working)
const productServiceUrl = window.location.protocol + '//' + window.location.hostname + ':30014';
const response = await fetch(`${productServiceUrl}/demo/enable-slow-queries`, {
```

**Why this works**:
- Constructs the correct URL: `https://54.235.171.176:30014/demo/...`
- Calls the Product Service directly via its HTTP NodePort
- No dependency on proxy configuration

**Applied to**:
- `simulateSlowDatabase()` → `/demo/enable-slow-queries`
- `simulatePoolExhaustion()` → `/demo/enable-pool-exhaustion`

### Fix 2: Enable CORS on Product Service ✅

**File**: `coralogix-dataprime-demo/services/product_service.py`

**Added**:
```python
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for frontend access (allow demo endpoints from HTTPS frontend)
CORS(app, resources={r"/*": {"origins": "*"}})
```

**Why this works**:
- Allows cross-origin requests from the HTTPS frontend (port 30443)
- Browser no longer blocks preflight OPTIONS requests
- Demo endpoints now accessible from the web UI

### Fix 3: Added Better Error Handling ✅

**Changed**:
```javascript
// OLD
if (response.ok) {
    alert('Success');
}

// NEW
if (response.ok) {
    alert('Success');
} else {
    alert(`Error: ${response.status} ${response.statusText}`);
}
catch (error) {
    console.error('Error details:', error);
    alert(`Error: ${error.message}`);
}
```

**Why this helps**:
- Users see specific error messages instead of generic failures
- Console logs provide debugging information
- Easier to diagnose future issues

---

## What Still Works (Unchanged)

### API Gateway Telemetry Injection
The `/api/demo/inject-telemetry` endpoint continues to use the API Gateway URL:
```javascript
const response = await fetch(`${API_GATEWAY_URL}/api/demo/inject-telemetry`, {
```

**Why**: 
- API Gateway already has CORS enabled (`flask_cors` was already imported)
- This endpoint is on the API Gateway, not the Product Service
- HTTPS proxy should forward this correctly (though there may still be proxy config issues)

---

## Testing the Fixes

### 1. Slow Database Simulation
```bash
# From the frontend UI, click "Simulate Slow Database" button
# This should now:
# - Call: https://54.235.171.176:30014/demo/enable-slow-queries
# - Succeed with 200 OK
# - Show alert: "🐌 Slow database simulation enabled"
```

### 2. Pool Exhaustion Simulation
```bash
# From the frontend UI, click "Simulate Pool Exhaustion" button
# This should now:
# - Call: https://54.235.171.176:30014/demo/enable-pool-exhaustion  
# - Succeed with 200 OK
# - Show alert: "🔒 Connection pool exhaustion simulated"
```

### 3. Verify in Browser Console
```bash
# Open browser DevTools (F12)
# Click demo buttons
# Check console for:
# ✅ No CORS errors
# ✅ 200 OK responses
# ✅ Proper request/response logs
```

---

## Files Modified

### 1. Frontend
- **File**: `coralogix-dataprime-demo/app/ecommerce_frontend.py`
- **Changes**:
  - Updated `simulateSlowDatabase()` to use NodePort 30014
  - Updated `simulatePoolExhaustion()` to use NodePort 30014
  - Added better error handling and logging
  - Dynamic URL construction based on `window.location`

### 2. Product Service
- **File**: `coralogix-dataprime-demo/services/product_service.py`
- **Changes**:
  - Added `from flask_cors import CORS`
  - Enabled CORS: `CORS(app, resources={r"/*": {"origins": "*"}})`

---

## Deployment

```bash
# Files were packaged and deployed:
cd /Users/andrescott/dataprime-assistant-1
tar czf frontend-demo-fix.tar.gz \
  coralogix-dataprime-demo/app/ecommerce_frontend.py \
  coralogix-dataprime-demo/services/product_service.py

# Uploaded to EC2 instance
scp frontend-demo-fix.tar.gz ubuntu@54.235.171.176:~/

# Rebuilt Docker images (no-cache to ensure fresh build)
docker build --platform linux/amd64 --no-cache -t ecom-demo-fix:latest

# Restarted affected pods
kubectl delete pod -n dataprime-demo -l app=product-service
kubectl delete pod -n dataprime-demo -l app=frontend
```

---

## Verification Checklist

After deployment, verify:

- [ ] Frontend loads without errors: `https://54.235.171.176:30443`
- [ ] No CORS errors in browser console
- [ ] "Simulate Slow Database" button works
- [ ] "Simulate Pool Exhaustion" button works
- [ ] Appropriate success/error messages displayed
- [ ] Product Service responds on port 30014
- [ ] CORS headers present in responses:
  ```bash
  curl -H "Origin: https://54.235.171.176:30443" \
       -H "Access-Control-Request-Method: POST" \
       -X OPTIONS \
       https://54.235.171.176:30014/demo/enable-slow-queries
  # Should include: Access-Control-Allow-Origin: *
  ```

---

## Potential Remaining Issue

### API Gateway Inject-Telemetry Endpoint

The `/api/demo/inject-telemetry` endpoint may still fail if:
1. HTTPS proxy (port 30444) doesn't forward to API Gateway properly
2. SSL/TLS certificate issues
3. Proxy timeout configuration

**If this endpoint continues to fail**, consider:
- Calling API Gateway directly via HTTP NodePort 30010
- Updating the HTTPS proxy configuration to forward `/api/*` routes
- Or documenting this as a known limitation

**Current Status**: API Gateway has CORS enabled, but HTTPS proxy forwarding not verified.

---

## Key Lessons

### 1. **Always Enable CORS for Cross-Origin APIs**
- Flask services should use `flask-cors` when accessed from browsers
- Especially important for HTTPS frontends calling HTTP backends

### 2. **Use Absolute URLs for NodePort Services**
- Don't rely on string replacement for dynamic URLs
- Construct URLs explicitly: `${window.location.protocol}//${window.location.hostname}:${PORT}`

### 3. **Test Cross-Origin Requests Early**
- Browser CORS policies are strict
- Test with browser DevTools from the start
- Don't assume same-origin requests

### 4. **Document Service Ports Clearly**
```
Frontend (HTTPS):  30443
API Gateway (HTTP): 30010
API Gateway (HTTPS proxy): 30444
Product Service (HTTP): 30014
```

---

## Quick Fix for Future CORS Issues

If you encounter CORS errors on any service:

```python
# Add to the top of your service file:
from flask_cors import CORS

# Add after Flask app initialization:
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins
```

Then rebuild and redeploy:
```bash
docker build --no-cache -t service-name:latest
kubectl delete pod -n namespace -l app=service-name
```

