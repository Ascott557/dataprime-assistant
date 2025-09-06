#!/usr/bin/env python3
"""
🌐 API Gateway - Unified Telemetry Version
Uses single global telemetry configuration to ensure proper trace correlation.
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Import global telemetry
from global_telemetry import get_global_tracer, instrument_flask_app, is_telemetry_enabled

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Get the global tracer (same for all services)
tracer = get_global_tracer()

# Service endpoints
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"

# Gateway statistics
gateway_stats = {
    "requests": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def propagate_trace_context(headers=None):
    """Propagate the current trace context to downstream services."""
    if headers is None:
        headers = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "api_gateway",
        "telemetry_enabled": is_telemetry_enabled(),
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Main endpoint for generating DataPrime queries."""
    propagator = TraceContextTextMapPropagator()
    incoming_context = propagator.extract(dict(request.headers))
    
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        gateway_stats["requests"] += 1
        with tracer.start_as_current_span("api_gateway.generate_query_pipeline") as span:
            # Use span attributes to identify the service, not different service names
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("service.name", "dataprime_distributed_system")
            span.set_attribute("operation.name", "generate_query_pipeline")
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                gateway_stats["errors"] += 1
                return jsonify({"success": False, "error": "Missing user_input"}), 400
            
            user_input = data['user_input']
            span.set_attribute("user.input", user_input)
            
            # Call Query Service
            with tracer.start_as_current_span("api_gateway.call_query_service") as query_span:
                query_span.set_attribute("service.component", "api_gateway")
                query_span.set_attribute("downstream.service", "query_service")
                
                headers = propagate_trace_context()
                
                query_response = requests.post(
                    f"{QUERY_SERVICE_URL}/generate",
                    json={"user_input": user_input},
                    headers=headers,
                    timeout=15
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"Query service error: {query_response.text}")
                
                query_result = query_response.json()
                query_span.set_attribute("query.generated", query_result.get("query", ""))
                query_span.set_attribute("query.intent", query_result.get("intent", ""))
            
            # Call Validation Service
            with tracer.start_as_current_span("api_gateway.call_validation_service") as validation_span:
                validation_span.set_attribute("service.component", "api_gateway")
                validation_span.set_attribute("downstream.service", "validation_service")
                
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
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "submit_feedback")
            
            feedback_data = {
                "rating": data.get("rating"),
                "feedback": data.get("feedback", ""),
                "query": data.get("query", ""),
                "timestamp": datetime.now().isoformat(),
                "service": "api_gateway"
            }
            
            span.set_attribute("feedback.rating", feedback_data["rating"])
            span.set_attribute("feedback.has_text", bool(feedback_data["feedback"]))
            
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
            span.set_attribute("service.component", "api_gateway")
            
            stats = {
                "service": "api_gateway",
                "status": "healthy",
                "requests_processed": gateway_stats["requests"],
                "errors": gateway_stats["errors"],
                "uptime_seconds": int((datetime.now() - gateway_stats["start_time"]).total_seconds()),
                "telemetry_enabled": is_telemetry_enabled(),
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("stats.requests_processed", stats["requests_processed"])
            span.set_attribute("stats.errors", stats["errors"])
            
            return jsonify(stats)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

if __name__ == '__main__':
    # Initialize global telemetry FIRST
    from global_telemetry import initialize_global_telemetry
    telemetry_enabled = initialize_global_telemetry()
    
    # Instrument Flask app with global config
    instrument_flask_app(app, "api_gateway")
    
    print("🌐 API Gateway (Unified Telemetry) starting on port 8010...")
    print(f"   Global telemetry enabled: {telemetry_enabled}")
    app.run(host='0.0.0.0', port=8010, debug=False)
