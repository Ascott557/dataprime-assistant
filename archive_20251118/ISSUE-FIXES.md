# Issues Fixed - November 15, 2025

## Overview

Three critical issues were identified and resolved:

1. ✅ **RUM SDK ORB Blocking** - Coralogix RUM SDK blocked by browser
2. ✅ **API Gateway Connection Error** - Frontend couldn't reach backend
3. ⚠️ **OpenAI API Key Invalid** - AI recommendations failing with 401 error

---

## Issue 1: RUM SDK Blocked by ORB ❌ → ✅

### Problem

```
(failed) net::ERR_BLOCKED_BY_ORB
```

The Coralogix RUM SDK (`coralogix-rum.min.js`) was being blocked by the browser's **Opaque Response Blocking** (ORB) security policy.

### Root Cause

The CDN script was loaded without the `crossOrigin` attribute, causing the browser to block the response for security reasons.

### Fix

Added `crossOrigin = 'anonymous'` to the script tag:

```javascript
const script = document.createElement('script');
script.src = 'https://cdn.coralogix.com/rum/latest/coralogix-rum.min.js';
script.crossOrigin = 'anonymous';  // ✅ Fix ORB blocking
```

Also added better error handling:

```javascript
script.onerror = function(error) {
    console.warn('⚠️ Coralogix RUM SDK failed to load from CDN');
    console.log('📝 Continuing without RUM tracking - app will still work normally');
};
```

### Files Changed

- `coralogix-dataprime-demo/app/ecommerce_frontend.py`

### Status

✅ **Fixed and Deployed**

### Verification

1. Open: http://54.235.171.176:30020
2. Open Browser Developer Tools (F12)
3. Check Network tab - `coralogix-rum.min.js` should load successfully (200 OK)
4. Check Console for: `✅ Coralogix RUM initialized`

---

## Issue 2: API Gateway Connection Error ❌ → ✅

### Problem

```
❌ Connection Error: Failed to fetch
Make sure the backend services are running.
```

When clicking "Get AI Recommendations", the browser showed a connection error.

### Root Cause

The `API_GATEWAY_URL` environment variable was set to the **internal Kubernetes service name**:

```
API_GATEWAY_URL=http://api-gateway:8010
```

This works for pod-to-pod communication inside the cluster, but **browsers cannot resolve internal Kubernetes DNS names**. The browser needs the external IP and NodePort.

### Fix

Updated the `API_GATEWAY_URL` to use the external NodePort:

```yaml
# deployment/kubernetes/deployments/frontend.yaml
- name: API_GATEWAY_URL
  value: "http://54.235.171.176:30010"  # External NodePort URL for browser access
```

**Before:**
```javascript
// Browser tried to fetch from:
http://api-gateway:8010/api/recommendations  ❌ DNS resolution fails
```

**After:**
```javascript
// Browser now fetches from:
http://54.235.171.176:30010/api/recommendations  ✅ Works!
```

### Files Changed

- `deployment/kubernetes/deployments/frontend.yaml`

### Status

✅ **Fixed and Deployed**

### Verification

1. Open: http://54.235.171.176:30020
2. Enter a search query (e.g., "laptop for gaming")
3. Click "Get AI Recommendations"
4. ⚠️ **Note**: You'll now get a different error (see Issue 3 below)

---

## Issue 3: OpenAI API Key Invalid ⚠️ (Requires User Action)

### Problem

After fixing the connection issue, the AI recommendations now fail with:

```json
{
  "error": "AI service error: 500",
  "message": "Error code: 401 - Incorrect API key provided: sk-proj-****...****T-0A",
  "service": "recommendation_ai_service"
}
```

### Root Cause

The OpenAI API key stored in the Kubernetes secret is **invalid or expired**. OpenAI returns a 401 (Unauthorized) error.

### Fix Required

You need to provide a **valid OpenAI API key**. Here's how:

#### Step 1: Get a Valid OpenAI API Key

1. Go to: https://platform.openai.com/account/api-keys
2. Log in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...` or `sk-...`)

#### Step 2: Update the Kubernetes Secret

SSH into your EC2 instance and update the secret:

```bash
# SSH to EC2
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Update the OpenAI API key
kubectl patch secret dataprime-secrets -n dataprime-demo \
  -p="{\"data\":{\"OPENAI_API_KEY\":\"$(echo -n 'YOUR_ACTUAL_OPENAI_KEY' | base64)\"}}"

# Restart the Recommendation AI service to pick up the new key
kubectl rollout restart deployment/recommendation-ai -n dataprime-demo

# Wait for pod to be ready
kubectl get pods -n dataprime-demo -l app=recommendation-ai -w
```

#### Step 3: Verify the Fix

```bash
# Test the recommendation AI service
kubectl run -n dataprime-demo test-ai --image=curlimages/curl:latest --rm -i --restart=Never -- \
  curl -s -X POST http://recommendation-ai:8011/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","user_context":"laptop for gaming"}' \
  --max-time 30

