# Frontend Buttons Not Working - Root Cause Analysis

**Date**: November 17, 2025  
**Status**: ❌ BROKEN - API Gateway rejecting requests

---

## 🔍 Root Cause

The **API Gateway** is returning **HTTP 400** errors because it requires query parameters that the frontend doesn't send:

```
Error: "Missing required parameters: category, price_min, price_max"
```

### What Happened

1. ✅ **Scene 9 button works** → Uses `/api/demo/inject-telemetry` (no parameters needed)
2. ❌ **Products button fails** → Calls `/api/products` without required query params
3. ❌ **Recommendations button fails** → Calls `/api/recommendations` with wrong parameters
4. ❌ **All other buttons fail** → Same API parameter mismatch issue

---

## 📊 Current State

| Component | Status | Issue |
|-----------|--------|-------|
| Frontend | ✅ Running | Sending requests correctly |
| API Gateway | ⚠️ Running | **Strict parameter validation** |
| Product Service | ✅ Running | Working when called directly |
| All Services | ✅ Running | Backend services are fine |
| **Problem** | ❌ | **API Gateway <-> Frontend mismatch** |

---

## 🎯 What Needs to be Fixed

The API Gateway endpoints need to:
1. Make query parameters **optional** (use defaults if not provided)
2. Accept requests from frontend without strict validation
3. Match the contract that the frontend expects

---

##Fixed Endpoints Needed

### 1. `/api/products` (Currently Broken)
**Current**: Requires `category`, `price_min`, `price_max`  
**Needed**: Make all parameters optional, return all products if no filters

### 2. `/api/recommendations` (Currently Broken)
**Current**: Unknown validation issue  
**Needed**: Accept POST with `user_id` and context

### 3. `/api/feedback` (Probably Broken)
**Needed**: Accept POST with feedback data

### 4. `/api/demo/inject-telemetry` (✅ WORKING)
**Status**: Already works - this is why Scene 9 button works

---

## 🔧 Fix Options

### Option 1: Fix API Gateway Code (Best Long-term)
- Update `api_gateway.py` to make parameters optional
- Add default values for missing parameters
- Redeploy API Gateway

**Time**: 10-15 minutes  
**Risk**: Low  
**Result**: All buttons will work

### Option 2: Update Frontend to Send Parameters (Workaround)
- Modify frontend JavaScript to always send required parameters
- Redeploy frontend

**Time**: 5-10 minutes  
**Risk**: Medium (might break other things)  
**Result**: Buttons work but hacky

### Option 3: Use the Working Version (Rollback)
- Find the old `api_gateway.py` that was working
- Deploy that version

**Time**: 5 minutes  
**Risk**: Low  
**Result**: Get back to working state

---

## 💡 Recommended Fix

**Fix the API Gateway** to make parameters optional:

```python
@app.route('/api/products', methods=['GET'])
def proxy_products():
    # Make parameters optional with defaults
    category = request.args.get('category', '')
    price_min = request.args.get('price_min', '0')
    price_max = request.args.get('price_max', '10000')
    
    # Don't validate as required - use defaults
    # ...rest of code
```

---

## 🚨 Why This Happened

When we rebuilt the Docker image with the optimized version, the **API Gateway code** was from a version that has stricter parameter validation than what the frontend expects.

**The mismatch**:
- Frontend: Built to work with simple APIs (no required params)
- API Gateway: Deployed with code that requires strict parameters
- Result: Frontend → HTTP 400 → Buttons don't work

---

## ✅ What Still Works

- ✅ Frontend loads
- ✅ HTTPS proxy working
- ✅ Scene 9 button (inject telemetry)
- ✅ All backend services running
- ✅ Database connections
- ✅ OTel Collector

**Only issue**: API Gateway parameter validation

---

## 🎯 Next Steps

1. **Check** if there's an `old_app_files` version of `api_gateway.py` that worked
2. **Fix** the parameter validation in API Gateway
3. **Rebuild** and deploy the API Gateway
4. **Test** all buttons work

This is a **quick fix** - probably 10-15 minutes to resolve.

---

**Would you like me to fix this now?**

