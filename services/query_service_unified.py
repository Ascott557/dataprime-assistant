#!/usr/bin/env python3
"""
🧠 Query Service - Unified Telemetry Version
Uses single global telemetry configuration to ensure proper trace correlation.
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Import global telemetry
from global_telemetry import get_global_tracer, instrument_flask_app, is_telemetry_enabled

# Initialize Flask app
app = Flask(__name__)

# Get the global tracer (same for all services)
tracer = get_global_tracer()

def extract_trace_context():
    """Extract trace context from incoming request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/generate', methods=['POST'])
def generate_query():
    """Generate DataPrime query with unified telemetry."""
    # Extract incoming trace context
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("query_service.generate_query") as span:
            # Use span attributes to identify the service component
            span.set_attribute("service.component", "query_service")
            span.set_attribute("service.name", "dataprime_distributed_system")
            span.set_attribute("operation.name", "generate_dataprime_query")
            
            data = request.get_json()
            user_input = data.get('user_input', '')
            
            span.set_attribute("user.input", user_input)
            
            # Simulate LLM processing time
            time.sleep(0.1)
            
            # Generate query based on input (simplified logic)
            if 'error' in user_input.lower():
                query = "source logs last 1h | filter $m.severity == 'Error'"
                intent = "error_analysis"
                confidence = 0.85
            elif 'performance' in user_input.lower():
                query = "source logs last 1h | filter $d.response_time > 1000"
                intent = "performance_analysis"
                confidence = 0.90
            else:
                query = "source logs last 1h | filter $m.severity in ['Warning', 'Error']"
                intent = "general_analysis"
                confidence = 0.75
            
            result = {
                "success": True,
                "query": query,
                "intent": intent,
                "intent_confidence": confidence,
                "service": "query_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("query.generated", query)
            span.set_attribute("query.intent", intent)
            span.set_attribute("query.confidence", confidence)
            
            return jsonify(result)
            
    except Exception as e:
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        return jsonify({"success": False, "error": str(e)}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "query_service",
        "telemetry_enabled": is_telemetry_enabled(),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Instrument Flask app with global config (no local telemetry init)
    instrument_flask_app(app, "query_service")
    
    print("🧠 Query Service (Unified Telemetry) starting on port 8011...")
    print(f"   Global telemetry enabled: {is_telemetry_enabled()}")
    app.run(host='0.0.0.0', port=8011, debug=False)
