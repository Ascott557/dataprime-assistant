#!/usr/bin/env python3
"""
🌐 API Gateway Service - Simple working version for distributed tracing test
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize tracer
tracer = trace.get_tracer(__name__)
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Service endpoints
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"

# Gateway statistics
gateway_stats = {
    "requests": 0,
    "errors": 0,
    "start_time": datetime.now()
}

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Stats tracking
gateway_stats = {
    "requests_processed": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def propagate_trace_context(headers=None):
    """Inject current trace context into headers for downstream services."""
    if headers is None:
        headers = {}
    
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for the API Gateway."""
    with tracer.start_as_current_span("api_gateway.health_check") as span:
        span.set_attribute("service.name", "api_gateway")
        span.set_attribute("service.version", "1.0.0")
        
        time.sleep(0.005)  # 5ms
        
        return jsonify({
            "status": "healthy",
            "service": "api_gateway",
            "version": "1.0.0",
            "stats": gateway_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Main endpoint for query generation - orchestrates the full pipeline."""
    # Extract incoming trace context
    propagator = TraceContextTextMapPropagator()
    incoming_context = propagator.extract(dict(request.headers))
    
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        gateway_stats["requests"] += 1
        with tracer.start_as_current_span("api_gateway.generate_query_pipeline") as span:
            span.set_attribute("service.name", "api_gateway")
            span.set_attribute("operation.name", "generate_query_pipeline")
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                return jsonify({"error": "Missing 'user_input' in request"}), 400
                
            user_input = data['user_input'].strip()
            if not user_input:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty user_input"))
                return jsonify({"error": "Empty user input"}), 400
            
            span.set_attribute("user.input.length", len(user_input))
            span.set_attribute("user.input.query", user_input[:100])
            
            time.sleep(0.008)  # 8ms gateway processing
            
            # Step 1: Generate query via Query Service
            with tracer.start_as_current_span("api_gateway.call_query_service") as query_span:
                headers = propagate_trace_context()
                
                query_response = requests.post(
                    f"{QUERY_SERVICE_URL}/generate",
                    json={"user_input": user_input},
                    headers=headers,
                    timeout=30
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"Query service error: {query_response.text}")
                
                query_result = query_response.json()
                query_span.set_attribute("query.generated", query_result.get("query", "")[:100])
                query_span.set_attribute("query.intent", query_result.get("intent", "unknown"))
            
            # Step 2: Validate query via Validation Service
            with tracer.start_as_current_span("api_gateway.call_validation_service") as validation_span:
                headers = propagate_trace_context()
                
                validation_response = requests.post(
                    f"{VALIDATION_SERVICE_URL}/validate",
                    json={"query": query_result.get("query", "")},
                    headers=headers,
                    timeout=10
                )
                
                if validation_response.status_code != 200:
                    raise Exception(f"Validation service error: {validation_response.text}")
                
                validation_result = validation_response.json()
                validation_span.set_attribute("validation.is_valid", validation_result.get("is_valid", False))
                validation_span.set_attribute("validation.score", validation_result.get("syntax_score", 0))
            
            # Combine results
            final_result = {
                "success": True,
                "query": query_result.get("query", ""),
                "intent": query_result.get("intent", "unknown"),
                "intent_confidence": query_result.get("intent_confidence", 0.0),
                "validation": validation_result,
                "demo_mode": "permissive",
                "services_called": ["query_service", "validation_service"]
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.query_length", len(final_result["query"]))
            
            return jsonify(final_result)
            
    except Exception as e:
        gateway_stats["errors"] += 1
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Handle feedback submission."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        with tracer.start_as_current_span("api_gateway.submit_feedback") as span:
            # Log feedback data (in a real system, you'd store this in a database)
            feedback_data = {
                "rating": data.get("rating"),
                "feedback": data.get("feedback", ""),
                "query": data.get("query", ""),
                "timestamp": datetime.now().isoformat(),
                "service": "api_gateway"
            }
            
            span.set_attribute("feedback.rating", feedback_data["rating"])
            span.set_attribute("feedback.has_text", bool(feedback_data["feedback"]))
            
            # In a real system, you'd store this in a database
            # For now, just log it and return success
            print(f"📝 Feedback received: {feedback_data}")
            
            return jsonify({
                "success": True,
                "message": "Feedback submitted successfully",
                "timestamp": feedback_data["timestamp"]
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        with tracer.start_as_current_span("api_gateway.get_stats") as span:
            stats = {
                "service": "api_gateway",
                "status": "healthy",
                "requests_processed": gateway_stats["requests"],
                "errors": gateway_stats["errors"],
                "uptime_seconds": int((datetime.now() - gateway_stats["start_time"]).total_seconds()),
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("stats.requests", stats["requests_processed"])
            span.set_attribute("stats.errors", stats["errors"])
            
            return jsonify(stats)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

if __name__ == '__main__':
    print("🌐 API Gateway starting on port 8010...")
    app.run(host='0.0.0.0', port=8010, debug=False)