# Should return AI-generated recommendations (not an error)
```

#### Alternative: Use Mock Mode (No OpenAI Key Required)

If you don't have an OpenAI API key, you can modify the Recommendation AI service to return mock data instead of calling OpenAI. This is useful for demo purposes.

**Option A**: Set a flag to use mock responses
```bash
kubectl set env deployment/recommendation-ai -n dataprime-demo USE_MOCK_AI=true
```

**Option B**: Modify the code to skip OpenAI and return sample recommendations
- Edit `coralogix-dataprime-demo/services/recommendation_ai_service.py`
- Comment out the OpenAI API calls
- Return static mock data instead

### Status

⚠️ **Requires Your Action** - You must provide a valid OpenAI API key

### Current Behavior

- ✅ Frontend loads successfully
- ✅ Browser can reach API Gateway
- ✅ API Gateway can reach Recommendation AI service
- ❌ Recommendation AI fails when calling OpenAI API (401 Unauthorized)

---

## Summary of All Fixes

| Issue | Root Cause | Fix | Status |
|-------|------------|-----|--------|
| RUM SDK ORB Blocking | Missing `crossOrigin` attribute | Added `crossOrigin='anonymous'` | ✅ Fixed |
| API Gateway Connection | Internal K8s DNS used for browser | Changed to external NodePort URL | ✅ Fixed |
| OpenAI API 401 Error | Invalid/expired API key | User must provide valid key | ⚠️ Action Required |

---

## Architecture: Browser Communication

### Before (Broken)

```
Browser
  ↓
  Tries to fetch: http://api-gateway:8010  ❌ DNS fails
```

### After (Fixed)

```
Browser
  ↓
  Fetches: http://54.235.171.176:30010 (External IP:NodePort)  ✅
  ↓
  API Gateway (running on K3s)
  ↓
  Recommendation AI (internal: http://recommendation-ai:8011)  ✅
  ↓
  OpenAI API (if valid key provided)  ⚠️
```

### Key Insight

**Internal Kubernetes service names** (e.g., `api-gateway:8010`) work for:
- ✅ Pod-to-pod communication inside the cluster
- ✅ Server-side requests (Python, Node.js services)

But **NOT** for:
- ❌ Browser JavaScript (fetch, XHR)
- ❌ External clients

**Browsers need external IPs and NodePorts** (e.g., `54.235.171.176:30010`)

---

## Testing Checklist

### ✅ Frontend Loads
- [ ] Open http://54.235.171.176:30020
- [ ] Page loads without errors
- [ ] No console errors (except OpenAI 401 after clicking button)

### ✅ RUM SDK Loads
- [ ] Check Network tab: `coralogix-rum.min.js` status 200
- [ ] Check Console: `✅ Coralogix RUM initialized`
- [ ] No ORB blocking errors

### ✅ API Gateway Reachable
- [ ] Enter search query: "laptop for gaming"
- [ ] Click "Get AI Recommendations"
- [ ] Browser successfully sends POST to `http://54.235.171.176:30010/api/recommendations`
- [ ] Network tab shows 200 or 500 response (not "Failed to fetch")

### ⚠️ OpenAI Integration (Requires Valid API Key)
- [ ] Update OpenAI API key in secret (see Issue 3)
- [ ] Restart Recommendation AI deployment
- [ ] Test recommendations again
- [ ] Should see AI-generated product recommendations

---

## Files Modified

### Application Code
- `coralogix-dataprime-demo/app/ecommerce_frontend.py`
  - Added `crossOrigin='anonymous'` to RUM SDK script tag
  - Added better error handling for RUM initialization

### Kubernetes Deployment
- `deployment/kubernetes/deployments/frontend.yaml`
  - Changed `API_GATEWAY_URL` from `http://api-gateway:8010` to `http://54.235.171.176:30010`

---

## Next Steps

1. **Update OpenAI API Key** (See Issue 3 instructions above)
   - Get key from: https://platform.openai.com/account/api-keys
   - Update Kubernetes secret
   - Restart recommendation-ai deployment

2. **Verify Full Functionality**
   - Test AI recommendations
   - Check RUM data in Coralogix dashboard
   - Verify traces in APM

3. **Monitor for Issues**
   - Watch pod logs: `kubectl logs -n dataprime-demo deployment/recommendation-ai -f`
   - Check Coralogix for errors
   - Monitor application performance

---

## Support

If you encounter additional issues:

1. **Check pod status:**
   ```bash
   kubectl get pods -n dataprime-demo
   ```

2. **Check pod logs:**
   ```bash
   kubectl logs -n dataprime-demo deployment/frontend
   kubectl logs -n dataprime-demo deployment/api-gateway
   kubectl logs -n dataprime-demo deployment/recommendation-ai
   ```

3. **Check service endpoints:**
   ```bash
   kubectl get svc -n dataprime-demo
   ```

4. **Test internal connectivity:**
   ```bash
   kubectl run -n dataprime-demo test-curl --image=curlimages/curl:latest --rm -i --restart=Never -- \
     curl -s http://api-gateway:8010/api/health
   ```

---

**Deployment Status**: ✅ 2 of 3 issues fixed  
**Application URL**: http://54.235.171.176:30020  
**Action Required**: Update OpenAI API key to enable AI recommendations  

