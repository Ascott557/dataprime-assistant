# RUM Verification Steps

## Quick Start

### 1. Access the Application

Open your browser and navigate to:
```
http://54.235.171.176:30020
```

### 2. Open Browser Developer Tools

Press `F12` or right-click and select "Inspect"

### 3. Check Console

You should see:
```
✅ Coralogix RUM initialized
✅ RUM initialized
```

### 4. Check Network Tab

Filter by "coralogix" or "rum" and you should see:
- RUM SDK loading from CDN: `coralogix-rum.min.js`
- Beacon requests to: `rum-ingress.eu2.coralogix.com`

### 5. Test User Actions

1. **Enter a search query**:
   - Type "laptop for work" in the search box
   - Click "Get AI Recommendations"

2. **Check Console**:
   - Should show RUM action tracking
   - Should show user context being set

3. **Check Network Tab**:
   - Look for RUM beacon requests containing your action data
   - These are POST requests to the RUM ingress endpoint

### 6. Verify in Coralogix Dashboard

1. **Log in to Coralogix**:
   ```
   https://coralogix.com/
   Select region: EU2
   ```

2. **Navigate to RUM**:
   - Click on "RUM" in the left sidebar
   - Select application: **ecom_reccomendation**

3. **Check Session Data**:
   - You should see active sessions
   - Your session should appear within 1-2 minutes
   - Session should show:
     - User ID (e.g., `demo_user_1731657600000`)
     - Actions performed
     - Page views
     - Performance metrics

4. **Check Session Replay**:
   - Click on a session
   - Look for "Session Replay" tab
   - You should be able to replay your session visually

5. **Check Custom Actions**:
   - Navigate to "Actions" view
   - You should see:
     - `get_recommendations_start`
     - `get_recommendations_success` (or `get_recommendations_error`)
   - Each action should have:
     - Timestamp
     - User context
     - Custom metadata

## Expected RUM Data

### Session Information
```json
{
  "user_id": "demo_user_1731657600000",
  "session_duration": "45s",
  "page_views": 1,
  "actions": 3,
  "environment": "production",
  "deployment": "k3s",
  "region": "aws-us-east-1"
}
```

### Custom Actions
```json
{
  "action": "get_recommendations_start",
  "timestamp": "2025-11-15T10:30:00Z",
  "user_context": "laptop for work",
  "user_id": "demo_user_1731657600000"
}
```

### Performance Metrics
- **Page Load Time**: Time to interactive
- **API Response Time**: Recommendation service latency
- **Resource Loading**: CSS, JS, images
- **Core Web Vitals**:
  - LCP (Largest Contentful Paint)
  - FID (First Input Delay)
  - CLS (Cumulative Layout Shift)

## Troubleshooting

### ❌ RUM SDK Not Loading

**Check**:
1. Browser console for errors
2. Network tab for failed CDN requests
3. Ad blockers or privacy extensions (may block RUM)

**Fix**:
- Disable ad blockers for this domain
- Check firewall/network settings
- Verify CDN is accessible: `https://cdn.coralogix.com/rum/latest/coralogix-rum.min.js`

### ❌ No Console Messages

**Check**:
1. `CX_RUM_PUBLIC_KEY` environment variable in pod
2. Frontend pod logs

**Fix**:
```bash
# Check if key is set
kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.CX_RUM_API_KEY}' | base64 -d

# Check frontend logs
kubectl logs -n dataprime-demo deployment/frontend
```

### ❌ No Data in Coralogix

**Check**:
1. Application name matches: `ecom_reccomendation`
2. Domain matches: `EU2`
3. Public key is correct
4. Wait 2-3 minutes for ingestion

**Fix**:
- Verify configuration in browser console:
  ```javascript
  // Check if RUM is initialized
  console.log(window.CoralogixRum);
  ```
- Check browser Network tab for failed beacon requests
- Verify RUM subscription is active in Coralogix account

### ❌ Session Replay Not Working

**Check**:
1. `sessionReplayEnabled: true` in initialization
2. Browser compatibility (Chrome, Firefox, Safari, Edge)
3. Session duration (must be > 5 seconds)

**Fix**:
- Ensure you interact with the page for at least 10 seconds
- Refresh and try again
- Check Coralogix documentation for browser requirements

## Advanced Verification

### 1. Check RUM SDK Configuration

Open browser console and run:
```javascript
// Check if RUM is loaded
console.log('RUM SDK loaded:', typeof window.CoralogixRum !== 'undefined');

// Check configuration (may not be exposed depending on SDK version)
console.log('RUM initialized:', window.CoralogixRum);
```

### 2. Manually Trigger Custom Action

```javascript
// Test custom action tracking
window.CoralogixRum.addAction('test_action', {
  test_key: 'test_value',
  timestamp: new Date().toISOString()
});

// This should appear in Coralogix RUM dashboard under Actions
```

### 3. Simulate Error

```javascript
// Test error tracking
throw new Error('Test RUM error tracking');

// This should appear in Coralogix RUM dashboard under Errors
```

### 4. Check Network Beacon

In Network tab, find a RUM beacon request and inspect:
- **Request URL**: Should contain `rum-ingress.eu2.coralogix.com`
- **Request Payload**: JSON with session data
- **Response**: 200 OK or 204 No Content

## Success Criteria

✅ **RUM SDK Loaded**: Console message appears  
✅ **Session Tracked**: Session appears in Coralogix within 2 minutes  
✅ **Actions Tracked**: Custom actions visible in dashboard  
✅ **Performance Metrics**: Page load and API times captured  
✅ **Session Replay**: Visual playback available  
✅ **Error Tracking**: JavaScript errors captured  
✅ **User Context**: User ID and metadata visible  

## Next Steps After Verification

1. **Set Up Alerts**:
   - Create alerts for high error rates
   - Monitor slow page loads
   - Track user drop-off points

2. **Analyze User Behavior**:
   - Most common search queries
   - User flow through the application
   - Conversion funnels

3. **Optimize Performance**:
   - Identify slow API calls
   - Optimize resource loading
   - Improve Core Web Vitals scores

4. **Correlate with Backend**:
   - Link RUM sessions to APM traces
   - Track full user journeys
   - Identify backend bottlenecks affecting frontend

## Support

If you encounter issues:
1. Check this verification guide
2. Review `RUM-INTEGRATION.md` for detailed configuration
3. Check Coralogix documentation: https://coralogix.com/docs/user-guides/rum/
4. Contact Coralogix support with:
   - Application name: `ecom_reccomendation`
   - Public key (first 10 chars): `cxtp_lYys5...`
   - Browser console errors
   - Network tab screenshots

---

**Current Deployment**: http://54.235.171.176:30020  
**RUM Application**: ecom_reccomendation  
**RUM Domain**: EU2  
**Version**: 1.0.0  

