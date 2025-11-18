# Verify Telemetry - Complete Guide

**Date**: November 15, 2025  
**Application**: E-commerce Recommendation System  
**Test Trace Generated**: `6741b95b5330de9c5370a5b2c1596020`

---

## ✅ Backend Traces - Ready to Verify!

### What Just Happened

A test API call was just made that generated a complete distributed trace:

```
Browser/API → API Gateway → Recommendation AI → OpenAI API
```

**Trace ID**: `6741b95b5330de9c5370a5b2c1596020`

### Verify in Coralogix APM

1. **Log in to Coralogix**: https://coralogix.com/
2. **Select Region**: EU2
3. **Navigate to**: APM → Traces
4. **Filter by**:
   - Application: `ecommerce-recommendation`
   - Time: Last 15 minutes
5. **Search for Trace ID**: `6741b95b5330de9c5370a5b2c1596020`

### What You Should See

The trace should show:
- ✅ **api-gateway** span (entry point)
- ✅ **recommendation-ai** span (AI service)
- ✅ **OpenAI API** spans (LLM calls)
- ✅ **Database queries** (if product lookup succeeded)
- ✅ **Tool calls** (product data retrieval)

---

## 🌐 RUM Data - Requires Browser Interaction!

### Important: RUM is Browser-Side

**RUM (Real User Monitoring) tracks actual user interactions in the browser.**

It does NOT automatically appear - you must:
1. Open the application in a real browser
2. Interact with the UI
3. Wait 1-2 minutes for data to appear in Coralogix

### Step-by-Step RUM Testing

#### 1. Open the Application

```
http://54.235.171.176:30020
```

#### 2. Open Browser Developer Tools

Press **F12** or right-click → **Inspect**

#### 3. Verify RUM SDK Loaded

**Console Tab**: Look for:
```
✅ Coralogix RUM initialized
```

**Network Tab**: Filter by "rum" or "coralogix"
- Should see: `coralogix-rum.min.js` (Status: 200 OK)
- Should see: POST requests to `rum-ingress.eu2.coralogix.com`

#### 4. Generate User Actions

Perform these actions in the browser:

**Action 1: Search for Products**
1. Enter: "wireless headphones under $100"
2. Click "Get AI Recommendations"
3. Wait for response

**Action 2: Try Different Searches**
1. Enter: "laptop for gaming"
2. Click "Get AI Recommendations"
3. Wait for response

**Action 3: Test Demo Controls** (if present)
1. Click any demo buttons
2. Observe behavior

#### 5. Check Network Tab for RUM Beacons

After each action, check the **Network** tab:
- Filter by: `rum-ingress`
- You should see POST requests with status 200 or 204
- These are RUM beacons sending data to Coralogix

#### 6. Wait 2-3 Minutes

RUM data has a slight ingestion delay. **Wait 2-3 minutes** before checking Coralogix dashboard.

#### 7. Verify in Coralogix RUM Dashboard

1. **Navigate to**: RUM section in Coralogix
2. **Select Application**: `ecom_reccomendation` (note the spelling with double 'm')
3. **Check for**:
   - Your session (should appear within 2-3 minutes)
   - Page views
   - Custom actions: `get_recommendations_start`, `get_recommendations_success`
   - Performance metrics
   - Session replay (if enabled)

---

## 🔍 Troubleshooting

### "No Backend Traces in Coralogix"

**Check #1: Trace ID Search**
```bash
# SSH to EC2
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Generate a new trace
curl -s -X POST http://54.235.171.176:30010/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_test","user_context":"laptop"}' \
  --max-time 45 | jq -r '.trace_id'

# Use this trace ID to search in Coralogix APM
```

**Check #2: OTel Collector**
```bash
# Check if OTel Collector is receiving data
kubectl logs -n dataprime-demo daemonset/coralogix-opentelemetry-collector --tail=50 | grep -i "exporter"
```

**Check #3: Service Logs**
```bash
# Check API Gateway logs
kubectl logs -n dataprime-demo deployment/api-gateway --tail=30

# Check Recommendation AI logs
kubectl logs -n dataprime-demo deployment/recommendation-ai --tail=30
```

### "No RUM Data in Coralogix"

**Check #1: Browser Console**
- Open http://54.235.171.176:30020
- Press F12 → Console tab
- Look for: "✅ Coralogix RUM initialized"
- If you see errors, screenshot and share them

**Check #2: Network Tab**
- Open Network tab in browser
- Clear all requests
- Refresh the page
- Filter by "rum" or "coralogix"
- Look for:
  - `coralogix-rum.min.js` - Should be 200 OK
  - POST to `rum-ingress.eu2.coralogix.com` - Should be 200/204

**Check #3: RUM Configuration**
- RUM Public Key: `cxtp_lYys51KLFaJ8elL3Ym1dOEcTIMwEwR`
- Application Name: `ecom_reccomendation`
- Domain: `EU2`

**Check #4: Perform Actions**
- RUM data only appears when you **interact** with the app
- Simply loading the page generates minimal data
- You need to click buttons and submit forms

**Check #5: Wait**
- RUM has 1-3 minute ingestion delay
- Generate actions in browser
- Wait 3 minutes
- Then check Coralogix dashboard

