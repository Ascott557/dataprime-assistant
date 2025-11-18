#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

E-commerce Recommendation System - Frontend
Web interface for product recommendations with Coralogix RUM integration.
"""

import os
import sys
from flask import Flask, render_template_string
from datetime import datetime

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize OpenTelemetry BEFORE creating Flask app
try:
    from app.shared_telemetry import ensure_telemetry_initialized
    ensure_telemetry_initialized()
    # Override service name for frontend
    os.environ.setdefault("OTEL_SERVICE_NAME", "frontend")
    os.environ.setdefault("SERVICE_NAME", "frontend")
    print("✅ Frontend telemetry initialized")
except Exception as e:
    print(f"⚠️ Frontend telemetry initialization failed: {e}")
    print("   Continuing without telemetry...")

app = Flask(__name__)

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8010")
CX_RUM_PUBLIC_KEY = os.getenv("CX_RUM_PUBLIC_KEY", "pub_your_key_here")

@app.route('/')
def index():
    """Serve the e-commerce frontend."""
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>🛍️ E-commerce Product Recommendations - Coralogix Demo</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }
        
        .container { 
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95); 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 { 
            color: #2d3748; 
            font-weight: 700;
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #718096;
            font-size: 1.1rem;
        }
        
        .section {
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #e2e8f0;
        }
        
        .section-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .form-group { 
            margin-bottom: 20px; 
        }
        
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #4a5568;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 15px;
            font-family: inherit;
            transition: all 0.3s ease;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        
        button { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 15px; 
            font-weight: 600;
            margin-right: 10px; 
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled { 
            background: #94a3b8; 
            cursor: not-allowed; 
            transform: none;
        }
        
        button.secondary {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }
        
        button.danger {
            background: linear-gradient(135deg, #f56565, #c53030);
        }
        
        .product-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        
        .product-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .product-name {
            font-size: 1.1rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 5px;
        }
        
        .product-price {
            font-size: 1.3rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .product-description {
            color: #718096;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }
        
        .recommendation-text {
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin-bottom: 20px;
            white-space: pre-wrap;
        }
        
        .loading { 
            text-align: center; 
            color: #4a5568; 
            font-weight: 500;
            padding: 40px;
        }
        
        .loading::before {
            content: '';
            display: inline-block;
            width: 30px;
            height: 30px;
            border: 3px solid #e2e8f0;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background: #48bb78; }
        .status-warning { background: #ecc94b; }
        .status-error { background: #f56565; }
        
        .feedback-stars {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }
        
        .star-button {
            background: transparent;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-right: 5px;
        }
        
        .star-button:hover {
            transform: scale(1.1);
            border-color: #667eea;
        }
        
        .star-button.selected {
            background: #667eea;
            border-color: #667eea;
        }
        
        .demo-controls {
            background: #fef5e7;
            border: 2px solid #f39c12;
            border-radius: 12px;
            padding: 20px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-info {
            background: #ebf8ff;
            border: 1px solid #90cdf4;
            color: #2c5282;
        }
        
        .alert-warning {
            background: #fffbeb;
            border: 1px solid #f6e05e;
            color: #744210;
        }
        
        .alert-success {
            background: #f0fff4;
            border: 1px solid #9ae6b4;
            color: #22543d;
        }
        
        .trace-id {
            font-family: monospace;
            background: #1a202c;
            color: #e2e8f0;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛍️ E-commerce Product Recommendations</h1>
            <p class="subtitle">AI-Powered Shopping Assistant - Coralogix Observability Demo</p>
        </header>
        
        <!-- Status Section -->
        <div class="section">
            <div class="section-title">
                <span class="status-indicator status-healthy"></span>
                System Status
            </div>
            <div id="systemStatus">
                <p>✅ All systems operational</p>
            </div>
        </div>
        
        <!-- User Preferences Section -->
        <div class="section">
            <div class="section-title">
                👤 Your Shopping Preferences
            </div>
            
            <div class="form-group">
                <label for="userContext">What are you looking for?</label>
                <textarea id="userContext" placeholder="Example: Looking for wireless headphones for work, budget $50-150, prefer noise cancelling">Looking for wireless headphones, budget $50-150</textarea>
            </div>
            
            <button onclick="getRecommendations()" id="getRecBtn">
                🤖 Get AI Recommendations
            </button>
            
            <button onclick="viewProducts()" class="secondary">
                📦 Browse Products
            </button>
        </div>
        
        <!-- Demo Controls Section -->
        <div class="section demo-controls">
            <div class="section-title">
                🎯 Demo Controls (Failure Scenarios)
            </div>
            
            <p style="margin-bottom: 15px; color: #744210;">
                <strong>⚠️ Demo Mode:</strong> Simulate infrastructure failures to observe cascading impact
            </p>
            
            <button onclick="simulateDatabaseScenario()" class="danger">
                🔥 Simulate Database Issues (Scene 9)
            </button>
            
            <button onclick="simulateSlowDatabase()" class="danger">
                🐌 Simulate Slow Database
            </button>
            
            <button onclick="simulatePoolExhaustion()" class="danger">
                🔒 Simulate Connection Pool Exhaustion
            </button>
            
            <button onclick="abandonCart()" class="secondary">
                🚪 Abandon Cart (RUM Event)
            </button>
            
            <button onclick="disableSimulations()" class="secondary">
                ✅ Reset to Normal
            </button>
        </div>
        
        <!-- Results Section -->
        <div id="resultsSection" style="display: none;">
            <div class="section">
                <div class="section-title">
                    ✨ AI Recommendations
                </div>
                
                <div id="recommendations"></div>
                
                <!-- Feedback Section -->
                <div id="feedbackSection" style="display: none;">
                    <div class="feedback-stars">
                        <span style="font-weight: 600; color: #4a5568; margin-right: 10px;">Rate this recommendation:</span>
                        <button class="star-button" onclick="submitFeedback(1)">👎</button>
                        <button class="star-button" onclick="submitFeedback(2)">😐</button>
                        <button class="star-button" onclick="submitFeedback(3)">👍</button>
                        <button class="star-button" onclick="submitFeedback(4)">😊</button>
                        <button class="star-button" onclick="submitFeedback(5)">🌟</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Coralogix RUM Integration -->
    <script>
        // Configuration
        const API_GATEWAY_URL = '{{ api_gateway_url }}';
        const CX_RUM_PUBLIC_KEY = '{{ cx_rum_public_key }}';
        
        // Session tracking
        let currentTraceId = null;
        let currentRecommendations = null;
        let sessionStartTime = Date.now();
        
        // Load Pako compression library FIRST (required for Session Replay)
        (function() {
            const pakoScript = document.createElement('script');
            pakoScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js';
            pakoScript.crossOrigin = 'anonymous';
            // Removed integrity check - was causing SRI mismatch errors
            pakoScript.onload = function() {
                console.log('✅ Pako compression library loaded for Session Replay');
                console.log('   Pako version:', window.pako ? 'Available' : 'NOT available');
            };
            pakoScript.onerror = function(error) {
                console.error('❌ Failed to load Pako library:', error);
                console.warn('⚠️ Session Replay will not work without Pako compression');
            };
            document.head.appendChild(pakoScript);
        })();
        
        // Initialize Coralogix RUM SDK from correct CDN (after Pako loads)
        (function() {
            if (CX_RUM_PUBLIC_KEY && CX_RUM_PUBLIC_KEY !== 'pub_your_key_here') {
                // Wait a moment for Pako to load
                setTimeout(function() {
                    const script = document.createElement('script');
                    // Use correct CDN URL from official docs
                    script.src = 'https://cdn.rum-ingress-coralogix.com/coralogix/browser/2.10.0/coralogix-browser-sdk.js';
                    script.crossOrigin = 'anonymous';
                    script.onload = function() {
                    try {
                        // Initialize RUM SDK with Session Replay
                        // Note: Application name must match Coralogix integration (case-sensitive)
                        window.CoralogixRum.init({
                            public_key: CX_RUM_PUBLIC_KEY,
                            application: 'ecomm_reccomendation',  // Fixed: double 'm' to match integration
                            version: '1.0.0',
                            coralogixDomain: 'EU2',
                            sessionSampleRate: 100,
                            
                            // ✅ Session Replay Configuration (correct parameter)
                            sessionRecordingConfig: {
                                enable: true,
                                autoStartSessionRecording: true,
                                recordConsoleEvents: true,
                                sessionRecordingSampleRate: 100,
                                
                                // Privacy settings
                                blockClass: 'rr-block',
                                ignoreClass: 'rr-ignore',
                                maskTextClass: 'rr-mask',
                                maskAllInputs: false,
                                maskInputOptions: { 
                                    password: true,
                                    email: false
                                },
                                
                                // Performance optimization
                                maxMutations: 5000,
                                
                                // Sampling configuration
                                sampling: {
                                    mousemove: true,
                                    mouseInteraction: true,
                                    scroll: 150,
                                    media: 800,
                                    input: 'last'
                                }
                            }
                        });
                        
                        // Set initial labels
                        window.CoralogixRum.setLabels({
                            environment: 'production',
                            deployment: 'k3s',
                            region: 'aws-us-east-1'
                        });
                        
                        console.log('✅ Coralogix RUM initialized successfully!');
                        console.log('   Application: ecomm_reccomendation (FIXED: double m)');
                        console.log('   SDK Version: 2.10.0');
                        console.log('   Session Replay: ENABLED with Pako compression');
                        console.log('   Session ID:', window.CoralogixRum.getSessionId ? window.CoralogixRum.getSessionId() : 'N/A');
                        console.log('   Pako available:', typeof window.pako !== 'undefined');
                        updateSystemStatus('RUM + Session Replay + Pako active', 'healthy');
                    } catch (error) {
                        console.warn('⚠️ RUM initialization error:', error);
                        updateSystemStatus('RUM init failed', 'warning');
                    }
                };
                script.onerror = function(error) {
                    console.warn('⚠️ Failed to load Coralogix RUM SDK');
                    console.log('   Backend telemetry still working');
                    updateSystemStatus('Backend telemetry only', 'healthy');
                };
                document.head.appendChild(script);
                }, 500);  // Wait 500ms for Pako to load
            } else {
                console.warn('⚠️ CX_RUM_PUBLIC_KEY not configured');
            }
        })();
        
        // Track RUM action (with error handling)
        function trackRumAction(name, data) {
            try {
                if (window.CoralogixRum && typeof window.CoralogixRum.addAction === 'function') {
                    window.CoralogixRum.addAction(name, {
                        ...data,
                        timestamp: new Date().toISOString()
                    });
                    console.log('📊 RUM Action:', name, data);
                } else {
                    // SDK loaded but addAction not available - just log it
                    console.debug('RUM action (method unavailable):', name, data);
                }
            } catch (error) {
                // Silently fail - don't break the application
                console.debug('RUM tracking skipped:', error.message);
            }
        }
        
        // Update system status
        function updateSystemStatus(message, status = 'healthy') {
            const statusDiv = document.getElementById('systemStatus');
            const icons = {
                healthy: '✅',
                warning: '⚠️',
                error: '❌'
            };
            statusDiv.innerHTML = `<p>${icons[status]} ${message}</p>`;
        }
        
        // Get AI recommendations
        async function getRecommendations() {
            const userContext = document.getElementById('userContext').value.trim();
            
            if (!userContext) {
                alert("Please enter what you're looking for!");
                return;
            }
            
            const btn = document.getElementById('getRecBtn');
            btn.disabled = true;
            btn.textContent = '🤖 Getting recommendations...';
            
            const resultsSection = document.getElementById('resultsSection');
            const recommendations = document.getElementById('recommendations');
            
            resultsSection.style.display = 'block';
            recommendations.innerHTML = '<div class="loading">AI is analyzing your preferences...</div>';
            
            // Generate user ID for this session
            const userId = 'demo_user_' + Date.now();
            
            // Set user context in RUM
            if (window.CoralogixRum && window.CoralogixRum.setUserContext) {
                window.CoralogixRum.setUserContext({
                    user_id: userId,
                    user_metadata: {
                        searchContext: userContext.substring(0, 50),
                        sessionStart: new Date(sessionStartTime).toISOString()
                    }
                });
            }
            
            // Track RUM action
            trackRumAction('get_recommendations_start', {
                userContext: userContext,
                userId: userId
            });
            
            try {
                const response = await fetch(`${API_GATEWAY_URL}/api/recommendations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: 'demo_user_' + Date.now(),
                        user_context: userContext
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentTraceId = data.trace_id;
                    currentRecommendations = data.recommendations;
                    
                    // Track RUM action
                    trackRumAction('get_recommendations_success', {
                        traceId: data.trace_id,
                        toolCallSuccess: data.tool_call_success,
                        fallbackUsed: data.ai_fallback_used
                    });
                    
                    // Display recommendations
                    let html = '';
                    
                    // Show warning if fallback was used
                    if (data.ai_fallback_used) {
                        html += `
                            <div class="alert alert-warning">
                                <strong>⚠️ Limited Inventory Access:</strong> Unable to access real-time product database. 
                                Recommendations may not reflect current inventory. 
                                <br><small>Trace ID: <span class="trace-id">${data.trace_id}</span></small>
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="alert alert-success">
                                <strong>✅ Success:</strong> Retrieved real-time product data from catalog.
                                <br><small>Trace ID: <span class="trace-id">${data.trace_id}</span></small>
                            </div>
                        `;
                    }
                    
                    // Display recommendations text
                    html += `<div class="recommendation-text">${data.recommendations}</div>`;
                    
                    recommendations.innerHTML = html;
                    document.getElementById('feedbackSection').style.display = 'block';
                    
                } else {
                    recommendations.innerHTML = `
                        <div class="alert alert-error">
                            <strong>❌ Error:</strong> ${data.error || 'Unknown error'}
                        </div>
                    `;
                }
                
            } catch (error) {
                recommendations.innerHTML = `
                    <div class="alert alert-error">
                        <strong>❌ Connection Error:</strong> ${error.message}
                        <br><small>Make sure the backend services are running.</small>
                    </div>
                `;
                
                trackRumAction('get_recommendations_error', {
                    error: error.message
                });
            } finally {
                btn.disabled = false;
                btn.textContent = '🤖 Get AI Recommendations';
            }
        }
        
        // View products (direct catalog access)
        async function viewProducts() {
            alert('Direct product browsing - Coming soon in this demo!');
        }
        
        // Submit feedback
        async function submitFeedback(rating) {
            if (!currentTraceId) {
                alert('No recommendation to rate!');
                return;
            }
            
            trackRumAction('submit_feedback', {
                rating: rating,
                traceId: currentTraceId
            });
            
            try {
                const response = await fetch(`${API_GATEWAY_URL}/api/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rating: rating,
                        trace_id: currentTraceId,
                        comment: `Frontend rating: ${rating}/5`
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Highlight selected rating
                    document.querySelectorAll('.star-button').forEach((btn, index) => {
                        btn.classList.toggle('selected', index === rating - 1);
                    });
                    
                    alert(`✅ Thank you! Your ${rating}-star rating has been recorded.`);
                }
            } catch (error) {
                alert(`❌ Error submitting feedback: ${error.message}`);
            }
        }
        
        // Simulate database scenario (Scene 9)
        async function simulateDatabaseScenario() {
            if (!confirm(`Inject Scene 9: Database APM telemetry?

This will send 43 pre-recorded database spans to Coralogix:
- 3 calling services (product, order, inventory)
- P95: 2800ms, P99: 3200ms
- Pool: 95% utilized
- Failure rate: ~8%

Check results in: APM → Database Monitoring → productcatalog`)) {
                return;
            }
            
            trackRumAction('inject_database_telemetry', {});
            
            updateSystemStatus('Injecting database telemetry...', 'warning');
            
            try {
                const response = await fetch(`${API_GATEWAY_URL}/api/demo/inject-telemetry`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    updateSystemStatus(
                        `Telemetry injected: ${data.spans_created} spans from ${data.services.length} services`,
                        'warning'
                    );
                    alert(`✅ Database telemetry injected!

Check Coralogix (wait 10-15 seconds):
APM → Database Monitoring → productcatalog

You should see:
- 3 calling services
- Query Duration P95: ~2800ms
- 43 spans
- ~8% failure rate`);
                } else {
                    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
                    alert(`❌ Error: ${errorData.error || response.statusText}`);
                }
            } catch (error) {
                updateSystemStatus(`Error: ${error.message}`, 'error');
                alert(`❌ Connection Error: ${error.message}`);
            }
        }
        
        // Simulate slow database
        async function simulateSlowDatabase() {
            if (!confirm('Simulate slow database queries (2800ms)? This will cause AI tool calls to timeout.')) {
                return;
            }
            
            trackRumAction('simulate_slow_database', {});
            
            try {
                // Call demo endpoint via HTTPS proxy (port 30444 forwards /demo/* to product-service)
                const demoServiceUrl = window.location.protocol + '//' + window.location.hostname + ':30444';
                const response = await fetch(`${demoServiceUrl}/demo/enable-slow-queries`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ delay_ms: 2800 })
                });
                
                if (response.ok) {
                    updateSystemStatus('Slow database simulation enabled (2800ms)', 'warning');
                    alert('🐌 Slow database simulation enabled. Next recommendation will timeout and use AI fallback.');
                } else {
                    alert(`Error: ${response.status} ${response.statusText}`);
                }
            } catch (error) {
                console.error('Slow query error:', error);
                alert(`Error: ${error.message}`);
            }
        }
        
        // Simulate pool exhaustion
        async function simulatePoolExhaustion() {
            if (!confirm('Simulate connection pool exhaustion? This will hold 95+ database connections.')) {
                return;
            }
            
            trackRumAction('simulate_pool_exhaustion', {});
            
            try {
                // Call demo endpoint via HTTPS proxy (port 30444 forwards /demo/* to product-service)
                const demoServiceUrl = window.location.protocol + '//' + window.location.hostname + ':30444';
                const response = await fetch(`${demoServiceUrl}/demo/enable-pool-exhaustion`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    updateSystemStatus('Connection pool exhausted (95+ connections held)', 'error');
                    alert('🔒 Connection pool exhaustion simulated. Subsequent requests will fail.');
                } else {
                    alert(`Error: ${response.status} ${response.statusText}`);
                }
            } catch (error) {
                console.error('Pool exhaustion error:', error);
                alert(`Error: ${error.message}`);
            }
        }
        
        // Abandon cart
        function abandonCart() {
            trackRumAction('cart_abandonment', {
                reason: 'demo_button',
                sessionDuration: Date.now() - sessionStartTime
            });
            
            alert('🚪 Cart abandonment event sent to RUM!');
        }
        
        // Disable simulations
        async function disableSimulations() {
            try {
                await fetch(`${API_GATEWAY_URL.replace(':8010', ':8014')}/demo/reset`, {
                    method: 'POST'
                });
                
                updateSystemStatus('All systems operational', 'healthy');
                alert('✅ Simulations disabled, system reset to normal.');
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    </script>
</body>
</html>
    """
    
    return render_template_string(
        html_template,
        api_gateway_url=API_GATEWAY_URL,
        cx_rum_public_key=CX_RUM_PUBLIC_KEY
    )


if __name__ == '__main__':
    print("🛍️ E-commerce Frontend starting on port 8020...")
    print(f"   API Gateway: {API_GATEWAY_URL}")
    print(f"   RUM Configured: {CX_RUM_PUBLIC_KEY != 'pub_your_key_here'}")
    app.run(host='0.0.0.0', port=8020, debug=False)

