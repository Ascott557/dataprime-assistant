# Coralogix RUM Integration

## Overview

The e-commerce recommendation application now includes full Coralogix Real User Monitoring (RUM) integration to track:
- User sessions and page views
- User interactions and actions
- Network requests and performance metrics
- JavaScript errors with full context
- Session replay for debugging

## Configuration

### Application Settings
```json
{
  "public_key": "cxtp_lYys51KLFaJ8elL3Ym1dOEcTIMwEwR",
  "application": "ecom_reccomendation",
  "version": "1.0.0",
  "coralogixDomain": "EU2"
}
```

### Source Map Upload Key
```
cxtp_JG9Z2JVZOnUutZFCBBg9HAwrbcYaeX
```

## Implementation Details

### 1. SDK Initialization

The Coralogix RUM SDK is loaded dynamically from CDN and initialized in the frontend:

```javascript
// Load SDK from CDN
const script = document.createElement('script');
script.src = 'https://cdn.coralogix.com/rum/latest/coralogix-rum.min.js';

script.onload = function() {
    // Initialize with exact configuration
    window.CoralogixRum.init({
        public_key: 'cxtp_lYys51KLFaJ8elL3Ym1dOEcTIMwEwR',
        application: 'ecom_reccomendation',
        version: '1.0.0',
        coralogixDomain: 'EU2',
        sessionSampleRate: 100,  // Capture all sessions
        sessionReplayEnabled: true
    });
    
    // Set global labels
    window.CoralogixRum.setLabels({
        environment: 'production',
        deployment: 'k3s',
        region: 'aws-us-east-1'
    });
};
```

### 2. User Context Tracking

When users interact with the application, their context is tracked:

```javascript
const userId = 'demo_user_' + Date.now();

window.CoralogixRum.setUserContext({
    user_id: userId,
    user_metadata: {
        searchContext: userContext.substring(0, 50),
        sessionStart: new Date(sessionStartTime).toISOString()
    }
});
```

### 3. Custom Action Tracking

Key user actions are explicitly tracked:

```javascript
function trackRumAction(name, data) {
    if (window.CoralogixRum) {
        window.CoralogixRum.addAction(name, {
            timestamp: new Date().toISOString(),
            ...data
        });
    }
}

// Example usage
trackRumAction('get_recommendations_start', {
    userContext: userContext,
    userId: userId
});
```

### 4. Error Tracking

All JavaScript errors are automatically captured by the RUM SDK with full stack traces and context.

## Source Maps

### Flask Application Note

This is a Flask application with **inline JavaScript** (embedded in Python templates). Traditional JavaScript source maps are not applicable because:
- There is no JavaScript build process
- No transpilation or minification
- JavaScript code is embedded directly in HTML templates

### If You Add a Build Process

If you migrate to a JavaScript build pipeline (webpack, rollup, etc.) in the future:

1. **Install RUM CLI**:
```bash
npm install -g @coralogix/rum-cli
```

2. **Generate source maps during build**:
```bash
# Example for webpack
webpack --mode production --devtool source-map
```

3. **Upload source maps**:
```bash
coralogix-rum-cli upload-source-maps \
  -k "cxtp_JG9Z2JVZOnUutZFCBBg9HAwrbcYaeX" \
  -a "ecom_reccomendation" \
  -e "EU2" \
  -v "1.0.0" \
  -f "./dist"
```

4. **Use the provided script**:
```bash
./scripts/upload-source-maps.sh ./dist
```

## Verification

### 1. Access the Application

Open the frontend in a browser:
```
http://54.235.171.176:30020
```

### 2. Check Browser Console

Look for the RUM initialization message:
```
✅ Coralogix RUM initialized
```

### 3. Open Browser Developer Tools

**Network Tab**: You should see requests to Coralogix RUM endpoints:
```
https://rum-ingress.eu2.coralogix.com/...
```

**Console Tab**: Check for any RUM-related messages or errors.

### 4. Check Coralogix Dashboard

1. Log in to Coralogix: https://coralogix.com/
2. Navigate to **RUM** section
3. Select application: **ecom_reccomendation**
4. You should see:
   - Active sessions
   - Page views
   - User actions
   - Performance metrics
   - Session replays

### 5. Test User Actions

Perform actions in the app to generate RUM data:
1. Enter a search query (e.g., "laptop for gaming")
2. Click "Get AI Recommendations"
3. Wait for recommendations to load
4. Click product links

Each action should appear in the Coralogix RUM dashboard with:
- Action name
- Timestamp
- User context
- Performance metrics

## Features Enabled

### ✅ Session Tracking
- All user sessions are captured (100% sampling rate)
- Session duration and page views
- User flow through the application

### ✅ Performance Monitoring
- Page load times
- API request durations
- Resource loading performance
- Core Web Vitals (LCP, FID, CLS)