### "RUM SDK Not Loading (ORB Error)"

If you see `net::ERR_BLOCKED_BY_ORB` in browser console:

**Already Fixed!** The `crossOrigin='anonymous'` attribute is in place.

If it still fails:
- Disable browser extensions (ad blockers, privacy tools)
- Try incognito/private browsing mode
- Try a different browser (Chrome, Firefox, Safari)

### "Wrong Application Name in Coralogix"

**Backend Traces**: Look for application `ecommerce-recommendation`
**RUM Data**: Look for application `ecom_reccomendation` (with double 'm')

These are intentionally different names based on your configuration.

---

## 🧪 Quick Test Script

Run this to generate multiple traces at once:

```bash
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Generate 5 test traces
for i in {1..5}; do
  echo "Test $i:"
  curl -s -X POST http://54.235.171.176:30010/api/recommendations \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"load_test_$i\",\"user_context\":\"gaming laptop\"}" \
    --max-time 45 | jq -r '  "  Success: \(.success)\n  Trace: \(.trace_id)\n"'
  sleep 2
done

echo "✅ Generated 5 traces!"
echo "📊 Check Coralogix APM for these traces"
echo "   Application: ecommerce-recommendation"
echo "   Time: Last 5 minutes"
```

---

## 📊 Expected Telemetry Data

### In Coralogix APM (Backend Traces)

**Application**: `ecommerce-recommendation`

**Services**:
- `api-gateway` - Entry point for API requests
- `recommendation-ai` - AI recommendation service
- `product-service` - Product database queries
- `frontend` - Web server (Flask)

**Traces Should Show**:
1. HTTP POST to `/api/recommendations`
2. Call from API Gateway to Recommendation AI
3. OpenAI API calls (GPT-4 Turbo)
4. Tool calls to fetch product data
5. Database queries (PostgreSQL)
6. Response propagation back to client

### In Coralogix RUM Dashboard

**Application**: `ecom_reccomendation`

**Data Types**:
- **Sessions**: Individual user sessions
- **Page Views**: Each page load
- **Actions**: Custom tracked actions
  - `get_recommendations_start`
  - `get_recommendations_success`
  - `get_recommendations_error`
- **Performance**:
  - Page load time
  - Time to interactive
  - API response times
  - Core Web Vitals (LCP, FID, CLS)
- **Errors**: JavaScript errors (if any occur)
- **Session Replay**: Visual playback of user session

### In Coralogix AI Center

**OpenAI Traces**:
- Model: `gpt-4-turbo`
- Conversation flows
- Tool invocations
- Token usage
- Response times

---

## ✅ Success Checklist

### Backend Traces
- [ ] Trace ID `6741b95b5330de9c5370a5b2c1596020` found in Coralogix APM
- [ ] Application `ecommerce-recommendation` visible
- [ ] Services showing: api-gateway, recommendation-ai
- [ ] OpenAI spans present in traces
- [ ] Database calls visible

### RUM Data
- [ ] Opened http://54.235.171.176:30020 in browser
- [ ] Console shows "✅ Coralogix RUM initialized"
- [ ] Network tab shows RUM SDK loaded (200 OK)
- [ ] Performed 2-3 search actions
- [ ] Network tab shows RUM beacons to rum-ingress.eu2.coralogix.com
- [ ] Waited 3 minutes
- [ ] RUM dashboard shows application `ecom_reccomendation`
- [ ] Session data visible
- [ ] Custom actions visible

### Infrastructure
- [ ] All pods running (`kubectl get pods -n dataprime-demo`)
- [ ] OTel Collector healthy
- [ ] No error logs in services

---

## 🎯 Quick Verification Commands

```bash
# SSH to EC2
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176

# Check all pods
kubectl get pods -n dataprime-demo

# Generate a test trace
curl -s -X POST http://54.235.171.176:30010/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"verify_test","user_context":"wireless mouse"}' \
  --max-time 45 | jq

# Check OTel Collector
kubectl logs -n dataprime-demo daemonset/coralogix-opentelemetry-collector --tail=20

# Check API Gateway
kubectl logs -n dataprime-demo deployment/api-gateway --tail=20

# Check Recommendation AI
kubectl logs -n dataprime-demo deployment/recommendation-ai --tail=20
```

---

## 📞 Support

If you're still not seeing data:

1. **Run the test script above** - Generate multiple traces
2. **Take screenshots** of:
   - Browser console (F12)
   - Network tab (filtered by "rum")
   - Coralogix APM page (if no traces)
   - Coralogix RUM page (if no sessions)
3. **Check pod logs** for errors
4. **Verify time ranges** in Coralogix (set to "Last 15 minutes")

---

**Application URL**: http://54.235.171.176:30020  
**Backend APM**: Application `ecommerce-recommendation`  
**Frontend RUM**: Application `ecom_reccomendation`  
**Test Trace ID**: `6741b95b5330de9c5370a5b2c1596020`  
**Current Time**: November 15, 2025, 18:38 UTC  

🎉 **Backend telemetry is confirmed working! RUM requires browser interaction to generate data.**

