#!/usr/bin/env python3
"""
🌐 Distributed Frontend - Simple web interface for the distributed system
Serves a lightweight frontend that calls the API Gateway.
"""

import os
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the distributed system frontend."""
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Distributed DataPrime Assistant</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    
    <!-- Simplified approach - no external CDN dependencies -->
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            line-height: 1.6;
        }
        .container { 
            background: rgba(255, 255, 255, 0.95); 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        h1 { 
            color: #2d3748; 
            text-align: center; 
            margin-bottom: 30px; 
            font-weight: 700;
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status { 
            padding: 20px; 
            border-radius: 12px; 
            margin-bottom: 25px; 
            font-weight: 500;
            border-left: 4px solid #28a745;
            background: linear-gradient(135deg, #d4edda, #c3e6cb); 
            color: #155724; 
        }
        .form-group { margin-bottom: 25px; }
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #2d3748;
            font-size: 1.1rem;
        }
        textarea { 
            width: 100%; 
            padding: 14px 16px; 
            border: 2px solid #e2e8f0; 
            border-radius: 10px; 
            box-sizing: border-box; 
            font-size: 16px;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.9);
            font-family: inherit;
            resize: vertical;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        button { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; 
            padding: 14px 28px; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600;
            margin-right: 12px; 
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
            box-shadow: none;
        }
        .result { 
            margin-top: 25px; 
            padding: 20px; 
            background: rgba(248, 250, 252, 0.9); 
            border: 1px solid #e2e8f0; 
            border-radius: 12px;
        }
        .query { 
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace; 
            background: #1a202c; 
            color: #e2e8f0; 
            padding: 16px; 
            border-radius: 8px; 
            margin: 15px 0; 
            font-size: 14px;
            line-height: 1.5;
            overflow-x: auto;
        }
        .loading { 
            text-align: center; 
            color: #4a5568; 
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .loading::before {
            content: '';
            width: 20px;
            height: 20px;
            border: 2px solid #e2e8f0;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .service-info {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-size: 14px;
        }
        .service-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .service-item {
            background: rgba(255, 255, 255, 0.5);
            padding: 8px 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
        }
        .feedback-container {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .feedback-button {
            background: transparent;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.3s ease;
        }
        .feedback-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .feedback-button.selected {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Distributed DataPrime Assistant</h1>
        
        <div class="status">
            ✅ <strong>Enterprise Distributed System Active</strong><br>
            This frontend connects to the API Gateway which orchestrates 6 microservices with proper distributed tracing.
        </div>
        
        <div class="service-info">
            <strong>🏗️ Architecture:</strong> API Gateway → Query Service → Validation Service → Queue Service → Processing Service → Storage Service
            <div class="service-list">
                <div class="service-item">🌐 API Gateway (5000)</div>
                <div class="service-item">🧠 Query Service (5001)</div>
                <div class="service-item">✅ Validation Service (5002)</div>
                <div class="service-item">📬 Queue Service (5003)</div>
                <div class="service-item">⚙️ Processing Service (5004)</div>
                <div class="service-item">💾 Storage Service (5005)</div>
            </div>
        </div>
        
        <form id="queryForm">
            <div class="form-group">
                <label for="userInput">Enter your observability question:</label>
                <textarea id="userInput" rows="3" placeholder="Try: 'Show me errors from last hour grouped by service' or 'Find slow API calls with high response times'"></textarea>
            </div>
            <button type="submit">🔍 Generate DataPrime Query</button>
            <button type="button" onclick="testSystemHealth()">🏥 Test System Health</button>
            <button type="button" onclick="getSystemStats()">📊 System Stats</button>
        </form>
        
        <div id="result" style="display: none;"></div>
        
        <div style="margin-top: 30px; font-size: 12px; color: #666; text-align: center;">
            Distributed DataPrime Assistant | Enterprise Architecture Demo<br>
            <span style="font-size: 10px; opacity: 0.7;">🔍 Check Coralogix for single root span traces across all 8 services</span><br>
            <span style="font-size: 10px; opacity: 0.7;">💡 Demo shortcuts: Ctrl+S (toggle mode), Ctrl+D (slow database demo), Ctrl+B (slow database)</span>
        </div>
    </div>

    <!-- Simplified Session Management without External CDN -->
    <script>
        // Global variables
        window.API_GATEWAY_URL = 'http://localhost:8010';
        window.currentQuery = null;
        window.userSessionSpan = null;
        window.userSessionContext = null;
        window.sessionTraceId = null;
        window.sessionSpanId = null;
        window.currentTraceId = null;
        window.sessionStartTime = null;
        window.currentMode = 'enterprise'; // Track current demo mode
    </script>
    
    <script>
        // Non-module script for main functionality

        // Generate W3C trace ID
        function generateTraceId() {
            return Array.from({length: 32}, () => Math.floor(Math.random() * 16).toString(16)).join('');
        }

        // Generate W3C span ID
        function generateSpanId() {
            return Array.from({length: 16}, () => Math.floor(Math.random() * 16).toString(16)).join('');
        }

        // Initialize user journey with persistent session management
        function initializeUserJourney() {
            if (!window.sessionTraceId) {
                // Create persistent session identifiers
                window.sessionTraceId = generateTraceId();
                window.sessionSpanId = generateSpanId();
                window.sessionStartTime = new Date().toISOString();
                
                console.log('🌟 Created user session root span:', window.sessionTraceId);
                console.log('🔗 Root span ID:', window.sessionSpanId);
                console.log('🕐 Session start time:', window.sessionStartTime);
                
                // Create a session metadata object that backend can use
                window.sessionMetadata = {
                    sessionId: window.sessionTraceId,
                    rootSpanId: window.sessionSpanId,
                    startTime: window.sessionStartTime,
                    userAgent: navigator.userAgent,
                    sessionType: 'distributed_frontend'
                };
                
                // Log session end when page unloads
                window.addEventListener('beforeunload', () => {
                    const sessionDuration = Date.now() - new Date(window.sessionStartTime).getTime();
                    console.log('🏁 Ending user session - Duration:', sessionDuration + 'ms');
                });
            }
        }
        
        // Track operation span IDs for sequential parent-child chaining
        let lastOperationSpanId = null;  // Store span ID from previous operation
        let operationSequence = 0;       // Track operation order

        // Create trace headers with sequential parent-child relationships
        function createTraceHeaders(operationType = 'default') {
            initializeUserJourney();
            operationSequence++;
            
            let parentSpanId;
            
            switch(operationType) {
                case 'query':
                    // First operation - child of session root
                    parentSpanId = window.sessionSpanId;
                    console.log(`🔗 Query (op ${operationSequence}): Parent = session root (${parentSpanId})`);
                    break;
                    
                case 'feedback':
                    // Subsequent operation - child of previous operation (query)
                    parentSpanId = lastOperationSpanId || window.sessionSpanId;
                    console.log(`🔗 Feedback (op ${operationSequence}): Parent = ${lastOperationSpanId ? 'previous operation' : 'session root'} (${parentSpanId})`);
                    break;
                    
                default:
                    // Default to session for other operations
                    parentSpanId = window.sessionSpanId;
                    console.log(`🔗 ${operationType} (op ${operationSequence}): Parent = session root (${parentSpanId})`);
            }
            
            window.currentTraceId = window.sessionTraceId;
            
            const headers = {
                'traceparent': `00-${window.sessionTraceId}-${parentSpanId}-01`,
                'tracestate': `parent=${window.sessionSpanId}`,  // Root reference
                'Content-Type': 'application/json'
            };
            
            console.log(`📤 ${operationType}: Sending request with parent ${parentSpanId}`);
            console.log('🚀 Trace headers:', headers.traceparent);
            
            return headers;
        }

        // Store span ID for chaining subsequent operations
        function storeOperationSpanId(spanId, operationType) {
            lastOperationSpanId = spanId;
            console.log(`📝 Stored ${operationType} span for chaining: ${spanId}`);
        }

        // Initialize user journey when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initializeUserJourney();
            console.log('🎯 User journey initialized for session');
        });

        // Handle form submission
        document.getElementById('queryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userInput = document.getElementById('userInput').value.trim();
            if (!userInput) {
                alert('Please enter a question!');
                return;
            }
            
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">Generating query through distributed system...</div>';
            
            try {
                const headers = createTraceHeaders('query'); // Specify query operation type
                
                const response = await fetch(`${API_GATEWAY_URL}/api/generate-query`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ user_input: userInput })
                });
                
                const data = await response.json();
                
                // Verify trace correlation and store span for chaining
                if (data.trace_id) {
                    console.log('📊 Query response trace ID:', data.trace_id);
                    console.log('📊 Query response trace type:', data.trace_type);
                    console.log('📊 Is root span:', data.is_root_span);
                }
                
                if (data.success) {
                    // Store query operation span ID for chaining feedback
                    if (data.span_id) {
                        storeOperationSpanId(data.span_id, 'query');
                    } else {
                        // Fallback: generate span ID for chaining
                        storeOperationSpanId(generateSpanId(), 'query');
                    }
                    
                    currentQuery = data.query;
                    displayResult(data, userInput);
                } else {
                    resultDiv.innerHTML = `<div style="color: #e53e3e; padding: 15px; background: #fed7d7; border-radius: 8px;">
                        <strong>❌ Error:</strong> ${data.error || 'Unknown error occurred'}
                    </div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div style="color: #e53e3e; padding: 15px; background: #fed7d7; border-radius: 8px;">
                    <strong>❌ Connection Error:</strong> ${error.message}<br>
                    <small>Make sure the distributed system is running: ./start_distributed_system.sh</small>
                </div>`;
            }
        });

        function displayResult(data, userInput) {
            const resultDiv = document.getElementById('result');
            
            const servicesInfo = data.services_called ? 
                `<div class="service-info">
                    <strong>🔗 Services Called:</strong> ${data.services_called.join(' → ')}
                    <br><strong>⏱️ Processing Time:</strong> ${data.processing_time_ms || 'N/A'}ms
                    <br><strong>🔍 Trace ID:</strong> <code>${currentTraceId || 'N/A'}</code>
                </div>` : '';
            
            resultDiv.innerHTML = `
                <div class="result">
                    <h3>✅ Query Generated Successfully</h3>
                    <p><strong>Your question:</strong> "${userInput}"</p>
                    <p><strong>Detected intent:</strong> ${data.intent} (confidence: ${(data.intent_confidence * 100).toFixed(1)}%)</p>
                    
                    ${servicesInfo}
                    
                    <div class="query">${data.query}</div>
                    
                    <div style="margin-top: 15px;">
                        <strong>🔍 Validation Results:</strong><br>
                        Status: ${data.validation.is_valid ? '✅ Valid' : '❌ Invalid'}<br>
                        Syntax Score: ${(data.validation.syntax_score * 100).toFixed(1)}%<br>
                        ${data.validation.warnings && data.validation.warnings.length > 0 ? 
                            `Warnings: ${data.validation.warnings.join(', ')}` : ''}
                    </div>
                    
                    ${createFeedbackSection()}
                </div>
            `;
        }

        function createFeedbackSection() {
            return `
                <div class="feedback-container">
                    <span style="font-weight: 600; color: #4a5568;">Rate this query:</span>
                    <button class="feedback-button" onclick="submitFeedback(1)">👎</button>
                    <button class="feedback-button" onclick="submitFeedback(2)">😐</button>
                    <button class="feedback-button" onclick="submitFeedback(3)">👍</button>
                    <button class="feedback-button" onclick="submitFeedback(4)">😊</button>
                    <button class="feedback-button" onclick="submitFeedback(5)">🌟</button>
                </div>
            `;
        }

        async function submitFeedback(rating) {
            if (!currentQuery) {
                alert('No query to rate!');
                return;
            }
            
            try {
                const headers = createTraceHeaders('feedback'); // Specify feedback operation type
                
                const response = await fetch(`${API_GATEWAY_URL}/api/feedback`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        user_input: document.getElementById('userInput').value,
                        generated_query: currentQuery,
                        rating: rating,
                        comment: `Frontend rating: ${rating}/5`,
                        metadata: { source: 'distributed_frontend', trace_id: currentTraceId }
                    })
                });
                
                const data = await response.json();
                
                // Verify trace correlation and store span for potential chaining
                if (data.trace_id) {
                    console.log('📊 Feedback response trace ID:', data.trace_id);
                    console.log('📊 Feedback response trace type:', data.trace_type);
                    console.log('📊 Should be child:', data.should_be_child);
                    console.log('📊 Is root span:', data.is_root_span);
                }
                
                if (data.success) {
                    // Store feedback operation span ID for potential future chaining
                    if (data.span_id) {
                        storeOperationSpanId(data.span_id, 'feedback');
                    }
                    
                    // Highlight selected rating
                    document.querySelectorAll('.feedback-button').forEach((btn, index) => {
                        btn.classList.toggle('selected', index + 1 === rating);
                    });
                    
                    console.log(`✅ Feedback connected to trace: ${data.trace_id}`);
                    alert(`✅ Feedback submitted and connected to query! (Rating: ${rating}/5)`);
                } else {
                    alert('❌ Failed to submit feedback');
                }
            } catch (error) {
                alert(`❌ Error submitting feedback: ${error.message}`);
            }
        }

        async function testSystemHealth() {
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">Testing system health...</div>';
            
            try {
                const headers = createTraceHeaders('health'); // Specify health operation type
                const response = await fetch(`${API_GATEWAY_URL}/api/health`, {
                    method: 'GET',
                    headers: headers
                });
                const data = await response.json();
                
                let healthHtml = `
                    <div class="result">
                        <h3>🏥 System Health Status</h3>
                        <p><strong>API Gateway:</strong> ${data.status}</p>
                        <p><strong>Uptime:</strong> ${data.uptime}</p>
                        
                        <h4>Downstream Services:</h4>
                `;
                
                if (data.downstream_services) {
                    for (const [service, info] of Object.entries(data.downstream_services)) {
                        const status = info.status === 'healthy' ? '✅' : '❌';
                        const responseTime = info.response_time ? ` (${(info.response_time * 1000).toFixed(1)}ms)` : '';
                        healthHtml += `<p><strong>${service}:</strong> ${status} ${info.status}${responseTime}</p>`;
                    }
                }
                
                healthHtml += '</div>';
                resultDiv.innerHTML = healthHtml;
                
            } catch (error) {
                resultDiv.innerHTML = `<div style="color: #e53e3e; padding: 15px; background: #fed7d7; border-radius: 8px;">
                    <strong>❌ Health Check Failed:</strong> ${error.message}
                </div>`;
            }
        }

        async function getSystemStats() {
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">Retrieving system statistics...</div>';
            
            try {
                const headers = createTraceHeaders('stats'); // Specify stats operation type
                const response = await fetch(`${API_GATEWAY_URL}/api/stats`, {
                    method: 'GET', 
                    headers: headers
                });
                const data = await response.json();
                
                let statsHtml = `
                    <div class="result">
                        <h3>📊 System Statistics</h3>
                `;
                
                if (data.stats) {
                    for (const [service, stats] of Object.entries(data.stats)) {
                        if (typeof stats === 'object' && stats !== null) {
                            statsHtml += `
                                <h4>${service.replace('_', ' ').toUpperCase()}</h4>
                                <div style="margin-left: 20px; font-family: monospace; font-size: 14px;">
                            `;
                            
                            for (const [key, value] of Object.entries(stats)) {
                                if (key !== 'start_time') {
                                    statsHtml += `<p>${key}: ${value}</p>`;
                                }
                            }
                            
                            statsHtml += '</div>';
                        }
                    }
                }
                
                statsHtml += '</div>';
                resultDiv.innerHTML = statsHtml;
                
            } catch (error) {
                resultDiv.innerHTML = `<div style="color: #e53e3e; padding: 15px; background: #fed7d7; border-radius: 8px;">
                    <strong>❌ Stats Retrieval Failed:</strong> ${error.message}
                </div>`;
            }
        }
        
        // Demo keyboard shortcuts
        document.addEventListener('keydown', async function(e) {
            // Ctrl+S: Toggle demo mode
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault(); // Prevent browser save dialog
                
                try {
                    const response = await fetch(`${API_GATEWAY_URL}/api/toggle-mode`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        currentMode = data.current_mode;
                        
                        // Show mode change notification
                        const resultDiv = document.getElementById('result');
                        resultDiv.style.display = 'block';
                        resultDiv.innerHTML = `
                            <div class="result" style="background: #e7f3ff; border-color: #007bff;">
                                <h3>🎭 Demo Mode Changed</h3>
                                <p><strong>Previous:</strong> ${data.previous_mode}</p>
                                <p><strong>Current:</strong> ${data.current_mode}</p>
                                <p><small>Mode affects query generation behavior in the distributed system</small></p>
                            </div>
                        `;
                        
                        console.log(`🎭 Mode switched to: ${currentMode}`);
                    }
                } catch (error) {
                    console.log('Mode toggle failed:', error);
                }
            }
            
            // Ctrl+D: Create slow database performance demo (like the good trace you're happy with)
            if (e.ctrlKey && e.key === 'd') {
                e.preventDefault();
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<div class="loading">🔵 Creating slow database performance demo...</div>';
                
                try {
                    // Create trace headers for distributed tracing (like the good trace)
                    const headers = createTraceHeaders('slow_db_performance_demo');
                    
                    const response = await fetch(`${API_GATEWAY_URL}/api/demo/slow-db`, {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            ...headers
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.success) {
                        resultDiv.innerHTML = `
                            <div class="result" style="background: #e7f3ff; border-color: #007bff;">
                                <h3>🔵 Slow Database Performance Demo</h3>
                                <p><strong>Operation:</strong> SQLite database performance analysis</p>
                                <p><strong>Duration:</strong> ${data.duration_seconds}s</p>
                                <p><strong>Services:</strong> ${data.performance_analysis.services_involved.join(', ')}</p>
                                <p><strong>Database Operations:</strong> ${data.storage_result.operations_performed} SQLite operations</p>
                                <p><strong>Status:</strong> ✅ Complete with nested SQLite spans</p>
                                <p><small><strong>Trace ID:</strong> ${data.trace_id}</small></p>
                                <p><small><strong>Analysis:</strong> ${data.storage_result.performance_analysis.total_duration}</small></p>
                            </div>
                        `;
                        
                        console.log(`🔵 Slow database demo completed: ${data.trace_id}`);
                    } else {
                        resultDiv.innerHTML = `
                            <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                                <h3>❌ Slow Database Demo Failed</h3>
                                <p>${data.error || 'Unknown error'}</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `
                        <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                            <h3>💥 Network Error:</h3>
                            <p>Failed to create slow database demo. Please check if the distributed system is running.</p>
                        </div>
                    `;
                }
            }
            
            // Ctrl+B: Slow database demo for performance analysis
            if (e.ctrlKey && e.key === 'b') {
                e.preventDefault();
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<div class="loading">🐌 Running slow database operation through distributed system...</div>';
                
                try {
                    // Create trace headers for distributed tracing
                    const headers = createTraceHeaders('slow_db_demo');
                    
                    const response = await fetch(`${API_GATEWAY_URL}/api/demo/slow-db`, {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            ...headers
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.success) {
                        resultDiv.innerHTML = `
                            <div class="result" style="background: #fff3cd; border-color: #ffc107;">
                                <h3>🐌 Slow Database Operation Completed</h3>
                                <p><strong>Duration:</strong> ${data.duration_seconds}s</p>
                                <p><strong>Trace ID:</strong> <code>${data.trace_id}</code></p>
                                <p><strong>Database:</strong> ${data.storage_result.database_system}</p>
                                
                                <h4>📊 Performance Analysis:</h4>
                                <ul>
                                    <li><strong>Total Duration:</strong> ${data.performance_analysis.total_duration}</li>
                                    <li><strong>Services Involved:</strong> ${data.performance_analysis.services_involved.join(' → ')}</li>
                                    <li><strong>Distributed Tracing:</strong> ${data.performance_analysis.distributed_tracing}</li>
                                </ul>
                                
                                <h4>💡 Optimization Recommendations:</h4>
                                <ul>
                                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                                </ul>
                                
                                <h4>📋 Database Results:</h4>
                                <pre>${JSON.stringify(data.storage_result.results, null, 2)}</pre>
                                
                                <p><small><strong>Demo Purpose:</strong> This slow operation demonstrates how distributed tracing helps identify database performance bottlenecks across microservices. Check Coralogix for detailed span analysis!</small></p>
                            </div>
                        `;
                        
                        console.log(`🐌 Slow DB demo completed in ${data.duration_seconds}s (trace: ${data.trace_id})`);
                    } else {
                        resultDiv.innerHTML = `
                            <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                                <h3>❌ Slow Database Demo Failed</h3>
                                <p>${data.error || 'Unknown error occurred'}</p>
                                ${data.trace_id ? `<p><strong>Trace ID:</strong> <code>${data.trace_id}</code></p>` : ''}
                            </div>
                        `;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `
                        <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                            <h3>💥 Network Error:</h3>
                            <p>Failed to run slow database demo: ${error.message}</p>
                            <p><small>Please check if the distributed system is running.</small></p>
                        </div>
                    `;
                }
            }
        });
    </script>
</body>
</html>
    """
    return render_template_string(html_template)

if __name__ == '__main__':
    print("🌐 Starting Distributed Frontend on port 8000...")
    print("   API Gateway: http://localhost:8010")
    print("   Frontend: http://localhost:8020")
    app.run(host='0.0.0.0', port=8020, debug=False)
