#!/usr/bin/env python3
"""
✅ Validation Service - Unified Telemetry Version
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

@app.route('/validate', methods=['POST'])
def validate_query():
    """Validate DataPrime query with unified telemetry."""
    # Extract incoming trace context
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("validation_service.validate_query") as span:
            # Use span attributes to identify the service component
            span.set_attribute("service.component", "validation_service")
            span.set_attribute("service.name", "dataprime_distributed_system")
            span.set_attribute("operation.name", "validate_dataprime_syntax")
            
            data = request.get_json()
            query = data.get('query', '')
            
            span.set_attribute("query.text", query)
            
            # Simulate validation processing time
            time.sleep(0.05)
            
            # Simple validation logic
            is_valid = True
            warnings = []
            syntax_score = 0.9
            
            if not query.strip():
                is_valid = False
                syntax_score = 0.0
                warnings.append("Empty query")
            elif 'source' not in query.lower():
                warnings.append("Query should start with 'source'")
                syntax_score = 0.7
            
            result = {
                "success": True,
                "is_valid": is_valid,
                "syntax_score": syntax_score,
                "warnings": warnings,
                "service": "validation_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("validation.is_valid", is_valid)
            span.set_attribute("validation.syntax_score", syntax_score)
            span.set_attribute("validation.warnings_count", len(warnings))
            
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
        "service": "validation_service",
        "telemetry_enabled": is_telemetry_enabled(),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Instrument Flask app with global config (no local telemetry init)
    instrument_flask_app(app, "validation_service")
    
    print("✅ Validation Service (Unified Telemetry) starting on port 8012...")
    print(f"   Global telemetry enabled: {is_telemetry_enabled()}")
    app.run(host='0.0.0.0', port=8012, debug=False)