### ✅ User Context
- Unique user ID for each session
- Search context (what users are looking for)
- Session start time
- Custom metadata

### ✅ Error Tracking
- JavaScript errors with stack traces
- Failed network requests
- Console errors and warnings

### ✅ Session Replay
- Visual playback of user sessions
- Mouse movements and clicks
- Scroll behavior
- Form interactions

### ✅ Custom Labels
- Environment: production
- Deployment: k3s
- Region: aws-us-east-1

## Files Modified

1. **Frontend Application**:
   - `coralogix-dataprime-demo/app/ecommerce_frontend.py`
   - Updated RUM SDK initialization
   - Added user context tracking
   - Implemented custom action tracking

2. **RUM Configuration**:
   - `.coralogix/rum.config.json`
   - Stores RUM settings for source map uploads

3. **Source Map Upload Script**:
   - `scripts/upload-source-maps.sh`
   - Automated source map upload using Coralogix RUM CLI
   - Ready for future JavaScript build pipelines

4. **Kubernetes Deployment**:
   - `deployment/kubernetes/deployments/frontend.yaml`
   - Updated to use RUM API key from secrets

5. **Kubernetes Secret**:
   - `deployment/kubernetes/secret.yaml.template`
   - Added `CX_RUM_API_KEY` and `CX_RUM_SOURCE_MAP_KEY` fields

## Troubleshooting

### RUM Not Initializing

1. Check browser console for errors
2. Verify the public key is correct in secrets:
```bash
kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.CX_RUM_API_KEY}' | base64 -d
```
3. Ensure the CDN script loads successfully (check Network tab)

### No Data in Coralogix Dashboard

1. Verify the application name matches: **ecom_reccomendation**
2. Check the domain is correct: **EU2**
3. Wait a few minutes for data to appear (ingestion delay)
4. Check browser Network tab for RUM beacon requests

### Session Replay Not Working

1. Verify `sessionReplayEnabled: true` in initialization
2. Check that the RUM SDK version supports session replay
3. Ensure browser is compatible (modern browsers only)

### Source Map Upload Fails

1. Verify the source map key:
```bash
SOURCE_MAP_KEY="cxtp_JG9Z2JVZOnUutZFCBBg9HAwrbcYaeX"
```
2. Ensure the application name matches the SDK initialization
3. Check that the folder contains `.js.map` files
4. Verify version matches between SDK init and upload

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (User)                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Frontend (Flask Template)                            │  │
│  │                                                        │  │
│  │  1. Load Coralogix RUM SDK from CDN                   │  │
│  │  2. Initialize with public_key                        │  │
│  │  3. Set user context on interactions                  │  │
│  │  4. Track custom actions                              │  │
│  │  5. Automatically capture errors                      │  │
│  │  6. Record session replay                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │ HTTPS
                            ▼
          ┌─────────────────────────────────┐
          │  Coralogix RUM Ingress (EU2)    │
          │  rum-ingress.eu2.coralogix.com  │
          └─────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │    Coralogix RUM Platform       │
          │                                  │
          │  • Session Storage               │
          │  • Performance Analysis          │
          │  • Error Aggregation             │
          │  • Session Replay Storage        │
          │  • Dashboards & Alerts           │
          └─────────────────────────────────┘
```

## Next Steps

1. **Monitor Production Traffic**:
   - Watch for RUM data in Coralogix dashboard
   - Analyze user behavior patterns
   - Identify performance bottlenecks

2. **Set Up Alerts**:
   - High error rates
   - Slow page loads
   - Failed API requests
   - Unusual user behavior

3. **Optimize Performance**:
   - Use RUM data to identify slow components
   - Optimize API response times
   - Improve frontend loading speed

4. **Correlate with Backend Traces**:
   - Link RUM sessions to APM traces
   - End-to-end visibility from browser to database
   - Full user journey tracking

## Resources

- **Coralogix RUM Documentation**: https://coralogix.com/docs/user-guides/rum/
- **RUM CLI Documentation**: https://github.com/coralogix/rum-cli
- **Source Maps Guide**: https://coralogix.com/docs/user-guides/rum/sdk-features/source-maps/
- **Session Replay**: https://coralogix.com/docs/user-guides/rum/sdk-features/session-replay/

## Summary

✅ **RUM SDK Initialized**: Application name `ecom_reccomendation`, version `1.0.0`  
✅ **User Context Tracking**: Captures user IDs and metadata  
✅ **Custom Actions**: Tracks recommendation requests and interactions  
✅ **Session Replay**: Enabled for all sessions  
✅ **Error Tracking**: Automatic JavaScript error capture  
✅ **Performance Monitoring**: Core Web Vitals and resource timing  
✅ **Source Map Ready**: Script prepared for future JavaScript builds  

The RUM integration is now **fully operational** and ready to provide real-time insights into user behavior and application performance! 🎉

