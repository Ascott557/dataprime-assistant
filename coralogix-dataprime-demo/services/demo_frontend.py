#!/usr/bin/env python3
"""
Demo Frontend for re:Invent 2025 Database Monitoring Demo

Simple Flask app that serves a demo page with buttons to trigger
database operations through the proper trace chain.
"""

import os
import sys
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry
ensure_telemetry_initialized()

from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)

app = Flask(__name__)
CORS(app)

# Service URLs - these will be passed to the browser, so they need to be external
# Get the external host from environment or use localhost
EXTERNAL_HOST = os.getenv("EXTERNAL_HOST", "localhost")
INVENTORY_SERVICE_URL = f"http://{EXTERNAL_HOST}:30015"
ORDER_SERVICE_URL = f"http://{EXTERNAL_HOST}:30016"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>re:Invent 2025 - Database Monitoring Demo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 800px;
            width: 100%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 32px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        
        .demo-section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }
        
        .demo-section h2 {
            color: #444;
            margin-bottom: 15px;
            font-size: 20px;
            display: flex;
            align-items: center;
        }
        
        .demo-section h2::before {
            content: "🔧";
            margin-right: 10px;
            font-size: 24px;
        }
        
        .button-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            box-shadow: none;
        }
        
        .result-box {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .result-box pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #333;
        }
        
        .trace-id {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        
        .trace-id strong {
            color: #d39e00;
        }
        
        .loading {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
            margin-left: 8px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .status {
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-top: 10px;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-top: 20px;
            border-radius: 4px;
        }
        
        .info-box strong {
            color: #1976D2;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 re:Invent 2025 Database Demo</h1>
        <p class="subtitle">Coralogix Database APM - Connection Pool Monitoring</p>
        
        <div class="demo-section">
            <h2>Inventory Operations</h2>
            <div class="button-grid">
                <button onclick="checkStock(1)">Check Stock (Product 1)</button>
                <button onclick="checkStock(2)">Check Stock (Product 2)</button>
                <button onclick="reserveStock()">Reserve Stock</button>
            </div>
        </div>
        
        <div class="demo-section">
            <h2>Order Operations</h2>
            <div class="button-grid">
                <button onclick="getPopularProducts()">Get Popular Products</button>
                <button onclick="createOrder()">Create New Order</button>
            </div>
        </div>
        
        <div class="demo-section">
            <h2>Demo Scenarios</h2>
            <div class="button-grid">
                <button onclick="generateLoad()">Generate Normal Load</button>
                <button onclick="enableSlowQueries()">Enable Slow Queries</button>
                <button onclick="resetDemo()">Reset Demo</button>
            </div>
        </div>
        
        <div class="result-box" id="result">
            <p style="color: #999;">Click a button above to trigger a database operation...</p>
        </div>
        
        <div class="info-box">
            <strong>📊 Coralogix:</strong> Watch Database APM for:
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li>Connection pool utilization</li>
                <li>Query latency</li>
                <li>All calling services (inventory, order)</li>
            </ul>
        </div>
    </div>
    
    <script>
        async function makeRequest(url, options = {}) {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML += ' <span class="loading"></span>';
            
            const result = document.getElementById('result');
            result.innerHTML = '<p style="color: #999;">Loading...</p>';
            
            try {
                const response = await fetch(url, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });
                
                const data = await response.json();
                
                let html = '<div class="status ' + (response.ok ? 'success' : 'error') + '">';
                html += response.ok ? '✅ Success' : '❌ Error';
                html += '</div>';
                
                html += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                
                if (data.trace_id) {
                    html += '<div class="trace-id">';
                    html += '<strong>🔍 Trace ID:</strong><br>';
                    html += data.trace_id;
                    html += '<br><br><em>Search for this trace ID in Coralogix</em>';
                    html += '</div>';
                }
                
                result.innerHTML = html;
            } catch (error) {
                result.innerHTML = '<div class="status error">❌ Error</div><pre>' + error.message + '</pre>';
            } finally {
                btn.disabled = false;
                btn.innerHTML = btn.innerHTML.replace(/ <span class="loading"><\/span>/, '');
            }
        }
        
        async function checkStock(productId) {
            await makeRequest('{{ inventory_url }}/inventory/check/' + productId);
        }
        
        async function reserveStock() {
            await makeRequest('{{ inventory_url }}/inventory/reserve', {
                method: 'POST',
                body: JSON.stringify({
                    product_id: 1,
                    quantity: 1
                })
            });
        }
        
        async function getPopularProducts() {
            await makeRequest('{{ order_url }}/orders/popular-products?limit=5');
        }
        
        async function createOrder() {
            await makeRequest('{{ order_url }}/orders/create', {
                method: 'POST',
                body: JSON.stringify({
                    user_id: 'demo_user_' + Date.now(),
                    product_id: Math.floor(Math.random() * 3) + 1,
                    quantity: 1
                })
            });
        }
        
        async function generateLoad() {
            const result = document.getElementById('result');
            result.innerHTML = '<p>🚀 Generating load (5 requests)...</p>';
            
            for (let i = 0; i < 5; i++) {
                await checkStock(1);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            result.innerHTML += '<p style="color: green;">✅ Load generation complete! Check Coralogix Database APM.</p>';
        }
        
        async function enableSlowQueries() {
            await makeRequest('{{ inventory_url }}/demo/enable-slow-queries', {
                method: 'POST',
                body: JSON.stringify({ delay_ms: 2900 })
            });
        }
        
        async function resetDemo() {
            await makeRequest('{{ inventory_url }}/demo/reset', {
                method: 'POST'
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the demo frontend."""
    # Get service URLs from environment
    inventory_url = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:30015")
    order_url = os.getenv("ORDER_SERVICE_URL", "http://localhost:30016")
    
    return render_template_string(
        HTML_TEMPLATE,
        inventory_url=inventory_url,
        order_url=order_url
    )

@app.route('/health')
def health():
    """Health check endpoint."""
    with tracer.start_as_current_span("demo_frontend.health") as span:
        span.set_attribute("service.name", "demo_frontend")
        return jsonify({
            "status": "healthy",
            "service": "demo_frontend",
            "inventory_service": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:30015"),
            "order_service": os.getenv("ORDER_SERVICE_URL", "http://localhost:30016")
        })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 30017))
    print(f"🎯 Demo Frontend starting on port {port}...")
    print(f"   Inventory Service: {os.getenv('INVENTORY_SERVICE_URL', 'http://localhost:30015')}")
    print(f"   Order Service: {os.getenv('ORDER_SERVICE_URL', 'http://localhost:30016')}")
    print(f"   Open: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

