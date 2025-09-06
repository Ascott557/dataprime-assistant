#!/usr/bin/env python3
"""
🌐 API Gateway Service - Clean working version with feedback support
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize telemetry for Coralogix export
def initialize_telemetry():
    """Initialize OpenTelemetry with Coralogix export."""
    try:
        print("🔧 Initializing telemetry for Coralogix export...")
        
        # Import telemetry libraries
        from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        # Setup Coralogix export
        setup_export_to_coralogix(
            service_name="dataprime_distributed_system",
            application_name="ai-dataprime-enterprise", 
            subsystem_name="api-gateway-service",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT', 'https://ingress.coralogix.com/api/v1/otel/v1/traces'),
            capture_content=True
        )
        print("✅ Coralogix export configured")
        
        # Instrument libraries
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled")
        
        RequestsInstrumentor().instrument()
        print("✅ Requests instrumentation enabled")
        
        return True
        
    except Exception as e:
        print(f"❌ Telemetry setup failed: {e}")
        print("⚠️  Service will continue without telemetry export...")
        return False

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
            span.set_attribute("service.name", "api_gateway")
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
            stats = {
                "service": "api_gateway",
                "status": "healthy",
                "requests_processed": gateway_stats["requests"],
                "errors": gateway_stats["errors"],
                "uptime_seconds": int((datetime.now() - gateway_stats["start_time"]).total_seconds()),
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
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize telemetry
    telemetry_enabled = initialize_telemetry()
    
    # Initialize Flask instrumentation
    if telemetry_enabled:
        try:
            from opentelemetry.instrumentation.flask import FlaskInstrumentor
            FlaskInstrumentor().instrument_app(app)
            print("✅ Flask instrumentation enabled")
        except Exception as e:
            print(f"⚠️  Flask instrumentation failed: {e}")
    
    print("🌐 API Gateway starting on port 8010...")
    print(f"   Telemetry enabled: {telemetry_enabled}")
    app.run(host='0.0.0.0', port=8010, debug=False)
