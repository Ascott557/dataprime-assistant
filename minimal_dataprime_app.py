#!/usr/bin/env python3
"""
🤖 Minimal DataPrime Assistant with Coralogix Observability

This is a stripped-down version focusing ONLY on what we know works:
- Basic Flask endpoints
- Proven telemetry setup from test_telemetry_integration.py
- Core DataPrime functionality
- Minimal error handling but maximum reliability
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
from opentelemetry import trace

# Environment variable validation
def validate_environment():
    """Validate required environment variables are set."""
    required_vars = ['OPENAI_API_KEY', 'CX_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n🔧 Quick fix:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your API keys")
        print("   3. Restart the application")
        print(f"\nExample .env file:")
        print(f"OPENAI_API_KEY=your-openai-api-key-here")
        print(f"CX_TOKEN=your-coralogix-token-here")
        return False
    
    print("✅ All required environment variables are set")
    return True

# Validate environment before proceeding
if not validate_environment():
    sys.exit(1)

def initialize_telemetry():
    """Initialize telemetry using the EXACT setup that worked in our integration test."""
    try:
        print("🔧 Initializing Coralogix telemetry...")
        
        # Import and setup - exactly like our working integration test
        from llm_tracekit import OpenAIInstrumentor, setup_export_to_coralogix
        
        setup_export_to_coralogix(
            service_name="dataprime_assistant",
            application_name="ai-dataprime",
            subsystem_name="query-generator",
            capture_content=True
        )
        print("✅ Coralogix export configured")
        
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled")
        
        return True
    except Exception as e:
        print(f"❌ Telemetry setup failed: {e}")
        print("⚠️  App will continue without telemetry...")
        return False

def load_dataprime_components():
    """Load only the essential DataPrime components that we know work."""
    try:
        # Add src to path so we can import our working components
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from knowledge_base import DataPrimeKnowledgeBase
        from utils.validation import DataPrimeValidator
        
        knowledge_base = DataPrimeKnowledgeBase()
        validator = DataPrimeValidator()
        
        print("✅ DataPrime components loaded successfully")
        return knowledge_base, validator
    except Exception as e:
        print(f"❌ Failed to load DataPrime components: {e}")
        # Return None values - app will work in basic mode
        return None, None



# Initialize telemetry FIRST
telemetry_enabled = initialize_telemetry()

# Initialize DataPrime components
knowledge_base, validator = load_dataprime_components()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-minimal-app')

# Global stats for basic monitoring + demo mode
app_stats = {
    "queries_processed": 0,
    "successful_queries": 0,
    "errors": 0,
    "start_time": datetime.now().isoformat(),
    "demo_mode": "permissive"  # Default to permissive for demo
}

@app.route('/api/toggle-mode', methods=['POST'])
def toggle_mode():
    """Secret endpoint to toggle between smart and permissive mode for demo."""
    try:
        current_mode = app_stats.get("demo_mode", "permissive")
        new_mode = "smart" if current_mode == "permissive" else "permissive"
        app_stats["demo_mode"] = new_mode
        
        print(f"🎭 [DEMO] Mode switched to: {new_mode}")
        
        return jsonify({
            "success": True,
            "previous_mode": current_mode,
            "current_mode": new_mode,
            "message": f"Demo mode is now {new_mode}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Essential health check endpoint."""
    try:
        status = {
            "status": "healthy",
            "service": "dataprime_assistant",
            "version": "minimal-1.0",
            "telemetry_enabled": telemetry_enabled,
            "dataprime_components": knowledge_base is not None,
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "coralogix_configured": bool(os.getenv('CX_TOKEN')),
            "timestamp": datetime.now().isoformat(),
            "stats": app_stats,
            "demo_mode": app_stats.get("demo_mode", "permissive")
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Core query generation endpoint - minimal but functional."""
    try:
        app_stats["queries_processed"] += 1
        
        # Get user input
        data = request.get_json()
        if not data or 'user_input' not in data:
            app_stats["errors"] += 1
            return jsonify({"error": "Missing 'user_input' in request"}), 400
            
        user_input = data['user_input'].strip()
        if not user_input:
            app_stats["errors"] += 1
            return jsonify({"error": "Empty user input"}), 400
        
        print(f"🔍 Processing query: {user_input}")
        
        # Step 1: Intent classification (if available)
        intent_info = {}
        if knowledge_base:
            try:
                # Access the classifier directly from the knowledge base
                intent_result = knowledge_base.classifier.classify(user_input)
                intent_info = {
                    "intent": intent_result.intent_type.value,
                    "confidence": intent_result.confidence,
                    "keywords": intent_result.keywords_found
                }
                print(f"📊 Intent: {intent_info.get('intent', 'unknown')} (confidence: {intent_result.confidence:.2f})")
            except Exception as e:
                print(f"⚠️ Intent classification failed: {e}")
                intent_info = {"intent": "unknown", "confidence": 0.0}
        
        # Step 2: Generate DataPrime query using OpenAI (DYNAMIC DEMO MODE)
        try:
            # Get current demo mode
            current_mode = app_stats.get("demo_mode", "permissive")
            print(f"🎭 [DEMO] Current mode: {current_mode}")
            
            if current_mode == "smart":
                # SMART MODE: Reject inappropriate queries
                system_prompt = """You are an expert in converting observability questions into query language.

You help users analyze logs, traces, and metrics for system monitoring and troubleshooting.

Generate ONLY the query syntax, no explanations. Use this format:
- source logs [timeframe] | filter [condition] | ...
- Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Fatal'  
- Common fields: $m.severity, $l.subsystemname, $d.response_time
- Time formats: last 1h, last 24h, between timestamps

Examples:
- "Show errors from last hour" → source logs last 1h | filter $m.severity == 'Error'
- "Count by service" → source logs | groupby $l.subsystemname aggregate count()

If the question is not about system observability, logs, errors, or monitoring, respond with: "This question is not related to system observability or log analysis."
"""
            else:
                # PERMISSIVE MODE: Generate queries for everything
                system_prompt = """You are an expert in converting any user question into query language syntax.

Always generate a query using this format, regardless of the topic:
- source logs [timeframe] | filter [condition] | ...
- source spans [timeframe] | filter [condition] | ...
- Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Fatal'  
- Common fields: $m.severity, $l.subsystemname, $d.response_time
- Time formats: last 1h, last 24h, between timestamps

Examples:
- "Show errors from last hour" → source logs last 1h | filter $m.severity == 'Error'
- "Count by service" → source logs | groupby $l.subsystemname aggregate count()
- "What is McDonald's menu?" → source logs | filter $l.restaurant == 'McDonalds' | select menu_items
- "What is Coralogix?" → source logs | filter $l.service_name == 'coralogix' | select description

Generate ONLY the query syntax, no explanations. Make your best attempt to create a query for any input.
"""
            
            user_prompt = user_input  # Clean user input for proper evaluation!
            
            # This OpenAI call will be automatically instrumented by llm_tracekit
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            generated_query = response.choices[0].message.content.strip()
            print(f"✅ Generated query: {generated_query}")
            
            # Add evaluation context to the current span for Coralogix AI Center
            current_span = trace.get_current_span()
            if current_span:
                # Add evaluation-friendly attributes
                current_span.set_attribute("ai.user_query", user_input)
                current_span.set_attribute("ai.generated_response", generated_query) 
                current_span.set_attribute("ai.intent_classification", intent_info.get("intent", "unknown"))
                current_span.set_attribute("ai.confidence_score", intent_info.get("confidence", 0.0))
                
                # Domain-specific context for evaluations
                current_span.set_attribute("business.domain", "observability") 
                current_span.set_attribute("business.use_case", "dataprime_query_generation")
                current_span.set_attribute("business.expected_topics", "logs,traces,metrics,errors,performance")
                
                # Query characteristics for evaluation
                query_complexity = len(generated_query.split("|")) - 1
                current_span.set_attribute("dataprime.query_complexity", query_complexity)
                current_span.set_attribute("dataprime.has_time_filter", "last" in generated_query.lower())
                current_span.set_attribute("demo.mode", current_mode)  # Track demo mode
            
        except Exception as e:
            print(f"❌ OpenAI query generation failed: {e}")
            app_stats["errors"] += 1
            return jsonify({
                "error": "Query generation failed",
                "details": str(e)
            }), 500
        
        # Step 3: Smart validation based on mode
        validation_result = {"is_valid": True, "warnings": []}
        if validator and current_mode == "smart":
            # Only validate strictly in smart mode
            try:
                val_result = validator.validate(generated_query)
                validation_result = {
                    "is_valid": val_result.is_valid,
                    "warnings": [issue.message for issue in val_result.issues if issue.level.value == "warning"],
                    "syntax_score": val_result.syntax_score,
                    "complexity": val_result.complexity_score
                }
                print(f"✅ Validation: {'PASS' if val_result.is_valid else 'FAIL'} (syntax: {val_result.syntax_score:.2f})")
            except Exception as e:
                print(f"⚠️ Validation failed: {e}")
                validation_result = {"is_valid": True, "warnings": [], "error": str(e)}
        else:
            # In permissive mode, assume valid if it looks like DataPrime syntax
            is_dataprime_like = ("source" in generated_query.lower() and 
                               ("|" in generated_query or "filter" in generated_query.lower()))
            validation_result = {
                "is_valid": is_dataprime_like,
                "warnings": [],
                "syntax_score": 0.95 if is_dataprime_like else 0.1,
                "complexity": 0.3
            }
            print(f"✅ Permissive validation: {'PASS' if is_dataprime_like else 'FAIL'}")
        
        # Step 4: Return result
        app_stats["successful_queries"] += 1
        
        result = {
            "success": True,
            "query": generated_query,
            "user_input": user_input,
            "intent": intent_info.get("intent", "unknown"),
            "validation": validation_result,
            "timestamp": datetime.now().isoformat(),
            "telemetry_enabled": telemetry_enabled,
            "evaluation_ready": True,
            "demo_mode": current_mode  # Show current demo mode
        }
        
        print(f"🎉 Query generated successfully!")
        return jsonify(result)
        
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        app_stats["errors"] += 1
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Basic stats endpoint for monitoring."""
    try:
        return jsonify({
            "service": "dataprime_assistant",
            "stats": app_stats,
            "environment": {
                "telemetry_enabled": telemetry_enabled,
                "dataprime_loaded": knowledge_base is not None,
                "openai_key_set": bool(os.getenv('OPENAI_API_KEY')),
                "coralogix_token_set": bool(os.getenv('CX_TOKEN'))
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def web_interface():
    """Minimal web interface for testing."""
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>🤖 DataPrime Query Assistant</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .status { padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .status.ok { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; }
        .query { font-family: 'Courier New', monospace; background: #f1f3f4; padding: 10px; border-radius: 3px; margin: 10px 0; }
        .loading { text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 DataPrime Query Assistant <span id="modeIndicator" style="font-size: 0.5em; margin-left: 10px;">🟠</span></h1>
        
        <div class="demo-info" style="background: #f0f8ff; color: #0d47a1; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #1976d2;">
            <strong>🎯 Try these examples:</strong> "Show me errors from last hour" or "Find slow API calls" - Watch how the system responds to different types of queries!
        </div>
        
        <div class="status {{ 'ok' if telemetry_enabled else 'warning' }}">
            <strong>Status:</strong> 
            Telemetry: {{ '✅ Enabled' if telemetry_enabled else '⚠️ Disabled' }} | 
            DataPrime: {{ '✅ Loaded' if dataprime_loaded else '⚠️ Not loaded' }}
        </div>
        
        <form id="queryForm">
            <div class="form-group">
                <label for="userInput">Enter your question:</label>
                <textarea id="userInput" rows="3" placeholder="Try: 'Show me errors from last hour' or 'Find slow API calls'"></textarea>
            </div>
            <button type="submit">🔍 Generate DataPrime Query</button>
        </form>
        
        <div id="result" style="display: none;"></div>
        
        <div style="margin-top: 30px; font-size: 12px; color: #666; text-align: center;">
            DataPrime Query Assistant | Built with ❤️ for Coralogix Observability | <small>Press Ctrl+S to toggle</small>
        </div>
    </div>

    <script>
        let currentMode = 'permissive'; // Track current mode
        
        // Secret keyboard shortcut: Ctrl+S to toggle mode
        document.addEventListener('keydown', async (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault(); // Prevent browser save dialog
                
                try {
                    const response = await fetch('/api/toggle-mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        currentMode = data.current_mode;
                        
                        // Update the subtle indicator - just a colored circle
                        const indicator = document.getElementById('modeIndicator');
                        if (currentMode === 'smart') {
                            indicator.textContent = '🟢'; // Green circle for strict/smart mode
                        } else {
                            indicator.textContent = '🟠'; // Orange circle for permissive mode
                        }
                        
                        console.log('🎭 Demo mode switched to:', currentMode);
                        
                        // Optional: Brief flash to confirm switch (very subtle)
                        indicator.style.opacity = '1';
                        setTimeout(() => indicator.style.opacity = '0.7', 1000);
                    }
                } catch (error) {
                    console.log('Mode toggle failed:', error);
                }
            }
        });
        
        // Initialize mode indicator
        window.addEventListener('load', () => {
            const indicator = document.getElementById('modeIndicator');
            indicator.textContent = '🟠'; // Start with orange (permissive)
        });
        
        document.getElementById('queryForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const userInput = document.getElementById('userInput').value.trim();
            if (!userInput) {
                alert('Please enter a question!');
                return;
            }
            
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">🔄 Generating query...</div>';
            
            try {
                const response = await fetch('/api/generate-query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_input: userInput })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="result">
                            <h3>✅ Generated DataPrime Query:</h3>
                            <div class="query">${data.query}</div>
                            <p><strong>Intent:</strong> ${data.intent}</p>
                            <p><strong>Valid:</strong> ${data.validation.is_valid ? '✅ Yes' : '❌ No'}</p>
                            ${data.validation.warnings.length > 0 ? '<p><strong>Warnings:</strong> ' + data.validation.warnings.join(', ') + '</p>' : ''}
                            <p><small>Generated at: ${data.timestamp}</small></p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                            <h3>❌ Error:</h3>
                            <p>${data.error}</p>
                            ${data.details ? '<p><small>' + data.details + '</small></p>' : ''}
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="result" style="border-color: #dc3545; background: #f8d7da;">
                        <h3>💥 Network Error:</h3>
                        <p>Failed to connect to the server. Please check if the app is running.</p>
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, 
                                telemetry_enabled=telemetry_enabled, 
                                dataprime_loaded=(knowledge_base is not None))

if __name__ == '__main__':
    print("🚀 Starting Minimal DataPrime Assistant...")
    
    # Check required environment variables
    required_vars = ['OPENAI_API_KEY', 'CX_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("💡 Set these variables before running:")
        for var in missing_vars:
            print(f"   export {var}='your-{var.lower().replace('_', '-')}'")
        sys.exit(1)
    
    print("✅ Environment variables configured")
    print(f"✅ Telemetry: {'Enabled' if telemetry_enabled else 'Disabled'}")
    print(f"✅ DataPrime: {'Loaded' if knowledge_base else 'Basic mode'}")
    print()
    print("🌐 Starting Flask server on http://localhost:8000")
    print("📊 Health check: http://localhost:8000/api/health")
    print("🔍 Query API: POST http://localhost:8000/api/generate-query")
    print()
    
    app.run(
        debug=True,
        host='0.0.0.0', 
        port=8000,
        threaded=True
    ) 