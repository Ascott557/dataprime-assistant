#!/usr/bin/env python3
"""
✅ Validation Service with Coralogix Telemetry
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_telemetry():
    """Initialize OpenTelemetry with Coralogix export."""
    try:
        print("🔧 Validation Service: Initializing telemetry...")
        from llm_tracekit import setup_export_to_coralogix
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        setup_export_to_coralogix(
            service_name="dataprime_distributed_system",
            application_name="ai-dataprime-enterprise", 
            subsystem_name="validation-service",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT', 'https://ingress.coralogix.com/api/v1/otel/v1/traces'),
            capture_content=True
        )
        RequestsInstrumentor().instrument()
        print("✅ Validation Service: Telemetry initialized")
        return True
    except Exception as e:
        print(f"⚠️  Validation Service: Telemetry setup failed: {e}")
        return False

# Initialize telemetry
telemetry_enabled = initialize_telemetry()

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Initialize Flask instrumentation
if telemetry_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        print("✅ Validation Service: Flask instrumentation enabled")
    except Exception as e:
        print(f"⚠️  Validation Service: Flask instrumentation failed: {e}")

def extract_trace_context():
    """Extract trace context from incoming request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/validate', methods=['POST'])
def validate_query():
    """Validate DataPrime query with telemetry."""
    # Extract incoming trace context
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("validation_service.validate_query") as span:
            span.set_attribute("service.name", "validation_service")
            
            data = request.get_json()
            query = data.get('query', '')
            
            span.set_attribute("query.text", query)
            span.set_attribute("operation.name", "validate_dataprime_syntax")
            
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
        "telemetry_enabled": telemetry_enabled,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("✅ Validation Service with Telemetry starting on port 8012...")
    print(f"   Telemetry enabled: {telemetry_enabled}")
    app.run(host='0.0.0.0', port=8012, debug=False)
